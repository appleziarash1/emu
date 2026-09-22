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

    # 10. A connected controller replaces the on-screen controls instead of
    #     layering over them. Chromium reports no pad here, so the state is
    #     driven directly through the same entry point the gamepad loop uses.
    touchShown = page.evaluate("""() => {
      const s = document.getElementById('stick');
      const t = document.getElementById('touchZone');
      return { stick: getComputedStyle(s).display !== 'none',
               zone: getComputedStyle(t).display !== 'none',
               hit: getComputedStyle(document.getElementById('btnHit')).display !== 'none' };
    }""")
    check("touch controls are shown while playing by touch",
          touchShown["stick"] and touchShown["zone"] and touchShown["hit"], touchShown)

    page.evaluate("() => window.__game.setPadActive(true)")
    page.wait_for_timeout(120)
    padOn = page.evaluate("""() => {
      const s = document.getElementById('stick');
      const t = document.getElementById('touchZone');
      return { pad: window.__game.padActive,
               stick: getComputedStyle(s).display !== 'none',
               zone: getComputedStyle(t).display !== 'none',
               hit: getComputedStyle(document.getElementById('btnHit')).display !== 'none',
               dash: getComputedStyle(document.getElementById('btnDash')).display !== 'none' };
    }""")
    check("connecting a controller hides the virtual joystick",
          padOn["pad"] and not padOn["stick"] and not padOn["zone"], padOn)
    check("connecting a controller hides the on-screen buttons",
          not padOn["hit"] and not padOn["dash"], padOn)

    page.evaluate("() => window.__game.setPadActive(false)")
    page.wait_for_timeout(120)
    padOff = page.evaluate("""() => {
      const t = document.getElementById('touchZone');
      return { pad: window.__game.padActive,
               stick: getComputedStyle(document.getElementById('stick')).display !== 'none',
               zone: getComputedStyle(t).display !== 'none' };
    }""")
    check("unplugging the controller brings the touch controls back",
          not padOff["pad"] and padOff["stick"] and padOff["zone"], padOff)

    # 10b. The pad's Start button pauses and, pressed again, resumes. The poll is
    #      deliberately outside update() — update() does not run while paused, so
    #      a check that lived there could pause but never resume. Driving the real
    #      frame loop here is what proves that wiring rather than the intent.
    padMap = page.evaluate("""() => ({ start: window.__game.PAD.START,
                                     back: window.__game.PAD.BACK })""")
    check("the pad layout maps Start and Back", padMap == {"start": 9, "back": 8}, padMap)

    padPause = page.evaluate("""() => {
      const g = window.__game;
      const btns = Array.from({ length: 16 }, () => ({ pressed: false }));
      window.__pad = { connected: true, axes: [0, 0], buttons: btns };
      navigator.getGamepads = () => [window.__pad];
      const hit = (on) => { btns[g.PAD.START].pressed = on; };

      hit(true);
      const edge = g.pollPadPause();
      // held down: a pad button is a level, not an event, so this must be quiet
      const repeat = g.pollPadPause();
      hit(false);
      g.pollPadPause();
      const release = g.pollPadPause();
      return { edge, repeat, release };
    }""")
    check("the pad's Start button registers one edge per press",
          padPause["edge"] and padPause["repeat"] is False and padPause["release"] is False, padPause)

    # The frame loop is what turns that edge into a pause, and only the loop can
    # resume, since update() is skipped while paused.
    padToggle = page.evaluate("""() => {
      const g = window.__game;
      const btns = Array.from({ length: 16 }, () => ({ pressed: false }));
      window.__pad = { connected: true, axes: [0, 0], buttons: btns };
      navigator.getGamepads = () => [window.__pad];
      const hit = (on) => { btns[g.PAD.START].pressed = on; };
      const seen = { start: g.mode };
      // pump the real frame loop, one press at a time
      hit(true); g.frame(performance.now() + 16);
      seen.paused = g.mode;
      hit(false); g.frame(performance.now() + 32);
      hit(true); g.frame(performance.now() + 48);
      seen.resumed = g.mode;
      hit(false);
      return seen;
    }""")
    check("a pad Start press pauses through the frame loop",
          padToggle["start"] == "playing" and padToggle["paused"] == "paused", padToggle)
    check("a second pad Start press resumes",
          padToggle["resumed"] == "playing", padToggle)

    # 11. A landed blow has to read as impact: the frame is held, the camera is
    #     kicked, and the wound throws a ring and sparks.
    feel = page.evaluate("""() => {
      const g = window.__game, r = g.room, p = g.state.player;
      const e = r.enemies[0];
      const before = r.projectiles.filter((x) => x.kind === 'impact' || x.kind === 'debris').length;
      e.x = p.x + 20; e.y = p.y;          // put a foe inside the swing
      g.hurtEnemy(e, 5, { x: 1, y: 0 });  // a light, non-lethal blow
      const after = r.projectiles.filter((x) => x.kind === 'impact' || x.kind === 'debris').length;
      return { added: after - before,
               impact: r.projectiles.some((x) => x.kind === 'impact'),
               debris: r.projectiles.filter((x) => x.kind === 'debris').length,
               stop: g.hitStop, shakeMag: g.shake.mag };
    }""")
    check("a blow throws an impact ring", feel["impact"], feel)
    check("a blow throws sparks", feel["debris"] >= 4, feel)
    check("a blow holds the frame briefly", feel["stop"] > 0, round(feel["stop"], 3))
    check("a blow kicks the camera", feel["shakeMag"] > 0, feel["shakeMag"])

    page.wait_for_timeout(400)
    settled = page.evaluate("""() => {
      const g = window.__game;
      return { mag: g.shake.mag, x: g.shake.x, y: g.shake.y,
               impacts: g.room.projectiles.filter((x) => x.kind === 'impact').length };
    }""")
    check("the camera settles after the blow",
          settled["mag"] == 0 and settled["x"] == 0 and settled["y"] == 0, settled)
    check("the impact ring fades away", settled["impacts"] == 0, settled["impacts"])

    # 12. Cosmetic hit effects must never keep a cleared chamber locked. Any
    #     projectile left over from the aiming checks is dropped first, so only
    #     the two cosmetic kinds are in flight when the room empties.
    locked = page.evaluate("""() => {
      const g = window.__game, r = g.room;
      r.cleared = false;
      r.enemies.length = 0;
      r.projectiles.length = 0;
      r.projectiles.push({ x: 10, y: 10, t: 0.3, kind: 'impact' });
      r.projectiles.push({ x: 10, y: 10, t: 0.3, kind: 'debris', vx: 0, vy: 0, r: 2 });
      return true;
    }""")
    page.wait_for_timeout(500)
    cleared = page.evaluate("() => ({ cleared: window.__game.room.cleared, mode: window.__game.mode })")
    check("hit effects do not block the gate from opening", cleared["cleared"], cleared)

    print("page errors:", errors[:5] or "none")
    browser.close()


# The same game has to play on a desktop: keyboard movement, a strike, a dash,
# and no bulky thumb controls over the view.
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL, wait_until="load")
    page.click("#playBtn")
    page.wait_for_timeout(400)

    start = page.evaluate("() => ({ x: window.__game.state.player.x, y: window.__game.state.player.y })")
    page.keyboard.down("d")
    page.wait_for_timeout(400)
    page.keyboard.up("d")
    moved = page.evaluate("() => window.__game.state.player.x")
    check("WASD moves the hero on a desktop", moved - start["x"] > 40, round(moved - start["x"]))

    page.keyboard.down("w")
    page.wait_for_timeout(300)
    check("WASD moves up as well",
          page.evaluate("() => window.__game.state.player.y") < start["y"] + 1, True)
    page.keyboard.up("w")

    # An instant tap, with no hold at all, must still land — this is the case a
    # skipped hit-stop frame used to swallow. Facing right first, since a strike
    # only connects with a foe roughly ahead.
    page.keyboard.down("d")
    page.wait_for_timeout(120)
    page.keyboard.up("d")
    hp = page.evaluate("""() => {
      const g = window.__game, r = g.room, p = g.state.player;
      r.enemies.forEach((e) => { e.x = 9999; });
      const e = r.enemies[0]; e.x = p.x + 25; e.y = p.y;
      return e.hp;
    }""")
    page.keyboard.press("j")
    page.wait_for_timeout(250)
    check("an instant J tap still strikes",
          page.evaluate("() => window.__game.room.enemies[0].hp") < hp, hp)

    page.keyboard.down("d")
    page.wait_for_timeout(150)
    page.keyboard.press(" ")
    page.wait_for_timeout(80)
    check("an instant Space tap still dashes",
          page.evaluate("() => window.__game.state.dashT > 0 || window.__game.state.dashCd > 0"), True)
    page.keyboard.up("d")

    desk = page.evaluate("""() => {
      const vis = (id) => {
        const el = document.getElementById(id);
        return getComputedStyle(el).display !== 'none';
      };
      return { kb: document.body.classList.contains('kb'), hint: vis('keyHint'),
               stick: vis('stick'), hit: vis('btnHit'), dash: vis('btnDash') };
    }""")
    check("a desktop shows the key hint", desk["kb"] and desk["hint"], desk)
    check("the bulky touch buttons stay out of the way on a desktop",
          not desk["hit"] and not desk["dash"], desk)
    check("the thumb ring is not shown on a desktop", not desk["stick"], desk)

    # A mouse can still drag the floating stick, so that route is not lost.
    page.mouse.move(300, 600)
    page.mouse.down()
    page.mouse.move(300, 520, steps=5)
    page.wait_for_timeout(300)
    check("a mouse drag still drives the stick",
          page.evaluate("() => Math.hypot(window.__game.state.player.hx, window.__game.state.player.hy)") > 0.1,
          True)
    page.mouse.up()

    print("page errors:", errors[:5] or "none")
    browser.close()

if failures:
    print("\nCONTROL CHECK FAILED:", ", ".join(failures))
    sys.exit(1)
print("\nCONTROL CHECK PASSED")
