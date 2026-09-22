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

    # --- the reward screen offers gods only: the arm is locked for the run
    page.evaluate("""() => {
      const g = window.__game, s = g.state;
      s.depth = 1;
      s.dmg = 400;
      g.room.enemies.length = 0;   // clear the room so the reward screen opens
    }""")
    page.wait_for_timeout(900)
    cards = page.evaluate("""() => {
      const cards = [...document.querySelectorAll('#cardsBody .card')];
      return { count: cards.length,
               want: window.__game.offerCount,
               sub: document.getElementById('cardsSub').textContent,
               trades: cards.filter((c) => c.textContent.includes('CHANGE YOUR ARM')).length,
               weapons: cards.filter((c) => c.textContent.includes('Xiphos') ||
                                             c.textContent.includes('Spear') ||
                                             c.textContent.includes('Fangs') ||
                                             c.textContent.includes('Hammer') ||
                                             c.textContent.includes('Bow')).length,
               title: document.getElementById('cardsTitle').textContent };
    }""")
    check("reward screen offers gods only", cards["trades"] == 0 and cards["weapons"] == 0, cards)
    check("reward screen offers exactly two gods",
          cards["count"] == 2 and cards["want"] == 2, cards["count"])
    check("the reward screen explains the pair", "Two gods" in cards["sub"], cards["sub"])

    # A god card no longer binds itself: it opens the slot chooser, and the
    # binding only happens when the player says where the power goes.
    picked = page.evaluate("""() => {
      const g = window.__game;
      const held = g.state.weapon.id;
      document.querySelector('#cardsBody .card').click();
      const slots = [...document.querySelectorAll('#slotsBody .slot')];
      return { held, mode: g.mode, slots: slots.length,
               suggested: slots.filter((s) => s.querySelector('.tag')).length,
               after: g.state.weapon.id };
    }""")
    check("picking a god opens the slot chooser",
          picked["mode"] == "slot" and picked["slots"] == 3, picked)
    check("the chooser flags a suggested slot", picked["suggested"] >= 1, picked)

    bound = page.evaluate("""() => {
      const g = window.__game;
      const held = g.state.weapon.id;
      document.querySelector('#slotsBody .slot').click();
      return { held, after: g.state.weapon.id, mode: g.mode,
               filled: Object.values(g.state.slots).filter(Boolean).length };
    }""")
    check("binding a power keeps the chosen arm and returns to play",
          bound["after"] == bound["held"] and bound["mode"] == "playing" and
          bound["filled"] == 1, bound)

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

    # --- the chamber is larger than the viewport, so the camera has to pan
    size = page.evaluate("""() => {
      const g = window.__game, r = g.room;
      return { w: r.w, h: r.h, vw: window.innerWidth / g.cam.scale,
               vh: window.innerHeight / g.cam.scale, inset: r.inset,
               torches: r.torches.length, pillars: r.pillars.length,
               rubble: r.rubble.length, bones: r.bones.length };
    }""")
    check("the chamber is wider than the view", size["w"] > size["vw"] * 1.3,
          (size["w"], round(size["vw"])))
    check("the chamber is taller than the view", size["h"] > size["vh"] * 1.3,
          (size["h"], round(size["vh"])))
    check("the chamber is walled", size["inset"] >= 40, size["inset"])
    check("the walls are dressed with torches and pillars",
          size["torches"] >= 2 and size["pillars"] >= 1, size)
    check("the floor is dressed with rubble and bone",
          size["rubble"] >= 4 and size["bones"] >= 2, size)

    # panning: walking to one side of the hall must move the camera, not the hero
    # alone, and the camera must never show past the walls
    pan = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room;
      s.player.x = r.inset + 60; s.player.y = r.h / 2;
      return { x: s.player.x };
    }""")
    page.wait_for_timeout(500)
    left = page.evaluate("""() => ({ cam: window.__game.cam.x, player: window.__game.state.player.x })""")
    page.evaluate("""() => { const r = window.__game.room; window.__game.state.player.x = r.w - r.inset - 60; }""")
    page.wait_for_timeout(700)
    right = page.evaluate("""() => {
      const g = window.__game, r = g.room;
      const vw = window.innerWidth / g.cam.scale;
      return { cam: g.cam.x, player: g.state.player.x, maxCam: r.w - vw,
               wall: r.w - r.inset };
    }""")
    check("the camera pans as the hero crosses the hall", right["cam"] > left["cam"] + 60,
          (round(left["cam"]), round(right["cam"])))
    check("the camera never shows past the far wall",
          0 <= right["cam"] <= right["maxCam"] + 0.6, right)
    check("the hero is held inside the wall", right["player"] <= right["wall"] + 1, right)

    # --- the walls actually block: shoving the hero at a wall must not pass it
    blocked = page.evaluate("""() => {
      const g = window.__game, s = g.state, r = g.room;
      s.player.x = r.inset + 40; s.player.y = r.h / 2;
      s.player.hx = -1; s.player.hy = 0;
      return { inset: r.inset };
    }""")
    page.mouse.move(120, 600)
    page.mouse.down()
    page.mouse.move(20, 600, steps=6)
    page.wait_for_timeout(900)
    page.mouse.up()
    wall = page.evaluate("""() => {
      const g = window.__game, r = g.room;
      return { x: g.state.player.x, inset: r.inset };
    }""")
    check("the hero cannot walk through the wall", wall["x"] >= wall["inset"] - 1, wall)

    # --- the minimap: in a hall several screens across the gate must stay findable
    mini = page.evaluate("""() => {
      const g = window.__game, r = g.room;
      const c = document.getElementById('mapCanvas');
      const box = c.getBoundingClientRect();
      const px = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      const seen = new Set();
      for (let i = 0; i < px.length; i += 4 * 37) seen.add(px[i] + ',' + px[i+1] + ',' + px[i+2]);
      return { visible: box.width > 0 && box.height > 0, colors: seen.size,
               w: r.w, h: r.h };
    }""")
    check("the minimap is on screen", mini["visible"], mini)
    check("the minimap draws the chamber, road and gate", mini["colors"] > 5, mini)

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
