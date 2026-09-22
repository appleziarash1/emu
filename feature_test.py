"""Checks for the five weapons, the road through each chamber, and the walk
between chambers.

Weapons are tested by driving real swings and real arrows through the sim, so a
weapon that is only cosmetically different would fail here. The road and the
corridor are checked by sampling the canvas, because "there is a path" is a
visual claim.
"""
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:12001/?debug=1"

failures = []


def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + (("  -> " + str(detail)) if detail else ""))
    if not ok:
        failures.append(label)


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 390, "height": 780}, has_touch=True, is_mobile=True)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL, wait_until="load")
    page.click("#playBtn")
    page.wait_for_timeout(400)

    # --- weapons: each one must connect, and feel different from the others
    melee = page.evaluate("""() => {
      const g = window.__game, out = {};
      const ids = g.weapons.map((w) => w.id);
      for (const id of ids) {
        const w = g.weapons.find((x) => x.id === id);
        if (w.kind !== 'melee') continue;
        const s = g.state, r = g.room;
        r.enemies.length = 0;
        const p = s.player;
        s.dmg = 20; s.weapon = w;
        const e = { kind: 'shade', x: p.x + 30, y: p.y, r: 14, hp: 900, max: 900,
                    speed: 0, dmg: 0, color: '#8f7bd8', atk: 0 };
        r.enemies.push(e);
        p.hx = 1; p.hy = 0; p.faceX = 1; p.faceY = 0;
        s.swingCd = 0;
        g.swing();
        out[id] = { dealt: Math.round(900 - e.hp), cd: w.cooldown, reach: w.reach };
      }
      return out;
    }""")
    for wid, info in melee.items():
        check(wid + " lands a hit", info["dealt"] > 0, info)
    check("weapons deal different damage", len({v["dealt"] for v in melee.values()}) > 1,
          {k: v["dealt"] for k, v in melee.items()})
    check("hammer hits hardest", melee["hammer"]["dealt"] == max(v["dealt"] for v in melee.values()),
          melee["hammer"]["dealt"])
    check("daggers are the fastest", melee["daggers"]["cd"] == min(v["cd"] for v in melee.values()),
          melee["daggers"]["cd"])
    check("spear outranges the sword", melee["spear"]["reach"] > melee["xiphos"]["reach"],
          (melee["spear"]["reach"], melee["xiphos"]["reach"]))

    # the hammer must actually throw a body further than the sword does
    knock = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room;
      const out = {};
      for (const id of ['xiphos', 'hammer']) {
        const w = g.weapons.find((x) => x.id === id);
        r.enemies.length = 0;
        const p = s.player;
        s.dmg = 20; s.weapon = w; s.knock = 0;
        const e = { kind: 'shade', x: p.x + 30, y: p.y, r: 14, hp: 900, max: 900,
                    speed: 0, dmg: 0, color: '#8f7bd8', atk: 0 };
        r.enemies.push(e);
        p.hx = 1; p.hy = 0; p.faceX = 1; p.faceY = 0;
        s.swingCd = 0;
        g.swing();
        out[id] = Math.round(Math.hypot(e.kx || 0, e.ky || 0));
      }
      return out;
    }""")
    check("hammer knocks foes back, sword does not", knock["hammer"] > 100 > knock["xiphos"], knock)

    # --- the bow: fires a real projectile that damages a distant foe
    bow = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room;
      const w = g.weapons.find((x) => x.id === 'bow');
      r.enemies.length = 0; r.projectiles.length = 0;
      const p = s.player;
      s.dmg = 25; s.weapon = w;
      // well beyond any melee reach
      const e = { kind: 'shade', x: p.x + 200, y: p.y, r: 14, hp: 900, max: 900,
                  speed: 0, dmg: 0, color: '#8f7bd8', atk: 0 };
      r.enemies.push(e);
      p.hx = 1; p.hy = 0; p.faceX = 1; p.faceY = 0;
      s.swingCd = 0;
      g.swing();
      const fired = r.projectiles.filter((pr) => pr.kind === 'arrow').length;
      return { fired, hp: e.hp, reach: w.reach };
    }""")
    check("bow looses an arrow", bow["fired"] == 1, bow)
    check("bow reaches past melee range", bow["reach"] > 300, bow["reach"])

    page.wait_for_timeout(700)      # let the arrow travel
    landed = page.evaluate("""() => {
      const r = window.__game.room;
      return { hp: r.enemies[0] ? r.enemies[0].hp : null };
    }""")
    check("arrow damages the distant foe", landed["hp"] is not None and landed["hp"] < 900, landed)

    # --- swapping arms mid-run is offered and works
    swap = page.evaluate("""() => {
      const g = window.__game, s = g.state;
      s.depth = 1;
      g.state.dmg = 400;
      // clear the room so the reward screen opens
      g.room.enemies.length = 0;
      return true;
    }""")
    page.wait_for_timeout(900)
    cards = page.evaluate("""() => {
      const cards = [...document.querySelectorAll('#cardsBody .card')];
      return { count: cards.length, trades: cards.filter((c) => c.textContent.includes('CHANGE YOUR ARM')).length,
               title: document.getElementById('cardsTitle').textContent };
    }""")
    check("reward screen offers weapon trades", cards["trades"] == 4, cards)

    traded = page.evaluate("""() => {
      const cards = [...document.querySelectorAll('#cardsBody .card')];
      const trade = cards.find((c) => c.textContent.includes('Spear'));
      if (!trade) return null;
      trade.click();
      const g = window.__game;
      return { weapon: g.state.weapon.id, mode: g.mode };
    }""")
    check("trading a weapon takes effect immediately",
          traded and traded["weapon"] == "spear" and traded["mode"] == "playing", traded)

    # --- the road: a chamber has one, and it runs from the entry to the gate
    road = page.evaluate("""() => {
      const g = window.__game, r = g.room;
      if (!r.road) return null;
      const pts = r.road.pts;
      const first = pts[0], last = pts[pts.length - 1];
      return { points: pts.length, width: r.road.width,
               entry: r.entry, door: { x: r.door.x, y: r.door.y },
               startsAtEntry: Math.hypot(first.x - r.entry.x, first.y - r.entry.y) < 1,
               endsAtGate: Math.hypot(last.x - r.door.x, last.y - r.door.y) < 1,
               bends: pts.length - 2 };
    }""")
    check("each chamber has a road", road is not None, road)
    check("road starts at the entry", road and road["startsAtEntry"], road and road["entry"])
    check("road ends at the gate", road and road["endsAtGate"], road and road["door"])
    check("road bends rather than running straight", road and road["bends"] >= 2, road and road["bends"])

    # and it is actually painted: sample the canvas along the road against a spot
    # far off it, and the road pixels must differ.
    painted = page.evaluate("""() => {
      const g = window.__game, r = g.room;
      const c = document.getElementById('stage');
      const ctx = c.getContext('2d');
      const dpr = c.width / window.innerWidth;
      const s = g.cam.scale;
      const mid = r.road.pts[Math.floor(r.road.pts.length / 2)];
      const toScreen = (x, y) => [Math.round((x - g.cam.x) * s * dpr), Math.round((y - g.cam.y) * s * dpr)];
      const [rx, ry] = toScreen(mid.x, mid.y);
      const roadPx = ctx.getImageData(rx, ry, 1, 1).data;
      // a corner is always far from the road
      const [ox, oy] = toScreen(10, 10);
      const offPx = ctx.getImageData(ox, oy, 1, 1).data;
      const diff = Math.abs(roadPx[0] - offPx[0]) + Math.abs(roadPx[1] - offPx[1]) + Math.abs(roadPx[2] - offPx[2]);
      return { roadPx: [...roadPx].slice(0, 3), offPx: [...offPx].slice(0, 3), diff };
    }""")
    check("the road is visibly paved", painted["diff"] > 12, painted)

    # --- the corridor: reaching the gate walks a scene instead of cutting
    page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room;
      r.cleared = true;
      s.depth = 1;
      s.player.x = r.door.x; s.player.y = r.door.y;
    }""")
    page.wait_for_timeout(300)
    walk = page.evaluate("""() => ({ mode: window.__game.mode,
                                     depth: window.__game.state.depth,
                                     visible: !document.getElementById('corridor').hidden })""")
    check("walking through the gate opens the corridor",
          walk["mode"] == "corridor" and walk["visible"], walk)
    check("the corridor has not advanced the depth yet", walk["depth"] == 1, walk["depth"])

    corridor_px = page.evaluate("""() => {
      const c = document.getElementById('stage');
      const ctx = c.getContext('2d');
      const dpr = c.width / window.innerWidth;
      const cx = Math.round(c.width / 2);
      const near = ctx.getImageData(cx, Math.round(c.height * 0.9), 1, 1).data;
      const top = ctx.getImageData(cx, Math.round(c.height * 0.05), 1, 1).data;
      const diff = Math.abs(near[0] - top[0]) + Math.abs(near[1] - top[1]) + Math.abs(near[2] - top[2]);
      return { near: [...near].slice(0, 3), top: [...top].slice(0, 3), diff };
    }""")
    check("the corridor scene is drawn", corridor_px["diff"] > 10, corridor_px)

    # skipping must land in the next chamber with the HUD back
    page.click("#corridorSkip")
    page.wait_for_timeout(300)
    after_skip = page.evaluate("""() => ({
      mode: window.__game.mode,
      depth: window.__game.state.depth,
      hud: document.getElementById('hud').classList.contains('on'),
      enemies: window.__game.room.enemies.length,
      hidden: document.getElementById('corridor').hidden })""")
    check("skipping the walk enters the next depth",
          after_skip["mode"] == "playing" and after_skip["depth"] == 2, after_skip)
    check("the next chamber is populated and the HUD is back",
          after_skip["enemies"] > 0 and after_skip["hud"] and after_skip["hidden"], after_skip)

    print("page errors:", errors[:5] or "none")
    browser.close()

if failures:
    print("\nFEATURE CHECK FAILED:", ", ".join(failures))
    sys.exit(1)
print("\nFEATURE CHECK PASSED")
