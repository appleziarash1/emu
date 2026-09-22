"""Materialises the pre-fix build so the migration tests can run anywhere.

The stale-cache bug only reproduces from the cache-first service worker that
shipped before the fix, so these tests need that exact build. It is read out of
git rather than kept as a second copy in the tree, so the two can never drift.
"""
import os
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
OLD_COMMIT = "aaf3498"  # last commit before the service worker became network-first
ASSETS = ("index.html", "sw.js", "manifest.webmanifest",
          "icon-180.png", "icon-192.png", "icon-512.png")


def materialise(destination=None):
    """Write the pre-fix build into a directory and return its path."""
    destination = destination or tempfile.mkdtemp()
    os.makedirs(destination, exist_ok=True)
    for name in ASSETS:
        blob = subprocess.run(
            ["git", "show", f"{OLD_COMMIT}:{name}"],
            cwd=ROOT, capture_output=True, check=True).stdout
        with open(os.path.join(destination, name), "wb") as fh:
            fh.write(blob)
    return destination
