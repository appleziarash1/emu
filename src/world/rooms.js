// Room generation and loot. Pure data + light helpers so the run loop stays
// readable and the same rules apply to every realm.
import { ROOM_COUNT_PER_REALM, RARITY } from '../config.js';
import { BOONS, FALLBACK_ENEMIES } from '../content.js';

// Behaviour archetypes attached to the content enemies.
const BEHAVIOURS = [
  'chaser', 'chaser', 'charger', 'shooter', 'drainer',
  'exploder', 'shooter', 'guardian', 'teleporter', 'assassin',
];

export function enemyArchetype(index, content) {
  const list = (content && content.enemies) || FALLBACK_ENEMIES;
  const base = list[index % list.length];
  const color = typeof base.color === 'string' ? parseInt(base.color, 16) : base.color;
  return {
    name: base.name,
    hp: base.hp,
    damage: base.damage,
    color: color >>> 0,
    behaviour: BEHAVIOURS[index % BEHAVIOURS.length],
    index,
  };
}

export const ELITE_MODS = [
  { id: 'shielded', name: 'Shielded', color: 0x8fb4ff, hpMult: 1.9, dmgMult: 1.15 },
  { id: 'frenzied', name: 'Frenzied', color: 0xff8a5c, hpMult: 1.5, dmgMult: 1.35 },
  { id: 'volatile', name: 'Volatile', color: 0xf1c75b, hpMult: 1.4, dmgMult: 1.2 },
  { id: 'warded', name: 'Warded', color: 0x9c6cff, hpMult: 2.2, dmgMult: 1.1 },
];

// Build the room list for one realm. Deterministic given a seed so tests can
// reproduce a run exactly.
export function buildRealmRooms(realmIndex, seed) {
  const rand = mulberry32(seed + realmIndex * 7919);
  const rooms = [];
  const total = ROOM_COUNT_PER_REALM;
  for (let i = 0; i < total; i++) {
    let type = 'Combat';
    if (i === total - 1) type = 'Boss';
    else if (i === 2) type = rand() < 0.5 ? 'Elite' : 'Gauntlet';
    else if (i === 3) type = rand() < 0.5 ? 'Treasure' : 'Rest';
    else if (i === 1 && rand() < 0.4) type = 'Event';
    rooms.push({ index: i, type, difficulty: 1 + realmIndex * 0.5 + i * 0.15 });
  }
  return rooms;
}

export function roomBudget(type, realmIndex, roomIndex) {
  const base = 3 + Math.min(roomIndex, 3) + realmIndex;
  switch (type) {
    case 'Gauntlet': return Math.round(base * 1.8);
    case 'Elite': return Math.max(2, Math.round(base * 0.6));
    case 'Combat': return base;
    case 'Boss': return 0;
    default: return base;
  }
}

// Choose boon options. Curated boons come first so the headline choices always
// have real, working effects; generated JSON boons fill the remaining slots
// with small numeric modifiers.
export function rollBoonChoices(content, takenIds, count = 3, rand = Math.random) {
  const pool = [];
  const available = BOONS.filter((b) => !takenIds.includes(b.id));
  shuffle(available, rand);
  for (const b of available) {
    pool.push({ id: b.id, name: b.name, rarity: b.rarity, desc: b.desc, curated: true, apply: b.apply });
    if (pool.length >= count) return pool;
  }
  const generated = (content && content.boons) || [];
  const usedGenerated = new Set(takenIds.filter((id) => id.startsWith('boon_')));
  const genPool = generated.filter((b) => !usedGenerated.has(b.id));
  shuffle(genPool, rand);
  for (const b of genPool) {
    pool.push({
      id: b.id,
      name: b.name,
      rarity: b.rarity,
      desc: generatedDesc(b),
      curated: false,
      apply: generatedApply(b),
    });
    if (pool.length >= count) break;
  }
  // Absolute fallback so a reward screen can never come up empty.
  let guard = 0;
  while (pool.length < count && guard++ < 50) {
    pool.push({
      id: `filler_${guard}`,
      name: 'Veil Fragment',
      rarity: 'Common',
      desc: '+3% weapon damage.',
      curated: false,
      apply: (s) => { s.damageMult += 0.03; },
    });
  }
  return pool.slice(0, count);
}

function generatedDesc(b) {
  if (b.rarity === 'Legendary') return '+5% damage, +4 max HP.';
  if (b.rarity === 'Epic') return '+4% damage.';
  if (b.rarity === 'Rare') return '+2% move speed.';
  return '+2% weapon damage.';
}

function generatedApply(b) {
  return (s) => {
    if (b.rarity === 'Legendary') { s.damageMult += 0.05; s.maxHp += 4; s.hp += 4; }
    else if (b.rarity === 'Epic') s.damageMult += 0.04;
    else if (b.rarity === 'Rare') s.speedMult += 0.02;
    else s.damageMult += 0.02;
  };
}

export function rarityColor(rarity) {
  return (RARITY[rarity] || RARITY.Common).color;
}

export function shuffledLootRarity(rand = Math.random) {
  const total = Object.values(RARITY).reduce((a, b) => a + b.weight, 0);
  let r = rand() * total;
  for (const [name, cfg] of Object.entries(RARITY)) {
    r -= cfg.weight;
    if (r <= 0) return name;
  }
  return 'Common';
}

export function shuffle(arr, rand = Math.random) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

// Small deterministic PRNG (used for room layout so a seed replays).
export function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
