"""Does Zeus's Strike boon chain lightning to the foe beside the struck one?"""
import sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:12011/?debug=1"

with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_context(viewport={"width": 390, "height": 780}).new_page()
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(URL, wait_until="load")
    p.wait_for_timeout(500)
    p.click("#playBtn")
    p.wait_for_function("()=>window.__game&&window.__game.state", timeout=30000)
    p.wait_for_timeout(400)

    def run(bind_zeus):
        return p.evaluate(
            """(bindZeus) => {
                 const g = window.__game, r = g.room, s = g.state;
                 if (g.mode === 'playing') g.openPause();
                 r.cleared = true; r.enemies.length = 0; r.projectiles.length = 0;
                 if (bindZeus) g.bindPower('zeus', 'attack');
                 s.player.x = 200; s.player.y = 300;
                 s.player.faceX = 1; s.player.faceY = 0;
                 // struck foe directly ahead, its neighbour just beside it (60px)
                 r.enemies.push({ kind: 'brute', x: 240, y: 300, r: 22, hp: 500,
                   max: 500, speed: 0, dmg: 0, color: '#d96a4f', atk: 9, shoot: 9 });
                 r.enemies.push({ kind: 'brute', x: 240, y: 430, r: 22, hp: 500,
                   max: 500, speed: 0, dmg: 0, color: '#d96a4f', atk: 9, shoot: 9 });
                 s.swingCd = 0;
                 g.swing();
                 return { hpA: r.enemies[0].hp, hpB: r.enemies[1].hp,
                          seAttack: JSON.parse(JSON.stringify(s.se.attack || {})),
                          reach: s.reach };
               }""", bind_zeus)

    off = run(False)
    on = run(True)
    p.wait_for_timeout(200)
    print("without Zeus strike:", off)
    print("with    Zeus strike:", on)

    def dmg(side):
        return round(500 - side["hpB"], 1)

    # Both runs hit foe A; foe B should only lose health when the chain fires.
    print()
    print("foe A damage (no boon):", round(500 - off["hpA"], 1))
    print("foe A damage (Zeus)   :", round(500 - on["hpA"], 1))
    print("foe B damage (no boon):", dmg(off), " <- should be 0")
    print("foe B damage (Zeus)   :", dmg(on), " <- should be > 0")
    print("errors:", errs[:3] or "none")
    b.close()
