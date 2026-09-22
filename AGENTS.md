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
  `update_test.py` asserts the new build reaches a phone.
- Cosmetic projectiles are tracked in `room.projectiles` but must never count
  toward clearing a chamber, or a gate can stay shut forever.
- Presses are buffered (`pressBuf`, `padEdge`) because a frame can be skipped
  during hit stop; a raw tap would otherwise be dropped.

## Deploy
- The game is hosted from the branch `underworld-escape` in the user's repo
  `appleziarash1/emu` (kept separate from that repo's `main`, which is a
  different project). Push with `git push emu master:refs/heads/underworld-escape`.
- GitHub Pages for that branch is enabled by hand in the repo's Pages settings;
  the API token available here can push but not manage Pages.
