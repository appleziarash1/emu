// Single source of truth shared across scenes.
//
// Phaser scene restarts would otherwise force us to thread the whole run state
// through `scene.start` data every time; a small singleton keeps the run, the
// persistent profile, loaded content, and options in one place.
import { loadOptions, saveOptions, loadProfile, saveProfile, createRun } from '../state.js';
import { audio } from '../audio.js';
import { WEAPONS, BOSSES } from '../content.js';
import { buildRealmRooms, mulberry32 } from '../world/rooms.js';

export const gameState = {
  content: null,
  options: loadOptions(),
  profile: loadProfile(),
  run: null,
  rooms: [],
  seed: Math.floor(Math.random() * 1e9),
  weapon: null,
  isTouch: false,
  booted: false,

  init() {
    audio.setOptions(this.options);
    this.options = this.options || loadOptions();
  },

  setOptions(patch) {
    this.options = { ...this.options, ...patch };
    saveOptions(this.options);
    audio.setOptions(this.options);
  },

  get weaponDef() {
    return WEAPONS.find((w) => w.id === (this.run && this.run.weaponId)) || WEAPONS[0];
  },

  get bossDef() {
    return BOSSES[Math.min(BOSSES.length - 1, this.run ? this.run.realm : 0)];
  },

  get roomCount() {
    return this._roomCount || 5;
  },

  set roomCount(v) { this._roomCount = v; },

  startNewRun(weaponId, seed) {
    this.seed = seed != null ? seed : Math.floor(Math.random() * 1e9);
    this.profile.totalRuns = (this.profile.totalRuns || 0) + 1;
    saveProfile(this.profile);
    this.run = createRun(this.profile, weaponId);
    this.rooms = buildRealmRooms(0, this.seed);
    return this.run;
  },

  enterRealm(realmIndex) {
    this.run.realm = realmIndex;
    this.run.room = 0;
    this.rooms = buildRealmRooms(realmIndex, this.seed);
  },

  currentRoom() {
    return this.rooms[this.run.room] || this.rooms[this.rooms.length - 1];
  },

  rand() {
    // Run-stable RNG so a seed replays identically for tests.
    if (!this._rand) this._rand = mulberry32(this.seed ^ 0x9e3779b9);
    return this._rand();
  },

  resetRand() { this._rand = null; },

  persistProfile() { saveProfile(this.profile); },
};

export function budgetFor(type, realmIndex, roomIndex) {
  const base = 3 + Math.min(roomIndex, 3) + realmIndex;
  switch (type) {
    case 'Gauntlet': return Math.round(base * 1.8);
    case 'Elite': return Math.max(2, Math.round(base * 0.6));
    case 'Boss': return 0;
    default: return base;
  }
}
