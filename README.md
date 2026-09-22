# Underworld Escape

An original, Hades-inspired browser roguelike that installs as a PWA. Written as a
single self-contained `index.html` — no frameworks, no CDN, no backend — so it
keeps working offline once added to the iPhone Home Screen.

This is **not** Hades and contains none of its assets or code. It is an homage
built around the same ideas: descend through chambers, take a god's boon after
each one, and fight the Warden at the gate.

## Arms

Five weapons, chosen before the run. Each has its own reach, cadence and drawing, so
a run plays differently depending on what is in hand. The arm you pick is yours for
the whole descent: reward screens offer a god's boon, never a weapon swap.

| Arm | Kind | Reach | Cooldown | Character |
| --- | --- | --- | --- | --- |
| Xiphos | melee | 62 | 0.26s | balanced all-rounder |
| Dory Spear | melee | 92 | 0.34s | long thrust, safe pokes |
| Twin Fangs | melee | 50 | 0.13s | fast, low damage |
| War Hammer | melee | 70 | 0.60s | heavy, throws foes back |
| Apollo Bow | ranged | 420 | 0.40s | arrows at a distance |

## The descent

Each chamber is a hall several screens across - the view pans with the hero, so the
descent feels like travelling through a place rather than fighting in a box. Deeper
chambers grow larger.

A paved road runs in from the wall opposite the gate and bends its way to the gate,
past torches and pillars. The floor is laid stone with moss, rubble and old bone,
and dust drifts through the torchlight. Walls ring the hall, and they are solid.

The gate is easy to lose in a hall this size, so a minimap in the corner shows the
chamber outline, the road, the gate, the enemies, and the part of the room on screen.

When the gate opens, a short corridor scene plays - the hero walks the road toward
the next arch - which can be skipped with one tap.

## Hitting a foe

A landed blow is meant to feel like one. The frame stops for a moment, the camera is
kicked, and an impact ring and sparks burst out of the wound. Heavier strikes and
kills hit harder than quick taps do.

## Run

```bash
PORT=12001 node serve.js
```

Then open `http://localhost:12001/`. On a phone, add `?debug=1` to show a live
state readout.

## Continue where you left off

The run autosaves to the browser: every few seconds while you play, each time a
chamber is entered, and the moment the app goes to the background or closes.
Reopening the page (or the installed app) shows a **Continue run** button on the
menu, and it drops you back into the same chamber — same layout, same gate, the
foes you had not finished off standing at the health you left them at, your boons
still in hand, and a boon choice you had not made yet still on offer.

Dying or escaping ends the run and clears the save, so a finished run is never
offered again. The best depth on the menu is kept separately and lives on.

Two things make this cheap: enemies are stored explicitly, and the chamber's
layout is rebuilt from a seed rather than saved stone by stone. The seed feeds the
room's decoration only; combat rolls stay on `Math.random`, so the save never has
to replay a fight.

## Files

- `index.html` — the whole game (canvas renderer, sim, touch UI, PWA registration)
- `serve.js` — tiny static server with correct MIME types for the manifest and SW
- `manifest.webmanifest`, `sw.js`, `icon-*.png` — PWA install + offline shell
- `smoke_test.py` — headless playthrough: clears chambers, takes boons, beats a boss
- `save_test.py` — the run survives a reload: layout, foes, health, boons, offers
- `pwa_test.py` — checks install criteria, offline reload, and the touch joystick
- `control_test.py` — the floating stick (spawn, dead zone, tracking, release),
  controller takeover, the feel of a landed hit, and the desktop keyboard path
- `feature_test.py` — weapon mechanics, chamber size and walls, the road, the
  minimap, the corridor
- `update_test.py` — caches a build, ships a new one, asserts the new one arrives
- `stale_phone_test.py`, `clear_data_test.py` — the one-off migration off the old
  cache-first worker, for phones that installed a build before the fix
- `oldbuild.py` — reads that pre-fix build out of git for those two tests

## Tests

```bash
python3 smoke_test.py "http://localhost:12001/?debug=1"   # expects depths 1..8+, a boss at depth 5
python3 save_test.py                                       # resume rebuilds the exact chamber
python3 pwa_test.py                                        # expects all checks True
python3 control_test.py                                    # joystick, controller, hit feel
python3 feature_test.py                                    # weapons, big chambers, maps
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
- `STRIKE` / `J` / gamepad X swings the arm you carry; it snaps onto a nearby foe.
- `SPELL` / `U` / gamepad B bursts outward all around you, wounding everything
  close and knocking incoming shots out of the air. It recharges slowly.
- `SPECIAL` / `I` / gamepad Y hurls a blade that cuts one side of the room and
  comes back to your hand, cutting the same foes again on the way home.
- `DASH` / space / gamepad A dashes, and makes you briefly untouchable.
- `WASD`/arrows or a gamepad's left stick also move you. On a desktop the mouse can
  drag the floating stick too.
- A connected controller replaces the touch controls: they hide while it is in use
  and return when it is unplugged.
- On a mouse-and-keyboard machine the resting thumb ring and the touch buttons stay
  out of the way, and a small
  `WASD move · J strike · U spell · I special · Space dash` hint takes their place.
  Phones still get the full on-screen pad.
