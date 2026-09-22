// Main menu: title, descent, profile summary, options, how-to-play.
import Phaser from 'phaser';
import { W, H, C } from '../config.js';
import { audio } from '../audio.js';
import { gameState } from '../systems/gamestate.js';
import { WEAPONS, STORY } from '../content.js';
import { makeText, panel, Button, transitionTo } from '../ui.js';

export class Menu extends Phaser.Scene {
  constructor() { super('Menu'); }

  create() {
    this.cameras.main.setBackgroundColor(0x08070d);
    const bgKey = gameState.profile.bestRealm != null
      ? `bg_${['ash', 'tides', 'frost', 'shadows', 'throne'][Math.min(4, gameState.profile.bestRealm || 0)]}`
      : 'bg_hub';
    if (this.textures.exists(bgKey)) {
      const img = this.add.image(W / 2, H / 2, bgKey);
      img.setScale(Math.max(W / img.width, H / img.height)).setAlpha(0.35);
    }
    // drifting veil motes
    for (let i = 0; i < 40; i++) {
      const m = this.add.circle(Math.random() * W, Math.random() * H, 1 + Math.random() * 2.5, 0xffffff, 0.08 + Math.random() * 0.2);
      this.tweens.add({
        targets: m,
        y: m.y - 40 - Math.random() * 120,
        alpha: 0,
        duration: 4000 + Math.random() * 6000,
        repeat: -1,
        delay: Math.random() * 3000,
      });
    }

    makeText(this, W / 2, 128, 'VEILBORN', { size: 82, color: C.text, origin: 0.5 });
    makeText(this, W / 2, 196, 'DESCENT. RISE. REWRITE.', { size: 21, color: C.purple, origin: 0.5 });

    panel(this, W / 2 - 260, 250, 520, 66, { fill: C.panel, alpha: 0.7 });
    const p = gameState.profile;
    makeText(this, W / 2, 268, `Shards: ${p.shards || 0}   •   Kills: ${p.totalKills || 0}   •   Runs: ${p.totalRuns || 0}`, { size: 15, color: C.gold, origin: 0.5 });
    const realmName = ['Realm of Ash', 'Realm of Tides', 'Realm of Frost', 'Realm of Shadows', 'The Forgotten Throne'][Math.min(4, p.bestRealm || 0)];
    makeText(this, W / 2, 294, `Deepest descent: ${p.bestRealm ? realmName : 'none yet'}`, { size: 14, color: C.muted, origin: 0.5 });

    new Button(this, W / 2 - 170, 350, 340, 58, 'BEGIN DESCENT', () => this.begin(), { fill: 0x2a2036, hover: 0x3a2c4c, stroke: C.purple, size: 20 });
    new Button(this, W / 2 - 170, 420, 340, 50, 'THE SHATTERED GATE', () => transitionTo(this, 'Hub', {}, 260), { fill: C.panelLight, hover: 0x302941 });
    new Button(this, W / 2 - 170, 482, 340, 46, 'SOUND & VIDEO', () => this.scene.start('Options', { from: 'Menu' }), { fill: C.panelLight, hover: 0x302941, size: 16 });
    new Button(this, W / 2 - 170, 540, 340, 46, 'HOW TO PLAY', () => this.showHelp(), { fill: C.panelLight, hover: 0x302941, size: 16 });

    makeText(this, W / 2, H - 34, 'WASD / Arrows move • Mouse or Tap attack • SPACE / DASH • Right-click or SP special • 1-6 weapons', {
      size: 13, color: C.muted, origin: 0.5, wrap: 1100, align: 'center',
    });

    this.input.keyboard.once('keydown-ENTER', () => this.begin());
    this.cameras.main.fadeIn(300, 8, 7, 13);
    if (!this.sound_unlocked) {
      this.input.once('pointerdown', () => { audio.unlock(); audio.playMusic('hub'); this.sound_unlocked = true; });
      this.input.keyboard.once('keydown', () => { audio.unlock(); audio.playMusic('hub'); this.sound_unlocked = true; });
    }
  }

  begin() {
    audio.unlock();
    this.scene.start('WeaponSelect');
  }

  showHelp() {
    const o = this.add.container(0, 0).setDepth(100);
    o.add(this.add.rectangle(W / 2, H / 2, W, H, 0x08070d, 0.92));
    o.add(makeText(this, W / 2, 80, 'HOW TO PLAY', { size: 36, color: C.text, origin: 0.5 }));
    const lines = [
      'Move with WASD / arrow keys, or the left on-screen stick on a phone.',
      'Attack by clicking / tapping, holding to keep swinging. Aim with the cursor.',
      'Dash with SPACE (or the DASH button) — you are briefly invulnerable.',
      'Special with right-click (or the SP button). Specials cost energy.',
      'Clear a room to choose a boon. Boons stack for the whole run.',
      'Beat the realm boss to descend. You lose boons when you die, but shards persist.',
      'Spend shards at the Shattered Gate on permanent Memory upgrades.',
      'Five realms. Four endings. What you remember decides which one you get.',
    ];
    lines.forEach((l, i) => {
      o.add(makeText(this, 150, 150 + i * 42, `•  ${l}`, { size: 17, color: i === lines.length - 1 ? C.gold : C.text, wrap: 980 }));
    });
    const close = new Button(this, W / 2 - 110, 580, 220, 50, 'CLOSE', () => o.destroy(true), { fill: 0x241f34, hover: 0x342c4a });
    o.add([close.rect, close.label].filter(Boolean));
    this.helpOverlay = o;
  }
}
