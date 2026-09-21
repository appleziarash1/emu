/* PixelVault service worker (v2 - stability release)
 * - Pages: network-first with a 3.5s timeout, then cached shell (fast launch on slow/flaky mobile data)
 * - Emulator cores / cover art / fonts: cache-first (big files, rarely change)
 * - Same-origin assets: stale-while-revalidate
 * - Supabase, non-GET and Range requests are never touched
 * - Redirected responses are stripped before serving a navigation (Safari rejects them)
 * Bump VERSION to make every client drop old caches.
 */
const VERSION = 'v2';
const SHELL_CACHE = `pv-shell-${VERSION}`;
const CORE_CACHE = `pv-cores-${VERSION}`;
const MEDIA_CACHE = `pv-media-${VERSION}`;
const MAX_MEDIA_ENTRIES = 120; // opaque (no-cors) images are padded in Chromium quota, keep this modest
const NAV_TIMEOUT_MS = 3500;

const PRECACHE = [
  '/manifest.json',
  '/icons/icon-180.png',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

const hostMatches = (host, list) => list.some((h) => host === h || host.endsWith('.' + h));

// Emulator cores are large (5-30 MB) and versioned -> cache-first.
// Matched by host (official CDN) OR by path/extension, so self-hosted /data/ or any other CDN also works.
const CORE_HOSTS = ['cdn.emulatorjs.org', 'emulatorjs.org'];
const isCoreAsset = (url) =>
  hostMatches(url.hostname, CORE_HOSTS) ||
  /\.(wasm|7z)$/i.test(url.pathname) ||
  (/\/(cores|data)\//i.test(url.pathname) && /\.(data|zip|js|css|json)$/i.test(url.pathname));

const MEDIA_HOSTS = [
  'thumbnails.libretro.com',
  'raw.githubusercontent.com',
  'fonts.googleapis.com',
  'fonts.gstatic.com',
];
const BYPASS_HOSTS = ['supabase.co', 'supabase.in'];

// Safari refuses to serve a *redirected* response to a navigation request.
function clean(res) {
  if (res && res.redirected) {
    return new Response(res.body, { status: res.status, statusText: res.statusText, headers: res.headers });
  }
  return res;
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(SHELL_CACHE);
      await cache.addAll(PRECACHE).catch(() => {}); // never fail install because of one 404
      try {
        const res = await fetch('/');
        if (res && res.ok) await cache.put('/index.html', clean(res));
      } catch (e) { /* offline install: shell gets cached on first successful navigation */ }
      await self.skipWaiting();
    })()
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keep = new Set([SHELL_CACHE, CORE_CACHE, MEDIA_CACHE]);
      const names = await caches.keys();
      await Promise.all(names.filter((n) => n.startsWith('pv-') && !keep.has(n)).map((n) => caches.delete(n)));
      await self.clients.claim();
    })()
  );
});

async function trimCache(name, max) {
  const cache = await caches.open(name);
  const keys = await cache.keys();
  if (keys.length > max) {
    await Promise.all(keys.slice(0, keys.length - max).map((k) => cache.delete(k)));
  }
}

async function cacheFirst(request, cacheName, trim) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(request);
  if (hit) return hit;
  const res = await fetch(request);
  if (res && (res.ok || res.type === 'opaque')) {
    cache.put(request, res.clone());
    if (trim) trimCache(cacheName, trim);
  }
  return res;
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(request);
  const network = fetch(request)
    .then((res) => {
      if (res && res.ok) cache.put(request, res.clone());
      return res;
    })
    .catch(() => hit);
  return hit || network;
}

async function networkFirstPage(request, event) {
  const cache = await caches.open(SHELL_CACHE);
  const cached = (await cache.match('/index.html')) || (await cache.match('/'));

  const network = fetch(request)
    .then((res) => {
      if (res && res.ok) {
        const c = clean(res.clone());
        cache.put('/index.html', c);
      }
      return clean(res);
    })
    .catch(() => null);

  // let the refresh finish in the background even if we answer from cache
  if (event && event.waitUntil) event.waitUntil(network);

  if (!cached) return (await network) || Response.error(); // very first visit: just wait

  const timeout = new Promise((resolve) => setTimeout(() => resolve(null), NAV_TIMEOUT_MS));
  const res = await Promise.race([network, timeout]);
  return res || clean(cached) || Response.error();
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  if (request.headers.has('range')) return; // audio/video range requests

  const url = new URL(request.url);
  if (hostMatches(url.hostname, BYPASS_HOSTS)) return;

  if (request.mode === 'navigate') {
    event.respondWith(networkFirstPage(request, event));
    return;
  }

  if (isCoreAsset(url)) {
    event.respondWith(cacheFirst(request, CORE_CACHE));
    return;
  }

  if (hostMatches(url.hostname, MEDIA_HOSTS)) {
    event.respondWith(cacheFirst(request, MEDIA_CACHE, MAX_MEDIA_ENTRIES));
    return;
  }

  if (url.origin === self.location.origin) {
    event.respondWith(staleWhileRevalidate(request, SHELL_CACHE));
  }
});

self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting();
});
