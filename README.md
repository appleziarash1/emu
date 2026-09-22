# Underworld Escape

An original, Hades-inspired browser roguelike that installs as a PWA. Written as a
single self-contained `index.html` — no frameworks, no CDN, no backend — so it
keeps working offline once added to the iPhone Home Screen.

This is **not** Hades and contains none of its assets or code. It is an homage
built around the same ideas: descend through chambers, take a god's boon after
each one, and fight the Warden at the gate.

## Arms

Five weapons, chosen before the run and tradable at any reward screen. Each has
its own reach, cadence and drawing, so a run plays differently depending on what
is in hand.

| Arm | Kind | Reach | Cooldown | Character |
| --- | --- | --- | --- | --- |
| Xiphos | melee | 62 | 0.26s | balanced all-rounder |
| Dory Spear | melee | 92 | 0.34s | long thrust, safe pokes |
| Twin Fangs | melee | 50 | 0.13s | fast, low damage |
| War Hammer | melee | 70 | 0.60s | heavy, throws foes back |
| Apollo Bow | ranged | 420 | 0.40s | arrows at a distance |

## The descent

Each chamber is a place you walk through: a paved road runs in from the wall
opposite the gate and bends its way to the gate, with lanterns along it. When the
gate opens, a short corridor scene plays - the hero walks the road toward the next
arch - which can be skipped with one tap.

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
- `control_test.py` — the floating stick: spawn point, dead zone, tracking, release
- `feature_test.py` — weapon mechanics, the road through a chamber, the corridor
- `update_test.py` — caches a build, ships a new one, asserts the new one arrives
- `stale_phone_test.py`, `clear_data_test.py` — the one-off migration off the old
  cache-first worker, for phones that installed a build before the fix
- `oldbuild.py` — reads that pre-fix build out of git for those two tests

## Tests

```bash
python3 smoke_test.py "http://localhost:12001/?debug=1"   # expects depths 1..8+, a boss at depth 5
python3 pwa_test.py                                        # expects all checks True
python3 control_test.py                                    # joystick precision + aim assist
python3 feature_test.py                                    # weapons, road, corridor
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

- Touch anywhere on the left half of the screen: the stick appears under your
  thumb, and the ring follows it. A short travel is ignored, so a resting thumb
  does not make you drift.
- `STRIKE` / `J` / gamepad A swings the arm you carry; it snaps onto a nearby foe.
- `DASH` / space / gamepad B dashes, and makes you briefly untouchable.
- `WASD`/arrows or a gamepad's left stick also move you.
