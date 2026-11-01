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
    styles = {}
    for slot, qs in split(day):
        pid = f"{day['date']}-{slot}"
        style = make_styled.pick_style(day["date"], slot)
        styles[slot] = style
        post = dict(date=day["date"], slot=slot, style=style, quotes=qs, day_log=day.get("day_log", {}))
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
        queue.append({"id": pid, "video": vid, "cover": cover, "caption": caption, "style": style,
                      "post_after": after, "thumb_offset_ms": 3000})
    if dry:
        return
    queue.sort(key=lambda q: q["id"])
    json.dump(queue, open(qpath, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    # tag the day file with each post's style (the Otto comparison reads "style"; "styles" has both slots)
    day["styles"] = styles
    day["style"] = styles["am"]
    json.dump(day, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("Queued", ", ".join(f"{day['date']}-{s} ({st})" for s, st in styles.items()))


if __name__ == "__main__":
    main()
