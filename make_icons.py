"""Renders the PWA icons: a pixel-art hero bust with a bronze helm and red cloak.

Pure stdlib (zlib + struct) so the build needs no image libraries.
"""
import struct
import zlib

# 24x24 sprite. '.' transparent, g/G bronze, s/S skin, d dark, w white, r cloak.
SPRITE = [
    "........gggggggg........",
    "......gggggggggggg......",
    "....gggggggggggggggg....",
    "...gggggggggggggggggg...",
    "...gggggggggggggggggg...",
    "..gggggggggggggggggggg..",
    "..ggggGGGGGGGGGGgggggg..",
    "..ggggsssssssssssggggg..",
    "..gggssssssssssssssggg..",
    "..ggsssssssssssssssggg..",
    "..ggssddssssssddsssggg..",
    "..ggssdwssssssdwsssggg..",
    "..ggssddssssssddsssggg..",
    "..ggsssssssssssssssggg..",
    "..gggssssSSSSsssssgggg..",
    "..ggggsssssssssssggggg..",
    "...ggggggsssssggggggg...",
    "...rrrrrrrssssrrrrrrr...",
    "..rrrrrrrrssssrrrrrrrr..",
    ".rrrrrrrrrSSSSrrrrrrrrr.",
    ".rrrrrrrrrrrrrrrrrrrrrr.",
    ".rrrrrrrrrrrrrrrrrrrrrr.",
    "..rrrrrrrrrrrrrrrrrrrr..",
    "...rrrrrrrrrrrrrrrrrr...",
]

COLORS = {
    "g": (224, 164, 78),
    "G": (167, 106, 34),
    "s": (240, 208, 168),
    "S": (208, 152, 112),
    "d": (42, 23, 64),
    "w": (255, 255, 255),
    "r": (141, 43, 61),
}


def render(size):
    px = bytearray()
    sprite_h = len(SPRITE)
    sprite_w = len(SPRITE[0])
    # Leave a margin so iOS's rounded-corner mask never clips the character.
    target = size * 0.76
    scale = target / sprite_w
    off_x = (size - sprite_w * scale) / 2
    off_y = (size - sprite_h * scale) / 2 + size * 0.02
    cx = cy = size / 2.0

    for y in range(size):
        row = bytearray()
        for x in range(size):
            # background: deep purple with a warm glow behind the hero
            d = ((x - cx) ** 2 + (y - cy * 1.05) ** 2) ** 0.5 / (size * 0.62)
            glow = max(0.0, 1.0 - d) ** 1.7
            r = int(23 + glow * 92)
            g = int(11 + glow * 46)
            b = int(38 + glow * 60)

            sx = int((x - off_x) / scale)
            sy = int((y - off_y) / scale)
            if 0 <= sx < sprite_w and 0 <= sy < sprite_h:
                ch = SPRITE[sy][sx]
                if ch != ".":
                    r, g, b = COLORS[ch]

            # thin bronze ring, clipped by the icon edge
            ring = abs(((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 - size * 0.455) < size * 0.011
            if ring:
                r, g, b = 224, 164, 78

            row += bytes((r, g, b, 255))
        px += b"\x00" + bytes(row)
    return bytes(px)


def png(size, path):
    raw = render(size)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    hdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    blob = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", hdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(blob)


if __name__ == "__main__":
    for s, name in ((180, "icon-180.png"), (192, "icon-192.png"), (512, "icon-512.png")):
        png(s, name)
    print("icons written")
