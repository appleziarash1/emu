# Underworld Escape â€” notes for future sessions

Single-file canvas roguelike PWA. No build step: `index.html` is the whole game,
`sw.js` the offline shell, `manifest.webmanifest` + `icon-*.png` the install bits.

## Run and test
- Serve locally: `node serve.js` (port 12001).
- Tests are Playwright scripts run one at a time; they need the server up:
  `smoke_test.py`, `art_test.py`, `pwa_test.py`, `feature_test.py`,
  `control_test.py`, `save_test.py`, `god_test.py`, `update_test.py`,
  `stale_phone_test.py`, `clear_data_test.py`, `ability_test.py`.
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
- The hero has four abilities, one per face button: X strike, Y special, B spell,
  A dash. Shoulders and the D-pad are aliases. The same four are on `J`/`U`/`I`
  and space, and on the four touch buttons. `ability_test.py` drives a stub
  gamepad (`window.__pad`) because `navigator.getGamepads` is read-only.
- A test that empties `room.enemies` must set `room.cleared = true` first, or the
  chamber clears and the reward screen pauses the sim, making every later ability
  check look broken.

## Gods, slots and the market
- A god is one entry in `GODS` with a variant per slot (`attack`, `special`,
  `spell`), each holding `name`, `desc`, `apply(s)` and `flags`. `SLOTS` is the
  list of the three moves; `SHOP_ITEMS` is derived from `GODS`.
- Effect flags live in `state.se[slot].<flag>` and the combat hooks read only
  their **own** slot (`state.se.attack` in `swing`/`applyStrikeEffects`,
  `state.se.special` in the chakram update, `state.se.spell` in `castSpell`).
  Never read another slot's flags — that is exactly the bug the split prevents.
  `god_test.py` checks this by binding one god per slot and asserting the other
  slots stay empty.
- The move a power lands in is chosen on the slot screen, driven by `offerSlots`
  → `bindPower`. `state.slots[slot]` records the god and power, `state.se[slot]`
  the flags; `apply()` mutates the stat fields. All of it is in `SAVE_FIELDS`, so
  a resume needs no replay. Save version is bumped when the shape changes
  (`SAVE_VERSION`), and a save of the wrong version is rejected rather than
  guessed at.
- `state.pendingPower` holds a god chosen but not yet slotted; it is saved so a
  resume reopens the chooser, and `resumeRun()` checks it before `state.offer`.
- Cheap-but-silent flag names are easy to write and never read (this happened
  with `specTrail` vs `trail`): after adding a flag, grep the name in `index.html`
  and confirm it is actually consumed.
- Shop prices: Chaos 160, Ares/Zeus 130, the rest 110. `renderShop` marks
  unaffordable rows `.poor` and the click is refused, so a purse can never go
  negative.
- `window.__game` exposes `gods`, `slots`, `shopItems`, `bindPower`, `offerSlots`,
  `openShop`, `closeShop`, `openPause`, `closePause` and `tick(dt)` for the tests.
  `tick` is gated on `mode === 'playing'` exactly like the frame loop, so the
  pause tests can prove the sim does not advance.

## Pause
- `openPause`/`closePause` switch `mode` between `playing` and `paused`. `update`
  only runs in `playing`, so nothing needs a per-system pause check.
- The market is reachable from pause; `closeShop` returns to whichever screen
  opened it (`shopReturn`).
- `hideTouch()`/`showTouch()` bracket the overlay so the pad does not sit under
  the pause buttons.

## Save and resume
- `saveRun()` writes the live run to `ue_run_v1`; `resumeRun()` rebuilds it. The
  menu's Continue button and the HUD's SAVE button both drive it, and
  `die()`/`win()` call `clearSave()`.
- A chamber's layout is rebuilt from `room.seed`, not stored piece by piece. So
  **anything that decorates a room in `buildRoom()` must draw from `rng()`, never
  `Math.random()`** â€” one stray `Math.random()` shifts the stream and the room
  comes back different. Enemy spawning is exempt: it runs after the layout and
  its foes are written to the save explicitly.
- `save_test.py` guards this: it reloads and compares the rebuilt chamber stone
  for stone. If it fails with matching counts but different positions, look for a
  `Math.random()` that crept into `buildRoom()`.
- Power effects are captured by saving the resulting stats (`dmg`, `reach`,
  `shieldMax`, ...) plus the slot flags, not by replaying `apply()`, which would
  double them.
- A pending reward choice is stored as `state.offer` (god ids) so a resume shows
  the same three, and `pendingPower` for a god picked but not yet slotted.
  `saveRun()` records `mode` so the check can pick the mode it resumes into.

## Running the tests
Playwright is not installed by default: `pip install playwright` then
`python3 -m playwright install chromium`. Run the suites one at a time â€” several
browsers back to back can crash a page under load ("Target crashed"), which is
resource contention rather than a real failure; rerun that suite on its own.

## Deploy
- The game is hosted from the branch `underworld-escape` in the user's repo
  `appleziarash1/emu` (kept separate from that repo's `main`, which is a
  different project). Push with `git push emu master:refs/heads/underworld-escape`.
- GitHub Pages for that branch is enabled by hand in the repo's Pages settings;
  the API token available here can push but not manage Pages.
