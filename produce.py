#!/usr/bin/env python3
"""Turn one day file into two voiced Reels (morning + evening, rotating styles) and queue them.

  python3 produce.py days/2026-10-27.json            # render, copy to videos/, add to queue.json
  python3 produce.py days/2026-10-27.json --dry-run  # render to /tmp only, touch nothing

Run render/setup.sh once per machine first.
"""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "render"))

SFX = {"cash", "gavel", "stamp", "cheer", "applause", "chime", "drumroll", "boing", "whoosh_up", "ding"}


def validate(day):
    errs = []
    try:
        dt.date.fromisoformat(day["date"])
    except Exception:
        errs.append("date must be YYYY-MM-DD")
    qs = day.get("quotes", [])
    if not 3 <= len(qs) <= 6:
        errs.append("need 3 to 6 quotes")
    for i, q in enumerate(qs, 1):
        for k in ("topic", "where", "quote", "intro_say", "sources"):
            if not q.get(k):
                errs.append(f"quote {i}: missing {k}")
        if len(q.get("quote", "")) > 190:
            errs.append(f"quote {i}: quote over 190 characters")
        if len(q.get("where", "")) > 40:
            errs.append(f"quote {i}: where over 40 characters")
        if q.get("highlight") and q["highlight"] not in q.get("quote", ""):
            errs.append(f"quote {i}: highlight must be an exact piece of the quote")
        g = q.get("game")
        if g:
            if g.get("type") not in ("topic", "blank", "number"):
                errs.append(f"quote {i}: game type must be topic, blank or number")
            opts = g.get("options", [])
            if len(opts) != 3 or not all(isinstance(o, str) and 0 < len(o) <= 28 for o in opts):
                errs.append(f"quote {i}: game needs exactly 3 options of at most 28 characters")
            if g.get("answer") not in (0, 1, 2):
                errs.append(f"quote {i}: game answer must be 0, 1 or 2")
            if g.get("type") in ("blank", "number"):
                b = g.get("blank", "")
                if not b or q.get("quote", "").count(b) != 1:
                    errs.append(f"quote {i}: blank must appear exactly once in the quote")
                elif opts and g.get("answer") in (0, 1, 2) and opts[g["answer"]] != b:
                    errs.append(f"quote {i}: the right option must equal the blank text")
    if not day.get("day_log", {}).get("speeches") and not day.get("day_log", {}).get("posts"):
        errs.append("day_log needs speeches and/or posts")
    if errs:
        sys.exit("Day file problems:\n  " + "\n  ".join(errs))


OK_LICENSES = ("public domain", "pd", "cc0", "cc by", "cc-by")


def fetch_photo(day, work):
    """Background photo for the 'photo' style, from Wikimedia Commons, license-checked.
    day["photo"] = {"file": "File:Name.jpg"} or {"query": "Mar-a-Lago aerial", "match": "Mar-a-Lago"}.
    Returns (path, credit) or (None, None); the renderer falls back to a plain navy background."""
    import html
    import urllib.parse
    import urllib.request
    ph = day.get("photo") or {}
    if not ph:
        return None, None
    api = "https://commons.wikimedia.org/w/api.php?"
    ua = {"User-Agent": "trumpsday-render/1.0 (https://github.com/jck-bllli/trumps-day)"}

    def get(params):
        req = urllib.request.Request(api + urllib.parse.urlencode(dict(params, format="json")), headers=ua)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())

    base = dict(action="query", prop="imageinfo", iiprop="url|extmetadata", iiurlwidth=1600)
    try:
        if ph.get("file"):
            pages = get(dict(base, titles=ph["file"]))["query"]["pages"].values()
        else:
            pages = get(dict(base, generator="search", gsrsearch=ph["query"], gsrnamespace=6, gsrlimit=10)
                        ).get("query", {}).get("pages", {}).values()
            pages = sorted(pages, key=lambda p: p.get("index", 99))
        for pg in pages:
            info = (pg.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata", {})
            lic = meta.get("LicenseShortName", {}).get("value", "")
            title = pg.get("title", "")
            if not lic.lower().startswith(OK_LICENSES) or not title.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            if ph.get("match") and ph["match"].lower() not in (title + meta.get("ImageDescription", {}).get("value", "")).lower():
                continue
            url = info.get("thumburl") or info.get("url")
            path = os.path.join(work, "photo" + os.path.splitext(url)[1][:5])
            with urllib.request.urlopen(urllib.request.Request(url, headers=ua), timeout=60) as r:
                open(path, "wb").write(r.read())
            artist = re.sub("<[^>]+>", "", html.unescape(meta.get("Artist", {}).get("value", ""))).strip()
            credit = f"{artist or 'Wikimedia Commons'}, {lic}, via Wikimedia Commons"
            print(f"Photo: {title} ({lic})")
            return path, credit
        print("No photo with an allowed license matched; using the plain background.")
    except Exception as e:
        print(f"Photo fetch failed ({e}); using the plain background.")
    return None, None


def split(day):
    """Morning post gets the first half of the quotes, evening post the rest (3 or fewer quotes: morning only)."""
    qs = day["quotes"]
    if len(qs) <= 3:
        return [("am", qs)]
    h = (len(qs) + 1) // 2
    return [("am", qs[:h]), ("pm", qs[h:])]


def check_audio(video):
    """Stop before queueing a Reel that would post without sound."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-map", "0:a:0", "-af", "volumedetect",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"mean_volume: (-?[\d.]+) dB", r.stderr)
    if not m:
        sys.exit(f"{video} has no audio track, so it would post silent. Not queueing it.")
    if float(m.group(1)) < -40:
        sys.exit(f"{video} audio is near silent ({m.group(1)} dB mean), so it would post silent. Not queueing it.")
    print(f"Audio check passed ({m.group(1)} dB mean)")


def main():
    path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    day = json.load(open(path, encoding="utf-8"))
    validate(day)
    import make_styled

    d = dt.date.fromisoformat(day["date"])
    work = tempfile.mkdtemp(prefix="trumpsday_")
    qpath = os.path.join(ROOT, "queue.json")
    queue = json.load(open(qpath, encoding="utf-8")) if os.path.exists(qpath) else []
    styles, voices = {}, {}
    photo_path, photo_credit = None, None
    jobs = [(slot, qs, make_styled.pick_style(day["date"], slot)) for slot, qs in split(day)]
    if dry and "--all-styles" in sys.argv:  # test renders: every style once, alternating halves
        halves = split(day)
        jobs = [(halves[i % len(halves)][0], halves[i % len(halves)][1], st) for i, st in enumerate(make_styled.STYLES)]
    for slot, qs, style in jobs:
        pid = f"{day['date']}-{slot}-{style}" if dry else f"{day['date']}-{slot}"
        styles[slot] = style
        from chatterbox_voice import voice_for
        voice = voice_for(d.toordinal() * 2 + (slot == "pm"))  # both posts of a day share a voice, next day swaps
        voices[slot] = voice
        post = dict(date=day["date"], slot=slot, style=style, voice=voice, quotes=qs, day_log=day.get("day_log", {}))
        if style == "photo":
            if photo_path is None:
                photo_path, photo_credit = fetch_photo(day, work)
            post.update(photo_path=photo_path, photo_credit=photo_credit)
        ppath = os.path.join(work, f"{pid}.json")
        json.dump(post, open(ppath, "w", encoding="utf-8"), ensure_ascii=False)
        out = os.path.join(work, f"{pid}.mp4")
        make_styled.main(ppath, out)
        check_audio(out)
        caption = open(os.path.splitext(out)[0] + "_caption.txt", encoding="utf-8").read()
        if dry:
            print(f"Dry run done: {out}  ({style})\n\n{caption}\n")
            continue
        os.makedirs(os.path.join(ROOT, "videos"), exist_ok=True)
        vid, cover = f"videos/{pid}.mp4", f"videos/{pid}_cover.jpg"
        shutil.copy(out, os.path.join(ROOT, vid))
        if os.path.exists(os.path.splitext(out)[0] + "_cover.jpg"):
            shutil.copy(os.path.splitext(out)[0] + "_cover.jpg", os.path.join(ROOT, cover))
        # morning post goes out as soon as it is rendered; evening post after 00:15 UTC the next day
        # (4:15pm Pacific standard time on the day the morning post went out)
        after = None if slot == "am" else f"{d + dt.timedelta(days=2)}T00:15:00Z"
        queue = [q for q in queue if q["id"] != pid]
        queue.append({"id": pid, "video": vid, "cover": cover, "caption": caption, "style": style, "voice": voice,
                      "post_after": after, "thumb_offset_ms": 3000})
    if dry:
        return
    queue.sort(key=lambda q: q["id"])
    json.dump(queue, open(qpath, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    # tag the day file with each post's style (the Otto comparison reads "style"; "styles" has both slots)
    day["styles"] = styles
    day["style"] = styles["am"]
    day["voices"] = voices
    json.dump(day, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("Queued", ", ".join(f"{day['date']}-{s} ({st})" for s, st in styles.items()))


if __name__ == "__main__":
    main()
