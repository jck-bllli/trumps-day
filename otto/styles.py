#!/usr/bin/env python3
"""Otto, part 1: which of OUR styles gets the most attention.

Reads posted.json, looks up each post's style tag, pulls its Instagram insights,
and writes otto/report.md + otto/stats.json ranking styles.

Style tag lookup (first match wins):
  1. "style" on the posted.json entry
  2. "style" on the queue.json item with the same id
  3. "style" in days/<id>.json (trumps-day)
  otherwise "untagged"

Outlier score = a post's views / the account's median views (2.0 = twice normal).
Needs the secret IG_ACCESS_TOKEN (same one the posting workflow uses). Posts nothing.
"""
import json
import os
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://graph.instagram.com/v26.0"
TOKEN = os.environ.get("IG_ACCESS_TOKEN", "").strip()
METRICS = ["views", "reach", "likes", "comments", "shares", "saved", "total_interactions"]


def get(url, params):
    params = dict(params, access_token=TOKEN)
    try:
        with urllib.request.urlopen(f"{url}?{urllib.parse.urlencode(params)}", timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace").replace(TOKEN, "[token]")
        return {"error": body[:300]}


def insights(media_id):
    out = {}
    res = get(f"{API}/{media_id}/insights", {"metric": ",".join(METRICS)})
    if "error" in res:  # one bad metric fails the batch, so retry one at a time
        for m in METRICS:
            r = get(f"{API}/{media_id}/insights", {"metric": m})
            for d in r.get("data", []):
                out[d["name"]] = d["values"][0]["value"]
    else:
        for d in res.get("data", []):
            out[d["name"]] = d["values"][0]["value"]
    return out


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def style_of(entry, queue):
    if entry.get("style"):
        return entry["style"]
    for item in queue:
        if isinstance(item, dict) and item.get("id") == entry.get("id") and item.get("style"):
            return item["style"]
    day = load(f"days/{entry.get('id')}.json", {})
    if isinstance(day, dict) and day.get("style"):
        return day["style"]
    return "untagged"


def main():
    if not TOKEN:
        sys.exit("::error::IG_ACCESS_TOKEN is not set")
    posted = [p for p in load("posted.json", []) if p.get("media_id")]
    queue = load("queue.json", [])
    rows = []
    for p in posted:
        ins = insights(p["media_id"])
        rows.append({"id": p["id"], "style": style_of(p, queue), "permalink": p.get("permalink", ""),
                     "posted_at": p.get("posted_at", ""), **ins})
    if not rows:
        sys.exit("No posts with media ids yet.")

    views = [r.get("views", 0) for r in rows]
    med = statistics.median(views) or 1
    for r in rows:
        r["outlier"] = round(r.get("views", 0) / med, 2)
        r["eng_rate"] = round(r.get("total_interactions", 0) / max(r.get("reach", 0), 1), 4)

    styles = {}
    for r in rows:
        styles.setdefault(r["style"], []).append(r)
    summary = sorted(({
        "style": s, "posts": len(rs),
        "median_views": statistics.median(x.get("views", 0) for x in rs),
        "avg_outlier": round(statistics.mean(x["outlier"] for x in rs), 2),
        "median_eng_rate": statistics.median(x["eng_rate"] for x in rs),
        "shares": sum(x.get("shares", 0) for x in rs), "saves": sum(x.get("saved", 0) for x in rs),
    } for s, rs in styles.items()), key=lambda d: d["avg_outlier"], reverse=True)

    os.makedirs("otto", exist_ok=True)
    with open("otto/stats.json", "w") as f:
        json.dump({"median_views": med, "styles": summary, "posts": rows}, f, indent=1)

    lines = ["# Otto: styles ranked by attention", "",
             f"{len(rows)} posts, account median {med:g} views. Outlier = views / median.", "",
             "| Style | Posts | Median views | Avg outlier | Eng. rate | Shares | Saves |",
             "|---|---|---|---|---|---|---|"]
    for d in summary:
        lines.append(f"| {d['style']} | {d['posts']} | {d['median_views']:g} | {d['avg_outlier']}x"
                     f" | {d['median_eng_rate']:.1%} | {d['shares']} | {d['saves']} |")
    lines += ["", "## Top outlier posts", ""]
    for r in sorted(rows, key=lambda r: r["outlier"], reverse=True)[:5]:
        lines.append(f"- {r['outlier']}x, {r.get('views', 0)} views, style {r['style']}: {r['permalink']}")
    if len(rows) < 10 or any(d["posts"] < 3 for d in summary):
        lines += ["", "_Small sample: wait for 3+ posts per style before trusting the ranking._"]
    text = "\n".join(lines) + "\n"
    with open("otto/report.md", "w") as f:
        f.write(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(text)
    print(text)


if __name__ == "__main__":
    main()
