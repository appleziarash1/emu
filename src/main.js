// VEILBORN — entry point.
import Phaser from 'phaser';
import { W, H } from './config.js';
import { audio } from './audio.js';
import { gameState } from './systems/gamestate.js';
import { initPwa } from './pwa.js';
import { Boot } from './scenes/Boot.js';
import { Menu } from './scenes/Menu.js';
import { WeaponSelect } from './scenes/WeaponSelect.js';
import { Hub } from './scenes/Hub.js';
import { GameScene } from './scenes/Game.js';
import { Death } from './scenes/Death.js';
import { Ending } from './scenes/Ending.js';
import { Options } from './scenes/Options.js';

gameState.init();
initPwa();

// Clear the static "VEILBORN" boot notice once Phaser has a canvas.
const bootNotice = document.getElementById('boot-notice');
if (bootNotice) {
  const observer = new MutationObserver(() => {
    if (document.querySelector('#game canvas')) {
      bootNotice.remove();
      observer.disconnect();
    }
  });
  observer.observe(document.getElementById('game'), { childList: true });
  setTimeout(() => bootNotice.remove(), 6000);
}

// Unlock audio on the first real gesture anywhere in the page.
const unlock = () => audio.unlock();
window.addEventListener('pointerdown', unlock, { once: true });
window.addEventListener('keydown', unlock, { once: true });
window.addEventListener('touchstart', unlock, { once: true });

const config = {
  type: Phaser.AUTO,
  width: W,
  height: H,
  parent: 'game',
  backgroundColor: '#090a10',
  pixelArt: false,
  roundPixels: true,
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH,
    width: W,
    height: H,
  },
  input: {
    activePointers: 3,
  },
  scene: [Boot, Menu, WeaponSelect, Hub, GameScene, Death, Ending, Options],
};

const game = new Phaser.Game(config);

// Expose a tiny handle for debugging / automated smoke tests.
window.__VEILBORN__ = { game, gameState, audio };

// iOS Safari: keep the canvas from being dragged/scrolled while playing.
document.addEventListener('touchmove', (e) => {
  if (e.touches.length > 1) e.preventDefault();
}, { passive: false });
document.addEventListener('gesturestart', (e) => e.preventDefault());
