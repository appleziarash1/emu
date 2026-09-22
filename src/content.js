// Deterministic-ish content layer.
//
// data/content_expanded.json is the canonical bulk content source (10 enemies,
// 150 boons, 180 rooms, 160 dialogue fragments). It is imported as a module so
// Vite bundles it — no runtime fetch, which keeps the PWA fully offline-capable.
// The curated table below supplies the hand-authored identity for the things the
// player interacts with every run (weapons, bosses, boons).

import rawContent from '../data/content_expanded.json';

export function getContent() {
  if (rawContent && Array.isArray(rawContent.enemies) && rawContent.enemies.length) return rawContent;
  return { enemies: [], boons: [], rooms: [], dialogue: [] };
}

export const WEAPONS = [
  {
    id: 'ashen_edge',
    name: 'Ashen Edge',
    kind: 'melee',
    damage: 26,
    cooldown: 260,
    range: 104,
    arc: 1.1,
    color: 0xf0d7bd,
    lore: 'A blade quenched in the first funeral pyre. It cuts what memory holds.',
    special: 'Ashen Wake',
    specialDesc: 'Three-step lunge that leaves burning ground.',
    specialCost: 35,
  },
  {
    id: 'pyre_lance',
    name: 'Pyre Lance',
    kind: 'thrust',
    damage: 38,
    cooldown: 430,
    range: 148,
    arc: 0.42,
    color: 0xff714a,
    lore: 'Reach longer than regret. Thrust it and the room remembers heat.',
    special: 'Pyre Nova',
    specialDesc: 'Ring of fire that scorches everything around you.',
    specialCost: 40,
  },
  {
    id: 'tempest_gauntlets',
    name: 'Tempest Gauntlets',
    kind: 'melee',
    damage: 15,
    cooldown: 110,
    range: 88,
    arc: 1.5,
    color: 0x7be7ff,
    lore: 'Fists wrapped in a storm that never found land.',
    special: 'Chain Tempest',
    specialDesc: 'Rapid shockwave that stuns and pushes.',
    specialCost: 30,
  },
  {
    id: 'moonthread_bow',
    name: 'Moonthread Bow',
    kind: 'ranged',
    damage: 30,
    cooldown: 380,
    range: 900,
    arc: 0,
    color: 0xd4b5ff,
    lore: 'Strung with a strand of moonlight. It always finds the second heart.',
    special: 'Moonfall Volley',
    specialDesc: 'Fan of piercing arrows.',
    specialCost: 35,
  },
  {
    id: 'gravewind_scythe',
    name: 'Gravewind Scythe',
    kind: 'melee',
    damage: 44,
    cooldown: 520,
    range: 132,
    arc: 2.5,
    color: 0x9aa2b4,
    lore: 'It reaps in a wide arc, and the wind it leaves smells of graves.',
    special: 'Gravewind Reap',
    specialDesc: 'Wide vortex that pulls enemies inward.',
    specialCost: 45,
  },
  {
    id: 'tidebreaker_chakrams',
    name: 'Tidebreaker Chakrams',
    kind: 'ranged',
    damage: 22,
    cooldown: 300,
    range: 560,
    arc: 0,
    color: 0x63d9e8,
    lore: 'Two rings of drowned iron. They come back heavier than they left.',
    special: 'Tidebreaker Ring',
    specialDesc: 'Six orbiting chakrams that shred anything close.',
    specialCost: 40,
  },
];

// The five bosses named in the design document, each with distinct patterns.
export const BOSSES = [
  {
    id: 'zyther',
    name: 'Zyther, Lord of Ashes',
    title: 'He Who Burned the Archive',
    color: 0xd4402f,
    accent: 0xff714a,
    hp: 900,
    patterns: ['fan', 'charge', 'burnArena'],
    phases: 2,
    taunt: 'You came down here carrying a name. I will take that too.',
    defeat: 'Ash to ash. Even my grief burns down to nothing.',
  },
  {
    id: 'seraphine',
    name: 'Seraphine, Queen of the Drowned',
    title: 'She Who Sings Beneath',
    color: 0x3aa8d8,
    accent: 0x63d9e8,
    hp: 1250,
    patterns: ['spiral', 'summonAdds', 'wave'],
    phases: 2,
    taunt: 'Breathe, little thing. I have waited centuries for someone to drown.',
    defeat: 'The tide lets go. Tell the living it was never cruel — only full.',
  },
  {
    id: 'auren',
    name: 'Auren, the Last Watcher',
    title: 'He Who Never Blinked',
    color: 0x7fa8e0,
    accent: 0x9ec6ff,
    hp: 1600,
    patterns: ['snipe', 'frostNova', 'mirror'],
    phases: 3,
    taunt: 'I watched every ending you ever had. I am unmoved.',
    defeat: 'I blinked. Forgive me — I wanted to see what you would do.',
  },
  {
    id: 'draemor',
    name: 'Draemor, God of the Forgotten',
    title: 'He Whose Name Was Erased',
    color: 0x7a3fd0,
    accent: 0x9c6cff,
    hp: 1950,
    patterns: ['teleport', 'shadowClone', 'voidPull'],
    phases: 3,
    taunt: 'You do not remember me. That is the wound I live in.',
    defeat: 'Say my name. Say it once, and I can finally be gone.',
  },
  {
    id: 'hollow',
    name: 'The Hollow, The Empty King',
    title: 'The Throne That Waits',
    color: 0xc9a24a,
    accent: 0xf1c75b,
    hp: 2600,
    patterns: ['fan', 'voidPull', 'frostNova', 'mirror', 'shadowClone'],
    phases: 3,
    taunt: 'You were never meant to forget me.',
    defeat: 'Then remember — and choose what remains.',
  },
];

// Curated boons with real, implemented effects. `apply` mutates the run stats
// object; `stack` values accumulate. The generated JSON boons are used to fill
// out remaining choice slots with smaller numeric modifiers.
export const BOONS = [
  {
    id: 'veilheart',
    name: 'Veilheart',
    rarity: 'Common',
    desc: '+25 max HP, heal 25.',
    apply: (s) => { s.maxHp += 25; s.hp = Math.min(s.maxHp, s.hp + 25); },
  },
  {
    id: 'echo_blade',
    name: 'Echo Blade',
    rarity: 'Common',
    desc: '+10% weapon damage.',
    apply: (s) => { s.damageMult += 0.10; },
  },
  {
    id: 'second_breath',
    name: 'Second Breath',
    rarity: 'Common',
    desc: '+8% move speed.',
    apply: (s) => { s.speedMult += 0.08; },
  },
  {
    id: 'emberstep',
    name: 'Emberstep',
    rarity: 'Common',
    desc: '+15% energy regen.',
    apply: (s) => { s.energyRegenMult += 0.15; },
  },
  {
    id: 'thorn_veil',
    name: 'Thorn Veil',
    rarity: 'Rare',
    desc: 'Dashing burns nearby foes for 30.',
    apply: (s) => { s.dashBurn = (s.dashBurn || 0) + 30; },
  },
  {
    id: 'long_reach',
    name: 'Long Reach',
    rarity: 'Rare',
    desc: '+18% attack range and area.',
    apply: (s) => { s.rangeMult += 0.18; },
  },
  {
    id: 'quickened',
    name: 'Quickened',
    rarity: 'Rare',
    desc: '-12% attack cooldown.',
    apply: (s) => { s.cooldownMult = Math.max(0.35, s.cooldownMult - 0.12); },
  },
  {
    id: 'soul_ledger',
    name: 'Soul Ledger',
    rarity: 'Rare',
    desc: 'Kills restore 4 HP.',
    apply: (s) => { s.lifesteal += 4; },
  },
  {
    id: 'hunters_mark',
    name: "Hunter's Mark",
    rarity: 'Rare',
    desc: '+12% critical chance.',
    apply: (s) => { s.crit += 0.12; },
  },
  {
    id: 'executioner',
    name: 'Executioner',
    rarity: 'Epic',
    desc: '+45% critical damage.',
    apply: (s) => { s.critMult += 0.45; },
  },
  {
    id: 'veil_splinter',
    name: 'Veil Splinter',
    rarity: 'Epic',
    desc: 'Projectiles pierce one extra enemy.',
    apply: (s) => { s.pierce += 1; },
  },
  {
    id: 'mirrored_ward',
    name: 'Mirrored Ward',
    rarity: 'Epic',
    desc: 'Gain a 60-point barrier each room.',
    apply: (s) => { s.ward += 60; },
  },
  {
    id: 'twin_echo',
    name: 'Twin Echo',
    rarity: 'Epic',
    desc: 'Melee attacks release an echo shockwave.',
    apply: (s) => { s.echoShock = (s.echoShock || 0) + 1; },
  },
  {
    id: 'grave_tempo',
    name: 'Grave Tempo',
    rarity: 'Epic',
    desc: 'Attacks speed up the longer you fight in a room.',
    apply: (s) => { s.tempo = true; },
  },
  {
    id: 'hollow_crown',
    name: 'Hollow Crown',
    rarity: 'Legendary',
    desc: '+20% damage and +20% max HP. You feel heavier.',
    apply: (s) => { s.damageMult += 0.20; s.maxHp = Math.round(s.maxHp * 1.20); s.hp = Math.min(s.maxHp, s.hp + 20); },
  },
  {
    id: 'veilborn_pact',
    name: 'Veilborn Pact',
    rarity: 'Legendary',
    desc: 'Special costs 40% less energy and hits twice.',
    apply: (s) => { s.specialDiscount = Math.max(0.35, s.specialDiscount - 0.40); s.specialDouble = true; },
  },
  {
    id: 'timeless',
    name: 'Timeless',
    rarity: 'Legendary',
    desc: 'Dashes leave a slowing time rift.',
    apply: (s) => { s.dashRift = (s.dashRift || 0) + 1; },
  },
  {
    id: 'the_long_memory',
    name: 'The Long Memory',
    rarity: 'Legendary',
    desc: 'Damage grows each room you clear without dying.',
    apply: (s) => { s.longMemory = (s.longMemory || 0) + 0.06; },
  },
];

export const ROOM_TYPES = ['Combat', 'Combat', 'Elite', 'Treasure', 'Event', 'Rest', 'Gauntlet'];

// Story beats fired at realm transitions and endings.
export const STORY = {
  hubIntro: [
    'The Shattered Gate holds what the Veil could not swallow.',
    'Cael Varen wakes with five wounds and no memory of the sixth.',
  ],
  bossPre: {
    zyther: 'Mira: "He burned the archive to keep you from reading yourself."',
    seraphine: 'Korrin: "She drowns what she loves so it can never leave."',
    auren: 'Chronicler: "He watched. He only ever watched. Make him move."',
    draemor: 'Mira: "Say his name, Cael. Names are weapons down here."',
    hollow: 'The Hollow: "You were never meant to forget me."',
  },
  endings: {
    sealed: {
      title: 'ENDING: SEALED VEIL',
      lines: [
        'Cael closes the Veil and lets the memories burn inside it.',
        'The realms go quiet. The Gate keeps its silence, and its prisoners.',
        'He walks back up into a life that will never explain the dreams.',
      ],
    },
    open: {
      title: 'ENDING: OPEN VEIL',
      lines: [
        'Cael tears the Veil open and lets every forgotten thing return at once.',
        'The dead come home. So do the griefs they were carrying.',
        'Nothing is lost again. Nothing is quiet again, either.',
      ],
    },
    new: {
      title: 'ENDING: NEW VEIL',
      lines: [
        'Cael writes a Veil of his own and chooses what it will hold.',
        'Some names stay. Some are released with ceremony.',
        'He becomes the thing that remembers — deliberately, kindly, awake.',
      ],
    },
    true: {
      title: 'TRUE ENDING: THE VEILBORN',
      lines: [
        'The Hollow: "You were never meant to forget me."',
        'Cael: "Then I will remember — and choose what remains."',
        'The throne is not empty. It never was. It was waiting.',
      ],
    },
  },
};

// Fallback content, used only if the JSON fails to load.
export const FALLBACK_ENEMIES = [
  { name: 'Shade Wraith', hp: 36, damage: 12, color: '0x8f70d0' },
  { name: 'Bone Soldier', hp: 50, damage: 15, color: '0xbcb7aa' },
  { name: 'Ash Hound', hp: 65, damage: 20, color: '0xd45e58' },
  { name: 'Void Archer', hp: 42, damage: 18, color: '0x6e72a8' },
  { name: 'Soul Leech', hp: 28, damage: 9, color: '0x6fd8a6' },
];
