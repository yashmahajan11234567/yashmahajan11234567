#!/usr/bin/env python3
"""Fetch the real GitHub contribution calendar for a user via GraphQL.

Writes data/contribution-calendar.json with exact dates and contribution
counts. No invented data: if the API call fails, the script exits non-zero
and the previous dataset is kept (workflow uses continue-on-error).
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

USER = "yashmahajan11234567"
OUT_FILE = Path("data/contribution-calendar.json")

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            color
            weekday
          }
        }
      }
    }
  }
}
"""


def fetch(token: str) -> dict:
    to = datetime.now(timezone.utc)
    # 53 weeks back so the grid is a full year plus the current partial week
    frm = to - timedelta(days=364)
    payload = json.dumps({
        "query": QUERY,
        "variables": {
            "login": USER,
            "from": frm.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": to.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    }).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-graphics-bot",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    cal = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = []
    for w in cal["weeks"]:
        weeks.append({
            "days": [
                {
                    "date": d["date"],
                    "count": d["contributionCount"],
                    "color": d["color"],
                    "weekday": d["weekday"],
                }
                for d in w["contributionDays"]
            ]
        })
    return {
        "user": USER,
        "generatedAt": to.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"from": frm.strftime("%Y-%m-%d"), "to": to.strftime("%Y-%m-%d")},
        "totalContributions": cal["totalContributions"],
        "weeks": weeks,
    }


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GH_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    data = fetch(token)
    n_days = sum(len(w["days"]) for w in data["weeks"])
    n_weeks = len(data["weeks"])
    print(f"Fetched {n_weeks} weeks / {n_days} days, total={data['totalContributions']}")
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(data, separators=(",", ":")))
    print(f"Wrote {OUT_FILE}")


if __name__ == "__main__":
    main()