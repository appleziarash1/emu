"""Reproduces the user's bug and proves the fix.

Scenario: a phone loads the game once, caches it, then the site is *updated*.
The old cache-first service worker kept serving the stale build forever. This
test caches a "v1" page, replaces the server file with "v2", reloads, and checks
the phone actually receives v2 — plus that offline still works afterwards.
"""
import http.server
import os
import shutil
import socketserver
import sys
import tempfile
import threading

from playwright.sync_api import sync_playwright

SRC = os.path.dirname(os.path.abspath(__file__))


def free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


PORT = free_port()


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=self.directory, **kw)


def serve(directory):
    Handler.directory = directory
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


work = tempfile.mkdtemp()
for name in ("index.html", "sw.js", "manifest.webmanifest", "serve.js"):
    shutil.copy(os.path.join(SRC, name), work)

# v1 of the game
v1 = open(os.path.join(work, "index.html")).read()
open(os.path.join(work, "index.html"), "w").write(v1.replace("art build 5", "art build 1"))

httpd = serve(work)
url = f"http://127.0.0.1:{PORT}/"

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": 390, "height": 780},
                              has_touch=True, is_mobile=True)
    page = ctx.new_page()
    page.goto(url, wait_until="load")
    page.wait_for_timeout(1500)  # let the SW install and cache v1
    print("first visit build:", page.text_content("#buildLine"))

    # The site is updated while the phone is away.
    open(os.path.join(work, "index.html"), "w").write(
        v1.replace("art build 5", "art build 99"))

    page.reload(wait_until="load")
    page.wait_for_timeout(1800)
    seen = page.text_content("#buildLine")
    print("after update, build:", seen)
    assert seen == "art build 99", f"stale build served: {seen!r}"

    # Now go offline: the installed app must still open.
    ctx.set_offline(True)
    page.reload(wait_until="load")
    page.wait_for_timeout(800)
    offline_ok = page.evaluate("() => document.getElementById('playBtn') !== null")
    print("offline still loads:", offline_ok)
    assert offline_ok, "offline fallback broken"

    # And it can still be played offline.
    page.click("#playBtn")
    page.wait_for_timeout(600)
    print("plays offline:", page.evaluate("() => window.__game.mode"))
    assert page.evaluate("() => window.__game.mode") == "playing"

    browser.close()

httpd.shutdown()
shutil.rmtree(work, ignore_errors=True)
print("UPDATE TEST PASSED")
