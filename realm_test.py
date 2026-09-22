"""Realm overhaul tests.

Each realm must be a different place, not the same place recoloured: its own
palette, its own foes with their own behaviour, its own hazard, its own boss.
These checks drive the real game code in a browser and assert on what it builds.
"""
import sys

from playwright.sync_api import sync_playwright

URL = "http://localhost:12001/?debug=1"
FAILS = []


def check(cond, label):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page(viewport={"width": 390, "height": 780},
                          has_touch=True, is_mobile=True)
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(URL, wait_until="load")
        page.wait_for_timeout(1200)
        check(not errs, "no page errors at boot: " + str(errs[:3]))

        realms = page.evaluate("() => window.__game.REALMS.map(r => r.id)")
        check(len(realms) == 5, "five realms are defined")
        check(realms == ['tartarus', 'asphodel', 'elysium', 'styx', 'surface'],
              "realms are in depth order: " + str(realms))

        # Distinct design: no two realms may share a floor or wall palette, a
        # prop list, a hazard, a foe roster, or a boss.
        uniq = page.evaluate("""() => {
          const R = window.__game.REALMS;
          const k = (o) => JSON.stringify(o);
          return {
            floors: new Set(R.map(r => r.pal.floorA + r.pal.floorB)).size,
            walls: new Set(R.map(r => r.pal.wall)).size,
            props: new Set(R.map(r => k(r.props))).size,
            hazards: new Set(R.map(r => k(r.hazard))).size,
            foes: new Set(R.map(r => k(r.foes.map(f => f.kind)))).size,
            bosses: new Set(R.map(r => r.boss)).size,
            blurb: new Set(R.map(r => r.blurb)).size,
            tags: new Set(R.map(r => r.tag)).size,
          };
        }""")
        for field in uniq:
            if field == 'hazards':
                # Tartarus and Elysium are the two realms with no standing
                # hazard, so four distinct hazard signatures is the most the
                # table can hold; the specifics are asserted further down.
                check(uniq[field] >= 4, "realms differ in hazards (" + str(uniq[field]) + " kinds)")
            else:
                check(uniq[field] == 5, "all five realms differ in " + field)

        # Enemy power must rise realm over realm, not just within one.
        power = page.evaluate("""() => {
          const g = window.__game, R = g.REALMS;
          return R.map(r => {
            const t = r.foes.reduce((a, f) => a + f.w, 0);
            return r.foes.reduce((a, f) => a + (f.hp + f.dmg * 4 + f.speed * 0.3) * (f.w / t), 0);
          });
        }""")
        check(all(power[i] < power[i + 1] for i in range(4)),
              "realm foe power rises each realm: " +
              str([round(x, 1) for x in power]))

        # Every realm spawns only its own foes, and a boss of its own realm.
        spawns = page.evaluate("""() => {
          const g = window.__game;
          g.start();
          const out = [];
          for (const d of [1, 3, 6, 8, 11, 13, 16, 18, 21, 23, 5, 10, 15, 20, 25]) {
            g.state.depth = d;
            g.newRoom();
            g.room.enemies.length = 0;
            if (g.room.isBoss) g.spawnBoss(d); else g.spawnEnemy(d);
            out.push({ d, realm: g.room.realm,
                       kinds: g.room.enemies.map(e => e.kind),
                       kits: g.room.enemies.map(e => e.kit).filter(Boolean) });
          }
          return out;
        }""")
        by_depth = {s['d']: s for s in spawns}
        for d, want in [(1, 'tartarus'), (3, 'tartarus'), (6, 'asphodel'), (8, 'asphodel'),
                        (11, 'elysium'), (13, 'elysium'), (16, 'styx'), (18, 'styx'),
                        (21, 'surface'), (23, 'surface')]:
            s = by_depth[d]
            check(s['realm'] == want, f"depth {d} builds in {want}")
            roster = page.evaluate(
                "(rid) => window.__game.REALMS.find(r => r.id === rid).foes.map(f => f.kind)", want)
            check(all(k in roster for k in s['kinds']),
                  f"depth {d} spawns only {want} foes: {s['kinds']}")

        # Bosses are distinct, and the champions boss is a pair.
        for d, kit in [(5, 'fury'), (10, 'hydra'), (15, 'champions'),
                       (20, 'hound'), (25, 'lord')]:
            s = by_depth[d]
            check(s['kits'] and all(k == kit for k in s['kits']),
                  f"depth {d} boss uses the {kit} kit")

        boss_names = page.evaluate("""() => {
          const g = window.__game; g.start(); const names = [];
          for (const d of [5, 10, 15, 20, 25]) {
            g.state.depth = d; g.newRoom();
            names.push(g.room.bossName);
          }
          return names;
        }""")
        check(len(set(boss_names)) == 5, "five distinct boss names: " + str(boss_names))

        # Hazards: Asphodel pools are lava, Styx pools are poison, and the safe
        # realms get none at all.
        pools = page.evaluate("""() => {
          const g = window.__game; g.start(); const out = {};
          for (const d of [1, 6, 11, 16]) {
            g.state.depth = d; g.newRoom();
            const kinds = [...new Set(g.room.hazardPools.map(h => h.kind))];
            out[d] = { n: g.room.hazardPools.length, kinds };
          }
          return out;
        }""")
        check(pools['1']['n'] == 0, "Tartarus has no standing hazard")
        check(pools["6"]["kinds"] == ["lava"] and pools["6"]["n"] > 0,
              "Asphodel pools are lava: " + str(pools["6"]))
        check(pools['11']['n'] == 0, "Elysium has no standing hazard")
        check(pools["16"]["kinds"] == ["poison"] and pools["16"]["n"] > 0,
              "Styx pools are poison: " + str(pools["16"]))

        # Pools never block the gate, the entry or the road.
        clear = page.evaluate("""() => {
          const g = window.__game; g.start();
          let worst = Infinity, n = 0;
          for (let d = 6; d <= 25; d++) {
            g.state.depth = d; g.newRoom();
            for (const h of g.room.hazardPools) {
              n++;
              worst = Math.min(worst,
                Math.hypot(h.x - g.room.door.x, h.y - g.room.door.y) - h.r,
                Math.hypot(h.x - g.room.entry.x, h.y - g.room.entry.y) - h.r,
                g.roadDistance(h.x, h.y) - h.r);
            }
          }
          return { worst, n };
        }""")
        check(clear['n'] > 0 and clear['worst'] > 0,
              "hazard pools keep clear of gate, entry and road: " + str(clear))

        # A hazard is a hazard: standing in one drains health, but cannot kill.
        hazard = page.evaluate("""() => {
          const g = window.__game;
          g.start(); g.state.depth = 6; g.newRoom();
          g.state.hp = g.state.maxHp;
          const hp0 = g.state.hp;
          g.room.enemies.length = 0;
          const h = g.room.hazardPools[0];
          g.state.player.x = h.x; g.state.player.y = h.y;
          for (let i = 0; i < 60; i++) g.tick(1 / 60);
          const after = g.state.hp;
          // now park on it with almost no health: it must not be lethal
          g.state.hp = 3; g.state.inv = 0;
          for (let i = 0; i < 120; i++) { g.room.enemies.length = 0; g.tick(1 / 60); }
          return { drained: after < hp0, floor: g.state.hp, alive: g.state.hp > 0 };
        }""")
        check(hazard['drained'], "lava drains health with no attack")
        check(hazard['alive'] and hazard['floor'] >= 1,
              "lava leaves the hero at 1 hp rather than killing: " + str(hazard['floor']))

        # Kill styles: a cinder detonates when it dies, and a reviver gets back up
        # exactly once.
        kills = page.evaluate("""() => {
          const g = window.__game;
          g.start(); g.state.depth = 6; g.newRoom();
          g.room.enemies.length = 0;
          g.spawnEnemy(8);
          const e = g.room.enemies[0];
          e.kind = 'cinder'; e.boom = 1; e.hp = 1; e.max = 1;
          g.hurtEnemy(e, 999, null);
          const boomed = g.room.projectiles.some(p => p.kind === 'blast');

          g.state.depth = 11; g.newRoom();
          g.room.enemies.length = 0;
          g.spawnEnemy(12);
          const r2 = g.room.enemies[0];
          r2.kind = 'eidolon'; r2.revive = 1; r2.hp = 1; r2.max = 40;
          g.hurtEnemy(r2, 999, null);
          const first = { dead: !!r2.dead, reviving: r2.reviving > 0 };
          r2.reviving = 0.001;
          g.tick(0.05);
          const back = r2.hp > 0 && !r2.dead;
          r2.hp = 1;
          g.hurtEnemy(r2, 999, null);
          const second = !!r2.dead;
          return { boomed, first, back, second };
        }""")
        check(kills['boomed'], "a cinder bursts when it is killed")
        check(kills['first']['reviving'] and not kills['first']['dead'],
              "a reviver drops instead of dying the first time")
        check(kills['back'], "a reviver stands back up")
        check(kills['second'], "a reviver stays dead the second time")

        # A shield eats blows before health, and breaks with a tell.
        shield = page.evaluate("""() => {
          const g = window.__game;
          g.start(); g.state.depth = 11; g.newRoom();
          g.room.enemies.length = 0; g.spawnEnemy(11);
          const e = g.room.enemies[0];
          e.kind = 'hoplite'; e.shield = 20; e.shieldMax = 20; e.hp = 100; e.max = 100;
          g.hurtEnemy(e, 12, null);
          const a = { hp: e.hp, sh: e.shield };
          g.hurtEnemy(e, 30, null);
          const b = { hp: e.hp, sh: e.shield };
          return { a, b };
        }""")
        check(shield['a']['hp'] == 100 and shield['a']['sh'] == 8,
              "the first blows land on the shield, not the flesh: " + str(shield['a']))
        check(shield['b']['hp'] < 100 and shield['b']['sh'] == 0,
              "overflow damage reaches health once the shield breaks: " + str(shield['b']))

        # Boss scaling is unchanged by the overhaul: 5x per boss encounter.
        scale = page.evaluate("""() => {
          const g = window.__game; g.start(); const out = {};
          for (const d of [5, 10, 15]) {
            g.state.depth = d; g.newRoom();
            out[d] = g.room.enemies.reduce((a, e) => a + e.max, 0);
          }
          return out;
        }""")
        check(abs(scale['10'] / scale['5'] - 5) < 0.05,
              f"depth 10 boss is 5x depth 5: {scale['5']} -> {scale['10']}")
        check(abs(scale['15'] / scale['5'] - 25) < 0.1,
              f"depth 15 boss is 25x depth 5: {scale['5']} -> {scale['15']}")

        # A real play-through of every realm must not throw, and the draw pass for
        # each realm's boss must survive a frame.
        played = page.evaluate("""() => {
          const g = window.__game, errs = [];
          g.start();
          for (const d of [1, 6, 11, 16, 21, 5, 10, 15, 20, 25]) {
            try {
              g.state.depth = d; g.newRoom();
              for (let i = 0; i < 90; i++) g.tick(1 / 60);
              g.frame(performance.now() + 16);
            } catch (e) { errs.push(d + ': ' + e.message); }
          }
          return errs;
        }""")
        check(not played, "every realm runs 90 frames clean: " + str(played))
        check(not errs, "no page errors after running every realm: " + str(errs[:3]))

        b.close()

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED:")
        for f in FAILS:
            print("  - " + f)
        sys.exit(1)
    print("realm_test: all checks passed")


if __name__ == "__main__":
    main()
