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

## Tests

```bash
python3 smoke_test.py "http://localhost:12001/?debug=1"   # expects depths 1..8+, a boss at depth 5
python3 pwa_test.py                                        # expects all checks True
```

## Controls

- Left thumb on the round pad, `WASD`/arrows on a keyboard, or a gamepad's left stick
- `STRIKE` / `J` / gamepad A to swing, `DASH` / space / gamepad B to dash
