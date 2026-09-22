# Underworld Escape — notes for future sessions

Single-file canvas roguelike PWA. No build step: `index.html` is the whole game,
`sw.js` the offline shell, `manifest.webmanifest` + `icon-*.png` the install bits.

## Run and test
- Serve locally: `node serve.js` (port 12001).
- Tests are Playwright scripts run one at a time; they need the server up:
  `smoke_test.py`, `art_test.py`, `pwa_test.py`, `feature_test.py`,
  `control_test.py`, `update_test.py`, `stale_phone_test.py`, `clear_data_test.py`.
- `index.html` is one inline script; a quick syntax gate without a browser is
  `node -e "new Function(require('fs').readFileSync('index.html','utf8').match(/<script>([\s\S]*)<\/script>/)[1])"`.

## Conventions
- Every release bumps two strings together: the build label in `index.html`
  (`art build N`, shown on the menu) and `VERSION` in `sw.js` (`vN`).
  `update_test.py` asserts the new build reaches a phone. It also hard-codes the
  current label when it rewrites a test build, so update it in the same commit.
- Cosmetic projectiles are tracked in `room.projectiles` but must never count
  toward clearing a chamber, or a gate can stay shut forever.
- Presses are buffered (`pressBuf`, `padEdge`) because a frame can be skipped
  during hit stop; a raw tap would otherwise be dropped.

## Save and resume
- `saveRun()` writes the live run to `ue_run_v1`; `resumeRun()` rebuilds it. The
  menu's Continue button and the HUD's SAVE button both drive it, and
  `die()`/`win()` call `clearSave()`.
- A chamber's layout is rebuilt from `room.seed`, not stored piece by piece. So
  **anything that decorates a room in `buildRoom()` must draw from `rng()`, never
  `Math.random()`** — one stray `Math.random()` shifts the stream and the room
  comes back different. Enemy spawning is exempt: it runs after the layout and
  its foes are written to the save explicitly.
- `save_test.py` guards this: it reloads and compares the rebuilt chamber stone
  for stone. If it fails with matching counts but different positions, look for a
  `Math.random()` that crept into `buildRoom()`.
- Boon effects are captured by saving the resulting stats (`dmg`, `reach`,
  `shieldMax`, …), not by replaying `boon.apply()`, which would double them.
- A pending boon choice is stored as `state.offer` (boon ids) so a resume shows
  the same three, and `saveRun()` records `mode` so the check can pick the mode
  it resumes into.

## Running the tests
Playwright is not installed by default: `pip install playwright` then
`python3 -m playwright install chromium`. Run the suites one at a time — several
browsers back to back can crash a page under load ("Target crashed"), which is
resource contention rather than a real failure; rerun that suite on its own.

## Deploy
- The game is hosted from the branch `underworld-escape` in the user's repo
  `appleziarash1/emu` (kept separate from that repo's `main`, which is a
  different project). Push with `git push emu master:refs/heads/underworld-escape`.
- GitHub Pages for that branch is enabled by hand in the repo's Pages settings;
  the API token available here can push but not manage Pages.
