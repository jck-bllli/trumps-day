"""Fetch primary sources for one day on the home PC (open web) and save them as text under research/DATE/.

The cloud research task cannot reach most news and transcript sites, so this runs first on the PC.
Usage: python research/gather.py [DATE]   (default: yesterday, US Eastern)
Writes research/DATE/*.txt and research/DATE/_probe.txt (HTTP status of every source tried).
"""
import re, sys, os, html, urllib.request, urllib.error
from datetime import datetime, timedelta
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
MAXCHARS = 150_000


class T(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, a):
        if tag in ("script", "style", "nav", "footer", "svg"):
            self.skip += 1
        if tag in ("p", "br", "div", "li", "h1", "h2", "h3", "tr"):
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "svg") and self.skip:
            self.skip -= 1

    def handle_data(self, d):
        if not self.skip:
            self.out.append(d)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.status, r.read().decode("utf-8", "replace")


def text(raw):
    t = T()
    t.feed(raw)
    s = html.unescape("".join(t.out))
    return re.sub(r"\n\s*\n+", "\n\n", s).strip()[:MAXCHARS]


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else (datetime.now(ZoneInfo("America/New_York")) - timedelta(days=1)).strftime("%Y-%m-%d")
    y, m, d = date.split("-")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), date)
    os.makedirs(out, exist_ok=True)
    probe = []

    def save(name, url, body=None):
        try:
            code, raw = get(url) if body is None else (200, body)
            tx = text(raw)
            open(os.path.join(out, name), "w", encoding="utf-8").write(f"SOURCE: {url}\n\n{tx}\n")
            probe.append(f"{code} {len(tx):>7} chars  {url}")
            return raw
        except Exception as e:
            probe.append(f"FAIL {type(e).__name__} {e}  {url}")
            return ""

    # White House remarks and briefings: index pages, then every item linked for this month that mentions the day
    for idx, label in (("https://www.whitehouse.gov/remarks/", "wh_remarks"), ("https://www.whitehouse.gov/briefings-statements/", "wh_briefings")):
        raw = save(f"{label}_index.txt", idx)
        links = sorted(set(re.findall(r'href="(https://www\.whitehouse\.gov/[a-z\-]+/%s/%s/[^"#?]+)"' % (y, m), raw)))
        for i, u in enumerate(links[:40]):
            save(f"{label}_{i:02d}.txt", u)

    # Truth Social archive (front pages; the posts carry their own dates)
    raw = save("trumpstruth_front.txt", "https://trumpstruth.org/")
    ids = ["https://trumpstruth.org/statuses/" + i for i in dict.fromkeys(re.findall(r'/statuses/(\d+)', raw))]
    for i, u in enumerate(ids[:60]):
        save(f"trumpstruth_post_{i:02d}.txt", u)

    # Roll Call Factba.se and transcript sites (index pages; may need a search to find the item)
    for i, u in enumerate((
        "https://rollcall.com/factbase/trump/topic/calendar/",
        "https://rollcall.com/factbase/trump/search/?type=transcript",
        "https://www.rev.com/transcripts",
        "https://singjupost.com/",
        "https://www.c-span.org/person/?donaldtrump",
    )):
        save(f"transcripts_{i}.txt", u)

    open(os.path.join(out, "_probe.txt"), "w", encoding="utf-8").write(f"Gathered for {date}\n" + "\n".join(probe) + "\n")
    print("\n".join(probe))


main()
