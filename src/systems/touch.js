// On-screen controls for touch devices (iPhone/iPad/Android).
//
// Left half of the screen drives a floating virtual stick; the right side holds
// Attack / Dash / Special buttons. On desktop these are hidden.
import { W, H, C } from '../config.js';
import { audio } from '../audio.js';

export class TouchControls {
  constructor(scene) {
    this.scene = scene;
    this.enabled = scene.sys.game.device.input.touch && !scene.sys.game.device.os.desktop;
    this.move = { x: 0, y: 0, active: false };
    this.attackHeld = false;
    this.bufferedDash = false;
    this.bufferedSpecial = false;
    this.stickId = null;
    this.stickOrigin = { x: 0, y: 0 };

    if (!this.enabled) return;

    this.root = scene.add.container(0, 0).setDepth(120).setScrollFactor(0);

    // --- virtual stick -------------------------------------------------
    this.baseX = 150;
    this.baseY = H - 130;
    this.base = scene.add.circle(0, 0, 62, 0xffffff, 0.06).setStrokeStyle(3, 0xffffff, 0.18);
    this.knob = scene.add.circle(0, 0, 28, C.cyan, 0.30).setStrokeStyle(2, C.cyan, 0.6);
    this.base.setPosition(this.baseX, this.baseY);
    this.knob.setPosition(this.baseX, this.baseY);
    this.root.add([this.base, this.knob]);

    // --- buttons -------------------------------------------------------
    const mkBtn = (x, y, r, label, color, onDown, onUp) => {
      const c = scene.add.circle(x, y, r, color, 0.20).setStrokeStyle(3, color, 0.55);
      const t = scene.add.text(x, y, label, {
        fontFamily: 'Georgia, serif', fontSize: '15px', color: '#ffffff',
      }).setOrigin(0.5).setAlpha(0.85);
      this.root.add([c, t]);
      const zone = scene.add.zone(x, y, r * 2.3, r * 2.3).setInteractive({ useHandCursor: false });
      this.root.add(zone);
      zone.on('pointerdown', (p) => { audio.unlock(); c.setFillStyle(color, 0.45); onDown && onDown(p); });
      zone.on('pointerup', () => { c.setFillStyle(color, 0.20); onUp && onUp(); });
      zone.on('pointerout', () => { c.setFillStyle(color, 0.20); onUp && onUp(); });
      return { c, t, zone };
    };

    this.mkBtn = mkBtn;
    this.attackBtn = mkBtn(W - 110, H - 150, 54, 'ATK', C.red,
      () => { this.attackHeld = true; }, () => { this.attackHeld = false; });
    this.dashBtn = mkBtn(W - 210, H - 90, 44, 'DASH', C.cyan,
      () => { this.bufferedDash = true; });
    this.specialBtn = mkBtn(W - 90, H - 60, 40, 'SP', C.purple,
      () => { this.bufferedSpecial = true; });

    // --- stick capture zone (left half, below the HUD) ----------------
    this.zone = scene.add.zone(0, H * 0.42, W * 0.5, H * 0.58)
      .setOrigin(0, 0).setInteractive();
    this.root.add(this.zone);
    this.zone.on('pointerdown', (p) => this.startStick(p));
    scene.input.on('pointermove', (p) => this.moveStick(p));
    scene.input.on('pointerup', (p) => this.endStick(p));

    // Keep desktop pointer from also triggering attacks.
    scene.isTouch = true;
  }

  startStick(p) {
    audio.unlock();
    this.stickId = p.id;
    this.move.active = true;
    // Floating origin: stick appears where the thumb lands.
    this.stickOrigin.x = p.x;
    this.stickOrigin.y = p.y;
    this.base.setPosition(p.x, p.y);
    this.knob.setPosition(p.x, p.y);
  }

  moveStick(p) {
    if (this.stickId !== p.id || !this.move.active) return;
    const dx = p.x - this.stickOrigin.x;
    const dy = p.y - this.stickOrigin.y;
    const max = 62;
    const len = Math.hypot(dx, dy);
    const clamped = Math.min(len, max);
    const ang = Math.atan2(dy, dx);
    this.move.x = len < 8 ? 0 : Math.cos(ang);
    this.move.y = len < 8 ? 0 : Math.sin(ang);
    this.knob.setPosition(this.stickOrigin.x + Math.cos(ang) * clamped, this.stickOrigin.y + Math.sin(ang) * clamped);
  }

  endStick(p) {
    if (this.stickId !== p.id) return;
    this.stickId = null;
    this.move.active = false;
    this.move.x = 0;
    this.move.y = 0;
    this.knob.setPosition(this.baseX, this.baseY);
    this.base.setPosition(this.baseX, this.baseY);
  }

  consumeDash() { const v = this.bufferedDash; this.bufferedDash = false; return v; }
  consumeSpecial() { const v = this.bufferedSpecial; this.bufferedSpecial = false; return v; }

  setVisible(v) { if (this.root) this.root.setVisible(v); }

  destroy() { if (this.root) this.root.destroy(true); }
}
