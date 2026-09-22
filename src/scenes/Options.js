// Sound & video options. Reachable from the menu, hub, and the in-run pause menu.
import Phaser from 'phaser';
import { W, H, C } from '../config.js';
import { audio } from '../audio.js';
import { gameState } from '../systems/gamestate.js';
import { makeText, panel, Button, transitionTo } from '../ui.js';

const TOGGLES = [
  { key: 'music', name: 'Music' },
  { key: 'sfx', name: 'Sound effects' },
  { key: 'screenshake', name: 'Screen shake' },
  { key: 'damageNumbers', name: 'Damage numbers' },
  { key: 'reducedFlash', name: 'Reduce flashing' },
];

export class Options extends Phaser.Scene {
  constructor() { super('Options'); }

  create(data) {
    this.from = (data && data.from) || 'Menu';
    this.cameras.main.setBackgroundColor(0x08070d);
    this.add.rectangle(W / 2, H / 2, W, H, 0x08070d, 0.96);

    makeText(this, W / 2, 110, 'SOUND & VIDEO', { size: 38, color: C.text, origin: 0.5 });
    panel(this, W / 2 - 300, 180, 600, 380, { fill: C.panel, alpha: 0.92 });

    this.rows = [];
    TOGGLES.forEach((t, i) => {
      const y = 216 + i * 66;
      makeText(this, W / 2 - 260, y + 10, t.name, { size: 18, color: C.text });
      const btn = new Button(this, W / 2 + 90, y, 150, 46, '', () => this.toggle(t.key), {
        fill: 0x241f34, hover: 0x342c4a, size: 15,
      });
      this.rows.push({ t, btn });
    });

    new Button(this, W / 2 - 150, 600, 300, 52, 'BACK', () => this.back(), {
      fill: C.panelLight, hover: 0x302941,
    });

    makeText(this, W / 2, 566, 'Changes save automatically and apply immediately.', { size: 13, color: C.muted, origin: 0.5 });

    this.input.keyboard.on('keydown-ESC', () => this.back());
    this.refresh();
    this.cameras.main.fadeIn(200, 8, 7, 13);
  }

  toggle(key) {
    audio.unlock();
    const patch = { [key]: !gameState.options[key] };
    gameState.setOptions(patch);
    audio.ui();
    this.refresh();
  }

  refresh() {
    for (const row of this.rows) {
      const on = !!gameState.options[row.t.key];
      row.btn.setLabel(on ? 'ON' : 'OFF');
      row.btn.rect.setFillStyle(on ? 0x2c3145 : 0x241f34);
      row.btn.baseFill = on ? 0x2c3145 : 0x241f34;
      row.btn.label.setColor(on ? '#63d9e8' : '#aaa4bd');
    }
  }

  back() {
    if (this.from === 'Game') {
      this.scene.stop();
      this.scene.resume('Game');
    } else {
      transitionTo(this, this.from, {}, 200);
    }
  }
}
