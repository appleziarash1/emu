// PWA + iOS stability layer. Imported once from src/main.js (apply-pwa.mjs adds the import).
// Everything here is defensive: if EmulatorJS internals differ, the helpers quietly do nothing.
import './pwa.css';

const isIOS = () =>
  /iphone|ipad|ipod/i.test(navigator.userAgent) ||
  (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1); // iPadOS
const isStandalone = () =>
  window.navigator.standalone === true || window.matchMedia('(display-mode: standalone)').matches;
const $ = (id) => document.getElementById(id);
const safe = (fn) => { try { return fn(); } catch (e) { return undefined; } };
const store = {
  get: (k) => safe(() => localStorage.getItem(k)),
  set: (k, v) => safe(() => localStorage.setItem(k, v)),
};

/* ---------------------------------------------------------------- toast */
function toast(message, actionLabel, onAction) {
  const el = document.createElement('div');
  el.className = 'pv-toast';
  el.setAttribute('role', 'status');
  const text = document.createElement('span');
  text.className = 'pv-toast-text';
  text.textContent = message;
  el.appendChild(text);
  if (actionLabel) {
    const btn = document.createElement('button');
    btn.className = 'pv-toast-btn';
    btn.textContent = actionLabel;
    btn.addEventListener('click', () => { el.remove(); if (onAction) onAction(); });
    el.appendChild(btn);
  }
  const close = document.createElement('button');
  close.className = 'pv-toast-close';
  close.setAttribute('aria-label', 'Dismiss');
  close.textContent = '\u00d7';
  close.addEventListener('click', () => el.remove());
  el.appendChild(close);
  document.body.appendChild(el);
  return el;
}

/* -------------------------------------------------------- play session */
let wakeLock = null;
let pausedByUs = false;
let updateReady = false;

const view = () => $('emulator-view');
const isPlaying = () => { const v = view(); return !!v && getComputedStyle(v).display !== 'none'; };
const emu = () => window.EJS_emulator;

async function lockScreen() {
  if (wakeLock || !('wakeLock' in navigator)) return;
  try {
    wakeLock = await navigator.wakeLock.request('screen'); // keeps the screen on while playing
    wakeLock.addEventListener('release', () => { wakeLock = null; });
  } catch (e) { wakeLock = null; }
}
function unlockScreen() {
  const l = wakeLock;
  wakeLock = null;
  if (l && l.release) Promise.resolve(safe(() => l.release())).catch(() => {});
}
function resumeAudio() {
  const e = emu();
  const ctxs = [safe(() => e.Module.SDL2.audioContext), safe(() => e.Module.AL.currentCtx.audioCtx)];
  ctxs.forEach((c) => safe(() => c && c.resume && c.resume()));
}
function showUpdateToast() {
  toast('New version ready.', 'Reload', () => location.reload());
}
function syncPlaying() {
  const playing = isPlaying();
  document.body.classList.toggle('pv-playing', playing);
  if (playing) lockScreen(); else unlockScreen();
  if (!playing && updateReady) { updateReady = false; showUpdateToast(); }
}

// iOS suspends the page when you switch apps: pause cleanly, resume audio + game on return.
document.addEventListener('visibilitychange', () => {
  const e = emu();
  if (document.hidden) {
    if (isPlaying() && e && typeof e.pause === 'function' && !e.paused) {
      safe(() => e.pause(true));
      pausedByUs = true;
    }
    return;
  }
  if (isPlaying()) {
    if (pausedByUs && e && typeof e.play === 'function') safe(() => e.play(true));
    resumeAudio();
    lockScreen(); // wake locks are released automatically when the page is hidden
  }
  pausedByUs = false;
});

window.addEventListener('DOMContentLoaded', () => {
  const v = view();
  if (v && 'MutationObserver' in window) {
    new MutationObserver(syncPlaying).observe(v, { attributes: true, attributeFilter: ['style', 'class'] });
  }
  syncPlaying();
});

/* ------------------------------------------------------ service worker */
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  const hadController = !!navigator.serviceWorker.controller;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (!hadController) return; // very first install, nothing to reload
    if (isPlaying()) updateReady = true; // never reload in the middle of a game
    else showUpdateToast();
  });
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((e) => console.warn('[PWA] SW registration failed', e));
  });
}

/* --------------------------------------------------------- storage etc. */
// Ask the browser not to evict IndexedDB (ROMs, save states)
if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});

// Real viewport height on iOS Safari (address bar / keyboard safe)
function setVh() { document.documentElement.style.setProperty('--vh', `${window.innerHeight * 0.01}px`); }
setVh();
window.addEventListener('resize', setVh);
window.addEventListener('orientationchange', () => setTimeout(setVh, 200));

// Block pinch-zoom / double-tap zoom on the game screen (iOS ignores user-scalable=no)
const inGame = (t) => !!(t && t.closest && t.closest('#emulator-view, .virtual-gamepad'));
['gesturestart', 'gesturechange', 'gestureend'].forEach((evt) =>
  document.addEventListener(evt, (e) => { if (inGame(e.target)) e.preventDefault(); })
);
let lastTouchEnd = 0;
document.addEventListener('touchend', (e) => {
  const now = Date.now();
  if (now - lastTouchEnd < 300 && inGame(e.target)) e.preventDefault();
  lastTouchEnd = now;
}, { passive: false });

// Resume audio on first touch (iOS blocks AudioContext until a user gesture)
const unlockAudio = () => {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (Ctx) {
    const ctx = new Ctx();
    Promise.resolve(safe(() => ctx.resume())).finally(() => safe(() => ctx.close()));
  }
};
window.addEventListener('touchend', unlockAudio, { once: true });
window.addEventListener('click', unlockAudio, { once: true });

/* ------------------------------------------------------ iPhone UI fixes */
window.addEventListener('DOMContentLoaded', () => {
  const el = document.documentElement;
  // iPhone Safari has no Fullscreen API
  if (!(el.requestFullscreen || el.webkitRequestFullscreen)) {
    const b = $('fullscreen-btn');
    if (b) b.style.setProperty('display', 'none');
  }
  // iOS greys out files whose extension it doesn't know (.nes, .sfc, .gba ...) when <input accept=".ext"> is set
  if (isIOS()) {
    const input = $('rom-input');
    if (input) input.removeAttribute('accept');
  }
  // Touch wording instead of "drag & drop"
  if (window.matchMedia('(pointer: coarse)').matches) {
    const area = $('upload-area');
    const line1 = area && area.querySelector('p');
    const hint = area && area.querySelector('.upload-hint');
    if (line1) line1.textContent = 'Tap to choose a ROM file';
    if (hint) hint.textContent = 'from Files, iCloud Drive or Downloads';
  }
});

/* ------------------------------------------- first-run / install prompts */
function showIOSInstallHint() {
  if (!isIOS() || isStandalone() || store.get('pv-ios-hint-dismissed')) return;
  const el = document.createElement('div');
  el.className = 'pv-install-hint';
  const text = document.createElement('div');
  text.className = 'pv-install-text';
  text.innerHTML =
    '<strong>Install PixelVault</strong><br>Tap <span class="pv-share-icon" aria-label="Share">' +
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
    '<path d="M12 3v12M8 7l4-4 4 4M5 12v8a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-8"/></svg></span>' +
    ' then <strong>Add to Home Screen</strong>';
  const close = document.createElement('button');
  close.className = 'pv-install-close';
  close.setAttribute('aria-label', 'Dismiss');
  close.textContent = '\u00d7';
  close.addEventListener('click', () => {
    store.set('pv-ios-hint-dismissed', '1');
    el.remove();
  });
  el.appendChild(text);
  el.appendChild(close);
  document.body.appendChild(el);
}

window.addEventListener('load', () => {
  setTimeout(() => {
    if (isStandalone()) {
      // The Home Screen app has its own storage, separate from Safari
      if (!store.get('pv-standalone-seen')) {
        store.set('pv-standalone-seen', '1');
        toast('This app keeps its own game library \u2014 add your ROMs here once. Signed-in cloud saves carry over.', 'Got it');
      }
    } else {
      showIOSInstallHint();
    }
  }, 2500);
});
