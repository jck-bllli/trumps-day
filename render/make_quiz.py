#!/usr/bin/env python3
"""'Did he say it?' Reel: each round shows two REAL quotes; one is Trump's from yesterday, the other is someone
else's (verified). Viewers guess A or B, then the reveal names who said each one.

  python3 render/make_quiz.py days/quiz_2026-10-27.json out.mp4
"""
import json
import math
import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_video as mv  # noqa: E402
from make_video import (BLUE, INK, RED, SR, SS, WHITE, YEL, W, H, FPS, clamp, ease_out, emoji, font,  # noqa: E402
                        paste, pop, shrink, sticker, text_sticker, wrap)

GREEN = (34, 197, 94)
CARD_W, CARD_H = 900, 250
CARD_Y = (845, 1135)
COUNT = 3.0


def card_layout(text):
    for size in range(64, 34, -2):
        f = font("NunitoBlack", size * SS)
        lines = wrap("“" + text + "”", f, (CARD_W - 190) * SS)
        if len(lines) * f.size * 1.16 / SS <= CARD_H - 50:
            return f, lines
    return f, lines


def el_card(letter, text, state="open", who=None):
    """state: open | right | wrong"""
    s = SS
    f, lines = card_layout(text)
    ring = {"open": INK, "right": GREEN, "wrong": INK}[state]
    im, d = sticker(CARD_W, CARD_H, WHITE, radius=40, ow=10 if state == "right" else 8, sh=12)
    if state == "right":
        d.rounded_rectangle((0, 0, CARD_W * s - 1, CARD_H * s - 1), 40 * s, outline=GREEN, width=14 * s)
    # letter badge
    bc = {"A": RED, "B": BLUE}[letter]
    d.ellipse((34 * s, (CARD_H / 2 - 52) * s, 138 * s, (CARD_H / 2 + 52) * s), fill=bc, outline=INK, width=7 * s)
    d.text((86 * s, CARD_H / 2 * s + 4 * s), letter, font=font("LilitaOne", 76 * s), fill=WHITE, anchor="mm")
    lh = f.size * 1.16
    y = (CARD_H * s - len(lines) * lh) / 2
    for line in lines:
        d.text((170 * s, y), " ".join(line), font=f, fill=INK)
        y += lh
    out = shrink(im)
    if state == "wrong":
        dim = Image.new("RGBA", out.size, (37, 99, 235, 0))
        a = out.getchannel("A").point(lambda v: int(v * 0.55))
        out.putalpha(a)
    return out


def el_who(text, good):
    f = font("NunitoBlack", 34)
    mark = emoji("✅" if good else "❌", 40)
    w = int(f.getlength(text)) + mark.width + 70
    im = Image.new("RGBA", (w, 66), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, 65), 33, fill=GREEN if good else (20, 30, 70), outline=INK, width=5)
    im.alpha_composite(mark, (20, (66 - mark.height) // 2))
    d.text((mark.width + 34, 33), text, font=f, fill=WHITE, anchor="lm")
    return im.rotate(-2, resample=Image.BICUBIC, expand=True)


def el_header(date_iso, k, n):
    im = Image.new("RGBA", (W, 420), (0, 0, 0, 0))
    a = text_sticker("DID HE SAY IT?", 112, RED, WHITE, angle=-3)
    b = text_sticker(f"ROUND {k}/{n}" if k else f"{n} ROUNDS", 64, YEL, INK, angle=2)
    im.alpha_composite(a, ((W - a.width) // 2 + 40, 0))
    im.alpha_composite(b, ((W - b.width) // 2 + 190, a.height - 34))
    cal = mv.el_calendar(date_iso)
    im.alpha_composite(cal, (28, a.height - 120))
    return im


def el_countdown(p):
    """Shrinking timer bar + prompt."""
    im = Image.new("RGBA", (W, 150), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0, x1 = 300, 1010
    d.rounded_rectangle((x0, 10, x1, 52), 21, fill=(20, 40, 120), outline=INK, width=5)
    xm = x0 + (x1 - x0) * (1 - p)
    if xm > x0 + 30:
        d.rounded_rectangle((x0 + 5, 15, xm - 5, 47), 16, fill=YEL)
    lab = text_sticker("COMMENT A OR B", 40, WHITE, INK, pad=26)
    im.alpha_composite(lab, ((x0 + x1) // 2 - lab.width // 2 - 20, 70))
    hand = emoji("\U0001F447", 52)
    im.alpha_composite(hand, ((x0 + x1) // 2 + lab.width // 2 - 10, 78))
    return im


def el_end(n):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    a = text_sticker("HOW MANY", 128, WHITE, INK, angle=-3)
    b = text_sticker(f"DID YOU GET? /{n}", 104, RED, WHITE, angle=2)
    c = text_sticker("FOLLOW FOR TOMORROW'S ROUND", 46, YEL, INK, pad=30)
    y = 560
    for el in (a, b):
        im.alpha_composite(el, ((W - el.width) // 2, y))
        y += el.height - 10
    hand = emoji("\U0001F447", 110)
    im.alpha_composite(hand, ((W - hand.width) // 2, y + 10))
    y += hand.height + 50
    im.alpha_composite(c, ((W - c.width) // 2, y))
    d = ImageDraw.Draw(im)
    d.text((W // 2, y + 120), "Every quote is real · Sources in the caption",
           font=font("NunitoBlack", 30), fill=WHITE, anchor="mm")
    return im


def main(data_path, out):
    import music
    import sfx
    data = json.load(open(data_path))
    rounds = data["rounds"]
    n = len(rounds)
    clips = []
    intro = mv.say(data.get("intro_say", f"Did he say it? {n} rounds. Let's go!"))
    clips.append((0.25, intro))
    t = 0.25 + len(intro) / SR + 0.3
    segs = []
    for k, r in enumerate(rounds):
        start = t
        q = mv.say(f"Round {['one', 'two', 'three', 'four', 'five'][k]}. Which one did Trump say?")
        clips.append((start + 0.25, q))
        c0 = start + 0.25 + len(q) / SR + 0.2
        reveal = c0 + COUNT
        right = r["answer"]
        wrong = "B" if right == "A" else "A"
        a1 = mv.say(r["reveal_say"])
        a2 = mv.say(r["other_say"])
        clips.append((reveal + 0.45, a1))
        t2 = reveal + 0.45 + len(a1) / SR + 0.15
        clips.append((t2, a2))
        end = t2 + len(a2) / SR + 0.6
        segs.append(dict(start=start, c0=c0, reveal=reveal, wrong_t=t2, end=end))
        t = end
    outro = mv.say(data.get("outro_say", "How many did you get? Comment your score, and follow for tomorrow's round!"))
    end_start = t
    clips.append((end_start + 0.3, outro))
    total = end_start + 0.3 + len(outro) / SR + 1.2

    n_s = int(SR * (total + 1))
    vo, fx = np.zeros(n_s), np.zeros(n_s)

    def add(buf, sig, at, g=1.0):
        s0 = int(SR * at)
        e = min(len(buf), s0 + len(sig))
        buf[s0:e] += sig[: e - s0] * g

    for at, c in clips:
        add(vo, c / (np.max(np.abs(c)) + 1e-9) * 0.9, at)
    for sg in segs:
        add(fx, mv.whoosh(), sg["start"])
        for i in range(3):
            add(fx, sfx.get("ding") * 0.35, sg["c0"] + i)
        add(fx, sfx.drumroll(COUNT - 0.15) * 0.6, sg["c0"] + 0.1)
        add(fx, sfx.get("cheer") * 1.1, sg["reveal"])
        add(fx, sfx.get("boing") * 1.2, sg["wrong_t"])
    add(fx, mv.whoosh(), end_start)
    m = music.make_loop(total + 1)[:n_s]
    m = np.pad(m, (0, n_s - len(m)))
    env = np.convolve(np.abs(vo), np.ones(5760) / 5760, mode="same")
    duck = np.convolve(np.where(env > 0.008, 0.3, 1.0), np.ones(4800) / 4800, mode="same")
    mix = (vo + fx * 0.55 + m * 0.18 * duck)[: int(SR * total)]
    mix = mix / np.max(np.abs(mix)) * 0.95
    td = tempfile.mkdtemp()
    wav = os.path.join(td, "a.wav")
    sf.write(wav, np.column_stack([mix, mix]).astype(np.float32), SR)

    bg, sp = mv.make_bg()
    headers = [el_header(data["date"], 0, n)] + [el_header(data["date"], k + 1, n) for k in range(n)]
    prompt = text_sticker("WHICH ONE DID TRUMP SAY YESTERDAY?", 50, WHITE, INK, angle=-1, pad=34)
    cards = []
    for r in rounds:
        right = r["answer"]
        c = {}
        for L in "AB":
            c[(L, "open")] = el_card(L, r[L]["quote"])
            c[(L, "final")] = el_card(L, r[L]["quote"], "right" if L == right else "wrong")
            c[(L, "who")] = el_who(r[L]["who"], L == right)
        cards.append(c)
    intro_el = mv.el_intro(n)
    intro_el = Image.new("RGBA", (W, 760), (0, 0, 0, 0))
    big = text_sticker(f"{n} ROUNDS", 190, WHITE, INK, angle=-4, h=260)
    sub = text_sticker("ONE QUOTE IS HIS. ONE ISN'T.", 54, YEL, INK, angle=3)
    sub2 = text_sticker("BOTH ARE REAL", 48, RED, WHITE, angle=-2, pad=30)
    intro_el.alpha_composite(big, ((W - big.width) // 2, 40))
    intro_el.alpha_composite(sub, ((W - sub.width) // 2, 40 + big.height - 20))
    intro_el.alpha_composite(sub2, ((W - sub2.width) // 2, 40 + big.height + sub.height - 10))
    end_el = el_end(n)
    cd_cache = {}

    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                             "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                             "-movflags", "+faststart", "-shortest", out], stdin=subprocess.PIPE)
    cover = None
    for fi in range(int(total * FPS)):
        t = fi / FPS
        off = int((t * 30) % sp)
        fr = bg.crop((off, off, off + W, off + H)).convert("RGBA")
        if t < end_start:
            if t < segs[0]["start"]:
                fr.alpha_composite(headers[0], (0, 240))
                sc, al = pop(t, 0.0, 0.45)
                paste(fr, intro_el, W / 2, 1020, sc, al)
            else:
                k = max(i for i, s in enumerate(segs) if s["start"] <= t)
                sg, c = segs[k], cards[k]
                fr.alpha_composite(headers[k + 1], (0, 240))
                lt = t - sg["start"]
                psc, pal = pop(lt, 0.0)
                paste(fr, prompt, W / 2, 690, psc, pal)
                revealed = t >= sg["reveal"]
                for j, L in enumerate("AB"):
                    sc, al = pop(lt, 0.12 + 0.12 * j, 0.42)
                    el = c[(L, "final" if revealed else "open")]
                    bump = 1.0
                    if revealed and L == rounds[k]["answer"]:
                        bump = 1 + 0.06 * math.sin(clamp((t - sg["reveal"]) / 0.3) * math.pi)
                    paste(fr, el, W / 2, CARD_Y[j] + CARD_H / 2, sc * bump, al)
                    show_who = (L == rounds[k]["answer"] and revealed) or (L != rounds[k]["answer"] and t >= sg["wrong_t"])
                    if show_who:
                        wsc, wal = pop(t, sg["reveal"] if L == rounds[k]["answer"] else sg["wrong_t"], 0.35)
                        paste(fr, c[(L, "who")], W / 2 + 150, CARD_Y[j] + CARD_H + 6, wsc, wal)
                if sg["c0"] <= t < sg["reveal"]:
                    p = (t - sg["c0"]) / COUNT
                    key = int(p * 60)
                    if key not in cd_cache:
                        cd_cache.clear()
                        cd_cache[key] = el_countdown(key / 60)
                    paste(fr, cd_cache[key], W / 2 + 30, 1515)
                fig = mv.el_figure(t)
                fig = fig.resize((int(fig.width * 0.6), int(fig.height * 0.6)), Image.LANCZOS)
                fr.alpha_composite(fig, (40, 1640 - fig.height))
                if k == 0 and cover is None and lt > 0.8:
                    cover = fr.copy()
        else:
            sc, al = pop(t - end_start, 0.0, 0.45)
            paste(fr, end_el, W / 2, H / 2, sc, al)
        proc.stdin.write(fr.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    if cover is not None:
        cover.convert("RGB").save(os.path.splitext(out)[0] + "_cover.jpg", quality=92)
    print("wrote", out, f"{total:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
