"""Checks the recovery instructions given for old installs.

Loads the pre-fix build, deploys the fix, then clears the site's cache and
service worker the way Safari's "Clear Website Data" does, and confirms that a
single reopen immediately runs the new build.
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


def title_marker(directory, tag):
    with open(os.path.join(directory, "index.html"), "a") as fh:
        fh.write(f"<script>document.title={tag!r};</script>")


work = oldbuild.materialise()
shutil.copy(os.path.join(FIXED, "serve.js"), work)
title_marker(work, "OLDBUILD")
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
        page.goto(base + "/", wait_until="load")
        page.wait_for_timeout(1800)
        print("installed:", page.title())
        assert page.title() == "OLDBUILD"

        for n in NAMES:
            shutil.copy(os.path.join(FIXED, n), work)
        title_marker(work, "NEWBUILD")

        page.evaluate(
            """async () => {
                 const rs = await navigator.serviceWorker.getRegistrations();
                 await Promise.all(rs.map((r) => r.unregister()));
                 const ks = await caches.keys();
                 await Promise.all(ks.map((k) => caches.delete(k)));
               }"""
        )
        print("cleared site cache + service worker")

        page.goto(base + "/", wait_until="load")
        page.wait_for_timeout(2500)
        print("after one reopen:", page.title())
        assert page.title() == "NEWBUILD", "clearing data did not deliver the fix"
        browser.close()
finally:
    httpd.shutdown()
    shutil.rmtree(work, ignore_errors=True)

print("CLEAR-DATA RECOVERY PASSED")
