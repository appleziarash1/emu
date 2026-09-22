"""Checks for the boon rarity system, the pre-boss market and boss scaling.

Rarity is read from the DOM the player actually sees, so a card that carries no
label fails here even if the underlying data is right. Boss scaling is measured
by spawning the real bosses and comparing their health, because the curve is the
feature.
"""
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:12001/?debug=1"

failures = []


def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + (("  -> " + str(detail)) if detail else ""))
    if not ok:
        failures.append(label)


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 390, "height": 780}, has_touch=True, is_mobile=True)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL, wait_until="load")
    # The service worker reloads once it takes control; wait that out so the first
    # evaluate is not destroyed mid-navigation.
    page.wait_for_timeout(800)

    tiers = page.evaluate("() => Object.keys(window.__game.rarity)")
    check("the five Hades rarities exist",
          tiers == ["normal", "rare", "epic", "duo", "legendary"], tiers)

    # A deep run must still treat Legendary as the rare prize, so the odds are
    # sampled rather than trusted.
    share = page.evaluate("""() => {
      const g = window.__game;
      const counts = { normal: 0, rare: 0, epic: 0, duo: 0, legendary: 0 };
      let n = 0;
      for (let depth = 1; depth <= 25; depth++) {
        for (let i = 0; i < 400; i++) {
          const r = g.rollRarity(depth);
          counts[r]++; n++;
        }
      }
      const out = {};
      for (const k in counts) out[k] = counts[k] / n;
      return out;
    }""")
    check("legendary is rare at every depth", share["legendary"] < 0.03, share)
    check("normal is the common offer", share["normal"] > share["rare"], share)

    # Walk a real run far enough to clear a chamber, then inspect the cards.
    page.evaluate("""() => {
      const g = window.__game;
      g.start();
      // Clear the chamber by fiat: the assertion is about the reward screen, not
      // about combat, which the other suites cover.
      g.room.enemies.length = 0;
      g.room.cleared = false;
    }""")
    page.wait_for_timeout(300)
    cards = page.evaluate("""() => {
      const g = window.__game;
      if (g.mode !== 'reward') g.openReward();
      const els = [...document.querySelectorAll('#cardsBody .card')];
      return { mode: g.mode, count: els.length,
               tags: els.map((e) => (e.querySelector('.tag') || {}).textContent || ''),
               classes: els.map((e) => e.className) };
    }""")
    check("a cleared chamber shows a card per offered god", cards["count"] == 4, cards["count"])
    labels = {"NORMAL", "RARE", "EPIC", "DUO", "LEGENDARY"}
    check("every card prints a rarity label",
          all(t in labels for t in cards["tags"]), cards["tags"])
    check("no card says SUGGESTED any more",
          not any("SUGGEST" in t.upper() for t in cards["tags"]), cards["tags"])
    check("the shelf shows distinct rarities",
          len(set(cards["tags"])) == len(cards["tags"]), cards["tags"])

    # Pick a card and confirm the chooser carries the same rarity through.
    chosen = page.evaluate("""() => {
      const g = window.__game;
      const card = document.querySelector('#cardsBody .card');
      const tag = card.querySelector('.tag').textContent;
      card.click();
      const slots = [...document.querySelectorAll('#slotsBody .slot')];
      return { mode: g.mode, tag, slots: slots.length,
               slotTags: slots.map((s) => (s.querySelector('.tag') || {}).textContent || ''),
               pending: g.state.pendingRarity };
    }""")
    check("picking a card opens the four-slot chooser", chosen["mode"] == "slot" and chosen["slots"] == 4, chosen)
    check("the chooser keeps the card's rarity",
          all(t == chosen["tag"] for t in chosen["slotTags"]) and chosen["pending"] is not None, chosen)

    # The chosen rarity must actually reach the bound power.
    bound = page.evaluate("""() => {
      const g = window.__game;
      document.querySelector('#slotsBody .slot').click();
      return { rarity: g.state.slots.attack && g.state.slots.attack.rarity,
               boons: g.state.boons.length,
               lastBoon: g.state.boons[g.state.boons.length - 1] };
    }""")
    check("the bound power records its rarity",
          bound["rarity"] == chosen["pending"].lower(), bound)
    check("the boon is recorded on the run", bound["boons"] >= 1 and
          bound["lastBoon"]["rarity"] == bound["rarity"], bound)

    # Rarity must be worth something: a Legendary bind should out-damage a Normal.
    worth = page.evaluate("""() => {
      const g = window.__game;
      const base = () => ({ dmg: 10, reach: 60, knock: 0, splCdMax: 4, specCdMax: 4, dashCdMax: 4 });
      // Both binds must start from a clean run, or the damage left over by the
      // previous bind leaks into the comparison and the check goes flaky.
      g.start();
      g.bindPower('zeus', 'attack', 'normal');
      const norm = g.state.dmg;
      g.start();
      g.bindPower('zeus', 'attack', 'legendary');
      const leg = g.state.dmg;
      return { norm, leg, weaponBase: g.state.weapon.dmgMul };
    }""")
    check("a legendary boon hits harder than a normal one", worth["leg"] > worth["norm"], worth)

    # The market must open on a boss floor, and stay closed on a normal one.
    page.evaluate("""() => { window.__game.start(); window.__game.state.obols = 400; }""")
    page.evaluate("""() => {
      const g = window.__game;
      g.openCorridor(5);
      g.skipCorridor();
    }""")
    page.wait_for_timeout(200)
    bossShop = page.evaluate("""() => {
      const g = window.__game;
      return { mode: g.mode, depth: g.state.depth, isBoss: g.room.isBoss,
               shopVisible: !document.getElementById('shop').hidden };
    }""")
    check("a shop is guaranteed before a boss fight",
          bossShop["isBoss"] and bossShop["mode"] == "shop" and bossShop["shopVisible"], bossShop)

    page.evaluate("() => window.__game.closeShop()")
    page.wait_for_timeout(150)
    after = page.evaluate("""() => {
      const g = window.__game;
      return { mode: g.mode, shopVisible: !document.getElementById('shop').hidden,
               bossShopDepth: g.state.bossShopDepth };
    }""")
    check("closing the boss shop returns to the fight",
          after["mode"] == "playing" and not after["shopVisible"], after)
    check("the boss shop does not reopen for the same floor",
          after["bossShopDepth"] == 5, after)

    # A normal floor must not open the market.
    page.evaluate("""() => {
      const g = window.__game;
      g.openCorridor(6);
      g.skipCorridor();
    }""")
    page.wait_for_timeout(200)
    normal = page.evaluate("""() => {
      const g = window.__game;
      return { mode: g.mode, isBoss: g.room.isBoss,
               shopVisible: !document.getElementById('shop').hidden };
    }""")
    check("a normal floor opens no shop", not normal["isBoss"] and not normal["shopVisible"], normal)

    # Boss scaling: each boss is five times the one before it.
    scale = page.evaluate("""() => {
      const g = window.__game;
      const out = [];
      for (const d of [5, 10, 15, 20, 25]) {
        g.start();
        g.state.depth = d;
        g.room.isBoss = true;
        g.room.enemies.length = 0;
        g.spawnBoss ? g.spawnBoss(d) : null;
        // A boss encounter's health is the sum of its bodies, because a paired
        // boss splits one budget across two of them.
        const bs = g.room.enemies.filter((e) => e.kind === 'boss');
        const b = bs[0];
        out.push({ depth: d, hp: bs.reduce((a, e) => a + e.hp, 0),
                   dmg: b && b.dmg, scale: b && b.scale });
      }
      return out;
    }""")
    by_depth = {r["depth"]: r for r in scale}
    check("depth 10 boss is 5x the depth 5 boss",
          by_depth[10]["hp"] == by_depth[5]["hp"] * 5, scale)
    check("depth 15 boss is 25x the depth 5 boss",
          by_depth[15]["hp"] == by_depth[5]["hp"] * 25, scale)
    check("the boss scale is recorded on the enemy",
          by_depth[25]["scale"] == 625, by_depth[25])
    check("boss damage also climbs with the scale",
          by_depth[15]["dmg"] > by_depth[5]["dmg"], scale)

    print("page errors:", errors[:5] or "none")
    browser.close()

if failures:
    print("\nRARITY CHECK FAILED:", ", ".join(failures))
    sys.exit(1)
print("\nRARITY CHECK PASSED")
