#!/usr/bin/env python3
"""Generate assets/banner.svg -- unified hero banner matching the approved design.

Layout (1200x300): circular avatar LEFT, cyan separator, text block RIGHT,
navy grid background, neon zigzag waves along the bottom. The avatar PNG is
embedded as a data URI because GitHub serves README SVGs as <img>, which blocks
external sub-resources. Pure SVG + SMIL (no JS) so it animates on GitHub.
Regenerate with: python3 scripts/gen_banner.py
"""
import base64
import io
import os

from PIL import Image

W, H = 1200, 300
CYAN, BLUE, GREEN = "#00f0ff", "#58a6ff", "#39ff14"
MUTED = "#9aa7bd"

NAME = "YASH MAHAJAN"
BIO = "Hi there! I'm a developer from Pune, India \U0001F4CD"
ROLES = "Data Analyst/Engineer | Cloud/DevOps"

# avatar circle geometry (fractions of the reference design)
AV_CX, AV_CY, AV_R = 192, 150, 108
SEP_X = 336
TEXT_X = 372


def avatar_data_uri():
    path = os.path.join(os.path.dirname(__file__), "..", "assets", "profile-avatar.png")
    im = Image.open(path).convert("RGBA")
    im = im.resize((400, 400), Image.Resampling.LANCZOS)  # trim embedded size; crisp at 216px display
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def waves():
    out = []
    for base, amp, col, op, pulse in [
        (238, 60, CYAN, 0.55, True),
        (258, 85, BLUE, 0.40, False),
        (278, 50, GREEN, 0.30, False),
    ]:
        pts = " ".join(f"{x},{base - amp * abs((x % 200) - 100) / 100}" for x in range(0, W + 1, 50))
        anim = ('<animate attributeName="stroke-opacity" values="0.35;0.7;0.35" dur="4s" '
                'repeatCount="indefinite"/>') if pulse else ""
        out.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-opacity="{op}" '
                   f'stroke-width="2">{anim}</polyline>')
    return "".join(out)


def main():
    grid = "".join(
        f'<line x1="{gx}" y1="0" x2="{gx}" y2="{H}" stroke="{CYAN}" stroke-opacity="0.05"/>'
        for gx in range(0, W, 40)
    ) + "".join(
        f'<line x1="0" y1="{gy}" x2="{W}" y2="{gy}" stroke="{CYAN}" stroke-opacity="0.05"/>'
        for gy in range(0, H, 40)
    )
    caret_x = TEXT_X + len(ROLES) * 24 * 0.60 + 10
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#050b1a"/><stop offset="0.6" stop-color="#0a1633"/><stop offset="1" stop-color="#0b1e3f"/>
  </linearGradient>
  <linearGradient id="nameGrad" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{BLUE}"/><stop offset="1" stop-color="{CYAN}"/>
  </linearGradient>
  <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">
    <feGaussianBlur stdDeviation="6" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <clipPath id="avClip"><circle cx="{AV_CX}" cy="{AV_CY}" r="{AV_R}"/></clipPath>
</defs>
<rect width="{W}" height="{H}" fill="url(#bg)"/>
{grid}
{waves()}
<image x="{AV_CX - AV_R}" y="{AV_CY - AV_R}" width="{2 * AV_R}" height="{2 * AV_R}" clip-path="url(#avClip)" xlink:href="{avatar_data_uri()}" href="{avatar_data_uri()}"/>
<line x1="{SEP_X}" y1="75" x2="{SEP_X}" y2="195" stroke="{CYAN}" stroke-width="2" stroke-opacity="0.85" filter="url(#glow)"/>
<text x="{TEXT_X}" y="92" font-family="Segoe UI, Ubuntu, Sans-Serif" font-size="54" font-weight="800" fill="url(#nameGrad)" filter="url(#glow)" letter-spacing="3">{NAME}</text>
<text x="{TEXT_X}" y="134" font-family="Segoe UI, Ubuntu, Sans-Serif" font-size="20" fill="{MUTED}">{BIO}</text>
<text x="{TEXT_X}" y="180" font-family="Consolas, Menlo, monospace" font-size="24" font-weight="bold" fill="#ffffff" letter-spacing="1">{ROLES}</text>
<rect x="{caret_x}" y="{180 - 24 + 5}" width="13" height="24" fill="{CYAN}"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1s" repeatCount="indefinite"/></rect>
</svg>'''
    out = os.path.join(os.path.dirname(__file__), "..", "assets", "banner.svg")
    with open(out, "w") as f:
        f.write(svg)
    print("wrote", out, len(svg), "bytes")


if __name__ == "__main__":
    main()
