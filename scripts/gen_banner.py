#!/usr/bin/env python3
"""Generate assets/banner.svg -- neon hero banner with SMIL typing animation.

Pure SVG + SMIL (no JS), so it animates when embedded via <img> on GitHub.
Run once; the output is committed. Regenerate with: python3 scripts/gen_banner.py
"""
import os

W, H = 960, 260
CYAN, BLUE, GREEN, TEXT, MUTED = "#00f0ff", "#58a6ff", "#39ff14", "#e6edf3", "#8b949e"

TYPED = "Data | Analytics | ML | DevOps | Data Engineering"
CYCLE = 9.0          # seconds for one full type/erase cycle
CHAR_T = 0.09        # seconds per character


def typing_text(x, y, size):
    """Per-character SMIL opacity animation = typewriter effect that loops."""
    parts = [f'<text x="{x}" y="{y}" font-family="Consolas, Menlo, monospace" '
             f'font-size="{size}" fill="{TEXT}" letter-spacing="1">']
    for i, ch in enumerate(TYPED):
        b = (0.6 + i * CHAR_T) / CYCLE
        end = min(b + 0.03, 0.94)
        parts.append(
            f'<tspan><animate attributeName="opacity" values="0;0;1;1;0" '
            f'keyTimes="0;{b:.4f};{end:.4f};0.94;1" dur="{CYCLE}s" '
            f'repeatCount="indefinite"/>{ch}</tspan>'
        )
    # blinking caret after the text
    cx = x + len(TYPED) * size * 0.62 + 6
    parts.append(
        f'<rect x="{cx}" y="{y - size + 4}" width="{size * 0.55}" height="{size}" fill="{CYAN}">'
        f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" '
        f'dur="1s" repeatCount="indefinite"/></rect>'
    )
    parts.append("</text>")
    return "".join(parts)


def main():
    grid = []
    for gx in range(0, W, 40):
        grid.append(f'<line x1="{gx}" y1="0" x2="{gx}" y2="{H}" stroke="{CYAN}" stroke-opacity="0.05"/>')
    for gy in range(0, H, 40):
        grid.append(f'<line x1="0" y1="{gy}" x2="{W}" y2="{gy}" stroke="{CYAN}" stroke-opacity="0.05"/>')

    mountains = []
    for base, amp, col, op in [(250, 90, CYAN, 0.35), (265, 120, BLUE, 0.3), (280, 70, GREEN, 0.22)]:
        pts = " ".join(f"{x},{base - amp * abs((x % 240) - 120) / 120}" for x in range(0, W + 1, 60))
        mountains.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-opacity="{op}" stroke-width="1.5"/>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
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
</defs>
<rect width="{W}" height="{H}" fill="url(#bg)"/>
{''.join(grid)}
{''.join(mountains)}
<text x="48" y="100" font-family="Segoe UI, Ubuntu, Sans-Serif" font-size="46" font-weight="800"
      fill="url(#nameGrad)" filter="url(#glow)" letter-spacing="3">YASH MAHAJAN</text>
<text x="48" y="132" font-family="Segoe UI, Ubuntu, Sans-Serif" font-size="17" fill="{MUTED}">Hi there! I&#8217;m a developer from Pune, India &#128205;</text>
{typing_text(48, 178, 21)}
<g>
  <rect x="660" y="34" width="276" height="96" rx="9" fill="#0a0f1e" stroke="#30363d"/>
  <circle cx="678" cy="51" r="4.5" fill="#ff5f57"/><circle cx="694" cy="51" r="4.5" fill="#febc2e"/><circle cx="710" cy="51" r="4.5" fill="#28c840"/>
  <text x="674" y="78" font-family="Consolas, Menlo, monospace" font-size="12.5" fill="{GREEN}">&gt; whoami</text>
  <text x="674" y="98" font-family="Consolas, Menlo, monospace" font-size="12.5" fill="{GREEN}">&gt; data-analyst &amp; ml-enthusiast</text>
  <text x="674" y="118" font-family="Consolas, Menlo, monospace" font-size="12.5" fill="{GREEN}">&gt; building data systems_</text>
</g>
</svg>'''
    out = os.path.join(os.path.dirname(__file__), "..", "assets", "banner.svg")
    with open(out, "w") as f:
        f.write(svg)
    print("wrote", out, len(svg), "bytes")


if __name__ == "__main__":
    main()
