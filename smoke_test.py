"""Headless smoke test for Underworld Escape: plays a full loop and reports state."""
import json
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:12001/?debug=1"

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 390, "height": 780}, has_touch=True, is_mobile=True)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    # On a fresh profile the game installs its service worker and the worker's
    # `controllerchange` reloads the page once. That reload would blank
    # `__game.state` mid-run, so the update machinery is stubbed here; the
    # service worker has its own suite in pwa_test.py.
    page.add_init_script("""
      try {
        Object.defineProperty(navigator, 'serviceWorker', {
          configurable: true,
          value: { addEventListener() {}, register: () => new Promise(() => {}), controller: null },
        });
      } catch (e) {}
    """)
    page.goto(URL, wait_until="load")

    page.click("#playBtn")
    # The click can land while the game is still booting; wait for a live run
    # rather than assuming the first press took.
    page.wait_for_function("() => window.__game && window.__game.state")
    page.wait_for_timeout(600)
    print("after start:", page.evaluate("window.__game.mode"))
    # Hold the strike key for the whole run: the sim reads it every frame.
    page.keyboard.down("j")

    # Drive the run programmatically: clear chambers, take boons, reach the boss.
    # Reach and damage live on the weapon now, so the harness widens the arm it
    # is holding rather than a state field the sim no longer reads.
    page.evaluate(
        """() => {
          const g = window.__game;
          g.state.dmg = 400; g.state.speed = 320;
          g.state.weapon = Object.assign({}, g.state.weapon, { reach: 260 });
        }"""
    )

    phases = []
    for step in range(420):
        page.evaluate(
            """() => {
              const g = window.__game, s = g.state, r = g.room;
              if (!r) return;
              // aim the player at the nearest enemy, or at the door when clear
              let tx = r.door ? r.door.x : 0, ty = r.door ? r.door.y : 0;
              if (r.enemies.length) { tx = r.enemies[0].x; ty = r.enemies[0].y; }
              const p = s.player;
              // chambers are several screens wide now, so the harness strides
              // proportionally to the room instead of a fixed handful of units
              const dx = tx - p.x, dy = ty - p.y, d = Math.hypot(dx, dy) || 1;
              const stride = Math.max(9, Math.min(28, d * 0.25));
              p.x += (dx / d) * stride; p.y += (dy / d) * stride;
              p.faceX = dx / d; p.faceY = dy / d;
              p.hx = dx / d; p.hy = dy / d;
            }"""
        )
        page.wait_for_timeout(60)
        snap = page.evaluate(
            """() => {
              const g = window.__game, r = g.room, s = g.state;
              return { mode: g.mode, depth: s ? s.depth : null, enemies: r ? r.enemies.length : null,
                       boss: r ? !!r.isBoss : null, cleared: r ? r.cleared : null,
                       powers: s ? Object.values(s.slots).filter(Boolean).length : null };
            }"""
        )
        phases.append(snap)
        # the walk between chambers is skippable; the harness skips it
        if snap["mode"] == "corridor":
            page.evaluate("window.__game.skipCorridor()")
            page.wait_for_timeout(80)
        # when a reward is on screen, take the first god, then bind it to the
        # slot the game suggests
        if snap["mode"] == "reward":
            page.evaluate("document.querySelector('#cardsBody .card').click()")
            page.wait_for_timeout(120)
        if snap["mode"] == "slot":
            page.evaluate(
                """() => {
                  const slot = document.querySelector('#slotsBody .slot.rec') ||
                               document.querySelector('#slotsBody .slot');
                  slot.click();
                }"""
            )
            page.wait_for_timeout(120)
        if snap["mode"] == "dead":
            break

    final = page.evaluate(
        """() => ({ mode: window.__game.mode, depth: window.__game.state.depth,
                    kills: window.__game.state.kills,
                    powers: Object.values(window.__game.state.slots).filter(Boolean).length })"""
    )
    depths = sorted({p["depth"] for p in phases if p["depth"]})
    bosses = [p["depth"] for p in phases if p["boss"]]
    rewards = [p["depth"] for p in phases if p["mode"] == "reward"]
    print("depths visited:", depths)
    print("boss depths:", sorted(set(bosses)))
    print("reward screens at depths:", sorted(set(rewards)))
    print("final:", final)
    print("page errors:", errors[:5] or "none")

    page.screenshot(path="/tmp/underworld_final.png")
    browser.close()
