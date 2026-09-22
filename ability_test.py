"""The five abilities, and the pad and keyboard bindings that reach them.

The hero has one attack on each control: X strikes, Y throws the special, B casts
the spell, A dashes, and the Call spends the God Gauge. The same five are
reachable from a keyboard and from the on-screen buttons, and each has to be
independent — one press must not fire two abilities, and a cooling ability must
refuse rather than silently swallow the press.
"""
import sys
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:12001/?debug=1"
failures = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + ("  -> " + str(detail) if detail != "" else ""))
    if not ok:
        failures.append(name)


# A fake pad is installed into the page before the game runs: navigator.gamepads
# is read-only in a real browser, so the game talks to this stub through the
# same getGamepads() call it always uses.
PAD_STUB = """
() => {
  const state = { connected: true, buttons: new Array(17).fill(null).map(() => ({ pressed: false })),
                  axes: [0, 0] };
  window.__pad = state;
  navigator.getGamepads = () => (state.connected
    ? [{ axes: state.axes, buttons: state.buttons }]
    : [null]);
  return true;
}
"""

# A quiet chamber for measuring one ability at a time. The room is marked already
# cleared so an empty enemy list cannot open the reward screen — that would pause
# the simulation and make every ability look broken. No stand-in foe is added, so
# the enemies under test stay at index 0 where the checks expect them.
QUIET = """
() => {
  const g = window.__game;
  g.room.cleared = true;
  g.room.enemies.length = 0;
  g.state.maxHp = 100000; g.state.hp = 100000;
}
"""

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": 430, "height": 860})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL, wait_until="load")
    page.wait_for_timeout(200)

    # 1. All five buttons exist on the touch layer, not just the old two.
    IDS = "['btnHit', 'btnDash', 'btnSpec', 'btnSpell', 'btnCall']"
    ids = page.evaluate("""() => %s.map((id) => !!document.getElementById(id))""" % IDS)
    check("the touch layer carries all five abilities", all(ids), ids)
    labels = page.evaluate("""() => %s.map((id) => document.getElementById(id).textContent)""" % IDS)
    check("each touch button is labelled for its ability",
          labels == ["STRIKE", "DASH", "SPECIAL", "SPELL", "CALL"], labels)

    page.click("#playBtn")
    page.wait_for_timeout(400)

    # Park the run in a quiet corner so wandering foes cannot colour the results.
    page.evaluate(QUIET)
    page.evaluate("""() => {
      const p = window.__game.state.player;
      p.x = 480; p.y = 520;
    }""")
    page.evaluate("() => window.__game.setPadActive(true)")
    page.wait_for_timeout(200)

    # 2. The spell fires once, on its own, from a clean press. The nova is the
    #    marker: it is the only effect that reaches all around the hero.
    page.evaluate("() => window.__game.pressSpell()")
    page.wait_for_timeout(150)
    after_spell = page.evaluate("""() => ({
      novas: window.__game.room.projectiles.filter((x) => x.kind === 'nova').length,
      chakrams: window.__game.room.projectiles.filter((x) => x.kind === 'chakram').length,
      cd: window.__game.state.splCd })""")
    check("a spell press casts exactly one nova", after_spell["novas"] == 1, after_spell)
    check("a spell press does not also throw the special",
          after_spell["chakrams"] == 0, after_spell)
    check("casting the spell starts its cooldown", after_spell["cd"] > 0, after_spell)

    # 3. The special throws a blade, and the blade is not the spell.
    page.evaluate("() => window.__game.pressSpecial()")
    page.wait_for_timeout(150)
    after_spec = page.evaluate("""() => ({
      chakrams: window.__game.room.projectiles.filter((x) => x.kind === 'chakram').length,
      cd: window.__game.state.specCd })""")
    check("a special press throws exactly one blade", after_spec["chakrams"] == 1, after_spec)
    check("throwing the special starts its cooldown", after_spec["cd"] > 0, after_spec)

    # 4. On cooldown, a press is refused rather than stacking a second effect.
    page.evaluate("() => { window.__game.pressSpell(); }")
    page.wait_for_timeout(120)
    cooling = page.evaluate("""() => window.__game.room.projectiles
        .filter((x) => x.kind === 'nova').length""")
    check("a spell press on cooldown casts nothing", cooling <= 1, cooling)

    # 5. The spell earns its place: it hurts what is close and spares what is far.
    page.evaluate(QUIET)
    page.evaluate("""() => {
      const g = window.__game, r = g.room, p = g.state.player;
      r.projectiles.length = 0;
      g.state.splCd = 0;
      const mk = (dx, hp) => ({ kind: 'shade', x: p.x + dx, y: p.y, r: 22, hp, max: hp,
                                speed: 0, dmg: 1, color: '#888', atk: 0 });
      r.enemies.push(mk(60, 500), mk(500, 500));
    }""")
    page.evaluate("() => window.__game.castSpell()")
    page.wait_for_timeout(120)
    reach = page.evaluate("""() => window.__game.room.enemies.map((e) => e.hp)""")
    check("the spell wounds a nearby foe", reach[0] < 500, reach)
    check("the spell leaves a distant foe untouched", reach[1] == 500, reach)

    # 6. The spell clears hostile shots in its radius, which is its escape hatch.
    page.evaluate(QUIET)
    page.evaluate("""() => {
      const g = window.__game, p = g.state.player;
      g.state.splCd = 0;
      g.state.inv = 0;
      g.room.projectiles.push({ x: p.x + 40, y: p.y, vx: 0, vy: 0, r: 8, dmg: 5,
                                t: 4, kind: 'orb', hostile: true });
    }""")
    page.evaluate("() => window.__game.castSpell()")
    page.wait_for_timeout(150)
    orbs = page.evaluate("""() => window.__game.room.projectiles
        .filter((x) => x.kind === 'orb' && x.hostile).length""")
    check("the spell knocks incoming shots out of the air", orbs == 0, orbs)

    # 7. The blade cuts on the way out and again on the way home.
    page.evaluate(QUIET)
    page.evaluate("""() => {
      const g = window.__game, r = g.room, p = g.state.player;
      r.enemies.length = 0;
      r.projectiles.length = 0;
      g.state.specCd = 0;
      p.faceX = 1; p.faceY = 0;
      r.enemies.push({ kind: 'shade', x: p.x + 220, y: p.y, r: 26, hp: 900, max: 900,
                       speed: 0, dmg: 1, color: '#888', atk: 0 });
    }""")
    page.evaluate("() => window.__game.castSpecial()")
    page.wait_for_timeout(700)
    hp_one_pass = page.evaluate("() => window.__game.room.enemies[0].hp")
    page.wait_for_timeout(900)
    hp_both = page.evaluate("() => window.__game.room.enemies[0].hp")
    check("the thrown blade cuts a foe on the way out", hp_one_pass < 900, hp_one_pass)
    check("the blade cuts the same foe again on the way back", hp_both < hp_one_pass,
          (hp_one_pass, hp_both))
    returned = page.evaluate("""() => window.__game.room.projectiles
        .filter((x) => x.kind === 'chakram').length""")
    check("the blade is gone once it reaches the hero", returned == 0, returned)

    # 8. The pad's face buttons map to the abilities, checked one at a time so a
    #    shared code path cannot hide behind a passing neighbour.
    page.evaluate(PAD_STUB)
    page.wait_for_timeout(100)
    check("a connected pad hides the touch cluster",
          page.evaluate("() => window.__game.padActive"), True)
    hidden = page.evaluate("""() => %s
        .map((id) => getComputedStyle(document.getElementById(id)).display)""" % IDS)
    check("every touch button hides while the pad is steering",
          all(d == "none" for d in hidden), hidden)

    def tap(index, frames=6):
        page.evaluate(f"() => {{ window.__pad.buttons[{index}].pressed = true; }}")
        page.wait_for_timeout(90)
        page.evaluate(f"() => {{ window.__pad.buttons[{index}].pressed = false; }}")
        page.wait_for_timeout(frames * 20)

    # X strikes: a swing is visible as a swing timer starting up.
    page.evaluate(QUIET)
    page.evaluate("""() => { const g = window.__game;
                             g.room.projectiles.length = 0;
                             g.state.player.faceX = 1; g.state.player.faceY = 0;
                             g.state.swingCd = 0; g.state.swingT = 0; }""")
    tap(2)
    x_swung = page.evaluate("() => window.__game.state.swingT > 0 || window.__game.state.swingCd > 0")
    check("X strikes", x_swung, x_swung)

    page.evaluate(QUIET)
    page.evaluate("() => { window.__game.state.specCd = 0; window.__game.room.projectiles.length = 0; }")
    tap(3)
    y_threw = page.evaluate("""() => window.__game.room.projectiles
        .filter((x) => x.kind === 'chakram').length""")
    check("Y throws the special", y_threw == 1, y_threw)

    page.evaluate(QUIET)
    page.evaluate("() => { window.__game.state.splCd = 0; window.__game.room.projectiles.length = 0; }")
    tap(1)
    b_cast = page.evaluate("""() => window.__game.room.projectiles
        .filter((x) => x.kind === 'nova').length""")
    check("B casts the spell", b_cast == 1, b_cast)

    page.evaluate(QUIET)
    page.evaluate("""() => { const g = window.__game;
                             g.state.dashCd = 0; g.state.dashT = 0; g.state.inv = 0;
                             g.state.player.faceX = 0; g.state.player.faceY = 1; }""")
    tap(0)
    # The dash itself lasts 0.16s, which the tap's own wait can outlast, so the
    # cooldown is the reliable evidence that the press landed.
    a_dashed = page.evaluate("() => window.__game.state.dashCd > 0")
    check("A dashes", a_dashed, a_dashed)

    # The Call is the fifth verb. Every input has to reach it, or the strongest
    # button in the game is dead on whichever one was forgotten.
    CALL_READY = """() => {
      const g = window.__game, s = g.state;
      g.room.cleared = true; g.room.enemies.length = 0;
      s.slots.call = { slot: 'call', godId: 'zeus', name: 'Zeus Aid', level: 1 };
      s.se.call = {};
      s.gauge = 100;
      return true;
    }"""
    def gauge():
        return page.evaluate("() => window.__game.state.gauge")

    # dpad up, on a pad
    page.evaluate(CALL_READY)
    page.evaluate("() => { window.__pad.buttons[12].pressed = true; }")
    page.wait_for_timeout(120)
    page.evaluate("() => { window.__pad.buttons[12].pressed = false; }")
    page.wait_for_timeout(150)
    dpad = gauge()
    check("D-pad up spends the gauge", dpad == 0, dpad)

    page.evaluate("() => window.__game.setPadActive(false)")
    page.wait_for_timeout(120)
    # the on-screen button
    page.evaluate(CALL_READY)
    page.evaluate("() => document.getElementById('btnCall').click()")
    page.wait_for_timeout(180)
    btn = gauge()
    check("the CALL button spends the gauge", btn == 0, btn)

    # the keyboard, and that it does not also fire a neighbour. The Call draws its
    # own burst, so the tell is the spell's cooldown, not a projectile count.
    page.evaluate(CALL_READY)
    page.evaluate("""() => { const g = window.__game;
                             g.state.splCd = 0; g.state.specCd = 0;
                             g.room.projectiles.length = 0; }""")
    page.keyboard.press("o")
    page.wait_for_timeout(180)
    kb_call = page.evaluate("""() => ({
      gauge: window.__game.state.gauge,
      splCd: window.__game.state.splCd,
      specCd: window.__game.state.specCd })""")
    check("O spends the gauge from the keyboard", kb_call["gauge"] == 0, kb_call)
    check("O does not put the spell or the special on cooldown",
          kb_call["splCd"] == 0 and kb_call["specCd"] == 0, kb_call)

    # and that a short gauge refuses, so the Call cannot be spammed
    page.evaluate("""() => { const s = window.__game.state;
                             s.slots.call = { slot: 'call', godId: 'zeus', name: 'Zeus Aid', level: 1 };
                             s.se.call = {}; s.gauge = 40; }""")
    page.keyboard.press("o")
    page.wait_for_timeout(180)
    short = gauge()
    check("the Call refuses while the gauge is short", short == 40, short)

    # 9. Keyboard reaches the same verbs, and no key fires two abilities.
    page.evaluate("() => window.__game.setPadActive(false)")
    page.wait_for_timeout(120)
    page.evaluate(QUIET)
    page.evaluate("""() => { const g = window.__game;
                             g.state.splCd = 0; g.state.specCd = 0;
                             g.room.projectiles.length = 0; }""")
    page.keyboard.press("u")
    page.wait_for_timeout(150)
    kb_spell = page.evaluate("""() => ({
      novas: window.__game.room.projectiles.filter((x) => x.kind === 'nova').length,
      chakrams: window.__game.room.projectiles.filter((x) => x.kind === 'chakram').length })""")
    check("U casts the spell from the keyboard", kb_spell["novas"] == 1, kb_spell)
    check("U does not also throw the special", kb_spell["chakrams"] == 0, kb_spell)

    page.evaluate(QUIET)
    page.evaluate("""() => { const g = window.__game;
                             g.state.specCd = 0; g.room.projectiles.length = 0; }""")
    page.keyboard.press("i")
    page.wait_for_timeout(150)
    kb_spec = page.evaluate("""() => ({
      chakrams: window.__game.room.projectiles.filter((x) => x.kind === 'chakram').length,
      novas: window.__game.room.projectiles.filter((x) => x.kind === 'nova').length })""")
    check("I throws the special from the keyboard", kb_spec["chakrams"] == 1, kb_spec)
    check("I does not also cast the spell", kb_spec["novas"] == 0, kb_spec)

    check("the desktop hint lists every key",
          all(k in page.evaluate("() => document.getElementById('keyHint').textContent")
              for k in ["J", "U", "I", "Space"]),
          page.evaluate("() => document.getElementById('keyHint').textContent"))

    # 10. A blade still in the air must never hold the gate shut. The throw is the
    #     hero's own, so if the room is otherwise empty the way out has to open —
    #     a flight in progress must not be able to soft-lock the run.
    page.evaluate("""() => {
      const g = window.__game, r = g.room, p = g.state.player;
      r.cleared = false;
      r.enemies.length = 0;
      r.projectiles.length = 0;
      r.projectiles.push({ x: p.x + 30, y: p.y, vx: 520, vy: 0, r: 15, dmg: 1,
                           t: 1.4, kind: 'chakram', hostile: false,
                           spin: 0, returning: false, hitSet: [] });
    }""")
    page.wait_for_timeout(200)
    flying = page.evaluate("""() => ({
      cleared: window.__game.room.cleared,
      chakrams: window.__game.room.projectiles.filter((x) => x.kind === 'chakram').length })""")
    check("the blade really is still in the air for this check",
          flying["chakrams"] == 1, flying)
    check("a blade in flight cannot hold the gate shut", flying["cleared"] is True, flying)

    # 11. An enemy shot, by contrast, is unfinished business and must hold the gate.
    page.evaluate("""() => {
      const g = window.__game, r = g.room, p = g.state.player;
      r.cleared = false;
      r.enemies.length = 0;
      r.projectiles.length = 0;
      r.projectiles.push({ x: p.x + 200, y: p.y, vx: 0, vy: 0, r: 8, dmg: 5,
                           t: 4, kind: 'orb', hostile: true });
    }""")
    page.wait_for_timeout(200)
    held = page.evaluate("() => window.__game.room.cleared")
    check("an incoming shot keeps the gate shut until it lands", held is False, held)

    # 12. The help screen teaches the controls, including the pad mapping.
    page.evaluate("() => window.__game.clearSave()")
    page.reload(wait_until="load")
    page.wait_for_timeout(300)
    page.click("#helpBtn")
    page.wait_for_timeout(200)
    help_text = page.evaluate("() => document.getElementById('help').textContent")
    for token in ["SPELL", "SPECIAL", "X strike", "Y special", "B spell", "A dash", "call", "God Gauge"]:
        check("the help screen explains " + token, token in help_text)

    print("page errors:", errors[:5] or "none")
    browser.close()

if failures:
    print("\nABILITY CHECK FAILED:", ", ".join(failures))
    sys.exit(1)
print("\nABILITY CHECK PASSED")
