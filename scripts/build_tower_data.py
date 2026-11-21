#!/usr/bin/env python3
"""Build data/activity-tower.json — real GitHub activity data for the 3D Activity Tower.

Data source: GitHub REST API, public repos of the repo owner only.
- Paginates repos, branches and commits.
- total_commits per branch comes from the Link header of a per_page=1 probe
  (exact count), never inferred from the fetched page size.
- Repo colors are a deterministic hash of the repo name (stable across runs).
- Writes the file only when content changed. Exits non-zero on API failure so
  the caller (GitHub Actions) can keep the previous dataset (continue-on-error).

Env: GH_TOKEN or GITHUB_TOKEN (required). TOWER_COMMITS_PER_BRANCH (default 10).
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

OWNER = os.environ.get("TOWER_OWNER", "yashmahajan11234567")
OUT = os.environ.get("TOWER_OUT", "data/activity-tower.json")
PER_BRANCH = int(os.environ.get("TOWER_COMMITS_PER_BRANCH", "10"))
API = "https://api.github.com"


def token():
    t = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not t:
        sys.exit("GH_TOKEN/GITHUB_TOKEN not set")
    return t


def req(path, tok, want_headers=False):
    r = urllib.request.Request(API + path, headers={
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "activity-tower-bot",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    for attempt in range(4):
        try:
            with urllib.request.urlopen(r, timeout=30) as resp:
                body = resp.read()
                return (json.loads(body), resp.headers) if want_headers else json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < 3:  # rate limit / abuse
                time.sleep(10 * (attempt + 1))
                continue
            raise RuntimeError(f"API {e.code} for {path}: {e.read()[:200]!r}")


def paged(path, tok):
    """Yield all items across ?per_page=100 pages."""
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        data = req(f"{path}{sep}per_page=100&page={page}", tok)
        if not data:
            return
        yield from data
        if len(data) < 100:
            return
        page += 1


def branch_total_commits(owner, repo, branch, tok):
    """Exact commit count from the Link header of a per_page=1 request."""
    _, headers = req(
        f"/repos/{owner}/{repo}/commits?sha={urllib.parse.quote(branch)}&per_page=1",
        tok, want_headers=True)
    link = headers.get("Link", "")
    for part in link.split(","):
        if 'rel="last"' in part:
            import re
            m = re.search(r"[?&]page=(\d+)", part)
            if m:
                return int(m.group(1))
    return 1  # single page => at most 1 commit... caller fixes with len()


def repo_color(name):
    h = int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)
    hue = h % 360
    # hsl -> hex
    import colorsys
    r, g, b = colorsys.hls_to_rgb(hue / 360, 0.55, 0.75)
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def main():
    tok = token()
    repos = [r for r in paged(f"/users/{OWNER}/repos?type=owner&sort=updated", tok)
             if not r.get("private")]
    out_repos = []
    total_branches = 0
    total_displayed = 0
    for r in sorted(repos, key=lambda x: x["name"].lower()):
        name = r["name"]
        branches = list(paged(f"/repos/{OWNER}/{name}/branches", tok))
        # default branch first, then alphabetical — stable ordering
        branches.sort(key=lambda b: (b.get("name") != r.get("default_branch"), b["name"]))
        out_branches = []
        for b in branches:
            bname = b["name"]
            total = branch_total_commits(OWNER, name, bname, tok)
            commits = req(
                f"/repos/{OWNER}/{name}/commits?sha={urllib.parse.quote(bname)}"
                f"&per_page={PER_BRANCH}", tok)[:PER_BRANCH]
            if len(commits) == 1 and total == 1:
                pass
            out_commits = [{
                "sha": c["sha"][:7],
                "message": c["commit"]["message"].splitlines()[0][:120],
                "date": c["commit"]["author"]["date"],
                "url": c["html_url"],
            } for c in commits]
            total_displayed += len(out_commits)
            total_branches += 1
            out_branches.append({
                "name": bname,
                "url": f"https://github.com/{OWNER}/{name}/tree/{urllib.parse.quote(bname)}",
                "total_commits": total,
                "commits_displayed": len(out_commits),
                "commits": out_commits,
            })
        out_repos.append({
            "name": name,
            "url": r["html_url"],
            "description": r.get("description") or "",
            "is_fork": r.get("fork", False),
            "color": repo_color(name),
            "branches": out_branches,
        })
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user": OWNER,
        "commits_per_branch_limit": PER_BRANCH,
        "totals": {
            "repositories": len(out_repos),
            "branches": total_branches,
            "commits_displayed": total_displayed,
        },
        "repositories": out_repos,
    }
    blob = json.dumps(data, indent=1) + "\n"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT) and open(OUT).read() == blob:
        print("unchanged — not rewriting")
        return
    with open(OUT, "w") as f:
        f.write(blob)
    print(f"wrote {OUT}: {len(out_repos)} repos, {total_branches} branches, "
          f"{total_displayed} commits displayed")


if __name__ == "__main__":
    main()
