# Underworld Escape

An original, Hades-inspired browser roguelike that installs as a PWA. Written as a
single self-contained `index.html` — no frameworks, no CDN, no backend — so it
keeps working offline once added to the iPhone Home Screen.

This is **not** Hades and contains none of its assets or code. It is an homage
built around the same ideas: descend through chambers, take a god's boon after
each one, and fight the Warden at the gate.

## Run

```bash
PORT=12001 node serve.js
```

Then open `http://localhost:12001/`. On a phone, add `?debug=1` to show a live
state readout.

## Files

- `index.html` — the whole game (canvas renderer, sim, touch UI, PWA registration)
- `serve.js` — tiny static server with correct MIME types for the manifest and SW
- `manifest.webmanifest`, `sw.js`, `icon-*.png` — PWA install + offline shell
- `smoke_test.py` — headless playthrough: clears chambers, takes boons, beats a boss
- `pwa_test.py` — checks install criteria, offline reload, and the touch joystick
- `update_test.py` — caches a build, ships a new one, asserts the new one arrives
- `stale_phone_test.py`, `clear_data_test.py` — the one-off migration off the old
  cache-first worker, for phones that installed a build before the fix
- `oldbuild.py` — reads that pre-fix build out of git for those two tests

## Tests

```bash
python3 smoke_test.py "http://localhost:12001/?debug=1"   # expects depths 1..8+, a boss at depth 5
python3 pwa_test.py                                        # expects all checks True
python3 art_test.py                                        # per-character palette check
python3 update_test.py                                     # proves updates and offline both work
python3 stale_phone_test.py                                # old installs heal within two reopens
python3 clear_data_test.py                                 # clearing site data heals in one
```

`stale_phone_test.py` and `clear_data_test.py` need git history: they rebuild the
pre-fix build from commit `aaf3498` so the bug can actually be reproduced.

## Updating an installed copy

`sw.js` is network-first for the page and manifest, so while the phone is online
a new build is picked up on the first open, and the page then reloads itself once
to run it. Icons are served from cache and refreshed in the background.

Phones that installed a build *before* the worker became network-first are the
one exception: that old worker never re-checked itself, so it needs two opens
(one to install the new worker, one to run it). If a copy is stubborn, clearing
the site's data fixes it in a single open — Safari: Settings → Safari → Advanced
→ Website Data → find the site → Delete. The menu shows an `art build …` tag so
the running build is always visible.

## Controls

- Left thumb on the round pad, `WASD`/arrows on a keyboard, or a gamepad's left stick
- `STRIKE` / `J` / gamepad A to swing, `DASH` / space / gamepad B to dash
