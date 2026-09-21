#!/usr/bin/env node
/**
 * apply-pwa.mjs — makes the repo an iPhone-installable PWA.
 * Run from the repo root AFTER unzipping this kit over it:
 *
 *   node apply-pwa.mjs            # patch index.html, src/main.js, vercel.json
 *   node apply-pwa.mjs --verify   # after `npm run build`, check dist/ is complete
 *
 * Safe to run repeatedly (idempotent). No dependencies.
 */
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const P = (...a) => path.join(root, ...a);
const read = (p) => (fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : null);
const ok = (m) => console.log('  \u2713 ' + m);
const warn = (m) => console.log('  ! ' + m);

const ICONS = ['icon-180.png', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png'];
const SPLASH = [
  [1320, 2868, 3], [1206, 2622, 3], [1290, 2796, 3], [1179, 2556, 3], [1284, 2778, 3], [1170, 2532, 3],
  [1125, 2436, 3], [1242, 2688, 3], [828, 1792, 2], [1242, 2208, 3], [750, 1334, 2],
];

/* ------------------------------------------------------------------ verify */
if (process.argv.includes('--verify')) {
  console.log('Verifying dist/ ...');
  const need = ['index.html', 'sw.js', 'manifest.json', ...ICONS.map((i) => 'icons/' + i),
    ...SPLASH.map(([w, h]) => `splash/splash-${w}x${h}.png`)];
  const missing = need.filter((f) => !fs.existsSync(P('dist', f)));
  if (missing.length) { missing.forEach((f) => warn('missing dist/' + f)); process.exit(1); }
  const html = read(P('dist', 'index.html'));
  const checks = [
    ['viewport-fit=cover', /viewport-fit=cover/],
    ['manifest link', /rel="manifest"/],
    ['PNG apple-touch-icon', /apple-touch-icon"[^>]*icon-180\.png/],
    ['apple-mobile-web-app-capable', /apple-mobile-web-app-capable/],
    ['service worker registered in bundle', null],
  ];
  let bad = 0;
  for (const [name, re] of checks) {
    if (!re) continue;
    if (re.test(html)) ok(name); else { warn('index.html missing: ' + name); bad++; }
  }
  const assets = fs.existsSync(P('dist', 'assets')) ? fs.readdirSync(P('dist', 'assets')).filter((f) => f.endsWith('.js')) : [];
  const hasReg = assets.some((f) => read(P('dist', 'assets', f)).includes('/sw.js'));
  hasReg ? ok('service worker registration is in the bundle') : (warn("no '/sw.js' registration found in dist/assets/*.js"), bad++);
  try { JSON.parse(read(P('dist', 'manifest.json'))); ok('manifest.json is valid JSON'); } catch { warn('manifest.json invalid'); bad++; }
  console.log(bad ? '\nSome checks failed.' : '\nAll good \u2014 deploy it.');
  process.exit(bad ? 1 : 0);
}

/* ------------------------------------------------------------- index.html */
console.log('1/4 index.html');
const indexPath = P('index.html');
let html = read(indexPath);
if (html == null) { console.error('index.html not found. Run this from the repo root.'); process.exit(1); }

const BEGIN = '<!-- PWA:BEGIN (apply-pwa.mjs) -->';
const END = '<!-- PWA:END -->';
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// drop a previous run + the tags we replace
html = html.replace(new RegExp(`[ \\t]*${esc(BEGIN)}[\\s\\S]*?${esc(END)}\\r?\\n?`), '');
const drop = [
  /[ \t]*<meta\s+name=["']viewport["'][^>]*>\r?\n?/i,
  /[ \t]*<link\s+rel=["']manifest["'][^>]*>\r?\n?/i,
  /[ \t]*<link\s+rel=["']apple-touch-icon["'][^>]*>\r?\n?/gi,
  /[ \t]*<meta\s+name=["']theme-color["'][^>]*>\r?\n?/i,
  /[ \t]*<meta\s+name=["']apple-mobile-web-app-[a-z-]+["'][^>]*>\r?\n?/gi,
  /[ \t]*<meta\s+name=["']mobile-web-app-capable["'][^>]*>\r?\n?/i,
];
drop.forEach((re) => { html = html.replace(re, ''); });

const splashTags = SPLASH.map(([w, h, r]) =>
  `<link rel="apple-touch-startup-image" href="/splash/splash-${w}x${h}.png" ` +
  `media="(device-width: ${w / r}px) and (device-height: ${h / r}px) and (-webkit-device-pixel-ratio: ${r}) and (orientation: portrait)" />`);

const block = [
  BEGIN,
  '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, user-scalable=no" />',
  '<link rel="manifest" href="/manifest.json" />',
  '<meta name="theme-color" content="#e94560" />',
  '<meta name="mobile-web-app-capable" content="yes" />',
  '<meta name="apple-mobile-web-app-capable" content="yes" />',
  '<meta name="apple-mobile-web-app-title" content="PixelVault" />',
  '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />',
  '<meta name="format-detection" content="telephone=no" />',
  '<link rel="apple-touch-icon" href="/icons/icon-180.png" />',
  ...splashTags,
  END,
].map((l) => '    ' + l).join('\n') + '\n';

if (/<meta\s+charset[^>]*>\r?\n?/i.test(html)) {
  html = html.replace(/(<meta\s+charset[^>]*>\r?\n?)/i, `$1${block}`);
} else if (/<head[^>]*>/i.test(html)) {
  html = html.replace(/(<head[^>]*>\r?\n?)/i, `$1${block}`);
} else {
  console.error('No <head> found in index.html'); process.exit(1);
}
fs.writeFileSync(indexPath, html);
ok('viewport-fit=cover, manifest, PNG apple-touch-icon, iOS meta tags, 11 launch screens');

/* ------------------------------------------------------------ src/main.js */
console.log('2/4 src/main.js');
const mainCandidates = ['src/main.js', 'src/main.ts'].map((f) => P(f));
const mainPath = mainCandidates.find((f) => fs.existsSync(f));
if (!mainPath) {
  warn("src/main.js not found \u2014 add  import './pwa.js';  to your entry file yourself.");
} else {
  const main = read(mainPath);
  if (/['"]\.\/pwa(\.js)?['"]/.test(main)) ok('already imports pwa.js');
  else { fs.writeFileSync(mainPath, "import './pwa.js';\n" + main); ok("added  import './pwa.js';  to " + path.relative(root, mainPath)); }
}
if (!fs.existsSync(P('src', 'pwa.js')) || !fs.existsSync(P('src', 'pwa.css'))) warn('src/pwa.js or src/pwa.css missing \u2014 unzip the kit over the repo root first.');

/* ------------------------------------------------------------ vercel.json */
console.log('3/4 vercel.json (cache headers)');
const RULES = [
  { source: '/sw.js', headers: [
    { key: 'Cache-Control', value: 'no-cache, no-store, must-revalidate' },
    { key: 'Service-Worker-Allowed', value: '/' } ] },
  { source: '/manifest.json', headers: [
    { key: 'Content-Type', value: 'application/manifest+json' },
    { key: 'Cache-Control', value: 'public, max-age=0, must-revalidate' } ] },
  { source: '/icons/(.*)', headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }] },
  { source: '/splash/(.*)', headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }] },
];
const vPath = P('vercel.json');
try {
  const raw = read(vPath);
  const obj = raw ? JSON.parse(raw) : {};
  obj.headers = (obj.headers || []).filter((h) => !RULES.some((r) => r.source === h.source));
  obj.headers.push(...RULES);
  fs.writeFileSync(vPath, JSON.stringify(obj, null, 2) + '\n');
  ok(raw ? 'merged into existing vercel.json' : 'created vercel.json');
} catch (e) {
  warn('vercel.json is not plain JSON, left untouched. Add these header rules manually:\n' + JSON.stringify(RULES, null, 2));
}

/* --------------------------------------------------------------- scan src */
console.log('4/4 scanning for emulator data path');
const hits = new Set();
const walk = (d) => {
  if (!fs.existsSync(d)) return;
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const f = path.join(d, e.name);
    if (e.isDirectory()) { if (e.name !== 'node_modules') walk(f); continue; }
    if (!/\.(js|ts|html)$/.test(e.name)) continue;
    const t = read(f);
    for (const m of t.matchAll(/EJS_pathtodata\s*=\s*([^;\n]+)/gi)) hits.add(`${path.relative(root, f)}: EJS_pathtodata = ${m[1].trim()}`);
    for (const m of t.matchAll(/https?:\/\/[a-z0-9.-]*emulatorjs\.org[^\s'"`)]*/gi)) hits.add(`${path.relative(root, f)}: ${m[0]}`);
  }
};
walk(P('src'));
walk(P('public'));
for (const m of (read(P('index.html')) || '').matchAll(/https?:\/\/[a-z0-9.-]*emulatorjs\.org[^\s'"`)]*/gi)) hits.add(`index.html: ${m[0]}`);
if (hits.size) { [...hits].slice(0, 8).forEach((h) => ok(h)); console.log('    (sw.js caches cdn.emulatorjs.org and any /data/ or /cores/ or .wasm path automatically)'); }
else warn('no EmulatorJS data path found in source \u2014 if cores load from another host, add it to CORE_HOSTS in public/sw.js.');

console.log('\nDone. Next:  npm run build  &&  node apply-pwa.mjs --verify  &&  git push');
