"""Simulates a phone that installed an old build and then receives a fix.

Serves a directory over HTTP, loads the pre-fix build so the old cache-first
service worker caches it, swaps in the fixed build, and reports how many
reopens the phone needs before it runs the new code.
"""
import http.server
import os
import shutil
import socketserver
import threading

from playwright.sync_api import sync_playwright

import oldbuild

FIXED = os.path.dirname(os.path.abspath(__file__))
NAMES = ("index.html", "sw.js", "manifest.webmanifest", "serve.js",
         "icon-180.png", "icon-192.png", "icon-512.png")


def free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def stamp_tag(directory, tag):
    """Append a marker the test can read through document.title."""
    path = os.path.join(directory, "index.html")
    with open(path, "a") as fh:
        fh.write(f"<script>document.title={tag!r};</script>")


work = oldbuild.materialise()
shutil.copy(os.path.join(FIXED, "serve.js"), work)
stamp_tag(work, "OLDBUILD")

PORT = free_port()


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=work, **kw)


socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(("127.0.0.1", PORT), Handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{PORT}"

try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 780},
                                   has_touch=True, is_mobile=True).new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(base + "/", wait_until="load")
        page.wait_for_timeout(1800)
        print("installed build:", page.title())
        assert page.title() == "OLDBUILD"

        for n in NAMES:  # deploy the fixed build
            shutil.copy(os.path.join(FIXED, n), work)
        stamp_tag(work, "NEWBUILD")
        print("deployed the fixed build")

        healed = None
        for i in range(1, 6):
            page.goto(base + "/", wait_until="load")
            page.wait_for_timeout(2500)
            title = page.title()
            print(f"reopen #{i} -> running: {title}")
            if title == "NEWBUILD":
                healed = i
                break
        print("reopens needed to receive the fix:", healed)
        print("page errors:", errors[:3] or "none")

        # A phone running the pre-fix worker cannot notice the new worker until a
        # second visit, because that worker is only replaced after the page that
        # registered it has gone: one reopen installs it, the next runs it.
        # Once on the fixed worker every later update lands on the first visit
        # (asserted separately by update_test.py), so this ceiling is the honest
        # contract for the one-off migration.
        assert healed is not None, "fixed build never arrived"
        assert healed <= 2, f"took {healed} reopens, expected at most 2"
        browser.close()
finally:
    httpd.shutdown()
    shutil.rmtree(work, ignore_errors=True)
