#!/usr/bin/env python3
"""Bake a dark rounded background into each downloaded technology icon SVG.

simpleicons SVGs are transparent 24x24 glyphs; on light-theme viewers they are
low-contrast. Wrapping them in a dark card keeps the neon-dark theme consistent.
Custom badge icons (tsql/tableau/powerbi/excel) already have a background.
"""
import glob
import os
import re

ICONS = os.path.join(os.path.dirname(__file__), "..", "assets", "technology-icons")
CUSTOM = {"tsql.svg", "tableau.svg", "powerbi.svg", "excel.svg"}

for path in sorted(glob.glob(os.path.join(ICONS, "*.svg"))):
    name = os.path.basename(path)
    if name in CUSTOM:
        continue
    src = open(path).read()
    m = re.search(r"<svg[^>]*>(.*)</svg>", src, re.S)
    inner = m.group(1) if m else src
    out = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">'
        '<rect x="1.5" y="1.5" width="45" height="45" rx="10" fill="#0d1117" stroke="#1f6feb" stroke-opacity="0.45" stroke-width="1.5"/>'
        f'<g transform="translate(7,7) scale(1.417)">{inner}</g>'
        "</svg>"
    )
    open(path, "w").write(out)
    print("wrapped", name)
