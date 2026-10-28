#!/usr/bin/env python3
"""Build the link-in-bio "receipts" page (docs/index.html, served by GitHub Pages).

For each day in days/: the quotes with their sources, every speech (transcript + video), and every
Truth Social post from that day (Eastern time). Posts are fetched here, on GitHub Actions, and saved
to data/posts/<date>.json so each day only needs fetching once.

  python3 build_page.py            # fetch posts for recent days that still need them, then build the page
  python3 build_page.py --no-fetch # build from saved data only
"""
import datetime as dt
import glob
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.abspath(__file__))
ET_TZ = ZoneInfo("America/New_York")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36",
      "Accept": "application/json, application/rss+xml, text/xml, */*"}
TS_ACCOUNT = "107780257626128497"  # @realDonaldTrump on Truth Social
ARCHIVE = "https://www.trumpstruth.org"


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return r.read()


def strip_html(s):
    s = re.sub(r"<br\s*/?>|</p>", "\n", s or "")
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def day_window(date_iso):
    d = dt.date.fromisoformat(date_iso)
    start = dt.datetime(d.year, d.month, d.day, tzinfo=ET_TZ)
    return start, start + dt.timedelta(days=1)


def from_truthsocial(date_iso):
    """Truth Social's public API, paged back until we pass the start of the day. Complete when it works."""
    start, end = day_window(date_iso)
    out, max_id = [], None
    for _ in range(30):
        q = {"exclude_replies": "true", "limit": "40"}
        if max_id:
            q["max_id"] = max_id
        page = json.loads(get(f"https://truthsocial.com/api/v1/accounts/{TS_ACCOUNT}/statuses?"
                              + urllib.parse.urlencode(q)))
        if not page:
            return out, True
        for st in page:
            t = dt.datetime.fromisoformat(st["created_at"].replace("Z", "+00:00"))
            if start <= t < end:
                rb = st.get("reblog")
                text = strip_html(st.get("content"))
                kind = "repost" if rb else ("video" if any(m.get("type") == "video" for m in st.get("media_attachments", []))
                                            else "image" if st.get("media_attachments") else "text")
                if rb and not text:
                    text = "ReTruth: " + strip_html(rb.get("content"))[:200]
                out.append({"time": t.isoformat(), "text": text, "kind": kind,
                            "url": st.get("url") or f"https://truthsocial.com/@realDonaldTrump/{st['id']}"})
            if t < start:
                return out, True
        max_id = page[-1]["id"]
    return out, False


def from_archive_feed(date_iso):
    """trumpstruth.org RSS feed. Only holds recent posts, so it may not reach back to the start of the day."""
    start, end = day_window(date_iso)
    root = ET.fromstring(get(f"{ARCHIVE}/feed"))
    out, oldest = [], None
    for it in root.iter("item"):
        fields = {c.tag.split("}")[-1]: (c.text or "") for c in it}
        try:
            t = parsedate_to_datetime(fields.get("pubDate", ""))
        except Exception:
            continue
        oldest = t if oldest is None or t < oldest else oldest
        if not start <= t < end:
            continue
        orig = next((v for v in fields.values() if "truthsocial.com" in v and v.strip().startswith("http")), "")
        text = strip_html(fields.get("description") or fields.get("title"))
        out.append({"time": t.isoformat(), "text": text, "kind": "text" if text else "media",
                    "url": orig.strip() or fields.get("link", ""), "archive": fields.get("link", "")})
    return out, oldest is not None and oldest < start


def fetch_posts(date_iso):
    errors = []
    for name, fn in (("Truth Social", from_truthsocial), ("trumpstruth.org feed", from_archive_feed)):
        try:
            posts, complete = fn(date_iso)
            if posts or complete:
                posts.sort(key=lambda p: p["time"])
                return {"source": name, "complete": complete, "posts": posts,
                        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
            errors.append(f"{name}: no posts found")
        except Exception as e:
            errors.append(f"{name}: {e}")
    print("Could not fetch posts for", date_iso, "|", "; ".join(errors))
    return None


def link(u, label):
    if not u:
        return ""
    u = u if u.startswith("http") else "https://" + u
    return f'<a href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(label)}</a>'


def nice_topic(t):
    small = {"of", "the", "and", "a", "an", "in", "on", "to", "for", "at", "by", "with"}
    w = t.lower().split()
    return " ".join(x if (i and x in small) else x[:1].upper() + x[1:] for i, x in enumerate(w))


def fmt_time(iso):
    return dt.datetime.fromisoformat(iso).astimezone(ET_TZ).strftime("%-I:%M %p")


def day_html(day, posts, open_):
    d = dt.date.fromisoformat(day["date"])
    parts = [f'<details class="day"{" open" if open_ else ""}><summary><span class="date">{d.strftime("%A, %B %-d, %Y")}</span>'
             f'<span class="count">{len(day["quotes"])} quotes</span></summary>', '<h3>The quotes</h3><ol class="quotes">']
    for q in day["quotes"]:
        srcs = " · ".join(link(s, f"source {i + 1}") for i, s in enumerate(q.get("sources", [])))
        again = f'<span class="tag">said before{": " + html.escape(q["said_before_note"]) if q.get("said_before_note") else ""}</span>' if q.get("said_before") else ""
        parts.append(f'<li><p class="q">“{html.escape(q["quote"])}”</p><p class="meta">{html.escape(nice_topic(q["topic"]))} · '
                     f'{html.escape(q["where"])} {again}<br>{srcs}</p></li>')
    parts.append("</ol>")
    sp = day.get("day_log", {}).get("speeches", [])
    if sp:
        parts.append('<h3>Speeches and remarks</h3><ul class="links">')
        for s in sp:
            ls = " · ".join(x for x in (link(s.get("transcript"), "transcript"), link(s.get("video"), "video")) if x)
            parts.append(f"<li><b>{html.escape(s['title'])}</b><br>{ls}</li>")
        parts.append("</ul>")
    start, end = day_window(day["date"])
    archive = f"{ARCHIVE}/?start_date={day['date']}&end_date={day['date']}"
    if posts and posts.get("posts"):
        note = "" if posts.get("complete") else " (may be missing some; see the full archive)"
        parts.append(f'<h3>Truth Social posts ({len(posts["posts"])}){note}</h3><ul class="posts">')
        for p in posts["posts"]:
            text = p["text"] or f"({p['kind']} post)"
            text = text if len(text) <= 280 else text[:277].rsplit(" ", 1)[0] + "…"
            parts.append(f'<li><span class="time">{fmt_time(p["time"])}</span> {html.escape(text)} '
                         f'{link(p["url"], "open")}</li>')
        parts.append("</ul>")
    else:
        parts.append("<h3>Truth Social posts</h3>")
    parts.append(f'<p class="more">{link(archive, "Every post from this day in the trumpstruth.org archive")}</p></details>')
    return "\n".join(parts)


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trump's Day: Receipts</title>
<meta name="description" content="Every quote, speech transcript and Truth Social post behind each daily recap.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lilita+One&family=Nunito:wght@600;800;900&display=swap" rel="stylesheet">
<style>
:root{--blue:#2563eb;--ink:#121420;--red:#ef3340;--yel:#ffcd29;--card:#fff;--muted:#5a6070;--line:#e4e7ee}
*{box-sizing:border-box}body{margin:0;background:var(--blue);color:var(--ink);font:600 16px/1.5 Nunito,system-ui,sans-serif}
.wrap{max-width:720px;margin:0 auto;padding:24px 16px 60px}
header{text-align:center;color:#fff;margin-bottom:20px}
h1{font:400 44px/1.05 'Lilita One',sans-serif;margin:8px 0;display:inline-block;background:var(--red);padding:6px 18px;border:4px solid var(--ink);border-radius:16px;box-shadow:6px 6px 0 var(--ink);transform:rotate(-2deg)}
.sub{font-weight:800;margin:14px 0 0}
.day{background:var(--card);border:4px solid var(--ink);border-radius:18px;box-shadow:6px 6px 0 var(--ink);margin:18px 0;padding:0 18px}
summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;padding:16px 0;gap:12px}
summary::-webkit-details-marker{display:none}
.date{font:400 24px/1.1 'Lilita One',sans-serif}.count{background:var(--yel);border:3px solid var(--ink);border-radius:999px;padding:2px 12px;font-weight:900;font-size:14px;white-space:nowrap}
h3{font:400 20px 'Lilita One',sans-serif;margin:18px 0 8px;border-top:2px dashed var(--line);padding-top:14px}
ol,ul{padding-left:22px;margin:0}li{margin:0 0 12px}
.q{font-weight:900;font-size:18px;margin:0}.meta{color:var(--muted);margin:2px 0 0;font-size:14px}
.tag{background:var(--red);color:#fff;border-radius:6px;padding:1px 7px;font-weight:900;font-size:12px;text-transform:uppercase}
.posts li{font-size:15px;overflow-wrap:anywhere}.time{font-weight:900;color:var(--blue);white-space:nowrap}
a{color:var(--blue);font-weight:900}.more{margin:4px 0 18px}
footer{color:#fff;text-align:center;font-size:13px;opacity:.9;margin-top:28px}
</style></head><body><div class="wrap">
<header><h1>TRUMP'S DAY: RECEIPTS</h1><p class="sub">Every quote from the daily video, with its source, plus every speech and post from that day.</p></header>
{days}
<footer>Quotes are word for word. Unofficial recap, not affiliated with Donald Trump or the White House.<br>Post text links to the original on Truth Social. Updated {updated}.</footer>
</div></body></html>
"""


def main():
    fetch = "--no-fetch" not in sys.argv
    os.makedirs(os.path.join(ROOT, "data", "posts"), exist_ok=True)
    days = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(ROOT, "days", "*.json")), reverse=True)]
    today = dt.datetime.now(ET_TZ).date()
    blocks = []
    for i, day in enumerate(days):
        pp = os.path.join(ROOT, "data", "posts", f"{day['date']}.json")
        posts = json.load(open(pp)) if os.path.exists(pp) else None
        recent = (today - dt.date.fromisoformat(day["date"])).days <= 3
        if fetch and recent and not (posts and posts.get("complete")):
            got = fetch_posts(day["date"])
            if got and (not posts or len(got["posts"]) >= len(posts.get("posts", []))):
                posts = got
                json.dump(posts, open(pp, "w"), indent=2, ensure_ascii=False)
                print(f"{day['date']}: {len(posts['posts'])} posts from {posts['source']} (complete={posts['complete']})")
        blocks.append(day_html(day, posts, i == 0))
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    page = PAGE.replace("{days}", "\n".join(blocks)).replace(
        "{updated}", dt.datetime.now(ET_TZ).strftime("%B %-d, %Y %-I:%M %p ET"))
    open(os.path.join(ROOT, "docs", "index.html"), "w").write(page)
    open(os.path.join(ROOT, "docs", ".nojekyll"), "w").close()
    print("built docs/index.html with", len(days), "days")


if __name__ == "__main__":
    main()
