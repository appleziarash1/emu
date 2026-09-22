# VEILBORN — Final Browser Game Package

An original 2D action-roguelike that runs entirely in the browser. Descend five
realms, break five bosses, and decide what the Veil returns. Built with Phaser 3
and Vite; installable as an iPhone/Android PWA that works offline.

This is original IP — no proprietary Hades/Supergiant assets are included. All
art is generated procedurally or drawn at runtime from the game's own palette.

## Run locally

```bash
npm install
npm run dev          # http://localhost:5173
```

## Build and test

```bash
npm run build        # production bundle -> dist/
npm test             # end-to-end suite against dist/ (build first)
npm run test:build   # build then test in one step
```

The e2e suite boots the real built game in Chromium and asserts:

- content loads offline (no runtime fetch)
- every realm, every chamber, and every boss loads and spawns without scene errors
- a full playthrough from realm 1 room 1 through to the final ending
- all four endings are reachable from the throne choice
- the death path reaches the Death scene
- hub purchases persist to localStorage
- the service worker installs and the game boots with the network offline
- backgrounding the app auto-pauses a live run (iOS safety)

## Deploy

### GitHub Pages

```bash
npm run build:pages   # VITE_BASE=/veilborn/ -> dist/
```

Publish the contents of `dist/` to the `gh-pages` branch (or a `/docs` folder).
The service worker derives its scope at runtime, so the same build works at a
domain root or under a project subpath.

### Any static host

```bash
npm run build         # base = /
```

Upload `dist/` to Netlify, Vercel, Cloudflare Pages, S3, or any static server.

## iPhone PWA

Open the deployed URL in Safari, then Share -> Add to Home Screen. The installed
app:

- launches fullscreen from a themed splash screen (no white flash)
- respects the notch and home-indicator safe areas
- works offline from a precached app shell
- holds a wake lock during play so the screen does not dim mid-boss
- suspends and resumes audio when you switch apps
- auto-pauses the run the moment you background the app

## Controls

Keyboard: `WASD`/arrows to move, mouse to attack, `Space`/`Shift` to dash,
right-click for the weapon special, `1`-`6` to switch weapons, `Esc`/`P` to pause.

Touch: on-screen stick and action buttons on phones and tablets.

## Project layout

```
src/
  scenes/      Boot, Menu, WeaponSelect, Hub, Game, Death, Ending, Options
  systems/     gamestate, combat, effects, hud, touch
  entities/    player, enemy, boss, projectile
  world/       arena, rooms
  content.js   bundled content module (works with no network)
  pwa.js       iOS stability layer (wake lock, visibility, safe areas)
data/          content_expanded.json (bundled at build time)
public/        manifest, service worker, icons, splash screens
tests/e2e.mjs  end-to-end browser test
```
