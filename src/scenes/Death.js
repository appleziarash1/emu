// Death screen. Shows the run summary; shards banked persist.
import Phaser from 'phaser';
import { W, H, C, REALMS } from '../config.js';
import { audio } from '../audio.js';
import { gameState } from '../systems/gamestate.js';
import { makeText, panel, Button, transitionTo } from '../ui.js';

export class Death extends Phaser.Scene {
  constructor() { super('Death'); }

  create(data) {
    audio.stopMusic();
    this.cameras.main.setBackgroundColor(0x08070d);
    const run = (data && data.run) || gameState.run;

    this.add.rectangle(W / 2, H / 2, W, H, 0x08070d, 0.97);
    // red vignette
    const g = this.add.graphics();
    g.fillStyle(0x2a0d12, 0.5);
    g.fillRect(0, 0, W, H);

    makeText(this, W / 2, 110, 'THE VEIL REMEMBERS', { size: 46, color: C.text, origin: 0.5 });
    makeText(this, W / 2, 168, 'Cael fell, but the descent was not meaningless.', { size: 18, color: C.muted, origin: 0.5 });

    const realmName = REALMS[(data && data.realm) || 0].name;
    panel(this, W / 2 - 280, 220, 560, 240, { fill: C.panel, alpha: 0.92 });
    const rows = [
      ['Realm reached', realmName],
      ['Room reached', `${((data && data.room) || 0) + 1}`],
      ['Kills', `${run.kills}`],
      ['Boons carried', `${run.boons.length}`],
      ['Shards earned', `${run.shardsEarned}`],
      ['Shards banked', `${gameState.profile.shards || 0}`],
    ];
    rows.forEach((r, i) => {
      makeText(this, W / 2 - 240, 250 + i * 34, r[0], { size: 16, color: C.muted });
      makeText(this, W / 2 + 240, 250 + i * 34, r[1], { size: 16, color: C.text, origin: 1 });
    });

    new Button(this, W / 2 - 320, 500, 300, 54, 'TRY AGAIN', () => {
      audio.door();
      gameState.startNewRun(run.weaponId);
      transitionTo(this, 'Game', { mode: 'room' }, 320);
    }, { fill: 0x2a2036, hover: 0x3a2c4c, stroke: C.purple });
    new Button(this, W / 2 + 20, 500, 300, 54, 'THE SHATTERED GATE', () => transitionTo(this, 'Hub', {}, 300), {
      fill: C.panelLight, hover: 0x302941,
    });

    makeText(this, W / 2, 590, `Shards are permanent. Spend them at the Gate on Memory upgrades.`, {
      size: 14, color: C.gold, origin: 0.5,
    });

    this.cameras.main.fadeIn(400, 8, 7, 13);
  }
}
