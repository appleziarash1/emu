// Central tuning values and palette for VEILBORN.
export const W = 1280;
export const H = 720;

export const C = {
  bg: 0x090a10,
  panel: 0x151522,
  panelLight: 0x211d30,
  text: 0xf4f1ff,
  muted: 0xaaa4bd,
  red: 0xe05a68,
  gold: 0xf1c75b,
  cyan: 0x63d9e8,
  purple: 0x9c6cff,
  green: 0x6fd8a6,
  white: 0xffffff,
};

export const COLOR_HEX = (n) => '#' + n.toString(16).padStart(6, '0');

// Arena geometry (rooms and boss chambers share the same playfield).
export const ARENA = { x: 60, y: 150, w: 1160, h: 500 };
export const ARENA_MARGIN = 24;

export const RARITY = {
  Common: { color: 0xaaa4bd, weight: 60 },
  Rare: { color: 0x63d9e8, weight: 25 },
  Epic: { color: 0x9c6cff, weight: 12 },
  Legendary: { color: 0xf1c75b, weight: 3 },
};

export const REALMS = [
  {
    id: 'ash',
    name: 'Realm of Ash',
    boss: 'Zyther, Lord of Ashes',
    tint: 0x241416,
    accent: 0xff714a,
    bg: 'assets/backgrounds/ash.svg',
    intro: 'Ash falls like snow over a kingdom that burned itself free of memory.',
    theme: { burn: true },
  },
  {
    id: 'tides',
    name: 'Realm of Tides',
    boss: 'Seraphine, Queen of the Drowned',
    tint: 0x101f2b,
    accent: 0x63d9e8,
    bg: 'assets/backgrounds/tides.svg',
    intro: 'The drowned keep their promises. That is the cruelest part.',
    theme: { slow: true },
  },
  {
    id: 'frost',
    name: 'Realm of Frost',
    boss: 'Auren, the Last Watcher',
    tint: 0x151c2c,
    accent: 0x9ec6ff,
    bg: 'assets/backgrounds/frost.svg',
    intro: 'A watcher who never blinked froze his own name to keep it safe.',
    theme: { freeze: true },
  },
  {
    id: 'shadows',
    name: 'Realm of Shadows',
    boss: 'Draemor, God of the Forgotten',
    tint: 0x171324,
    accent: 0x9c6cff,
    bg: 'assets/backgrounds/shadows.svg',
    intro: 'Nothing is lost here. It is only hidden, and it remembers being hidden.',
    theme: { shadow: true },
  },
  {
    id: 'throne',
    name: 'The Forgotten Throne',
    boss: 'The Hollow, The Empty King',
    tint: 0x100d17,
    accent: 0xf1c75b,
    bg: 'assets/backgrounds/throne.svg',
    intro: 'The throne was never empty. It was waiting for someone worth taking.',
    theme: { hollow: true },
  },
];

export const KNIGHT = {
  baseHp: 100,
  baseEnergy: 100,
  energyRegen: 16, // per second
  baseSpeed: 250,
  dashDistance: 150,
  dashCooldown: 700,
  dashInvuln: 220,
  baseCrit: 0.05,
  baseCritMult: 1.6,
  pickupRadius: 46,
};

export const ROOM_COUNT_PER_REALM = 5;
export const REWARD_ENERGY_COST = 35;
