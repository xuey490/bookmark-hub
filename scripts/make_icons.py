"""Generate simple PNG icons for the Chrome extension (no third-party deps)."""

from __future__ import annotations

import os
import struct
import zlib

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "extension", "icons")


def _sample(px: float, py: float):
    radius = 0.22
    # rounded square mask
    cx = min(max(px, radius), 1 - radius)
    cy = min(max(py, radius), 1 - radius)
    if (px - cx) ** 2 + (py - cy) ** 2 > radius ** 2:
        return (0, 0, 0, 0)

    # blue gradient background
    t = py
    r = int(22 + (64 - 22) * t)
    g = int(119 + (150 - 119) * t)
    b = int(255 + (255 - 255) * t)

    # white bookmark ribbon with a V notch at the bottom
    if 0.34 <= px <= 0.66 and 0.22 <= py <= 0.78:
        notch = py > 0.60 and abs(px - 0.5) < (py - 0.60) / 0.18 * 0.13
        if not notch:
            return (255, 255, 255, 255)

    return (r, g, b, 255)


def make_png(size: int) -> bytes:
    scale = 4
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            total = [0, 0, 0, 0]
            for sy in range(scale):
                for sx in range(scale):
                    px = (x * scale + sx + 0.5) / (size * scale)
                    py = (y * scale + sy + 0.5) / (size * scale)
                    sample = _sample(px, py)
                    for i in range(4):
                        total[i] += sample[i]
            count = scale * scale
            row.extend(value // count for value in total)
        rows.append(bytes(row))

    raw = b"".join(rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for size in (16, 48, 128):
        path = os.path.join(OUT_DIR, f"icon{size}.png")
        with open(path, "wb") as handle:
            handle.write(make_png(size))
        print("wrote", path)


if __name__ == "__main__":
    main()
