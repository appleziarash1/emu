"""Verify the PWA install criteria, offline caching, and touch controls."""
from playwright.sync_api import sync_playwright

import sys
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:12001/"

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": 390, "height": 780}, has_touch=True, is_mobile=True)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL, wait_until="load")
    page.wait_for_timeout(1500)

    print("manifest link:", page.get_attribute('link[rel="manifest"]', "href"))
    print("manifest type:", page.evaluate(
        """async () => (await fetch('./manifest.webmanifest')).headers.get('content-type')"""))
    print("manifest body:", page.evaluate(
        """async () => (await (await fetch('./manifest.webmanifest')).json()).name"""))
    print("sw registered:", page.evaluate(
        """async () => {
             const r = await navigator.serviceWorker.getRegistration();
             return !!r;
           }"""))
    print("caches after load:", page.evaluate(
        """async () => (await caches.keys()).join(',')"""))
    print("cached urls:", page.evaluate(
        """async () => {
             const c = await caches.open('underworld-shell-v4');
             return (await c.keys()).map((r) => new URL(r.url).pathname).join(',');
           }"""))

    # icons actually load (a broken icon breaks iOS install prompts)
    for icon in ("icon-180.png", "icon-192.png", "icon-512.png"):
        print(icon, page.evaluate(
            """async (p) => { const r = await fetch(p); return r.status + ' ' + r.headers.get('content-type'); }""",
            icon))

    page.click("#playBtn")
    page.wait_for_timeout(400)
    print("touch pad visible:", page.is_visible("#stick"))
    print("strike button visible:", page.is_visible("#btnHit"))
    print("dash button visible:", page.is_visible("#btnDash"))
    print("canvas fills viewport:", page.evaluate(
        """() => { const c = document.getElementById('stage'); const r = c.getBoundingClientRect();
                   return Math.round(r.width) + 'x' + Math.round(r.height); }"""))

    # Drag on the left half and confirm the player actually moves. The stick is
    # floating, so the touch point is what defines the direction, not the ring.
    before = page.evaluate("() => ({x: window.__game.state.player.x, y: window.__game.state.player.y})")
    page.touchscreen.tap(120, 600)
    page.wait_for_timeout(120)
    origin = page.evaluate("""() => {
      const s = document.getElementById('stick');
      return { left: parseFloat(s.style.left), top: parseFloat(s.style.top) };
    }""")
    print("stick spawned under the thumb:", 60 < origin["left"] < 90 and 540 < origin["top"] < 570)
    page.mouse.move(120, 600)
    page.mouse.down()
    page.mouse.move(120, 520, steps=6)
    page.wait_for_timeout(500)
    page.mouse.up()
    after = page.evaluate("() => ({x: window.__game.state.player.x, y: window.__game.state.player.y})")
    moved = abs(after["x"] - before["x"]) + abs(after["y"] - before["y"])
    print("joystick moved player:", moved > 5, "distance:", round(moved))
    print("moved up as dragged:", after["y"] < before["y"])

    # Kill the server connection and confirm the cached shell still loads.
    page.route("**/*", lambda route: route.abort())
    page.reload(wait_until="load")
    page.wait_for_timeout(800)
    print("offline title still renders:", page.evaluate("() => document.getElementById('playBtn') !== null"))

    print("page errors:", errors[:5] or "none")
    page.screenshot(path="/tmp/underworld_mobile.png")
    browser.close()
