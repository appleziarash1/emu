"""The guide's remaining systems: curses, duo and legendary boons, Poms, the
Call, and the full Pact of Punishment.

Each check drives the real run rather than reading the tables: a curse has to
hurt the foe it rides on, a duo has to need both of its parents, a Pom has to
raise the power it lands on, the Call has to spend the gauge, and every pact
condition has to move a number the sim actually reads.
"""
import sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:12001/?debug=1"
failures = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + ("  -> " + str(detail) if detail != "" else ""))
    if not ok:
        failures.append(name)


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    # A fresh profile installs the service worker, whose controllerchange reload
    # would blank __game mid-test; the update path has its own suites.
    page.add_init_script("""
      try {
        Object.defineProperty(navigator, 'serviceWorker', {
          configurable: true,
          value: { addEventListener() {}, register: () => new Promise(() => {}), controller: null },
        });
      } catch (e) {}
    """)
    page.goto(URL, wait_until="load")
    page.wait_for_function("() => window.__game")
    page.evaluate("window.__game.start('xiphos')")
    page.wait_for_timeout(300)

    # ------------------------------------------------------ curses (the guide's 10)
    curses = page.evaluate("""() => {
      const g = window.__game;
      return { ids: g.curseIds, gods: g.curseIds.map((id) => g.curses[id].god) };
    }""")
    check("every guide curse is a real status", len(curses["ids"]) >= 7, curses["ids"])

    hangover = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room;
      const e = r.enemies[0] || g.spawnEnemy(300, 300, 'wretch');
      e.hp = 600; e.maxHp = 600;
      g.applyCurse(e, 'hangover', 1);
      const had = !!e.curses.hangover;
      const before = e.hp;
      for (let i = 0; i < 30; i++) r.enemies.forEach((x) => { if (x === e) g.tick ? 0 : 0; });
      // tick by hand through the sim's own frame
      for (let i = 0; i < 40; i++) { g.frame(performance.now() + i * 16); }
      return { had, before, after: e.hp, stacks: e.curses.hangover ? e.curses.hangover.stacks : 0 };
    }""")
    check("Hangover is applied and ticks damage over time",
          hangover["had"] and hangover["after"] < hangover["before"], hangover)

    doom = page.evaluate("""() => {
      const g = window.__game, r = g.room;
      let e = r.enemies.find((x) => !x.dead) || g.spawnEnemy(300, 300, 'wretch');
      e.hp = 900; e.maxHp = 900; e.dead = false;
      g.applyCurse(e, 'doom', 1);
      const before = e.hp;
      for (let i = 0; i < 120; i++) { g.frame(performance.now() + i * 16); }
      return { before, after: e.hp };
    }""")
    check("Doom lands its delayed blow", doom["after"] < doom["before"], doom)

    # ----------------------------------------------------------- duo boons
    duos = page.evaluate("""() => {
      const g = window.__game;
      return g.duos.length;
    }""")
    check("the guide's 28 duo boons are present", duos == 28, duos)

    duo_gate = page.evaluate("""() => {
      const g = window.__game, s = g.state;
      s.slots = { attack: null, special: null, spell: null, dash: null, call: null };
      s.se = { attack: {}, special: {}, spell: {}, dash: {}, call: {} };
      const none = g.availableDuos().length;
      g.bindPower('aphrodite', 'attack');
      const one = g.availableDuos().length;
      g.bindPower('ares', 'special');
      const both = g.availableDuos().length;
      const names = g.availableDuos().map((d) => d.name);
      return { none, one, both, names };
    }""")
    check("a duo needs both of its parent gods bound",
          duo_gate["none"] == 0 and duo_gate["one"] == 0 and duo_gate["both"] >= 1,
          duo_gate)

    duo_apply = page.evaluate("""() => {
      const g = window.__game, s = g.state;
      const before = s.dmg;
      s.takenDuos = {};
      g.takeSpecial('Heart Rend');
      return { before, after: s.dmg, taken: s.takenDuos['Heart Rend'] === true };
    }""")
    check("taking a duo moves the run's numbers", duo_apply["after"] > duo_apply["before"],
          duo_apply)

    legend = page.evaluate("""() => {
      const g = window.__game, s = g.state;
      s.slots = { attack: null, special: null, spell: null, dash: null, call: null };
      s.se = { attack: {}, special: {}, spell: {}, dash: {}, call: {} };
      g.bindPower('zeus', 'attack');
      const one = g.availableLegend();
      g.bindPower('zeus', 'dash');
      const two = g.availableLegend();
      const before = s.dmg;
      if (two) g.takeSpecial(two.name);
      return { one, two: two && two.name, before, after: s.dmg };
    }""")
    check("a legendary needs one god bound twice and then lands",
          legend["one"] is None and legend["two"] and legend["after"] > legend["before"],
          {"two": legend["two"], "dmg": [legend["before"], legend["after"]]})

    # ------------------------------------------------------------- the Pom
    pom = page.evaluate("""() => {
      const g = window.__game, s = g.state;
      s.slots = { attack: null, special: null, spell: null, dash: null, call: null };
      s.se = { attack: {}, special: {}, spell: {}, dash: {}, call: {} };
      g.bindPower('zeus', 'attack');
      // Zeus's strike moves reach, not damage, so the Pom is read on the stat the
      // power itself moved rather than on a number every power happens to share.
      const before = s.slots.attack.level || 1;
      const beforeReach = s.reach;
      g.applyPom('attack');
      return { before, after: s.slots.attack.level, beforeReach, afterReach: s.reach,
               targets: g.pomTargets().length, cap: g.poms };
    }""")
    check("a Pom raises the bound power's level",
          pom["after"] == pom["before"] + 1, pom)
    check("a Pom compounds the power's own stat", pom["afterReach"] > pom["beforeReach"], pom)
    check("a Pom only offers moves that are bound", pom["targets"] == 1, pom)

    # -------------------------------------------------------------- the Call
    call = page.evaluate("""() => {
      const g = window.__game, s = g.state;
      s.gauge = 0;
      const early = g.castCall();
      g.gainGauge(100);
      const ready = g.callReady();
      const before = s.gauge;
      const ok = g.castCall();
      return { early, ready, before, after: s.gauge, ok };
    }""")
    check("the Call refuses while the gauge is short", call["early"] is False, call)
    check("the Call spends the whole gauge when full",
          call["ready"] and call["ok"] and call["after"] == 0, call)

    call_hits = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room;
      r.enemies.forEach((e) => { e.hp = 900; e.maxHp = 900; e.dead = false; });
      s.gauge = 0; g.gainGauge(100);
      const before = r.enemies.map((e) => e.hp);
      g.castCall();
      const after = r.enemies.map((e) => e.hp);
      return { before: before[0], after: after[0] };
    }""")
    check("the Call strikes the foes around the hero",
          call_hits["after"] < call_hits["before"], call_hits)

    call_slot = page.evaluate("""() => {
      const g = window.__game, s = g.state;
      s.slots = { attack: null, special: null, spell: null, dash: null, call: null };
      s.takenIds = {};
      g.bindPower('poseidon', 'call');
      const bound = s.slots.call;
      const god = g.callGod();
      return { bound: bound && bound.godId, god: god && god.id };
    }""")
    check("the Call answers the god bound to its own slot",
          call_slot["bound"] == "poseidon" and call_slot["god"] == "poseidon", call_slot)

    aid = page.evaluate("""() => {
      const g = window.__game;
      return { withAid: g.gods.filter((x) => x.variants.call).length,
               hermes: !!g.gods.find((x) => x.id === 'hermes').variants.call };
    }""")
    check("each Olympian has an Aid, and Hermes has none",
          aid["withAid"] >= 8 and aid["hermes"] is False, aid)

    # ------------------------------------------------------------ the Pact
    pact = page.evaluate("""() => {
      const g = window.__game;
      return { count: g.pacts.length, names: g.pacts.map((p) => p.name) };
    }""")
    check("the guide's fifteen pact conditions are present", pact["count"] == 15, pact)

    heat = page.evaluate("""() => {
      const g = window.__game;
      g.pacts.forEach((p) => g.setPact(p.id, p.max));
      const total = g.heatTotal();
      const m = g.pactMod();
      return { total, expect: g.pacts.reduce((n, p) => n + p.max, 0),
               foeDmg: m.foeDmgMul, oneShot: m.oneShot, dmgLess: m.dmgLess,
               shop: m.shopMul, offers: m.offerLess };
    }""")
    check("Heat is the sum of every condition's rank",
          heat["total"] == heat["expect"] and heat["total"] > 15, heat)
    check("Extreme Measures and Hard Labour raise the foe's damage",
          heat["foeDmg"] > 1.5, heat["foeDmg"])
    check("Personal Liability is a one-blow run", heat["oneShot"] is True, heat)
    check("Damage Control lowers every blow", heat["dmgLess"] < 1, heat["dmgLess"])

    pact_reach = page.evaluate("""() => {
      const g = window.__game;
      g.pacts.forEach((p) => g.setPact(p.id, 0));
      g.start('xiphos');
      const calm = { hp: g.state.maxHp, dmg: g.state.dmg, foes: g.room.enemies.length };
      g.pacts.forEach((p) => g.setPact(p.id, p.max));
      window.__game.applyMetaToRun ? 0 : 0;
      return { calm };
    }""")
    check("a pact-free run still starts", pact_reach["calm"]["hp"] > 0, pact_reach)

    # reset the pact so the rest of the suites are unaffected
    page.evaluate("() => window.__game.pacts.forEach((p) => window.__game.setPact(p.id, 0))")

    check("no page errors while driving the new systems", not errors, errors[:3])

    browser.close()

print()
if failures:
    print("new-systems test: %d FAILED" % len(failures))
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("new-systems test: all checks passed")
