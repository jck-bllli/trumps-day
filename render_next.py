#!/usr/bin/env python3
"""Render the newest day file if it is not in queue.json yet. Used by the home PC and the cloud fallback.

  python render_next.py    # prints what it rendered, or that nothing was waiting

Writes rendered=DATE to $GITHUB_OUTPUT when it renders something.
"""
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    days = sorted(glob.glob(os.path.join(ROOT, "days", "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json")))
    if not days:
        print("No day files.")
        return
    newest = days[-1]
    date = os.path.splitext(os.path.basename(newest))[0]
    queued = {q["id"] for q in json.load(open(os.path.join(ROOT, "queue.json"), encoding="utf-8"))}
    if date in queued:
        print(f"{date} is already rendered and queued. Nothing to do.")
        return
    subprocess.run([sys.executable, os.path.join(ROOT, "produce.py"), newest], check=True, cwd=ROOT)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"rendered={date}\n")


if __name__ == "__main__":
    main()
