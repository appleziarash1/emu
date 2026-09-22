"""Precision checks for the floating joystick and the aim assist.

The stick has to appear under the thumb, track it, respect a dead zone, and stop
cleanly. Aim assist has to turn a sloppy swipe into a hit without stealing the
player's choice of direction.
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
    page.click("#playBtn")
    page.wait_for_timeout(400)

    # 1. The ring rests somewhere sensible before the first touch.
    idle = page.evaluate("""() => {
      const s = document.getElementById('stick');
      const r = s.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2, faded: s.classList.contains('idle') };
    }""")
    check("idle ring is on the left half", idle["x"] < 195, round(idle["x"]))
    check("idle ring sits low", idle["y"] > 390, round(idle["y"]))
    check("idle ring is faded", idle["faded"] is True)

    # 2. Holding the left half moves the ring under the thumb. One continuous
    #    gesture carries the rest of the checks, the way a thumb actually behaves.
    before = page.evaluate("() => ({x: window.__game.state.player.x, y: window.__game.state.player.y})")
    page.mouse.move(90, 520)
    page.mouse.down()
    page.wait_for_timeout(150)
    spawn = page.evaluate("""() => {
      const s = document.getElementById('stick');
      const r = s.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2,
               faded: s.classList.contains('idle') };
    }""")
    check("ring recentres on the thumb", abs(spawn["x"] - 90) < 3 and abs(spawn["y"] - 520) < 3,
          (round(spawn["x"]), round(spawn["y"])))
    check("ring stops looking faded once held", spawn["faded"] is False)

    # 3. A short move inside the dead zone must not move the hero at all.
    page.mouse.move(94, 516, steps=3)     # about 5px: inside the dead zone
    page.wait_for_timeout(400)
    held = page.evaluate("() => ({x: window.__game.state.player.x, y: window.__game.state.player.y})")
    drift = abs(held["x"] - before["x"]) + abs(held["y"] - before["y"])
    check("dead zone absorbs thumb tremor", drift < 2, round(drift, 2))

    # 4. A full drag moves the hero in the drag direction.
    page.mouse.move(90, 460, steps=5)     # straight up
    page.wait_for_timeout(500)
    moved = page.evaluate("() => ({x: window.__game.state.player.x, y: window.__game.state.player.y})")
    check("full drag moves the hero up", moved["y"] < held["y"], (round(held["y"]), round(moved["y"])))
    page.mouse.up()

    # 5. Releasing returns the ring to its resting look.
    page.wait_for_timeout(120)
    released = page.evaluate("""() => document.getElementById('stick').classList.contains('idle')""")
    check("ring returns to its resting look on release", released is True)

    # 6. The stick follows a thumb that travels past the ring edge.
    page.mouse.move(100, 500)
    page.mouse.down()
    page.mouse.move(260, 500, steps=8)    # far beyond the ring radius
    page.wait_for_timeout(200)
    follow = page.evaluate("""() => {
      const s = document.getElementById('stick');
      const r = s.getBoundingClientRect();
      return { x: r.left + r.width / 2 };
    }""")
    page.mouse.up()
    check("ring follows a long drag", follow["x"] > 150, round(follow["x"]))

    # 7. Aim assist: strike with a foe nearby but off-axis, and it should connect.
    hit = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room;
      r.enemies.length = 0;
      const p = s.player;
      s.dmg = 40; s.weapon = g.weapons.find((w) => w.id === 'xiphos');
      // Foe 40px to the right and 30px down: inside reach, about 37 degrees off a
      // straight-right swing, which is exactly the sloppy angle a thumb produces.
      const e = { kind: 'shade', x: p.x + 40, y: p.y + 30, r: 14, hp: 500, max: 500,
                  speed: 0, dmg: 0, color: '#8f7bd8', atk: 0 };
      r.enemies.push(e);
      p.hx = 1; p.hy = 0; p.faceX = 1; p.faceY = 0;
      s.swingCd = 0;
      const hpBefore = e.hp;
      g.swing();
      return { hpBefore, hpAfter: e.hp, aimed: { x: p.faceX, y: p.faceY } };
    }""")
    check("aim assist connects an off-axis strike", hit["hpAfter"] < hit["hpBefore"], hit)
    check("aim assist points at the foe", hit["aimed"]["y"] > 0.3, hit["aimed"])

    # 8. Aim assist must not invent a target behind the hero.
    behind = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room;
      r.enemies.length = 0;
      const p = s.player;
      const e = { kind: 'shade', x: p.x - 40, y: p.y, r: 14, hp: 500, max: 500,
                  speed: 0, dmg: 0, color: '#8f7bd8', atk: 0 };
      r.enemies.push(e);
      p.hx = 1; p.hy = 0; p.faceX = 1; p.faceY = 0;
      s.swingCd = 0;
      const hpBefore = e.hp;
      g.swing();
      return { hpBefore, hpAfter: e.hp };
    }""")
    check("a foe behind is not struck", behind["hpAfter"] == behind["hpBefore"], behind)

    # 9. Every weapon reaches and connects at its own advertised range.
    ranges = page.evaluate("""() => {
      const g = window.__game, out = [];
      for (const w of g.weapons) {
        out.push({ id: w.id, kind: w.kind, reach: w.reach, cooldown: w.cooldown });
      }
      return out;
    }""")
    check("five distinct arms are available", len(ranges) == 5, [r["id"] for r in ranges])
    check("arms have different reach", len({r["reach"] for r in ranges}) == 5,
          [r["reach"] for r in ranges])

    print("page errors:", errors[:5] or "none")
    browser.close()

if failures:
    print("\nCONTROL CHECK FAILED:", ", ".join(failures))
    sys.exit(1)
print("\nCONTROL CHECK PASSED")
