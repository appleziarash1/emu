// Persistent profile (meta progression) and per-run state.
import { KNIGHT } from './config.js';

const SAVE_KEY = 'veilborn_save_v2';
const OPTIONS_KEY = 'veilborn_options_v1';

export const DEFAULT_OPTIONS = {
  music: true,
  sfx: true,
  screenshake: true,
  damageNumbers: true,
  reducedFlash: false,
};

export function loadOptions() {
  try {
    const raw = JSON.parse(localStorage.getItem(OPTIONS_KEY));
    return { ...DEFAULT_OPTIONS, ...(raw || {}) };
  } catch {
    return { ...DEFAULT_OPTIONS };
  }
}

export function saveOptions(opts) {
  try { localStorage.setItem(OPTIONS_KEY, JSON.stringify(opts)); } catch {}
}

// Profile holds everything that survives death.
export function defaultProfile() {
  return {
    version: 2,
    shards: 0,            // permanent currency from failed runs
    totalKills: 0,
    totalRuns: 0,
    bestRealm: 0,
    unlockedWeapons: ['ashen_edge'],
    // Memory (meta upgrades purchased at the Gate)
    memory: {
      vitality: 0,   // +10 max hp per rank
      potency: 0,    // +4% damage per rank
      swiftness: 0,  // +3% speed per rank
      insight: 0,    // +2% crit per rank
      attunement: 0, // +5% energy regen per rank
    },
    endings: [],           // which endings the player has seen
    storySeen: [],         // dialogue ids already shown
  };
}

export function loadProfile() {
  try {
    const raw = JSON.parse(localStorage.getItem(SAVE_KEY));
    if (!raw) return defaultProfile();
    const base = defaultProfile();
    return {
      ...base,
      ...raw,
      memory: { ...base.memory, ...(raw.memory || {}) },
      unlockedWeapons: Array.isArray(raw.unlockedWeapons) && raw.unlockedWeapons.length
        ? raw.unlockedWeapons : base.unlockedWeapons,
      endings: Array.isArray(raw.endings) ? raw.endings : [],
      storySeen: Array.isArray(raw.storySeen) ? raw.storySeen : [],
    };
  } catch {
    return defaultProfile();
  }
}

export function saveProfile(profile) {
  try { localStorage.setItem(SAVE_KEY, JSON.stringify(profile)); } catch {}
}

export function clearProfile() {
  try { localStorage.removeItem(SAVE_KEY); } catch {}
}

// A run is one descent. Stats are the mutable numbers boons write into.
export function createRun(profile, weaponId) {
  const mem = profile.memory;
  const run = {
    realm: 0,
    room: 0,
    weaponId,
    kills: 0,
    shardsEarned: 0,
    roomsCleared: 0,
    elapsed: 0,
    boons: [],
    stats: {
      maxHp: KNIGHT.baseHp + mem.vitality * 10,
      hp: 0,
      maxEnergy: KNIGHT.baseEnergy,
      energy: KNIGHT.baseEnergy,
      damageMult: 1 + mem.potency * 0.04,
      speedMult: 1 + mem.swiftness * 0.03,
      energyRegenMult: 1 + mem.attunement * 0.05,
      cooldownMult: 1,
      rangeMult: 1,
      crit: KNIGHT.baseCrit + mem.insight * 0.02,
      critMult: KNIGHT.baseCritMult,
      lifesteal: 0,
      pierce: 0,
      ward: 0,
      dashBurn: 0,
      dashRift: 0,
      echoShock: 0,
      tempo: false,
      specialDiscount: 1,
      specialDouble: false,
      longMemory: 0,
      barrier: 0,
    },
    // Tracked for the ending branch: how much story the player chose to keep.
    memoriesFound: 0,
    remembered: 0,
    released: 0,
    mercyCount: 0,
    difficulty: 1,
  };
  run.stats.hp = run.stats.maxHp;
  return run;
}
