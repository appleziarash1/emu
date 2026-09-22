#!/usr/bin/env python3
"""Generate VEILBORN PWA icons and iOS launch screens.

Kept in-repo so the assets can be regenerated instead of being opaque binaries.
Run: python3 scripts/gen_pwa_assets.py
"""
from PIL import Image, ImageDraw, ImageFont
import os
import math
import random

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public")
ICON_DIR = os.path.join(ROOT, "icons")
SPLASH_DIR = os.path.join(ROOT, "splash")
os.makedirs(ICON_DIR, exist_ok=True)
os.makedirs(SPLASH_DIR, exist_ok=True)

BG_TOP = (48, 39, 68)
BG_BOTTOM = (7, 8, 16)
ACCENT = (156, 108, 255)
GOLD = (241, 199, 91)
CYAN = (99, 217, 232)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def gradient(size):
    img = Image.new("RGB", size, BG_BOTTOM)
    d = ImageDraw.Draw(img)
    w, h = size
    for y in range(h):
        d.line([(0, y), (w, y)], fill=lerp(BG_TOP, BG_BOTTOM, y / max(1, h - 1)))
    return img


def add_motes(draw, size, count, seed=7):
    rnd = random.Random(seed)
    w, h = size
    for _ in range(count):
        x = rnd.random() * w
        y = rnd.random() * h
        r = rnd.uniform(1, max(2, w * 0.006))
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))


def draw_mark(img, size, with_text=True):
    """The Veilborn sigil: a broken ring (the Veil) with a blade through it."""
    d = ImageDraw.Draw(img, "RGBA")
    w = h = size
    cx, cy = w / 2, h / 2 * (0.86 if with_text else 1.0)
    R = min(w, h) * (0.30 if with_text else 0.36)

    ring_w = max(2, int(R * 0.10))
    for start in (200, 320, 80):
        d.arc(
            [cx - R, cy - R, cx + R, cy + R],
            start=start, end=start + 100,
            fill=(*ACCENT, 235), width=ring_w,
        )
    d.ellipse(
        [cx - R * 0.66, cy - R * 0.66, cx + R * 0.66, cy + R * 0.66],
        outline=(*CYAN, 90), width=max(1, int(R * 0.05)),
    )
    bl = R * 1.15
    ang = math.radians(-58)
    dx, dy = math.cos(ang) * bl, math.sin(ang) * bl
    d.line([cx - dx, cy - dy, cx + dx, cy + dy], fill=(*GOLD, 245), width=max(2, int(R * 0.13)))
    hx, hy = cx + dx * 0.62, cy + dy * 0.62
    d.line([hx - dy * 0.18, hy + dx * 0.18, hx + dy * 0.18, hy - dx * 0.18],
           fill=(*GOLD, 245), width=max(2, int(R * 0.11)))
    d.ellipse([cx - R * 0.16, cy - R * 0.16, cx + R * 0.16, cy + R * 0.16], fill=(255, 255, 255, 210))

    if with_text:
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                int(w * 0.115),
            )
            small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
                int(w * 0.042),
            )
        except Exception:
            font = ImageFont.load_default()
            small = font
        txt = "VEILBORN"
        bbox = d.textbbox((0, 0), txt, font=font)
        tw = bbox[2] - bbox[0]
        d.text((cx - tw / 2, cy + R * 1.12), txt, font=font, fill=(244, 241, 255, 255))
        sub = "DESCENT. RISE. REWRITE."
        bbox2 = d.textbbox((0, 0), sub, font=small)
        d.text((cx - (bbox2[2] - bbox2[0]) / 2, cy + R * 1.12 + int(w * 0.135)),
               sub, font=small, fill=(*ACCENT, 255))
    return img


def make_icon(size, maskable=False):
    img = gradient((size, size)).convert("RGBA")
    add_motes(ImageDraw.Draw(img), (size, size), count=int(size * 0.5), seed=size)
    if maskable:
        inner = int(size * 0.72)
        mark = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        sub = Image.new("RGBA", (inner, inner), (0, 0, 0, 0))
        draw_mark(sub, inner, with_text=False)
        mark.alpha_composite(sub, ((size - inner) // 2, (size - inner) // 2))
        img.alpha_composite(mark)
    else:
        draw_mark(img, size, with_text=False)
    return img


def make_splash(w, h):
    img = gradient((w, h)).convert("RGBA")
    add_motes(ImageDraw.Draw(img), (w, h), count=int((w * h) / 9000), seed=w + h)
    # Draw the sigil on its own square canvas sized to the short edge, then
    # centre it, so wordmark proportions stay identical across phone sizes.
    mark_size = int(min(w, h) * 1.05)
    mark = Image.new("RGBA", (mark_size, mark_size), (0, 0, 0, 0))
    draw_mark(mark, mark_size, with_text=True)
    img.alpha_composite(mark, ((w - mark_size) // 2, (h - mark_size) // 2))
    return img


def main():
    for size in (180, 192, 512):
        make_icon(size).convert("RGB").save(os.path.join(ICON_DIR, f"icon-{size}.png"))
        print("icon", size)
    make_icon(512, maskable=True).convert("RGB").save(os.path.join(ICON_DIR, "icon-maskable-512.png"))
    print("icon maskable 512")

    splashes = [
        (1170, 2532), (1284, 2778), (1179, 2556), (1290, 2796),
        (1242, 2688), (1242, 2208), (1320, 2868), (1206, 2622),
        (1125, 2436), (828, 1792), (750, 1334),
    ]
    for (w, h) in splashes:
        make_splash(w, h).convert("RGB").save(os.path.join(SPLASH_DIR, f"splash-{w}x{h}.png"))
        print("splash", w, h)


if __name__ == "__main__":
    main()
