# Underworld Escape — notes for future sessions

Single-file canvas roguelike PWA. No build step: `index.html` is the whole game,
`sw.js` the offline shell, `manifest.webmanifest` + `icon-*.png` the install bits.

## Run and test
- Serve locally: `node serve.js` (port 12001).
- Tests are Playwright scripts run one at a time; they need the server up:
  `smoke_test.py`, `art_test.py`, `pwa_test.py`, `feature_test.py`,
  `control_test.py`, `save_test.py`, `god_test.py`, `update_test.py`,
  `stale_phone_test.py`, `clear_data_test.py`, `ability_test.py`,
  `realm_test.py`, `rarity_test.py`, `meta_test.py`.
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
- The pad's Start/Back button is polled from `frame()`, not from `update()`.
  `update()` only runs while `mode === 'playing'`, so a pause check inside it
  could pause the run but never resume it; the poll must sit where every mode
  reaches it. `pollPadPause()` keeps its own previous-state so a held button
  fires exactly once instead of toggling every frame.
- Hiding the touch controls is the `body.pad` class, but the stick and buttons
  carry their own `on` class. `setPadActive(false)` therefore re-runs
  `showTouch()`; without that, unplugging mid-run leaves them hidden (the CSS
  `display:none` lifts, the inner `on` state is already gone) until the next room
  reloads them. The two input paths are summed every frame (`input`, `kb`,
  `pad`), so a controller never has to disable touch to work.
- `window.__game` exposes `frame`, `pollPadPause` and `PAD` so a suite drives the
  real loop and reads the real mapping rather than reimplementing either — a test
  that calls `openPause()` itself passes even when the wiring is dead.

## Barriers
- `room.barriers` holds axis-aligned blocks, built in `buildRoom` from the room
  seed, so a resumed run gets them in the same spots. Placement rejects anything
  near the entrance, the gate or the road: a barrier must never seal the way in
  or the way on. `feature_test.py` asserts those minimums across 12 depths,
  because a bad generation would only show up on some screens and seeds.
- The hero is blocked while walking, but a dash passes straight through:
  `state.dashT > 0` skips `pushOutOfBarriers` entirely. Dash is deliberately
  reused as the "crosses stone" key — it is already the state where the body
  moves as a burst, so no new input or cooldown was needed. A dash that ends
  inside a block is finished off by `ejectFromBarriers` in the dash's own
  direction, so the hero is never left embedded in stone.
- Foes never pass: their `pushOutOfBarriers` call is unconditional, and the boss
  charge is stopped by it too (a charge is a shove, not a dash). `steerAround`
  feeds them a mostly-sideways direction when a block is ahead, so they walk
  around instead of grinding nose-first. There is no pathfinding — barriers are
  only about as wide as a body is thick, so sliding along one reaches the far
  side.
- `drawBarrier` extrudes the stone **upward from its collision footprint**: the
  bottom of the drawn body is `b.y + b.h/2`, not `b.y + b.h`. Drawing from
  `b.y - lift` down to `b.y + b.h` (the first version) put tall barriers' art 67px
  below the ground that actually blocks you, because a barrier's `h` is its
  depth, not its visual height. `feature_test.py` compares a canvas column with
  and without the stone to pin this down; the `lift` is purely visual and adds
  the lit top face above the footprint.
- Order inside the enemy loop matters: `pushOutOfBarriers` has to run **after**
  knockback and the wall clamp, or a knocked-back foe can be left inside a block
  for a frame.
- Do not empty `room.enemies` without setting `room.cleared = true` first, or the
  reward screen opens and pauses the sim — the barrier tests hit exactly this and
  read as "the hero will not move".

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
  `Math.random()`** — one stray `Math.random()` shifts the stream and the room
  comes back different. Enemy spawning is exempt: it runs after the layout and
  its foes are written to the save explicitly.
- `save_test.py` guards this: it reloads and compares the rebuilt chamber stone
  for stone. If it fails with matching counts but different positions, look for a
  `Math.random()` that crept into `buildRoom()`.
- Leaving the page fires the `pagehide` autosave, so **a reload overwrites the
  snapshot**. Read `ue_run_v1` back after the reload, not before, or a foe that
  lands a blow in between makes the check look like a save bug. `save_test.py`
  read it before the reload until this was fixed, and failed at random once
  barriers put foes closer to the hero.
- Power effects are captured by saving the resulting stats (`dmg`, `reach`,
  `shieldMax`, ...) plus the slot flags, not by replaying `apply()`, which would
  double them.
- A pending reward choice is stored as `state.offer` (god ids) so a resume shows
  the same pair, and `pendingPower` for a god picked but not yet slotted. How
  many gods a chamber offers is `OFFER_COUNT` (2); it is mirrored on
  `window.__game.offerCount` so the suites check the shipping value instead of
  hardcoding a number. `saveRun()` records `mode` so the check can pick the mode
  it resumes into.
- A god variant's `flags` are only read by the combat code for the slot it was
  bound to: `swing`/`applyStrikeEffects` read `state.se.attack`, the chakram
  branch of the projectile update reads `state.se.special`, and `castSpell`
  reads `state.se.spell`. A flag named for the wrong slot is written to the save
  and never read, so the power looks bound but does nothing. `god_test.py`
  audits this from the source and also drives the real swing/throw/cast, so add
  a new effect flag in both places or the suite fails.
- The special-slot flags live in the chakram branch of the projectile update,
  which is not next to `castSpecial` in the file. A new special flag must be
  read there, not in `castSpecial`, which only spawns the blade.
- Every `room.projectiles` kind must be handled by the update loop and by
  `drawProjectile`. Anything not matched by an `if (pr.kind === ...)` early-out
  falls through to the generic mover at the end of the update loop, which moves
  it with `pr.vx`. A cosmetic kind pushed without a velocity (a ring, a burst)
  therefore goes `NaN` on its first tick, and the failure surfaces much later as
  "createRadialGradient: non-finite value" from the orb fallback in
  `drawProjectile`. Only `arrow` and `orb` are always spawned with a velocity,
  so only they may use the fallback. `god_test.py` audits both loops against the
  pushed kinds, so a new kind must be added to both or the suite fails.

## Character art
- Every body on screen is built from the shared kit at the top of the draw
  section: `limb`, `ellipse`, `ring`, `plate`, `eye`, `slashBlade`, `groundPuff`
  and `shadowUnder`. Add a new look by composing those, not by hand-rolling
  `ctx.arc`/`ctx.fill` again — the light direction, the rim and the contact
  shadow only stay consistent across the roster if they all come from one place.
- Sprites are drawn facing **local +x**. `drawHero` and the weapon sprites use
  `ctx.scale(f, 1)` with `f` from `faceX` so a left-facing hero is a mirror, not
  a second set of coordinates. Anything with handedness must go inside that flip.
- The hero wears the bound god as a crest (`drawRelic`), keyed by `godId` in
  `RELIC_LOOK`. A new god needs an entry there too, or the hero falls back to
  the default bolt and the run stops showing which god it belongs to.
- `ring` refuses a non-finite or non-positive radius. A negative `ctx.arc`
  radius throws `IndexSizeError`, which kills the entire frame — the enemy
  telegraphs build radii from sines of `t`, so a NaN reaching one would blank
  the screen rather than skip a decoration. Keep that guard.
- `drawHero` takes `t` (the room clock) and must not read wall time. The relic's
  pulse used `performance.now()` at first, which made a paused frame still move
  and made the art tests non-reproducible.
- `art_test.py` reads real canvas pixels for the palettes, then audits the
  shading in the source (`createLinearGradient`, `shadowBlur`, the helper list,
  the relic map, the ring guard). Tone counting on the live canvas was dropped:
  the readback races the render loop and swung by ten tones between identical
  runs, so it could not gate a commit.

## Running the tests
Playwright is not installed by default: `pip install playwright` then
`python3 -m playwright install chromium`. Run the suites one at a time — several
browsers back to back can crash a page under load ("Target crashed"), which is
resource contention rather than a real failure; rerun that suite on its own.

## The House, aspects, mirror, keepsakes and the pact
- `ARMS` lists the six Hades arms (Stygius, Varatha, Aegis, Coronacht, Malphon,
  Exagryph) against the weapon ids the sim already uses. `ASPECTS` holds four per
  arm; an aspect's `arm` must be a real weapon id, because `aspectsOf(id)` and
  the House screen both key off it, and `meta_test.py` asserts the match.
- The War Hammer (`hammer`) is the game's own bonus arm and deliberately has no
  aspects. `meta_test.py` checks the six Hades arms have four each rather than
  demanding aspects of every weapon.
- `applyMetaToRun()` folds the permanent layer into a fresh run: the aspect's
  `mod` (speed/cd/dmg/knock/shield/hp), the keepsake and the mirror ranks. A new
  modifier must be applied here *and* consumed by the sim, or it is a stat that
  is written and never read — the same trap as an unread boon flag.
- Meta currency is `ue_meta_v1` (Darkness, Titan Blood, bought aspects, mirror
  ranks, keepsakes, pact levels); `ue_aspect_pick_v1` holds the chosen aspect.
  Both are separate from `ue_run_v1`, so clearing a run never wipes progress.
- Pact Heat is summed by `heatTotal()` and copied onto the run as `state.heat`.
  The pact's effects land as `foeCountAdd`, `foeDmgMul` and `bossHpMul`, so a
  test can read the run rather than the pact table.
- `meta_test.py` drives the real House screens, buys through the real entry
  points, and starts a real run to prove the layer reaches the numbers.

## Deploy
- The game is hosted from the branch `underworld-escape` in the user's repo
  `appleziarash1/emu` (kept separate from that repo's `main`, which is a
  different project). Push with `git push emu master:refs/heads/underworld-escape`.
- GitHub Pages for that branch is enabled by hand in the repo's Pages settings;
  the API token available here can push but not manage Pages.
