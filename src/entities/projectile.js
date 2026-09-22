// Player-owned projectiles, orbiting weapons, and lingering hazards.
import { ARENA } from '../config.js';

export class PlayerShot {
  constructor(scene, hit) {
    this.scene = scene;
    this.x = hit.x;
    this.y = hit.y;
    this.angle = hit.angle;
    this.speed = hit.speed;
    this.damage = hit.damage;
    this.pierce = hit.pierce || 0;
    this.color = hit.color;
    this.spin = !!hit.spin;
    this.alive = true;
    this.age = 0;
    this.life = hit.life || 1400;
    this.radius = hit.radius || 9;
    this.hitSet = new Set();
    this.returning = false;
    this.startX = hit.x;
    this.startY = hit.y;

    this.shape = scene.add.circle(this.x, this.y, this.radius, this.color, 0.95).setDepth(27);
    this.shape.setStrokeStyle(2, 0xffffff, 0.5);
    if (this.spin) {
      this.inner = scene.add.circle(this.x, this.y, this.radius * 0.45, 0xffffff, 0.35).setDepth(27);
    }
  }

  update(dt, ctx) {
    if (!this.alive) return;
    const s = dt / 1000;
    this.age += dt;
    if (this.age > this.life) { this.alive = false; return; }
    this.x += Math.cos(this.angle) * this.speed * s;
    this.y += Math.sin(this.angle) * this.speed * s;
    this.shape.setPosition(this.x, this.y);
    if (this.inner) this.inner.setPosition(this.x, this.y);
    if (this.spin) {
      const r = this.radius * (1 + Math.sin(this.age / 90) * 0.2);
      this.shape.setRadius(r);
      this.inner.setRadius(r * 0.45);
    }

    for (const e of ctx.enemies) {
      if (!e.alive || this.hitSet.has(e)) continue;
      if (Math.hypot(e.x - this.x, e.y - this.y) < this.radius + e.radius) {
        ctx.hitEnemy(e, this.damage, this.angle, this);
        this.hitSet.add(e);
        if (this.pierce-- <= 0) { this.alive = false; return; }
      }
    }
    if (ctx.boss && ctx.boss.alive && !this.hitSet.has(ctx.boss)) {
      const b = ctx.boss;
      if (Math.hypot(b.x - this.x, b.y - this.y) < this.radius + b.radius) {
        ctx.hitBoss(b, this.damage, this.angle, this);
        this.hitSet.add(b);
        if (this.pierce-- <= 0) { this.alive = false; return; }
      }
    }

    if (this.x < ARENA.x - 60 || this.x > ARENA.x + ARENA.w + 60
      || this.y < ARENA.y - 60 || this.y > ARENA.y + ARENA.h + 60) {
      this.alive = false;
    }
  }

  destroy() {
    this.shape.destroy();
    if (this.inner) this.inner.destroy();
  }
}

// Persistent area effect (burn patch, vortex, time rift).
export class Hazard {
  constructor(scene, def) {
    this.scene = scene;
    this.x = def.x;
    this.y = def.y;
    this.radius = def.radius;
    this.damage = def.damage;
    this.until = def.until;
    this.color = def.color || 0xff714a;
    this.pull = def.pull || 0;
    this.slow = def.slow || 0;
    this.hostile = def.hostile !== false ? def.hostile : false;
    this.tickInterval = def.tickInterval || 380;
    this.lastTick = -9999;
    this.alive = true;
    this.patch = def.patch || null;

    this.gfx = scene.add.circle(this.x, this.y, this.radius, this.color, 0.18)
      .setStrokeStyle(2, this.color, 0.5).setDepth(18);
  }

  update(dt, ctx, now) {
    if (!this.alive) return;
    if (now >= this.until) { this.expire(); return; }
    // gentle pulse
    const t = (this.until - now) / 1200;
    this.gfx.setAlpha(Math.min(0.35, 0.14 + Math.max(0, t) * 0.12));

    // pull player toward centre
    if (this.pull) {
      const dx = this.x - ctx.player.x;
      const dy = this.y - ctx.player.y;
      const d = Math.hypot(dx, dy) || 1;
      if (d < this.radius) {
        ctx.player.x += (dx / d) * this.pull * dt / 1000 * 0.5;
        ctx.player.y += (dy / d) * this.pull * dt / 1000 * 0.5;
      }
    }
  }

  hurtEnemiesAt(now, ctx, enemies, boss) {
    if (now - this.lastTick < this.tickInterval) return;
    this.lastTick = now;
    const list = [...enemies];
    if (boss && boss.alive) list.push(boss);
    for (const e of list) {
      if (!e.alive) continue;
      if (Math.hypot(e.x - this.x, e.y - this.y) < this.radius + e.radius) {
        ctx.hitEnemyOrBoss(e, this.damage, Math.atan2(e.y - this.y, e.x - this.x));
      }
    }
  }

  expire() {
    this.alive = false;
    this.gfx.destroy();
    if (this.patch && this.patch.destroy) this.patch.destroy();
  }

  destroy() { this.expire(); }
}

// A chakram orbiting the player.
export class Orbit {
  constructor(scene, def) {
    this.scene = scene;
    this.offset = def.offset;
    this.radius = def.radius;
    this.damage = def.damage;
    this.color = def.color;
    this.until = def.until;
    this.alive = true;
    this.hitTimers = new Map();
    this.angle = def.offset;
    this.shape = scene.add.circle(0, 0, 12, this.color, 0.9).setDepth(29);
    this.shape.setStrokeStyle(2, 0xffffff, 0.5);
  }

  update(dt, ctx, now) {
    if (!this.alive) return;
    if (now >= this.until) { this.alive = false; return; }
    this.angle += dt / 1000 * 5.2;
    const px = ctx.player.x + Math.cos(this.angle + this.offset) * this.radius;
    const py = ctx.player.y + Math.sin(this.angle + this.offset) * this.radius;
    this.shape.setPosition(px, py);
    const list = [...ctx.enemies];
    if (ctx.boss && ctx.boss.alive) list.push(ctx.boss);
    for (const e of list) {
      if (!e.alive) continue;
      const last = this.hitTimers.get(e) || -9999;
      if (now - last < 300) continue;
      if (Math.hypot(e.x - px, e.y - py) < 14 + e.radius) {
        this.hitTimers.set(e, now);
        ctx.hitEnemyOrBoss(e, this.damage, Math.atan2(e.y - py, e.x - px));
      }
    }
  }

  destroy() { this.shape.destroy(); }
}
