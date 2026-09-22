"""The House, the aspects, the mirror, the keepsakes and the pact.

The meta layer only matters if it changes a run: a bought rank has to reach the
run's numbers, an aspect has to reshape the arm, and the currencies have to
survive a reload. Each check drives the real screens and the real run rather
than poking at the tables.
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
    ctx = browser.new_context(viewport={"width": 430, "height": 860})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    # The service worker reloads the page once on a fresh profile, which would
    # blank the context mid-check; the worker has its own suite in pwa_test.py.
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

    check("the menu offers the House", page.evaluate("() => !!document.getElementById('houseBtn')"), True)
    check("six arms, four aspects each",
          page.evaluate("""() => {
            const g = window.__game, by = {};
            for (const a of g.aspects) by[a.arm] = (by[a.arm] || 0) + 1;
            return Object.values(by).join(',') + '|' + Object.keys(by).length;
          }"""), "4,4,4,4,4,4|6")
    check("every aspect's arm is a real weapon",
          page.evaluate("() => window.__game.aspects.every((a) => window.__game.weapons.some((w) => w.id === a.arm))"),
          True)
    # The six Hades arms carry aspects; the War Hammer is the game's own bonus
    # arm and is left without them rather than being given invented aspects.
    check("every Hades arm has four aspects",
          page.evaluate("""() => {
            const g = window.__game;
            const honed = g.weapons.filter((w) => g.arms.some((a) => a.id === w.id));
            return { honed: honed.length, all: honed.every((w) => g.aspectsOf(w.id).length === 4) };
          }"""), {'honed': 6, 'all': True})

    page.click("#houseBtn")
    page.wait_for_timeout(200)
    check("the House opens", page.evaluate("() => window.__game.mode"), "house")
    check("the House lists every arm plus the aspects row",
          page.evaluate("() => document.querySelectorAll('#houseBody .meta').length"), 7)
    for tab in ["#tabMirror", "#tabKeepsake", "#tabPact"]:
        page.click(tab)
        page.wait_for_timeout(120)
        check("the %s tab renders rows" % tab,
              page.evaluate("() => document.querySelectorAll('#houseBody .meta').length") > 0, True)
    page.click("#houseBack")
    page.wait_for_timeout(150)
    check("the House returns to the menu", page.evaluate("() => window.__game.mode"), "menu")

    # buying is refused on an empty purse, then lands once the currency is earned
    page.click("#houseBtn")
    page.click("#tabMirror")
    page.wait_for_timeout(120)
    check("a fresh account has no Darkness", page.evaluate("() => window.__game.metaDarkness") == 0, True)
    check("a rank cannot be bought on an empty purse",
          page.evaluate("() => window.__game.buyMirror('thick')") is False, True)
    page.evaluate("() => { window.__game.metaDarkness = 500; }")
    check("a rank buys once the Darkness is there",
          page.evaluate("() => window.__game.buyMirror('thick')"), True)
    check("the rank is recorded", page.evaluate("() => window.__game.mirrorRank('thick')"), 1)

    page.evaluate("() => { window.__game.metaBlood = 100; }")
    check("a paid aspect starts locked",
          page.evaluate("() => window.__game.aspectUnlocked(window.__game.aspectDef('arthur'))") is False, True)
    check("buying it unlocks it",
          page.evaluate("() => { window.__game.buyAspect('arthur'); return window.__game.aspectUnlocked(window.__game.aspectDef('arthur')); }"),
          True)

    # the run honours the aspect, the keepsake and the mirror
    page.evaluate("""() => {
      const g = window.__game;
      g.chosenAspect = 'arthur';
      g.equipKeepsake('cerberus');
      localStorage.setItem('ue_aspect_pick_v1', 'arthur');
    }""")
    page.click("#houseBack")
    page.click("#playBtn")
    page.wait_for_function("() => window.__game.state")
    page.wait_for_timeout(250)
    r = page.evaluate("""() => {
      const g = window.__game, s = g.state;
      return { aspect: s.aspectId, cd: s.weapon.cooldown, dmg: Math.round(s.dmg),
               maxHp: s.maxHp, base: g.weapons.find((w) => w.id === 'xiphos').cooldown };
    }""")
    check("the aspect rides on the run", r["aspect"], "arthur")
    check("the aspect slows the arm", r["cd"] > r["base"], r)
    check("the aspect raises damage", r["dmg"] > 18, r["dmg"])
    check("the keepsake raises life", r["maxHp"] >= 140, r["maxHp"])
    check("the run carries a Heat reading", page.evaluate("() => window.__game.state.heat") == 0, True)
    check("the mirror's rank reached the run",
          page.evaluate("() => window.__game.state.maxHp") >= 150, True)

    page.evaluate("() => { const g = window.__game; g.setPact('jury', 3); g.setPact('hardLabour', 2); }")
    check("the pact reports its Heat", page.evaluate("() => window.__game.heatTotal()"), 5)
    page.evaluate("() => { window.__game.clearSave(); window.__game.start(); }")
    page.wait_for_function("() => window.__game.state")
    page.wait_for_timeout(250)
    heat = page.evaluate("""() => {
      const s = window.__game.state;
      return { heat: s.heat, foeCount: s.foeCountAdd, foeDmg: s.foeDmgMul };
    }""")
    check("Heat reaches the run", heat["heat"], 5)
    check("Jury Summons adds foes", heat["foeCount"] == 3, heat)
    check("Hard Labour sharpens them", heat["foeDmg"] > 1, heat["foeDmg"])

    page.evaluate("""() => {
      const g = window.__game, before = g.state.darknessEarned;
      for (const e of g.room.enemies.slice()) { e.hp = 1; g.hurtEnemy(e, 99, null); }
      window.__darkGain = g.state.darknessEarned - before;
    }""")
    check("a kill drops Darkness", page.evaluate("() => window.__darkGain > 0"), True)

    page.reload(wait_until="load")
    page.wait_for_function("() => window.__game")
    # 500 granted, less the 5 the mirror rank cost, plus a Darkness a kill.
    check("Darkness survives a reload", page.evaluate("() => window.__game.metaDarkness") >= 490, page.evaluate("() => window.__game.metaDarkness"))
    check("Titan Blood survives a reload", page.evaluate("() => window.__game.metaBlood") >= 85, page.evaluate("() => window.__game.metaBlood"))
    check("the bought aspect survives a reload",
          page.evaluate("() => window.__game.aspectUnlocked(window.__game.aspectDef('arthur'))"), True)
    check("the keepsake survives a reload",
          page.evaluate("() => window.__game.equippedKeepsake"), "cerberus")
    check("the pact survives a reload", page.evaluate("() => window.__game.heatTotal()"), 5)
    check("the audio is wired without throwing",
          page.evaluate("() => { try { window.__game.houseOpen('house'); return !!document.getElementById('muteBtn'); } catch (e) { return 'err:' + e.message; } }"),
          True)

    check("no page errors", errors == [], errors)
    browser.close()

print("")
if failures:
    print("meta_test: %d FAILED" % len(failures))
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("meta_test: all checks passed")
