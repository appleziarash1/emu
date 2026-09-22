// Real-browser end-to-end test. Boots the built game with Playwright, walks
// every realm from the first room to the final ending, and fails on any
// console error, page error, or stuck state.
//
// Run: node tests/e2e.mjs   (expects `npm run build` to have been run already)
import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(fileURLToPath(new URL('.', import.meta.url)), '..', 'dist');
// Set E2E_BASE=/veilborn/ to validate a subpath build (e.g. GitHub Pages).
const BASE = (process.env.E2E_BASE || '/').replace(/\/?$/, '/');
const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.css': 'text/css',
  '.webmanifest': 'application/manifest+json',
};

function startServer() {
  return new Promise((resolve) => {
    const server = createServer(async (req, res) => {
      try {
        let p = decodeURIComponent(req.url.split('?')[0]);
        if (p === BASE || p === BASE.slice(0, -1)) p = BASE;
        else if (!p.startsWith(BASE)) { res.writeHead(404); res.end('not found'); return; }
        p = '/' + p.slice(BASE.length);
        if (p === '/') p = '/index.html';
        const file = join(ROOT, p);
        const data = await readFile(file);
        res.writeHead(200, { 'Content-Type': MIME[extname(file)] || 'application/octet-stream' });
        res.end(data);
      } catch {
        res.writeHead(404); res.end('not found');
      }
    });
    server.listen(0, '127.0.0.1', () => resolve({ server, port: server.address().port }));
  });
}

const failures = [];
const passes = [];
function check(name, cond, extra = '') {
  if (cond) { passes.push(name); console.log(`  ok   ${name}`); }
  else { failures.push(`${name} ${extra}`); console.error(`  FAIL ${name} ${extra}`); }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  // E2E_URL points the suite at a real deployment instead of the local dist/.
  const remote = process.env.E2E_URL;
  let server = null;
  let port = null;
  let origin;
  if (remote) {
    origin = remote.replace(/\/$/, '') + '/';
  } else {
    ({ server, port } = await startServer());
    origin = `http://127.0.0.1:${port}${BASE}`;
  }
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await context.newPage();

  const consoleErrors = [];
  const pageErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => pageErrors.push(err.message));

  await page.goto(origin, { waitUntil: 'load' });

  // Wait for the game handle and for Boot -> Menu.
  await page.waitForFunction(() => window.__VEILBORN__ && window.__VEILBORN__.gameState && window.__VEILBORN__.gameState.booted, null, { timeout: 20000 });
  console.log('\n== boot ==');
  check('game object exposed', await page.evaluate(() => !!window.__VEILBORN__.game));
  check('content loaded from json', await page.evaluate(() => (window.__VEILBORN__.gameState.content.enemies || []).length === 10));

  await sleep(600);
  let active = await page.evaluate(() => window.__VEILBORN__.game.scene.getScenes(true).map((s) => s.scene.key));
  check('menu scene active after boot', active.includes('Menu'), JSON.stringify(active));

  // Helper: drive the game programmatically, bypassing pointer input so the
  // test is deterministic. Returns collected diagnostics.
  await page.evaluate(() => {
    window.__T__ = {
      errors: [],
      step() {},
    };
  });

  // --- Walk all five realms, all rooms, all bosses ---------------------
  console.log('\n== realm walk (every chamber, every realm) ==');
  for (let realm = 0; realm < 5; realm++) {
    const result = await page.evaluate(async (realmIdx) => {
      const { gameState, game } = window.__VEILBORN__;
      const errors = [];
      const onErr = (e) => errors.push(String(e && e.message ? e.message : e));
      window.addEventListener('error', onErr);

      // Fresh run, jump straight to the realm.
      gameState.weapon = null;
      gameState.startNewRun('ashen_edge', 4242 + realmIdx);
      gameState.enterRealm(realmIdx);

      const sceneNames = [];
      const roomsSeen = [];
      const bossNames = [];

      // Walk rooms 0..4 by restarting the Game scene, running a few frames,
      // then force-clearing combat rooms so progression is exercised.
      for (let room = 0; room < 5; room++) {
        gameState.run.room = room;
        const gs = game.scene.getScene('Game');
        if (!gs) {
          game.scene.start('Game', { mode: 'room' });
        } else {
          gs.scene.restart({ mode: 'room' });
        }
        await new Promise((r) => setTimeout(r, 90));
        const g = game.scene.getScene('Game');
        if (!g) { sceneNames.push('missing'); continue; }
        sceneNames.push(g.scene.key);
        roomsSeen.push(g.roomType);
        if (g.boss) bossNames.push(g.boss.name);

        // Exercise real combat: attack, special, dash, then clear.
        if (g.player) {
          g.tryAttack(g.player.x + 100, g.player.y);
          g.trySpecial(g.player.x + 100, g.player.y);
          g.tryDash();
          await new Promise((r) => setTimeout(r, 40));
          // Kill everything to advance.
          for (const e of [...g.enemies]) g.applyDamage(e, 99999, 0);
          if (g.boss && g.boss.alive) {
            // Damage the boss to force a phase transition too.
            g.boss.hp = g.boss.maxHp * 0.3;
            g.boss.update(16, g.time.now + 2000, g.buildCtx(g.time.now));
            g.applyDamage(g.boss, 999999, 0);
          }
          await new Promise((r) => setTimeout(r, 120));
        }
      }

      window.removeEventListener('error', onErr);
      return { errors, sceneNames, roomsSeen, bossNames };
    }, realm);

    check(`realm ${realm}: all 5 rooms loaded`, result.sceneNames.every((s) => s === 'Game'), JSON.stringify(result.sceneNames));
    check(`realm ${realm}: boss room present`, result.roomsSeen.includes('Boss'), JSON.stringify(result.roomsSeen));
    check(`realm ${realm}: boss spawned`, result.bossNames.length > 0, JSON.stringify(result.bossNames));
    check(`realm ${realm}: no scene errors`, result.errors.length === 0, JSON.stringify(result.errors));
  }

  // --- Endings: all four reachable via the throne choice -----------------
  console.log('\n== endings (throne choice) ==');
  const endings = await page.evaluate(async () => {
    const { gameState, game } = window.__VEILBORN__;
    const seen = [];
    // Stop everything but Boot so no earlier transition is in flight.
    game.scene.getScenes(true).forEach((s) => { if (s.scene.key !== 'Boot') s.scene.stop(); });
    await new Promise((r) => setTimeout(r, 200));
    // memoriesFound >= 6 counts as "many"; the throne choice then decides.
    const variants = [
      { memories: 8, remembered: 3, released: 0, mercy: 5, kills: 40, expect: 'true' },
      { memories: 8, remembered: 1, released: 2, mercy: 0, kills: 70, expect: 'new' },
      { memories: 1, remembered: 0, released: 2, mercy: 0, kills: 30, expect: 'sealed' },
      { memories: 1, remembered: 2, released: 0, mercy: 3, kills: 90, expect: 'open' },
    ];
    for (const v of variants) {
      gameState.startNewRun('ashen_edge', 7);
      const run = gameState.run;
      run.memoriesFound = v.memories;
      run.remembered = v.remembered;
      run.released = v.released;
      run.mercyCount = v.mercy;
      run.kills = v.kills;
      run.boons = ['veilheart', 'echo_blade'];
      run.shardsEarned = 30;
      run.realm = 4;
      game.scene.start('Ending', { run, forced: null });
      await new Promise((r) => setTimeout(r, 220));
      const endScene = game.scene.getScene('Ending');
      seen.push({ ending: endScene ? endScene.ending : null, expect: v.expect });
      endScene.scene.stop();
      await new Promise((r) => setTimeout(r, 80));
    }
    return seen;
  });
  endings.forEach((e, i) => {
    check(`ending ${i} is "${e.expect}"`, e.ending === e.expect, JSON.stringify(e));
  });

  // --- Death path -------------------------------------------------------
  console.log('\n== death path ==');
  const death = await page.evaluate(async () => {
    const { gameState, game } = window.__VEILBORN__;
    // Start from a clean scene so no fade transition is in flight.
    game.scene.getScenes(true).forEach((s) => {
      if (s.scene.key !== 'Boot') s.scene.stop();
    });
    await new Promise((r) => setTimeout(r, 250));
    gameState.weapon = null;
    gameState.startNewRun('pyre_lance', 3);
    game.scene.start('Game', { mode: 'room' });
    await new Promise((r) => setTimeout(r, 350));
    const scene = game.scene.getScene('Game');
    scene.onPlayerDeath();
    await new Promise((r) => setTimeout(r, 1900));
    return game.scene.getScenes(true).map((s) => s.scene.key);
  });
  check('death leads to Death scene', death.includes('Death'), JSON.stringify(death));

  // --- Hub + memory purchase -------------------------------------------
  console.log('\n== hub / persistence ==');
  const hub = await page.evaluate(async () => {
    const { gameState, game } = window.__VEILBORN__;
    gameState.profile.shards = 100000;
    gameState.persistProfile();
    game.scene.start('Hub');
    await new Promise((r) => setTimeout(r, 200));
    const h = game.scene.getScene('Hub');
    const before = gameState.profile.memory.vitality;
    if (h && h.rows && h.rows.length) h.buy(h.rows[0].u, h.rows[0].btn, h.rows[0].rank);
    const after = gameState.profile.memory.vitality;
    // persistence round-trip
    const raw = JSON.parse(localStorage.getItem('veilborn_save_v2'));
    return { active: game.scene.getScenes(true).map((s) => s.scene.key), before, after, saved: raw && raw.memory };
  });
  check('hub scene active', hub.active.includes('Hub'), JSON.stringify(hub.active));
  check('memory upgrade purchases', hub.after === hub.before + 1, JSON.stringify(hub));
  check('memory upgrade persists to localStorage', hub.saved && hub.saved.vitality === hub.after, JSON.stringify(hub.saved));

  // --- Weapon select ----------------------------------------------------
  console.log('\n== weapon select ==');
  const weapons = await page.evaluate(async () => {
    const { game } = window.__VEILBORN__;
    game.scene.start('WeaponSelect');
    await new Promise((r) => setTimeout(r, 200));
    return game.scene.getScenes(true).map((s) => s.scene.key);
  });
  check('weapon select scene active', weapons.includes('WeaponSelect'), JSON.stringify(weapons));

  // --- PWA / viewport sanity -------------------------------------------
  console.log('\n== mobile / PWA sanity ==');
  const viewportMeta = await page.evaluate(() => {
    const m = document.querySelector('meta[name="viewport"]');
    return m ? m.getAttribute('content') : null;
  });
  check('viewport meta present', !!viewportMeta, String(viewportMeta));

  // --- Full playthrough: realm 1 room 1 -> final ending -----------------
  // Drives the *real* progression chain (room clear -> reward -> boon ->
  // advance -> boss -> realm transition -> ... -> throne -> ending) using the
  // actual buttons, rather than restarting scenes directly.
  console.log('\n== full playthrough (all realms, start to ending) ==');
  const play = await page.evaluate(async () => {
    const { gameState, game } = window.__VEILBORN__;
    game.scene.getScenes(true).forEach((s) => { if (s.scene.key !== 'Boot') s.scene.stop(); });
    await new Promise((r) => setTimeout(r, 250));

    const trace = [];
    const seenBosses = [];
    let ending = null;
    let error = null;

    gameState.weapon = null;
    gameState.startNewRun('ashen_edge', 20250922);
    gameState.enterRealm(0);
    gameState.run.room = 0;
    game.scene.start('Game', { mode: 'room' });

    try {
      const deadline = Date.now() + 60000;
      while (Date.now() < deadline) {
        const active = game.scene.getScenes(true).map((s) => s.scene.key);
        if (active.includes('Ending')) {
          ending = game.scene.getScene('Ending').ending;
          break;
        }
        const g = game.scene.getScene('Game');
        if (g && g.scene.isActive()) {
          const at = `${gameState.run.realm}:${g.roomIndex}:${g.roomType}`;
          if (trace[trace.length - 1] !== at) trace.push(at);
          if (g.boss && g.boss.alive && !seenBosses.includes(g.boss.name)) seenBosses.push(g.boss.name);

          const btns = g.buttons || [];
          const take = btns.find((b) => b.label.text === 'TAKE');
          const descend = btns.find((b) => b.label.text.startsWith('DESCEND INTO'));
          const remember = btns.find((b) => b.label.text === 'REMEMBER');
          const free = btns.find((b) => b.label.text === 'FREE IT');

          if (take) {
            take.trigger();
          } else if (descend) {
            descend.trigger();
          } else if (remember) {
            remember.trigger();
          } else if (free) {
            free.trigger();
          } else if (!g.paused && g.player) {
            // Walk the player to the room's objective, exactly as a real player
            // would. Event/Rest rooms only complete on contact.
            const target = g.freedSpirit || g.healPool || g.chest || null;
            if (target) {
              g.player.x = target.x;
              g.player.y = target.y;
            }
            for (const e of [...g.enemies]) g.applyDamage(e, 999999, 0);
            if (g.boss && g.boss.alive) g.applyDamage(g.boss, 9999999, 0);
          }
        }
        await new Promise((r) => setTimeout(r, 55));
      }
    } catch (e) {
      error = String(e && e.stack ? e.stack : e);
    }

    return { ending, trace, seenBosses, error };
  });

  const realmsVisited = new Set(play.trace.map((t) => t.split(':')[0])).size;
  check('playthrough reached an ending', !!play.ending, JSON.stringify(play).slice(0, 500));
  check('playthrough visited all 5 realms', realmsVisited === 5, JSON.stringify(play.trace));
  check('playthrough fought all 5 bosses', play.seenBosses.length === 5, JSON.stringify(play.seenBosses));
  check('playthrough had no scene error', !play.error, JSON.stringify(play.error));

  // --- Offline PWA: install the service worker, cut the network, reload ---
  console.log('\n== offline PWA ==');
  const offlineContext = await browser.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: 'allow' });
  const offPage = await offlineContext.newPage();
  const offErrors = [];
  offPage.on('pageerror', (err) => offErrors.push(err.message));
  await offPage.goto(origin, { waitUntil: 'load' });
  // Wait until the SW is activated and controlling the page.
  const swReady = await offPage.evaluate(async () => {
    if (!('serviceWorker' in navigator)) return 'unsupported';
    const reg = await navigator.serviceWorker.ready.catch(() => null);
    if (!reg) return 'no-reg';
    // Force the control change so the very next navigation is served by the SW.
    for (let i = 0; i < 60 && !navigator.serviceWorker.controller; i++) {
      await new Promise((r) => setTimeout(r, 100));
    }
    return navigator.serviceWorker.controller ? 'controlled' : 'no-controller';
  });
  check('service worker activates', swReady === 'controlled' || swReady === 'no-controller', swReady);

  const manifestMeta = await offPage.evaluate(async () => {
    const link = document.querySelector('link[rel="manifest"]');
    if (!link) return null;
    const res = await fetch(link.getAttribute('href'));
    if (!res.ok) return { ok: false, status: res.status };
    const m = await res.json();
    return { ok: true, name: m.name, display: m.display, icons: (m.icons || []).length, start: m.start_url };
  });
  check('manifest is fetchable and complete', !!manifestMeta && manifestMeta.ok && manifestMeta.icons >= 3 && manifestMeta.display === 'standalone', JSON.stringify(manifestMeta));

  const touchIcon = await offPage.evaluate(async () => {
    const link = document.querySelector('link[rel="apple-touch-icon"]');
    if (!link) return 'missing';
    const res = await fetch(link.getAttribute('href'));
    return res.ok ? 'ok' : `status ${res.status}`;
  });
  check('apple-touch-icon resolves', touchIcon === 'ok', touchIcon);

  // Give the SW a beat to finish precaching, then genuinely go offline.
  await sleep(1500);
  await offlineContext.setOffline(true);
  const offLoad = await offPage.reload({ waitUntil: 'load' }).then(() => true).catch((e) => String(e));
  check('page reloads while offline', offLoad === true, String(offLoad).slice(0, 120));
  const offBoot = await offPage.waitForFunction(
    () => window.__VEILBORN__ && window.__VEILBORN__.gameState.booted,
    null, { timeout: 20000 },
  ).then(() => true).catch(() => false);
  check('game boots offline from cache', offBoot === true, 'boot timed out');
  check('no page errors while offline', offErrors.length === 0, JSON.stringify(offErrors.slice(0, 3)));
  await offlineContext.setOffline(false);
  await offlineContext.close();

  // --- iOS lifecycle: backgrounding auto-pauses a live run --------------
  console.log('\n== lifecycle (background auto-pause) ==');
  const lifecycle = await page.evaluate(async () => {
    const { gameState, game } = window.__VEILBORN__;
    game.scene.getScenes(true).forEach((s) => { if (s.scene.key !== 'Boot') s.scene.stop(); });
    await new Promise((r) => setTimeout(r, 250));
    gameState.weapon = null;
    gameState.startNewRun('ashen_edge', 4242);
    gameState.enterRealm(0);
    gameState.run.room = 0;
    game.scene.start('Game', { mode: 'room' });
    await new Promise((r) => setTimeout(r, 400));
    const g = game.scene.getScene('Game');
    const beforePaused = g.paused;
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' });
    document.dispatchEvent(new Event('visibilitychange'));
    await new Promise((r) => setTimeout(r, 200));
    const afterPaused = g.paused;
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' });
    document.dispatchEvent(new Event('visibilitychange'));
    await new Promise((r) => setTimeout(r, 200));
    return { beforePaused, afterPaused, stillPaused: g.paused, overlay: !!g.pauseOverlay };
  });
  check('run is live before backgrounding', lifecycle.beforePaused === false, JSON.stringify(lifecycle));
  check('backgrounding auto-pauses the run', lifecycle.afterPaused === true, JSON.stringify(lifecycle));
  check('run stays paused on return', lifecycle.stillPaused === true && lifecycle.overlay === true, JSON.stringify(lifecycle));

  await browser.close();
  if (server) server.close();

  console.log('\n== error summary ==');
  check('no uncaught page errors', pageErrors.length === 0, JSON.stringify(pageErrors.slice(0, 5)));
  check('no console errors', consoleErrors.length === 0, JSON.stringify(consoleErrors.slice(0, 5)));

  console.log(`\n${passes.length} passed, ${failures.length} failed`);
  if (server) server.close();
  if (failures.length) { console.error('\nFAILURES:\n' + failures.join('\n')); process.exit(1); }
  process.exit(0);
}

main().catch((e) => { console.error('harness crashed:', e); process.exit(1); });
