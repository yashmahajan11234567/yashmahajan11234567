#!/usr/bin/env python3
"""Generate neon-styled profile stat SVGs from live GitHub API data.

Run locally (uses gh CLI auth) or in GitHub Actions (GH_TOKEN env).
Writes: assets/stats.svg, assets/streak.svg, assets/top-langs.svg,
        assets/contribution-graph.svg
All numbers come from the GitHub API -- nothing is hardcoded or fabricated.
"""
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta

USER = os.environ.get("PROFILE_USER", "yashmahajan11234567")
ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")

CYAN = "#00f0ff"
BLUE = "#58a6ff"
GREEN = "#39ff14"
TEXT = "#e6edf3"
MUTED = "#8b949e"
CARD = "#0d1117"
BORDER = "#1f6feb"


def gh_graphql(query, variables):
    env = dict(os.environ)
    token = env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")
    if token:
        env["GH_TOKEN"] = token  # fall back to gh's stored auth when unset
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}",
         *sum([["-F", f"{k}={v}"] for k, v in variables.items()], [])],
        capture_output=True, text=True, env=env, check=True,
    )
    return json.loads(out.stdout)["data"]


QUERY = """
query($u: String!) {
  user(login: $u) {
    createdAt
    followers { totalCount }
    following { totalCount }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        name
        description
        url
        pushedAt
        primaryLanguage { name }
        stargazerCount
        forkCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_open(w, h):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="Segoe UI, Ubuntu, Sans-Serif">')


def gen_stats(total_contrib, repo_count, stars, forks, years):
    cards = [
        ("🕒", str(total_contrib), "Contributions / yr", CYAN),
        ("📁", str(repo_count), "Public Repositories", BLUE),
        ("⭐", str(stars), "Stars Earned", "#f2c811"),
        ("⑂", str(forks), "Forks", "#a371f7"),
        ("📅", f"{years}+", "Years on GitHub", GREEN),
    ]
    cw, ch, gap = 156, 96, 12
    w = len(cards) * cw + (len(cards) - 1) * gap
    h = ch
    parts = [svg_open(w, h)]
    for i, (icon, val, label, color) in enumerate(cards):
        x = i * (cw + gap)
        parts.append(
            f'<rect x="{x}" y="0" width="{cw}" height="{ch}" rx="12" fill="{CARD}" '
            f'stroke="{color}" stroke-opacity="0.55" stroke-width="1.5"/>'
            f'<text x="{x+14}" y="30" font-size="20">{icon}</text>'
            f'<text x="{x+14}" y="62" font-size="26" font-weight="bold" fill="{color}">{val}</text>'
            f'<text x="{x+14}" y="84" font-size="11.5" fill="{MUTED}">{label}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def streaks(days):
    """days: list of (date_str, count) oldest->newest. Returns (current, longest)."""
    d = {date.fromisoformat(dd): c for dd, c in days}
    if not d:
        return 0, 0
    today = date.today()
    cur = 0
    day = today if d.get(today, 0) > 0 else today - timedelta(days=1)
    while d.get(day, 0) > 0:
        cur += 1
        day -= timedelta(days=1)
    longest = run = 0
    for dd in sorted(d):
        run = run + 1 if d[dd] > 0 else 0
        longest = max(longest, run)
    return cur, longest


def gen_streak(current, longest):
    w, h = 300, 120
    cx, cy, r = 60, 60, 44
    frac = (current / longest) if longest else 0
    circ = 2 * 3.14159 * r
    parts = [svg_open(w, h)]
    parts.append(f'<rect x="0" y="0" width="{w}" height="{h}" rx="12" fill="{CARD}" stroke="{BORDER}" stroke-opacity="0.55" stroke-width="1.5"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#21262d" stroke-width="9"/>')
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#g)" stroke-width="9" '
        f'stroke-linecap="round" stroke-dasharray="{circ:.1f}" stroke-dashoffset="{circ*(1-frac):.1f}" '
        f'transform="rotate(-90 {cx} {cy})">'
        f'<animate attributeName="stroke-dashoffset" from="{circ:.1f}" to="{circ*(1-frac):.1f}" dur="1.2s" fill="freeze"/></circle>'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#a371f7"/><stop offset="1" stop-color="{CYAN}"/></linearGradient></defs>'
    )
    parts.append(f'<text x="{cx}" y="{cy+9}" font-size="30" text-anchor="middle">🔥</text>')
    parts.append(f'<text x="120" y="48" font-size="24" font-weight="bold" fill="{TEXT}">{current} days</text>')
    parts.append(f'<text x="120" y="68" font-size="12" fill="{MUTED}">Current streak</text>')
    parts.append(f'<text x="120" y="90" font-size="12" fill="#f2c811">🏆 Longest: {longest} days</text>')
    parts.append("</svg>")
    return "".join(parts)


def gen_top_langs(lang_bytes):
    total = sum(lang_bytes.values()) or 1
    top = sorted(lang_bytes.items(), key=lambda kv: -kv[1])[:5]
    w, row = 320, 26
    h = 30 + len(top) * row + 10
    parts = [svg_open(w, h)]
    parts.append(f'<rect x="0" y="0" width="{w}" height="{h}" rx="12" fill="{CARD}" stroke="{BORDER}" stroke-opacity="0.55" stroke-width="1.5"/>')
    parts.append(f'<text x="16" y="24" font-size="13" font-weight="bold" fill="{CYAN}">Top Languages</text>')
    y = 44
    for name, b in top:
        pct = b / total * 100
        color = LANG_COLORS.get(name.lower(), "#8b949e")
        parts.append(f'<text x="16" y="{y+11}" font-size="11.5" fill="{TEXT}">{esc(name)}</text>')
        parts.append(f'<rect x="110" y="{y}" width="{190*(pct/100):.1f}" height="10" rx="5" fill="{color}"/>')
        parts.append(f'<rect x="110" y="{y}" width="190" height="10" rx="5" fill="none" stroke="#21262d"/>')
        parts.append(f'<text x="306" y="{y+11}" font-size="11" fill="{MUTED}" text-anchor="end">{pct:.1f}%</text>')
        y += row
    parts.append("</svg>")
    return "".join(parts)


LANG_COLORS = {
    "python": "#3572A5", "typescript": "#3178c6", "javascript": "#f1e05a",
    "go": "#00ADD8", "tsql": "#cc2927", "jupyter notebook": "#DA5B0B",
    "html": "#e34c26", "css": "#563d7c", "dockerfile": "#384d54",
    "shell": "#89e051", "hcl": "#844FBA", "tex": "#3D6117",
    "c++": "#f34b7d", "powershell": "#012456", "plpgsql": "#336790",
}


def gen_heatmap(weeks):
    cell, gap = 12, 3
    cols = len(weeks)
    w = 46 + cols * (cell + gap)
    h = 34 + 7 * (cell + gap)
    levels = ["#141b26", "#0f5132", "#1fa055", "#2ee66b", GREEN]
    maxc = max((d["contributionCount"] for wk in weeks for d in wk["contributionDays"]), default=1) or 1
    parts = [svg_open(w, h)]
    parts.append(f'<rect x="0" y="0" width="{w}" height="{h}" rx="12" fill="{CARD}" stroke="{BORDER}" stroke-opacity="0.55" stroke-width="1.5"/>')
    parts.append(f'<text x="16" y="22" font-size="13" font-weight="bold" fill="{CYAN}">Contribution Graph · last 52 weeks</text>')
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    prev_month = -1
    for ci, wk in enumerate(weeks):
        for ri, d in enumerate(wk["contributionDays"]):
            c = d["contributionCount"]
            lvl = 0 if c == 0 else 1 + min(3, c * 4 // (maxc + 1))
            x = 46 + ci * (cell + gap)
            y = 34 + ri * (cell + gap)
            parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{levels[lvl]}"><title>{c} contributions on {d["date"]}</title></rect>')
        dt = date.fromisoformat(wk["contributionDays"][0]["date"])
        if dt.month != prev_month:
            parts.append(f'<text x="{46 + ci*(cell+gap)}" y="30" font-size="9" fill="{MUTED}">{months[dt.month-1]}</text>')
            prev_month = dt.month
    for i, dow in enumerate(["Mon", "", "Wed", "", "Fri", ""]):
        if dow:
            parts.append(f'<text x="8" y="{34 + (i*2+1)*(cell+gap) - 2}" font-size="9" fill="{MUTED}">{dow}</text>')
    parts.append("</svg>")
    return "".join(parts)


def gen_featured(nodes):
    """2-col repo cards for a curated set; all data from the API."""
    featured = [n for n in nodes if n["name"] in FEATURED]
    featured.sort(key=lambda n: FEATURED.index(n["name"]))
    cw, ch, gap = 428, 118, 14
    cols = 2
    rows = (len(featured) + cols - 1) // cols
    w = cols * cw + (cols - 1) * gap
    h = rows * ch + (rows - 1) * gap + 8
    parts = [svg_open(w, h)]
    for i, r in enumerate(featured):
        x = (i % cols) * (cw + gap)
        y = (i // cols) * (ch + gap) + 4
        lang = (r["primaryLanguage"] or {}).get("name") or "—"
        color = LANG_COLORS.get(lang.lower(), "#8b949e")
        desc = (r["description"] or "").strip().replace("\n", " ")
        if len(desc) > 78:
            desc = desc[:75] + "…"
        parts.append(
            f'<a href="{r["url"]}" target="_blank">'
            f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="10" fill="{CARD}" '
            f'stroke="{BORDER}" stroke-opacity="0.6" stroke-width="1.4"/>'
            f'<text x="{x+14}" y="{y+28}" font-size="15" font-weight="bold" fill="{CYAN}">{esc(r["name"])}</text>'
            f'<text x="{x+14}" y="{y+50}" font-size="11.5" fill="{MUTED}">{esc(desc)}</text>'
            f'<circle cx="{x+20}" cy="{y+ch-22}" r="5" fill="{color}"/>'
            f'<text x="{x+32}" y="{y+ch-18}" font-size="11.5" fill="{TEXT}">{esc(lang)}</text>'
            f'<text x="{x+cw-14}" y="{y+ch-18}" font-size="11.5" fill="{MUTED}" text-anchor="end">⭐ {r["stargazerCount"]}   ⑂ {r["forkCount"]}</text>'
            f'</a>'
        )
    parts.append("</svg>")
    return "".join(parts)


FEATURED = [
    "Real-Time-Balance-Visibility-in-Microservice-Based-Money-Transfers",
    "personal-website",
    "digital-prescription-verification-devops",
    "devops-health-check",
    "PRIMETradeAI",
    "Sql-data-warehouse",
]


def main():
    data = gh_graphql(QUERY, {"u": USER})["user"]
    cal = data["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"]) for wk in cal["weeks"] for d in wk["contributionDays"]]
    repos = data["repositories"]
    nodes = [r for r in repos["nodes"] if r["name"].lower() != USER.lower()]  # exclude profile repo itself
    stars = sum(r["stargazerCount"] for r in nodes)
    forks = sum(r["forkCount"] for r in nodes)
    created = datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00")).date()
    years = date.today().year - created.year - ((date.today().month, date.today().day) < (created.month, created.day))
    lang_bytes = {}
    for r in nodes:
        for e in (r["languages"]["edges"] if r["languages"] else []):
            lang_bytes[e["node"]["name"]] = lang_bytes.get(e["node"]["name"], 0) + e["size"]
    cur, longest = streaks(days)

    os.makedirs(ASSETS, exist_ok=True)
    outputs = {
        "stats.svg": gen_stats(cal["totalContributions"], len(nodes), stars, forks, years),
        "streak.svg": gen_streak(cur, longest),
        "top-langs.svg": gen_top_langs(lang_bytes),
        "contribution-graph.svg": gen_heatmap(cal["weeks"]),
        "featured.svg": gen_featured(nodes),
    }
    for name, content in outputs.items():
        with open(os.path.join(ASSETS, name), "w") as f:
            f.write(content)
    print(f"OK: {cal['totalContributions']} contribs, {len(nodes)} repos, "
          f"{stars} stars, {forks} forks, {years} yrs, streak {cur}/{longest}, "
          f"langs={sorted(lang_bytes, key=lang_bytes.get, reverse=True)[:5]}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
