#!/usr/bin/env python3
"""Turn one day file into a voiced Reel and queue it for posting.

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
    if not 3 <= len(qs) <= 5:
        errs.append("need 3 to 5 quotes")
    for i, q in enumerate(qs, 1):
        for k in ("topic", "emoji", "where", "quote", "intro_say", "sfx", "sources"):
            if not q.get(k):
                errs.append(f"quote {i}: missing {k}")
        if q.get("sfx") and q["sfx"] not in SFX:
            errs.append(f"quote {i}: sfx must be one of {sorted(SFX)}")
        if len(q.get("topic", "")) > 26:
            errs.append(f"quote {i}: topic over 26 characters")
        if len(q.get("quote", "")) > 190:
            errs.append(f"quote {i}: quote over 190 characters (too long for the bubble)")
        if len(q.get("where", "")) > 40:
            errs.append(f"quote {i}: where over 40 characters")
    if not day.get("day_log", {}).get("speeches") and not day.get("day_log", {}).get("posts"):
        errs.append("day_log needs speeches and/or posts")
    if errs:
        sys.exit("Day file problems:\n  " + "\n  ".join(errs))


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
    day = json.load(open(path))
    validate(day)
    import make_video

    work = tempfile.mkdtemp(prefix="trumpsday_")
    out = os.path.join(work, f"{day['date']}.mp4")
    make_video.main(path, out)
    check_audio(out)
    caption = open(os.path.splitext(out)[0] + "_caption.txt").read()
    if dry:
        print(f"Dry run done: {out}\n\n{caption}")
        return
    os.makedirs(os.path.join(ROOT, "videos"), exist_ok=True)
    vid = f"videos/{day['date']}.mp4"
    cover = f"videos/{day['date']}_cover.jpg"
    shutil.copy(out, os.path.join(ROOT, vid))
    if os.path.exists(os.path.splitext(out)[0] + "_cover.jpg"):
        shutil.copy(os.path.splitext(out)[0] + "_cover.jpg", os.path.join(ROOT, cover))
    qpath = os.path.join(ROOT, "queue.json")
    queue = json.load(open(qpath)) if os.path.exists(qpath) else []
    queue = [q for q in queue if q["id"] != day["date"]]
    queue.append({"id": day["date"], "video": vid, "cover": cover, "caption": caption, "thumb_offset_ms": 6000})
    queue.sort(key=lambda q: q["id"])
    json.dump(queue, open(qpath, "w"), indent=2, ensure_ascii=False)
    print(f"Queued {day['date']} ({len(caption)} caption chars)")


if __name__ == "__main__":
    main()
