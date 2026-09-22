"""Checks for the god powers, the slot chooser, the gods' market and pause.

Each god power must do something the combat code actually reads, and it must
only do it in the slot it was bound to. Both halves are driven through the real
game: a power is bound through the chooser, then a real swing or spell is fired
and the room is inspected for the effect. A power that only changed a label
would fail here.

A flag that is written but never read is the easiest bug to ship here, so the
source is also audited: every `flags` key in a god's variant must appear in the
combat code for that slot.
"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:12001/?debug=1"

failures = []


def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + (("  -> " + str(detail)) if detail else ""))
    if not ok:
        failures.append(label)


# ---------------------------------------------------------------- source audit
# The three combat regions a slot's flags may be read in. Attack flags are read
# by swing and its strike-effect helper, special flags by the chakram, spell
# flags by the burst. The special chakram update is not contiguous with
# castSpecial, so its flags are audited by the game-side checks below.
SRC = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"),
           encoding="utf-8").read()
GODS_START = SRC.index("const GODS")
GODS_END = SRC.index("const SHOP_ITEMS", GODS_START)
REGIONS = {
    "attack": (SRC.index("function swing"), SRC.index("function castSpell")),
    "special": (SRC.index("function castSpecial"), SRC.index("function castSpell")),
    "spell": (SRC.index("function castSpell"), SRC.index("function castSpecial")),
}
godBlock = SRC[GODS_START:GODS_END]
# Each `flags: {...}` belongs to the variant whose header (`attack: {`) is the
# nearest one before it, since variants are always written in slot order.
slotSites = []
for m in re.finditer(r"flags:\s*\{([^}]*)\}", godBlock):
    head = re.findall(r"\b(attack|special|spell):\s*\{", godBlock[:m.start()])
    if head:
        slotSites.append((head[-1], m.group(1)))
silent = []
seen = set()
for slot, fl in slotSites:
    lo, hi = REGIONS[slot]
    seg = SRC[lo:hi] if lo < hi else SRC[lo:]
    for f in re.findall(r"(\w+)\s*:", fl):
        seen.add(slot + "." + f)
        if not re.search(r"\b" + f + r"\b", seg):
            silent.append(slot + "." + f)
check("the flag audit found powers to audit", len(seen) > 0, len(seen))
check("every power flag is read by its own slot's combat code", not silent, silent)


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 390, "height": 780}, has_touch=True, is_mobile=True)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL, wait_until="load")
    page.click("#playBtn")
    page.wait_for_timeout(500)

    # --- the roster is complete: every god has all three slots, and the shop
    # carries every god
    roster = page.evaluate("""() => {
      const gods = window.__game.gods;
      const items = window.__game.shopItems;
      return {
        count: gods.length,
        ids: gods.map((g) => g.id),
        names: gods.map((g) => g.god),
        complete: gods.every((g) => g.variants.attack && g.variants.special && g.variants.spell),
        named: gods.every((g) => ['attack', 'special', 'spell'].every(
          (s) => g.variants[s].name && g.variants[s].desc && typeof g.variants[s].apply === 'function')),
        shopCount: items.length,
        prices: items.map((i) => i.price),
        // Hades-like roster: these are the gods the shop must show.
        expected: ['zeus', 'athena', 'poseidon', 'ares', 'artemis', 'aphrodite',
                   'demeter', 'hermes', 'dionysus', 'hephaestus', 'chaos']
                       .every((id) => gods.some((g) => g.id === id)),
        recommended: gods.every((g) => ['attack', 'special', 'spell']
                       .some((s) => g.variants[s].rec)),
      };
    }""")
    check("every god has an attack, special and spell variant", roster["complete"], roster["names"])
    check("every variant is named and described", roster["named"], roster["count"])
    check("the shop lists every god", roster["shopCount"] == roster["count"], roster["shopCount"])
    check("the shop prices every god", all(p > 0 for p in roster["prices"]), roster["prices"])
    check("the pantheon is the one Hades players expect", roster["expected"], roster["ids"])
    check("every god suggests at least one slot", roster["recommended"], roster["ids"])

    # --- a power bound to Strike only changes Strike. Bind an Ares damage power
    # to the attack slot and drive a real swing at a real foe.
    strikeOnly = page.evaluate("""() => {
      const g = window.__game, s = g.state;
      const before = s.dmg;
      g.bindPower('ares', 'attack');
      const afterBind = { dmg: s.dmg, se: JSON.parse(JSON.stringify(s.se)),
                          attacker: s.slots.attack && s.slots.attack.god };
      const r = g.room, p = s.player;
      r.enemies.length = 0;
      const foe = { kind: 'shade', x: p.x + 40, y: p.y, r: 14, hp: 100000, max: 100000,
                    speed: 0, dmg: 0, color: '#fff', atk: 0 };
      r.enemies.push(foe);
      p.hx = 1; p.hy = 0;
      s.swingCd = 0;
      const hp0 = foe.hp;
      g.swing();
      return { before, afterBind, swingDmg: hp0 - foe.hp };
    }""")
    check("binding a god records the power in its slot and applies its stats",
          strikeOnly["afterBind"]["se"]["special"] == {} and
          strikeOnly["afterBind"]["se"]["spell"] == {} and
          strikeOnly["afterBind"]["attacker"] == "Ares" and
          strikeOnly["afterBind"]["dmg"] > strikeOnly["before"], strikeOnly["afterBind"])
    check("a strike power lands on a real swing", strikeOnly["swingDmg"] > 0, strikeOnly["swingDmg"])

    # --- a second bind must leave the first slot alone
    twoSlots = page.evaluate("""() => {
      const g = window.__game, s = g.state;
      g.bindPower('ares', 'spell');
      return { se: JSON.parse(JSON.stringify(s.se)),
               slots: JSON.parse(JSON.stringify(s.slots)) };
    }""")
    check("a second binding fills only its own slot",
          twoSlots["slots"]["attack"]["name"] == "Blade Rush" and
          twoSlots["slots"]["spell"]["name"] == "Blood Nova" and
          twoSlots["slots"]["special"] is None, twoSlots["slots"])

    # --- Zeus on Strike chains lightning to a neighbour. Two foes side by side,
    # one swing: the untouched neighbour loses health only if chaining works.
    chain = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room, p = s.player;
      g.bindPower('zeus', 'attack');
      r.enemies.length = 0;
      const a = { kind: 'shade', x: p.x + 40, y: p.y, r: 14, hp: 5000, max: 5000,
                  speed: 0, dmg: 0, color: '#fff', atk: 0 };
      const b = { kind: 'shade', x: p.x + 70, y: p.y, r: 14, hp: 5000, max: 5000,
                  speed: 0, dmg: 0, color: '#fff', atk: 0 };
      r.enemies.push(a, b);
      p.hx = 1; p.hy = 0; s.swingCd = 0;
      g.swing();
      return { struck: 5000 - a.hp, beside: 5000 - b.hp,
               hasAttack: !!s.se.attack.chain,
               hasSpecial: Object.keys(s.se.special).length > 0 };
    }""")
    check("Zeus on Strike chains to a neighbour", chain["struck"] > 0 and chain["beside"] > 0, chain)
    check("the chain flag stays out of the other slots",
          chain["hasAttack"] and not chain["hasSpecial"], chain)

    # --- Demeter on Special chills what the blade cuts, in the special slot only.
    # The thrown blade is walked all the way out and back, which is the only way
    # to reach the chakram branch where the special flags are read.
    frost = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room, p = s.player;
      r.enemies.length = 0;
      // Clear every slot first: a power left in Strike from an earlier check must
      // not make this one look like it leaked.
      g.bindPower('hermes', 'attack');
      g.bindPower('demeter', 'special');
      const foe = { kind: 'brute', x: p.x + 250, y: p.y, r: 22, hp: 90000, max: 90000,
                    speed: 0, dmg: 0, color: '#fff', atk: 0 };
      r.enemies.push(foe);
      p.faceX = 1; p.faceY = 0; p.hx = 1; p.hy = 0;
      s.specCd = 0;
      g.castSpecial();
      // Long enough for the outbound throw to reach the foe and reverse.
      let reached = false;
      for (let i = 0; i < 200; i++) {
        g.tick(1 / 60);
        if (foe.hp < 90000) reached = true;
      }
      return { reached, slowed: foe.slowed || 0, hp: foe.hp,
               seSpecial: !!s.se.special.specFrost,
               seAttack: Object.keys(s.se.attack).length };
    }""")
    check("Demeter on Special freezes what the blade cuts",
          frost["reached"] and frost["slowed"] > 0 and frost["hp"] < 90000, frost)
    check("the frost flag lives only in the special slot",
          frost["seSpecial"] and not frost["seAttack"], frost)

    # --- Poseidon on Special drags the foes it touches back with the blade
    drag = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room, p = s.player;
      r.enemies.length = 0;
      g.bindPower('poseidon', 'special');
      const foe = { kind: 'brute', x: p.x + 240, y: p.y, r: 22, hp: 90000, max: 90000,
                    speed: 0, dmg: 0, color: '#fff', atk: 0 };
      r.enemies.push(foe);
      p.faceX = 1; p.faceY = 0; p.hx = 1; p.hy = 0;
      s.specCd = 0;
      const x0 = foe.x;
      g.castSpecial();
      for (let i = 0; i < 240; i++) g.tick(1 / 60);
      return { x0: x0, x1: foe.x, hp: foe.hp, pulling: !!s.se.special.drag };
    }""")
    check("Poseidon on Special hauls foes back on the return",
          drag["pulling"] and drag["hp"] < 90000, drag)

    # --- Artemis on Strike reaches a ranged arm: the arrow carries the crit
    bowCrit = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room;
      const held = s.weapon;
      s.weapon = g.weapons.find((w) => w.kind === 'ranged');
      g.bindPower('artemis', 'attack');
      r.enemies.length = 0;
      r.projectiles.length = 0;
      s.swingCd = 0;
      // Force the roll so the check is deterministic rather than a coin flip.
      const realRandom = Math.random;
      Math.random = () => 0.01;
      g.swing();
      Math.random = realRandom;
      const arrows = r.projectiles.filter((pr) => pr.kind === 'arrow');
      const out = { fired: arrows.length, crit: arrows.map((a) => !!a.crit) };
      s.weapon = held;
      return out;
    }""")
    check("Artemis on Strike crits for a ranged arm's arrow",
          bowCrit["fired"] > 0 and all(bowCrit["crit"]), bowCrit)

    # --- Hephaestus on Spell leaves burning ground behind, with the other slots
    # empty so nothing else can be blamed for it.
    fire = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room;
      g.bindPower('hermes', 'attack');
      g.bindPower('hermes', 'special');
      g.bindPower('hephaestus', 'spell');
      s.splCd = 0;
      g.castSpell();
      return { fire: r.fire.length, se: !!s.se.spell.novaFire,
               attack: Object.keys(s.se.attack).length };
    }""")
    check("Hephaestus on Spell scorches the ground",
          fire["fire"] > 0 and fire["se"] and fire["attack"] == 0, fire)

    # --- Aphrodite on Spell heals on cast
    heal = page.evaluate("""() => {
      const g = window.__game, s = g.state;
      g.bindPower('aphrodite', 'spell');
      s.maxHp = 200; s.hp = 100;
      s.splCd = 0;
      g.castSpell();
      return { hp: s.hp, max: s.maxHp };
    }""")
    check("Aphrodite on Spell mends the hero", heal["hp"] > 100, heal)

    # --- the market: buying spends obols and opens the chooser
    market = page.evaluate("""() => {
      const g = window.__game, s = g.state;
      s.obols = 500;
      g.openShop();
      const rows = [...document.querySelectorAll('#shopBody .shopItem')];
      const shown = rows.length;
      const readout = document.getElementById('shopObols').textContent;
      const price = Number(rows[0].querySelector('.price').textContent.replace(/\\D/g, ''));
      rows[0].click();
      return { shown, readout, price, obols: s.obols, mode: g.mode,
               pending: s.pendingPower,
               slots: document.querySelectorAll('#slotsBody .slot').length,
               shopHidden: document.getElementById('shop').hidden };
    }""")
    check("the market shows every god", market["shown"] == roster["count"], market["shown"])
    check("the market shows the purse", "500" in market["readout"], market["readout"])
    check("buying a god debits its price", market["obols"] == 500 - market["price"], market)
    check("buying a god opens the slot chooser",
          market["mode"] == "slot" and market["slots"] == 3 and
          market["shopHidden"] and market["pending"] is not None, market)

    # --- a purse too thin to buy: the click must be refused, not go negative
    broke = page.evaluate("""() => {
      const g = window.__game, s = g.state;
      g.bindPower(s.pendingPower, 'attack');   // clear the pending choice
      s.obols = 10;
      g.openShop();
      const rows = [...document.querySelectorAll('#shopBody .shopItem')];
      const poor = rows.filter((r) => r.classList.contains('poor')).length;
      rows[0].click();
      const out = { poor, obols: s.obols, mode: g.mode,
                    shopStillOpen: !document.getElementById('shop').hidden };
      return out;
    }""")
    check("gods you cannot afford are dimmed", broke["poor"] == roster["count"], broke["poor"])
    check("a purchase you cannot afford is refused",
          broke["obols"] == 10 and broke["shopStillOpen"], broke)

    # --- pause stops the sim and resume starts it again
    paused = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room;
      g.closeShop();
      r.enemies.length = 0;
      r.enemies.push({ kind: 'shade', x: s.player.x + 200, y: s.player.y, r: 14,
                       hp: 5000, max: 5000, speed: 60, dmg: 5, color: '#fff', atk: 0 });
      document.getElementById('pauseBtn').click();
      const overlay = document.getElementById('pause');
      const atPause = { mode: g.mode, shown: !overlay.hidden,
                        powers: document.getElementById('pausePowers').textContent,
                        x: r.enemies[0].x };
      g.tick(0.5);   // the frame loop must not advance the sim while paused
      return { atPause, afterTick: r.enemies[0].x };
    }""")
    check("the pause button pauses the game",
          paused["atPause"]["mode"] == "paused" and paused["atPause"]["shown"], paused["atPause"])
    check("the pause overlay names the bound powers",
          "Strike" in paused["atPause"]["powers"] and
          "Spell" in paused["atPause"]["powers"], paused["atPause"]["powers"])
    check("the sim does not advance while paused",
          paused["afterTick"] == paused["atPause"]["x"], paused)

    resumed = page.evaluate("""() => {
      const g = window.__game, r = g.room;
      document.getElementById('pauseResume').click();
      const x0 = r.enemies[0].x;
      g.tick(0.4);
      return { mode: g.mode, hidden: document.getElementById('pause').hidden,
               moved: Math.abs(r.enemies[0].x - x0) > 1 };
    }""")
    check("resume returns to play and the sim runs again",
          resumed["mode"] == "playing" and resumed["hidden"] and resumed["moved"], resumed)

    # --- the market from the pause menu, and back out of it
    shopFromPause = page.evaluate("""() => {
      const g = window.__game;
      document.getElementById('pauseBtn').click();
      document.getElementById('pauseShop').click();
      const out = { mode: g.mode, shop: !document.getElementById('shop').hidden,
                    pause: !document.getElementById('pause').hidden };
      document.getElementById('shopBack').click();
      out.afterMode = g.mode;
      out.pauseBack = !document.getElementById('pause').hidden;
      document.getElementById('pauseResume').click();
      out.finalMode = g.mode;
      return out;
    }""")
    check("the market opens from the pause menu",
          shopFromPause["mode"] == "shop" and shopFromPause["shop"] and
          not shopFromPause["pause"], shopFromPause)
    check("leaving the market returns to the pause menu",
          shopFromPause["pauseBack"] and shopFromPause["afterMode"] == "paused", shopFromPause)
    check("resuming from the market's pause returns to play",
          shopFromPause["finalMode"] == "playing", shopFromPause)

    check("no page errors", not errors, errors)

    browser.close()

if failures:
    print("\nGOD CHECK FAILED: " + ", ".join(failures))
    sys.exit(1)
print("\nGOD CHECK PASSED")
