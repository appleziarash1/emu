// Ending scene. Which of the four endings you get depends on how you played:
// how many memories you recovered, how many enemies you spared by not fighting
// (mercy via resting/events), and whether you found the Hollow's true name.
import Phaser from 'phaser';
import { W, H, C } from '../config.js';
import { audio } from '../audio.js';
import { gameState } from '../systems/gamestate.js';
import { STORY } from '../content.js';
import { makeText, panel, Button, transitionTo } from '../ui.js';

// Ending selection.
//
// The four endings are chosen by *how you treated the Veil's memories*, not by
// an arbitrary kill count. At the final throne you pick one of two postures —
// Remember or Release — and that choice combines with what you did on the way
// down (how many memories you recovered, how merciful you were) to decide which
// ending you actually get. That makes all four reachable in normal play:
//
//   Sealed Veil  — few memories found, you chose Release
//   Open Veil    — few memories found, you chose Remember
//   New Veil     — many memories found, you chose Release
//   True Ending  — many memories found, you chose Remember, and you were merciful
export function determineEnding(run) {
  const memories = run.memoriesFound || 0;
  const remembered = (run.remembered || 0) > (run.released || 0);
  const released = (run.released || 0) > 0 && !remembered;
  const merciful = (run.mercyCount || 0) >= (run.kills || 0) * 0.5 || (run.mercyCount || 0) >= 4;

  // Fall back to stats when the player never reached the choice screen (e.g. a
  // run that ended early and was force-resolved).
  if (memories >= STORY_ENDING_THRESHOLD.high) {
    if (remembered) return merciful ? 'true' : 'new';
    if (released) return 'new';
    return run.kills > 80 ? 'open' : 'sealed';
  }
  if (remembered) return 'open';
  return 'sealed';
}

export const STORY_ENDING_THRESHOLD = { high: 6 };

export class Ending extends Phaser.Scene {
  constructor() { super('Ending'); }

  create(data) {
    this.run = data.run || gameState.run;
    this.ending = data.forced || determineEnding(this.run);
    audio.stopMusic();
    audio.victory();

    // Record the ending for the hub's collection tracker.
    const endings = gameState.profile.endings || (gameState.profile.endings = []);
    if (!endings.includes(this.ending)) {
      endings.push(this.ending);
      gameState.persistProfile();
    }

    this.cameras.main.setBackgroundColor(0x08070d);
    const tint = { sealed: 0x1a2030, open: 0x2a1020, new: 0x141428, true: 0x241d10 }[this.ending];
    this.add.rectangle(W / 2, H / 2, W, H, tint, 1);

    // Radiant motes
    for (let i = 0; i < 70; i++) {
      const m = this.add.circle(Math.random() * W, H + Math.random() * 200, 1 + Math.random() * 3, 0xffffff, 0.06 + Math.random() * 0.25);
      this.tweens.add({
        targets: m, y: -40, alpha: 0, duration: 5000 + Math.random() * 7000,
        repeat: -1, delay: Math.random() * 5000,
      });
    }

    const story = STORY.endings[this.ending];
    makeText(this, W / 2, 96, story.title, { size: 40, color: C.text, origin: 0.5 });

    story.lines.forEach((line, i) => {
      const t = makeText(this, W / 2, 190 + i * 44, line, {
        size: i === 0 ? 22 : 19, color: i === 0 ? C.gold : C.text, origin: 0.5, wrap: 920, align: 'center',
      });
      t.setAlpha(0);
      this.tweens.add({ targets: t, alpha: 1, duration: 900, delay: 500 + i * 700 });
    });

    panel(this, W / 2 - 300, 370, 600, 150, { fill: C.panel, alpha: 0.85 });
    const stats = [
      ['Kills', this.run.kills],
      ['Memories recovered', this.run.memoriesFound || 0],
      ['Boons carried', this.run.boons.length],
      ['Shards earned (incl. +50 ending bonus)', this.run.shardsEarned],
    ];
    stats.forEach((r, i) => {
      makeText(this, W / 2 - 260, 396 + i * 30, r[0], { size: 15, color: C.muted });
      makeText(this, W / 2 + 260, 396 + i * 30, `${r[1]}`, { size: 15, color: C.text, origin: 1 });
    });

    const allFound = ['sealed', 'open', 'new', 'true'].every((k) => (gameState.profile.endings || []).includes(k));
    if (allFound) {
      makeText(this, W / 2, 546, '★  ALL FOUR ENDINGS FOUND — The Veil holds nothing from you now.', { size: 16, color: C.gold, origin: 0.5 });
    } else {
      const remaining = 4 - (gameState.profile.endings || []).length;
      makeText(this, W / 2, 546, `${remaining} ending${remaining === 1 ? '' : 's'} still hidden. Descend differently.`, { size: 15, color: C.muted, origin: 0.5 });
    }

    new Button(this, W / 2 - 320, 600, 300, 54, 'DESCEND AGAIN', () => {
      gameState.startNewRun(this.run.weaponId);
      transitionTo(this, 'Game', { mode: 'room' }, 320);
    }, { fill: 0x2a2036, hover: 0x3a2c4c, stroke: C.purple });
    new Button(this, W / 2 + 20, 600, 300, 54, 'THE SHATTERED GATE', () => transitionTo(this, 'Hub', {}, 300), {
      fill: C.panelLight, hover: 0x302941,
    });

    this.cameras.main.fadeIn(700, 8, 7, 13);
  }
}
