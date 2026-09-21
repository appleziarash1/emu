# PixelVault → iPhone PWA (complete kit)

## Install (3 commands)
```bash
# 1. unzip this kit over the repo root (folders merge: public/, src/)
# 2. patch index.html, src/main.js, vercel.json automatically:
node apply-pwa.mjs
# 3. build, verify, deploy:
npm run build && node apply-pwa.mjs --verify && git add -A && git commit -m "iOS PWA" && git push
```
Then on the iPhone: open the Vercel URL in **Safari** → Share → **Add to Home Screen**.

## What's inside
| File | Purpose |
|---|---|
| `public/manifest.json` | standalone display, PNG icons, colours |
| `public/icons/*.png` | 180 (iOS), 192, 512, maskable-512 |
| `public/splash/*.png` | 11 iPhone launch screens (no white flash) |
| `public/sw.js` | fast launch even on slow data (3.5 s network timeout → cached shell), offline shell, caches emulator cores + cover art, never touches Supabase |
| `src/pwa.js` / `src/pwa.css` | stability layer: pause/resume when you switch apps, screen stays awake while playing, iOS ROM-picker fix, safe areas, zoom blocking, audio unlock, update + first-run notices |
| `apply-pwa.mjs` | idempotent patcher + `--verify` for dist/ |

`apply-pwa.mjs` only changes: the `<head>` of `index.html` (inside a `PWA:BEGIN/END` block, replacing the old viewport / apple-touch-icon / manifest tags), one `import './pwa.js';` line at the top of `src/main.js`, and merges header rules into `vercel.json` (existing rewrites are kept).

## Stability features (what they fix)
- **Switch apps / lock phone mid-game** → game pauses, then resumes with audio working when you come back (your own manual pause is respected).
- **Screen dimming while playing** → Wake Lock keeps it on (iOS 16.4+).
- **ROM files greyed out in the picker** → iOS quirk with `accept=".nes,.sfc,..."`; the attribute is removed on iOS.
- **Slow / flaky mobile data** → app opens from cache after 3.5 s instead of hanging.
- **Safari "response has redirections" white screen** → redirected responses are stripped before being served.
- **New deploy while playing** → never reloads mid-game; shows a "New version ready — Reload" toast when you're back in the library.
- **Installed app looks empty** → one-time notice that it has its own library.
- Landscape: header/footer hidden while playing for more screen.

## Updating the cache
Bump `VERSION` in `public/sw.js` to force every client to drop old caches.

## Known iOS limits
- Home Screen app storage is separate from Safari tabs: ROMs added in Safari won't appear in the installed app. Cloud saves (Supabase) do sync.
- Supabase OAuth (Google/GitHub/Discord) inside an installed iOS PWA can be flaky because of how iOS handles the redirect; email/password is reliable. Test it.
- N64 / PS1 / NDS may be slow on iPhone; NES / SNES / GB / GBA / Genesis run well.
- Don't add COOP/COEP headers unless you need threaded cores — they break loading cores from the CDN.
