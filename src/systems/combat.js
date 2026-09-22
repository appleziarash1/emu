// Weapon resolution: turning a weapon definition + run stats into concrete
// attacks. Kept separate from the scene so combat tuning lives in one place.
import { C } from '../config.js';
import { audio } from '../audio.js';

// Returns the list of "hits" an attack produces. A hit is
// { x, y, kind, range, arc, radius, angle, damage, pierce, fromPlayer:true }
export function buildAttack(weapon, player, stats, aimAngle) {
  const baseDamage = weapon.damage * stats.damageMult * (1 + (stats.longMemory || 0) * player.run.roomsCleared);
  const range = weapon.range * stats.rangeMult;
  const arc = weapon.arc;
  const swing = { angle: aimAngle, range, arc };

  switch (weapon.kind) {
    case 'ranged': {
      const count = weapon.id === 'tidebreaker_chakrams' ? 2 : 1;
      const spread = count > 1 ? 0.13 : 0;
      const hits = [];
      for (let i = 0; i < count; i++) {
        const a = aimAngle + (i - (count - 1) / 2) * spread;
        hits.push({
          kind: 'projectile',
          x: player.x, y: player.y, angle: a,
          speed: weapon.id === 'moonthread_bow' ? 780 : 620,
          damage: baseDamage,
          pierce: stats.pierce + (weapon.id === 'moonthread_bow' ? 1 : 0),
          color: weapon.color,
          spin: weapon.id === 'tidebreaker_chakrams',
          life: 1400,
        });
      }
      return hits;
    }
    case 'thrust': {
      return [{
        kind: 'melee', x: player.x, y: player.y, angle: aimAngle,
        range: range * 1.15, arc: arc, damage: baseDamage * 1.1,
        color: weapon.color, thrust: true,
      }];
    }
    default: {
      const hits = [{
        kind: 'melee', x: player.x, y: player.y, angle: aimAngle,
        range, arc, damage: baseDamage, color: weapon.color,
      }];
      if (stats.echoShock) {
        hits.push({
          kind: 'shock', x: player.x, y: player.y, radius: range * 0.8,
          damage: baseDamage * 0.35 * stats.echoShock, color: weapon.color,
        });
      }
      return hits;
    }
  }
}

export function buildSpecial(weapon, player, stats, aimAngle, ctx) {
  const cost = Math.round(weapon.specialCost * stats.specialDiscount);
  const dmg = weapon.damage * stats.damageMult * 2.2;
  const push = (hits) => {
    if (stats.specialDouble) {
      return hits.concat(hits.map((h) => ({ ...h, damage: (h.damage || 0) * 0.6 })));
    }
    return hits;
  };

  switch (weapon.id) {
    case 'ashen_edge': {
      // Three-step lunge leaving burning ground.
      const hits = [];
      for (let i = 0; i < 3; i++) {
        const a = aimAngle + (i - 1) * 0.35;
        const lx = player.x + Math.cos(aimAngle) * (i + 1) * 46;
        const ly = player.y + Math.sin(aimAngle) * (i + 1) * 46;
        hits.push({ kind: 'melee', x: lx, y: ly, angle: a, range: 92, arc: 1.6, damage: dmg * 0.7, color: weapon.color });
        ctx.addHazard({ x: lx, y: ly, radius: 52, damage: dmg * 0.18, until: ctx.now() + 2600, color: 0xff714a });
      }
      return { cost, hits: push(hits), dash: { angle: aimAngle, distance: 130 } };
    }
    case 'pyre_lance': {
      return {
        cost,
        hits: push([{ kind: 'nova', x: player.x, y: player.y, radius: 210, damage: dmg, color: 0xff714a }]),
      };
    }
    case 'tempest_gauntlets': {
      return {
        cost,
        hits: push([{ kind: 'shock', x: player.x, y: player.y, radius: 190, damage: dmg * 0.8, color: weapon.color, stun: 700 }]),
      };
    }
    case 'moonthread_bow': {
      const hits = [];
      for (let i = -4; i <= 4; i++) {
        hits.push({
          kind: 'projectile', x: player.x, y: player.y, angle: aimAngle + i * 0.14,
          speed: 760, damage: dmg * 0.75, pierce: stats.pierce + 3, color: weapon.color, life: 1600,
        });
      }
      return { cost, hits: push(hits) };
    }
    case 'gravewind_scythe': {
      return {
        cost,
        hits: push([{
          kind: 'vortex', x: player.x, y: player.y, radius: 250, damage: dmg * 0.9,
          color: weapon.color, pull: 340, until: ctx.now() + 1600,
        }]),
      };
    }
    case 'tidebreaker_chakrams': {
      const hits = [];
      for (let i = 0; i < 6; i++) {
        hits.push({
          kind: 'orbit', damage: dmg * 0.5, color: weapon.color,
          offset: (i / 6) * Math.PI * 2, radius: 110, until: ctx.now() + 3400,
        });
      }
      return { cost, hits: push(hits) };
    }
    default:
      return { cost, hits: [] };
  }
}

// Melee hit test: is `target` inside the cone/arc?
export function coneHits(hit, tx, ty, radius = 0) {
  const dx = tx - hit.x;
  const dy = ty - hit.y;
  const dist = Math.hypot(dx, dy);
  if (dist > hit.range + radius) return false;
  const a = Math.atan2(dy, dx);
  let diff = a - hit.angle;
  while (diff > Math.PI) diff -= Math.PI * 2;
  while (diff < -Math.PI) diff += Math.PI * 2;
  const half = hit.arc / 2;
  if (Math.abs(diff) <= half) return true;
  // Near the tip, allow a slightly wider arc so the swing feels generous.
  if (dist < hit.range * 0.5 && Math.abs(diff) <= half * 1.6) return true;
  return false;
}

export function rollCrit(stats, rand = Math.random) {
  return rand() < stats.crit;
}

export default { buildAttack, buildSpecial, coneHits, rollCrit };
