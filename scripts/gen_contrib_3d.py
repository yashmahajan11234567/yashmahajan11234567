#!/usr/bin/env python3
"""Render a standalone isometric 3D GitHub contribution calendar to PNG.

Reads data/contribution-calendar.json (fetched from the live GitHub GraphQL
API by scripts/build_contrib_data.py) and draws one isometric block per day:
7 weekday rows x 53 weekly columns, block height proportional to the day's
contribution count. Zero-contribution days are dark subtle tiles; active days
progress emerald -> bright green -> turquoise -> cyan with a soft glow.

Deterministic: no randomness, fixed palette, fixed camera. Pure stdlib + PIL.
Usage: python3 scripts/gen_contrib_3d.py [out.png]   (default: assets/contribution-graph-3d.png)
"""
import json
import math
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "contribution-calendar.json"
DEFAULT_OUT = ROOT / "assets" / "contribution-graph-3d.png"

# --- canvas / camera (fixed => deterministic) ---
SCALE = 2                 # supersampling factor
W, H = 1600, 1000         # final size
BG = (5, 10, 20)          # dark navy #050a14
GRID = (10, 26, 42)       # restrained grid floor #0a1a2a
U = 22.5                  # iso unit (px at 1x) — calendar scaled up ~1.5x vs U=15
A = U * math.cos(math.radians(30))   # x step per week
B = U * math.sin(math.radians(30))   # y step per (week+day)
H_UNIT = 2.1 * (U / 15.0)            # px height per contribution at 1x (proportional)
TILE_H = 1.6 * (U / 15.0)            # flat tile height for zero days

# level 0 = zero; 1..4 = quartiles of max count
LEVEL_COLORS = ["#141b26", "#0e6b4f", "#2ee66b", "#2affc8", "#00f0ff"]


def shade(hex_color: str, f: float) -> tuple:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return (min(255, int(r * f)), min(255, int(g * f)), min(255, int(b * f)))


def level_for(count: int, max_count: int) -> int:
    if count <= 0:
        return 0
    return 1 + min(3, int(4 * count / max(1, max_count)))


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    data = json.loads(DATA.read_text())
    weeks = data["weeks"]
    assert isinstance(weeks, list) and weeks and all(w.get("days") for w in weeks), "invalid contribution dataset"
    n_weeks = len(weeks)
    total = sum(d["count"] for w in weeks for d in w["days"])
    assert total == data["totalContributions"], "count sum mismatch vs totalContributions"
    max_count = max(d["count"] for w in weeks for d in w["days"])

    img = Image.new("RGB", (W * SCALE, H * SCALE), BG)
    glow = Image.new("RGB", (W * SCALE, H * SCALE), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    gdraw = ImageDraw.Draw(glow)

    # center the iso grid: extents over all block base corners
    def base_xy(wi: int, di: int) -> tuple:
        return (wi - di) * A, (wi + di) * B

    xs = [base_xy(w, d)[0] for w in range(n_weeks) for d in range(7)]
    ys = [base_xy(w, d)[1] for w in range(n_weeks) for d in range(7)]
    max_h = max(d["count"] for w in weeks for d in w["days"]) * H_UNIT + TILE_H
    span_x = (max(xs) - min(xs)) * SCALE
    span_y = (max(ys) - min(ys) + max_h) * SCALE
    margin = 48 * SCALE
    assert span_x + 2 * margin <= W * SCALE and span_y + 2 * margin <= H * SCALE, (
        f"calendar would crop: span {span_x}x{span_y} vs canvas {W * SCALE}x{H * SCALE}"
    )
    cx = (W * SCALE) / 2 - (min(xs) + max(xs)) / 2 * SCALE
    cy = (H * SCALE) / 2 - (min(ys) + max(ys) + max_h) / 2 * SCALE

    # grid floor lines
    for w in range(n_weeks + 1):
        x0, y0 = base_xy(w, 0)
        x1, y1 = base_xy(w, 7)
        draw.line([(cx + x0 * SCALE, cy + y0 * SCALE), (cx + x1 * SCALE, cy + y1 * SCALE)], fill=GRID, width=SCALE)
    for d in range(8):
        x0, y0 = base_xy(0, d)
        x1, y1 = base_xy(n_weeks, d)
        draw.line([(cx + x0 * SCALE, cy + y0 * SCALE), (cx + x1 * SCALE, cy + y1 * SCALE)], fill=GRID, width=SCALE)

    # blocks, painter's order: back (small w+d) to front
    blocks = []
    for wi, w in enumerate(weeks):
        for di, day in enumerate(w["days"]):
            blocks.append((wi + di, wi, di, day))
    blocks.sort(key=lambda t: t[0])

    for _, wi, di, day in blocks:
        count = day["count"]
        lvl = level_for(count, max_count)
        col = LEVEL_COLORS[lvl]
        h = (TILE_H if count == 0 else TILE_H + count * H_UNIT) * SCALE
        x0, y0 = base_xy(wi, di)
        x0, y0 = cx + x0 * SCALE, cy + y0 * SCALE
        # iso diamond corners (top face at height h)
        p = [
            (x0 + A * SCALE, y0),               # right
            (x0, y0 + B * SCALE),               # bottom
            (x0 - A * SCALE, y0),               # left
            (x0, y0 - B * SCALE),               # top
        ]
        top = [(x, y - h) for x, y in p]
        left_face = [p[2], p[3], top[3], top[2]]
        right_face = [p[1], p[2], top[2], top[1]]
        c_top = shade(col, 1.25)
        c_left = shade(col, 0.55)
        c_right = shade(col, 0.8)
        draw.polygon(left_face, fill=c_left)
        draw.polygon(right_face, fill=c_right)
        draw.polygon(top, fill=c_top)
        if lvl > 0:  # soft bioluminescent glow on active blocks
            gdraw.polygon(top, fill=shade(col, 1.6))

    glow = glow.filter(ImageFilter.GaussianBlur(7 * SCALE))
    img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), 0)  # noop keep
    # additive-ish glow: screen blend
    from PIL import ImageChops
    img = ImageChops.screen(img, glow)
    img = img.resize((W, H), Image.Resampling.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    # atomic write: never leave a partial/broken PNG at the asset path
    tmp = out.with_name(out.name + ".tmp")
    img.save(tmp, format="PNG", optimize=True)
    assert tmp.stat().st_size > 10_000, "generated PNG suspiciously small"
    os.replace(tmp, out)
    print(f"Wrote {out} ({out.stat().st_size} bytes) — {n_weeks} weeks x 7 days, total={total}, max/day={max_count}, span {span_x // SCALE}x{span_y // SCALE}px in {W}x{H}")


if __name__ == "__main__":
    main()
