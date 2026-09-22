// Underworld Escape — offline-capable shell.
//
// Strategy: network-first. An installed game must still work with no network,
// but a game that is *changed* must not be pinned to an old build on a phone
// the user cannot easily clear. So:
//   - navigations and the app shell: try the network, fall back to cache offline
//   - icons and the manifest: serve cache immediately, refresh in the background
// Bump VERSION on every release; activate() deletes every other cache.
const VERSION = 'v16';
const SHELL_CACHE = `underworld-shell-${VERSION}`;
const ASSETS = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-180.png', './icon-512.png'];

self.addEventListener('install', (e) => {
  self.skipWaiting();
  // Cache each file independently: one 404 must not abort the whole install.
  e.waitUntil(
    caches.open(SHELL_CACHE).then((c) =>
      Promise.all(ASSETS.map((url) => c.add(url).catch(() => {})))
    )
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== SHELL_CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('message', (e) => {
  if (e.data === 'skip-waiting') self.skipWaiting();
});

function isShellRequest(req) {
  if (req.mode === 'navigate') return true;
  const dest = req.destination;
  return dest === 'document' || dest === 'manifest';
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  if (new URL(req.url).origin !== self.location.origin) return;

  if (isShellRequest(req)) {
    // Network first, so a new build always wins while online.
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(SHELL_CACHE).then((c) => c.put(req, copy)).catch(() => {});
          }
          return res;
        })
        .catch(() => caches.match(req, { ignoreSearch: true })
          .then((hit) => hit || caches.match('./index.html')))
    );
    return;
  }

  // Everything else: instant from cache, refreshed in the background.
  e.respondWith(
    caches.match(req).then((hit) => {
      const network = fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(SHELL_CACHE).then((c) => c.put(req, copy)).catch(() => {});
          }
          return res;
        })
        .catch(() => hit);
      return hit || network;
    })
  );
});
