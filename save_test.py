"""Autosave and resume: closing the app must not cost the player their run.

A run is written to local storage on a timer, when a chamber is entered, and at
the moment the page is hidden. Reopening must rebuild the same chamber the same
way — same gate, same road, same foes at the same health — and put the hero back
where it stood, still carrying the boons it had taken.
"""
import sys
import time
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:12001/?debug=1"
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
    page.goto(URL, wait_until="load")

    # The menu has no run to continue on a fresh profile.
    page.wait_for_timeout(200)
    check("a fresh install shows no Continue button",
          page.evaluate("() => document.getElementById('resumeBtn').hidden"), True)

    page.click("#playBtn")
    page.wait_for_timeout(400)

    # Walk a little, hurt the hero, kill a foe, then take a boon so there is real
    # progress to lose: position, health, kills and a boon all in the save.
    page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room;
      s.player.x += 120; s.player.y += 90;
      s.hp -= 27; s.kills = 4; s.obols = 33;
    }""")
    expected = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room;
      return { depth: s.depth, hp: s.hp, kills: s.kills, obols: s.obols,
               x: s.player.x, y: s.player.y, seed: r.seed,
               door: r.door, total: r.enemies.length,
               foeHp: r.enemies.map((e) => e.hp),
               foePos: r.enemies.map((e) => [Math.round(e.x), Math.round(e.y)]) };
    }""")

    # Wound one foe so its partial health has to survive the round trip.
    page.evaluate("""() => {
      const r = window.__game.room;
      if (r.enemies[0]) r.enemies[0].hp = Math.max(1, r.enemies[0].hp - 11);
    }""")
    before = page.evaluate("() => window.__game.room.enemies.map((e) => e.hp)")
    page.evaluate("() => window.__game.save()")

    # Read the stored snapshot back and compare the resumed run against that, not
    # against the live state: the game keeps running between these calls, so a foe
    # could land a blow and change the health it holds.
    saved = page.evaluate("() => JSON.parse(localStorage.getItem('ue_run_v1'))")
    expected["hp"] = saved["hp"]
    expected["x"] = saved["px"]
    expected["y"] = saved["py"]
    expected["kills"] = saved["kills"]
    expected["obols"] = saved["obols"]
    expected["total"] = len(saved["enemies"])

    check("the run is written to storage", page.evaluate("() => window.__game.hasSave()"), True)

    # Reload the page entirely, the way reopening the app would.
    page.reload(wait_until="load")
    page.wait_for_timeout(300)
    check("the menu now offers to continue",
          page.evaluate("() => !document.getElementById('resumeBtn').hidden"), True)

    page.click("#resumeBtn")
    page.wait_for_timeout(400)

    got = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room;
      return { mode: g.mode, depth: s.depth, hp: s.hp, kills: s.kills, obols: s.obols,
               x: Math.round(s.player.x), y: Math.round(s.player.y), seed: r.seed,
               doorSide: r.door.side, total: r.enemies.length,
               foeHp: r.enemies.map((e) => e.hp),
               foeKind: r.enemies.map((e) => e.kind) };
    }""")

    check("the game is playable immediately after resume", got["mode"] == "playing", got["mode"])
    check("the same depth comes back", got["depth"] == expected["depth"], got["depth"])
    check("the hero's health comes back", got["hp"] == expected["hp"],
          (got["hp"], expected["hp"]))
    check("kills and obols come back",
          got["kills"] == expected["kills"] and got["obols"] == expected["obols"],
          (got["kills"], got["obols"]))
    check("the hero stands where it was left",
          abs(got["x"] - expected["x"]) <= 2 and abs(got["y"] - expected["y"]) <= 2,
          (got["x"], got["y"], expected["x"], expected["y"]))
    check("the chamber is rebuilt from the same seed", got["seed"] == expected["seed"],
          got["seed"])
    check("the gate is on the same wall", got["doorSide"] == expected["door"]["side"],
          got["doorSide"])
    check("every foe is back", got["total"] == expected["total"],
          (got["total"], expected["total"]))
    check("wounded foes keep their health", got["foeHp"] == before, (got["foeHp"], before))

    # The layout must match exactly, not merely be the same size. Take the
    # dressing of the resumed chamber, reload, resume again, and compare: a seed
    # that replays has to produce the same stones, torches, pillars and road.
    dress_now = page.evaluate("""() => {
      const r = window.__game.room;
      return { torches: r.torches.length, pillars: r.pillars.length,
               vases: r.vases.length, bones: r.bones.length, seed: r.seed,
               pillarSpots: r.pillars.map((p) => [Math.round(p.x), Math.round(p.y)]),
               road: r.road.pts.map((p) => [Math.round(p.x), Math.round(p.y)]) };
    }""")
    page.reload(wait_until="load")
    page.wait_for_timeout(250)
    page.click("#resumeBtn")
    page.wait_for_timeout(350)
    dress_resume = page.evaluate("""() => {
      const r = window.__game.room;
      return { torches: r.torches.length, pillars: r.pillars.length,
               vases: r.vases.length, bones: r.bones.length, seed: r.seed,
               pillarSpots: r.pillars.map((p) => [Math.round(p.x), Math.round(p.y)]),
               road: r.road.pts.map((p) => [Math.round(p.x), Math.round(p.y)]) };
    }""")
    check("the resumed chamber is rebuilt stone for stone",
          dress_resume == dress_now, (dress_resume, dress_now))

    # A brand new run rolls a different chamber, otherwise the seed would not be
    # doing anything and the match above would be meaningless.
    page.evaluate("() => window.__game.start()")
    page.wait_for_timeout(200)
    fresh = page.evaluate("() => window.__game.room.seed")
    check("a new run rolls a different chamber", fresh != dress_now["seed"],
          (fresh, dress_now["seed"]))

    # The HUD carries a Save button, so a player can stop on their own terms
    # without waiting for the next autosave.
    check("the Save button is only in the HUD, not the menu",
          page.evaluate("""() => {
            const b = document.getElementById('saveBtn');
            return b.closest('#hud') === document.getElementById('hud');
          }"""), True)
    page.evaluate("() => window.__game.clearSave()")
    check("clearing the save leaves nothing to continue",
          not page.evaluate("() => window.__game.hasSave()"), True)
    page.click("#saveBtn")
    page.wait_for_timeout(150)
    check("tapping Save writes the run immediately",
          page.evaluate("() => window.__game.hasSave()"), True)
    check("tapping Save says so on screen",
          "saved" in page.evaluate("() => document.getElementById('toast').textContent").lower(),
          page.evaluate("() => document.getElementById('toast').textContent"))

    # A reward screen interrupted mid-choice must come back with the same boons,
    # not a reroll.
    page.evaluate("""() => {
      const r = window.__game.room;
      r.enemies.forEach((e) => { e.x = 9999; });
      r.enemies = [];
      r.projectiles = r.projectiles.filter((x) => x.kind === 'impact' || x.kind === 'debris');
    }""")
    page.wait_for_timeout(300)
    offer = page.evaluate("""() => {
      const cards = [...document.querySelectorAll('#cards .card b')].map((b) => b.textContent);
      return { mode: window.__game.mode, cards };
    }""")
    check("clearing a chamber opens the reward screen with two gods",
          offer["mode"] == "reward" and len(offer["cards"]) == 2, offer)

    page.evaluate("() => window.__game.save()")
    page.reload(wait_until="load")
    page.wait_for_timeout(250)
    page.click("#resumeBtn")
    page.wait_for_timeout(400)
    again = page.evaluate("""() => {
      const cards = [...document.querySelectorAll('#cards .card b')].map((b) => b.textContent);
      return { mode: window.__game.mode, cards };
    }""")
    check("an interrupted boon choice comes back the same",
          again["mode"] == "reward" and again["cards"] == offer["cards"], (again, offer))

    # Taking the god must clear that offer; the slot chooser is what follows, and
    # binding the power is what actually writes it into the run.
    chosen = page.evaluate("""() => {
      const first = document.querySelector('#cards .card');
      first.click();
      const slots = [...document.querySelectorAll('#slots .slot')];
      return { mode: window.__game.mode, slots: slots.length,
               god: first.querySelector('em').textContent };
    }""")
    check("picking a god moves on to the slot chooser",
          chosen["mode"] == "slot" and chosen["slots"] == 3, chosen)

    page.evaluate("() => window.__game.save()")
    page.reload(wait_until="load")
    page.wait_for_timeout(250)
    page.click("#resumeBtn")
    page.wait_for_timeout(400)
    held = page.evaluate("""() => {
      const g = window.__game;
      const slots = [...document.querySelectorAll('#slots .slot')];
      return { mode: g.mode, slots: slots.length, pending: g.state.pendingPower };
    }""")
    check("an interrupted slot choice comes back the same",
          held["mode"] == "slot" and held["slots"] == 3 and held["pending"] is not None, held)

    slotName = page.evaluate("""() => {
      const first = document.querySelector('#slots .slot');
      const name = first.querySelector('b').textContent;
      first.click();
      return name;
    }""")
    page.wait_for_timeout(250)
    after = page.evaluate("""() => {
      const g = window.__game;
      return { mode: g.mode, slots: g.state.slots, offer: g.state.offer,
               pending: g.state.pendingPower, hasSave: g.hasSave() };
    }""")
    bound = [v for v in after["slots"].values() if v]
    check("binding a power fills one slot and clears the choice",
          after["mode"] == "playing" and after["offer"] is None and
          after["pending"] is None and len(bound) == 1 and bound[0]["name"] == slotName, after)

    page.reload(wait_until="load")
    page.wait_for_timeout(250)
    page.click("#resumeBtn")
    page.wait_for_timeout(350)
    replayed = page.evaluate("""() => {
      const g = window.__game;
      return { mode: g.mode, slots: g.state.slots };
    }""")
    check("the bound power is still held after a reopen",
          replayed["mode"] == "playing" and
          [v for v in replayed["slots"].values() if v][0]["name"] == slotName, replayed)

    # Boon effects are stored as numbers, so they must survive too. Give the hero
    # a damage boon and check the number comes back rather than the base value.
    page.evaluate("""() => {
      const g = window.__game;
      g.state.dmg = 61; g.state.reach = 97; g.state.shieldMax = 2; g.state.shield = 2;
      g.save();
    }""")
    page.reload(wait_until="load")
    page.wait_for_timeout(250)
    page.click("#resumeBtn")
    page.wait_for_timeout(300)
    stats = page.evaluate("""() => {
      const s = window.__game.state;
      return { dmg: s.dmg, reach: s.reach, shield: s.shield, shieldMax: s.shieldMax };
    }""")
    check("boon-adjusted stats survive a reopen",
          stats["dmg"] == 61 and stats["reach"] == 97 and stats["shieldMax"] == 2, stats)

    # Death ends the run, so there must be nothing left to continue.
    page.evaluate("""() => {
      const g = window.__game, p = g.state.player;
      g.state.hp = 20;
      // A toothy foe right on top of the hero, so the real contact path kills
      // it rather than a test calling die() directly.
      g.room.enemies.push({ kind: 'shade', x: p.x, y: p.y, r: 30, hp: 9999, max: 9999,
                            speed: 0, dmg: 999, color: '#8f7bd8', atk: 0 });
    }""")
    for _ in range(10):
        page.wait_for_timeout(250)
        # The hero is briefly invulnerable after each blow; clear the guard so the
        # next contact lands and the run can actually end.
        page.evaluate("() => { window.__game.state.inv = 0; }")
        if page.evaluate("() => window.__game.mode") == "dead":
            break
    dead = page.evaluate("""() => ({ mode: window.__game.mode,
                                     hasSave: window.__game.hasSave() })""")
    check("dying ends the run", dead["mode"] == "dead", dead)
    check("dying clears the save so no dead run can be continued", not dead["hasSave"], dead)

    print("page errors:", errors[:5] or "none")
    browser.close()
if failures:
    print("\nSAVE CHECK FAILED:", ", ".join(failures))
    sys.exit(1)
print("\nSAVE CHECK PASSED")
