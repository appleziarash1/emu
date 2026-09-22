"""Captures reference screenshots of each screen for visual review."""
import sys

from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:12001/"

with sync_playwright() as pw:
    b = pw.chromium.launch()
    page = b.new_context(viewport={"width": 390, "height": 780},
                         has_touch=True, is_mobile=True).new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(url, wait_until="load")
    page.wait_for_timeout(900)
    page.screenshot(path="/tmp/shot_menu.png")

    page.click("#playBtn")
    page.wait_for_timeout(900)
    page.screenshot(path="/tmp/shot_room.png")

    # Stand next to an enemy and swing, so hero and foe are both visible.
    page.evaluate(
        """() => {
             const g = window.__game, s = g.state, r = g.room, e = r.enemies[0];
             s.player.x = e.x - 40; s.player.y = e.y + 44;
             s.player.faceX = 1; s.player.faceY = -0.3;
             s.player.hx = 1; s.player.hy = -0.3;
             s.reach = 90;
           }"""
    )
    page.keyboard.down("j")
    page.wait_for_timeout(300)
    page.screenshot(path="/tmp/shot_fight.png")
    page.keyboard.up("j")

    # Clear the room to force the boon selection screen.
    page.evaluate("() => { window.__game.room.enemies.length = 0; }")
    page.wait_for_timeout(700)
    page.screenshot(path="/tmp/shot_reward.png")

    # Jump into a boss chamber for the boss art.
    page.evaluate("() => { document.querySelector('#cardsBody .card').click(); }")
    page.wait_for_timeout(200)
    page.evaluate("() => { window.__game.state.depth = 5; window.__game.room.enemies.length = 0; }")
    page.wait_for_timeout(2800)
    page.screenshot(path="/tmp/shot_boss.png")

    print("errors:", errs[:3] or "none")
    b.close()
