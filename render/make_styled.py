#!/usr/bin/env python3
"""Twice-daily Trump post: 3 quotes in one of 3 rotating styles, each quote optionally a mini-game.

  python3 render/make_styled.py post.json out.mp4

post.json = {"date", "slot": "am"|"pm", "style": "transcript"|"tabloid"|"poll", "quotes": [...], "day_log": {...}}
Each quote: topic, where, quote, quote_say?, intro_say, sources, highlight? (a phrase of the quote to mark),
game? = {"type": "topic"|"blank"|"number", "options": [3 strings], "answer": 0-2, "blank": "words hidden"}.
Writes out.mp4, out_cover.jpg and out_caption.txt. Narrator voice only (never an imitation of Trump).
"""
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_video import say  # same narrator voice as the daily recap

W, H, FPS, SR = 1080, 1920, 30, 48000
FD = os.path.join(HERE, "fonts")
STYLES = ("transcript", "tabloid", "poll")
_f = {}


def font(name, size):
    if (name, size) not in _f:
        _f[(name, size)] = ImageFont.truetype(os.path.join(FD, name), size)
    return _f[(name, size)]


PLAY, PLAYI, FRANK = "Playfair900.woff", "Playfair700i.woff", "Franklin800.woff"
MONO, INTER = "JetBrainsMono-Bold.ttf", "InterDisplay-Black.otf"
RED = (226, 54, 46)

SKIN = {
    "transcript": dict(bg=(14, 14, 16), ink=(245, 238, 225), dim=(150, 150, 150), accent=RED,
                       qfont=PLAY, qsize=88, upper=False, align="left", grain=0.08,
                       cta="Fair point or too far?", opt_fill=None, opt_ink=(245, 238, 225)),
    "tabloid": dict(bg=(236, 230, 214), ink=(15, 15, 15), dim=(70, 70, 70), accent=(200, 20, 30),
                    qfont=FRANK, qsize=104, upper=True, align="left", grain=0.10,
                    cta="Agree or disagree?", opt_fill=(15, 15, 15), opt_ink=(236, 230, 214)),
    "poll": dict(bg=None, ink=(15, 15, 15), dim=(110, 110, 110), accent=(15, 15, 15),
                 qfont=PLAY, qsize=76, upper=False, align="center", grain=0.05,
                 cta="Fair or too far?", opt_fill=(250, 248, 242), opt_ink=(15, 15, 15)),
}
GAME_TITLE = {"topic": "WHAT WAS HE TALKING ABOUT?", "blank": "FINISH THE QUOTE", "number": "GUESS THE NUMBER"}


def pick_style(date, slot):
    n = dt.date.fromisoformat(date).toordinal() * 2 + (slot == "pm")
    return STYLES[n % 3]


# ---------------- quote tokens (typing, highlight, blank) ----------------
BLANK = "\x00"


def tokens(q):
    """List of (word, is_highlight, is_blank). The blank token's word is the hidden text (+ trailing punctuation)."""
    text = "“" + q["quote"] + "”"
    game = q.get("game") or {}
    hl = q.get("highlight") or ""
    out = []
    if game.get("type") in ("blank", "number"):
        b = game["blank"]
        i = text.index(b)
        before, after = text[:i], text[i + len(b):]
        tail = after.split(" ", 1)
        out = [(w, False, False) for w in before.split()]
        out.append((b + tail[0], False, True))
        if len(tail) > 1:
            out += [(w, False, False) for w in tail[1].split()]
        return out
    words = text.split()
    if hl and hl in q["quote"]:
        start = len(q["quote"][:q["quote"].index(hl)].split()) if q["quote"].index(hl) else 0
        n = len(hl.split())
        return [(w, start <= k < start + n, False) for k, w in enumerate(words)]
    return [(w, False, False) for w in words]


def layout(toks, f, maxw, upper):
    lines, cur, cw = [], [], 0
    space = f.getlength(" ")
    for k, (w, hl, bl) in enumerate(toks):
        shown = w.upper() if upper else w
        ww = f.getlength(shown)
        if cur and cw + space + ww > maxw:
            lines.append(cur)
            cur, cw = [], 0
        cur.append((k, shown, ww))
        cw += (space if len(cur) > 1 else 0) + ww
    lines.append(cur)
    return lines


# ---------------- backgrounds ----------------
def make_bg(style):
    if style == "poll":
        im = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W // 2, H), fill=(28, 64, 170))
        d.rectangle((W // 2, 0, W, H), fill=(190, 30, 45))
        return im
    im = Image.new("RGB", (W, H), SKIN[style]["bg"])
    if style == "tabloid":
        d = ImageDraw.Draw(im)
        for yy in range(1380, H, 14):
            for xx in range((yy // 14 % 2) * 7, W, 14):
                d.ellipse((xx, yy, xx + 4, yy + 4), fill=(205, 197, 180))
    return im


def grains(n=4):
    return [Image.effect_noise((W, H), 40 + 10 * i).convert("RGB") for i in range(n)]


# ---------------- frame drawing ----------------
def draw_frame(style, bg, grain, st):
    """st: kicker, title, toks, lines, f, shown (words visible), reveal, options, answer, timer (0..1 or None),
    attribution, cta (str or None), opt_t (time since options appeared)."""
    sk = SKIN[style]
    im = bg.copy()
    d = ImageDraw.Draw(im)
    ink, dim, acc = sk["ink"], sk["dim"], sk["accent"]
    # header
    if style == "transcript":
        d.text((80, 150), st["kicker"], font=font(MONO, 34), fill=dim)
        d.text((80, 205), st["title"] or "WORD FOR WORD", font=font(MONO, 34), fill=acc)
        qtop = 420
    elif style == "tabloid":
        d.rectangle((0, 110, W, 250), fill=acc)
        t = st["title"] or "HE SAID IT"
        tf = font(FRANK, 120 if len(t) < 12 else 64)
        d.text((W // 2, 180), t, font=tf, fill="white", anchor="mm")
        d.text((60, 290), st["kicker"], font=font(MONO, 26), fill=(60, 60, 60))
        d.line((60, 340, W - 60, 340), fill=(20, 20, 20), width=6)
        qtop = 390
    else:
        t = st["title"] or "YOU DECIDE"
        d.text((W // 2, 170), t, font=font(INTER, 96 if len(t) < 14 else 58), fill="white", anchor="mm")
        d.text((W // 2, 270), st["kicker"], font=font(MONO, 30), fill=(235, 235, 235), anchor="mm")
    f, lines, toks = st["f"], st["lines"], st["toks"]
    lh = int(f.size * 1.28)
    if style == "poll":
        card_h = len(lines) * lh + 150
        d.rounded_rectangle((60, 360, W - 60, 360 + card_h), 28, fill=(250, 248, 242))
        qtop = 420
    y = qtop
    space = f.getlength(" ")
    for line in lines:
        lw = sum(w for _, _, w in line) + space * (len(line) - 1)
        x = (W - lw) / 2 if sk["align"] == "center" else (80 if style == "transcript" else 60)
        for k, shown, ww in line:
            if k >= st["shown"]:
                break
            _, hl, bl = toks[k]
            if bl and not st["reveal"]:
                bw = max(ww, f.getlength("______"))
                d.line((x, y + f.size * 1.05, x + bw, y + f.size * 1.05), fill=ink, width=8)
                x += bw + space
                continue
            if hl or (bl and st["reveal"]):
                bb = d.textbbox((x, y), shown, font=f)
                if style == "poll":
                    d.text((x, y), shown, font=f, fill=RED)
                else:
                    nxt_hl = k + 1 < len(toks) and toks[k + 1][1] and k + 1 < st["shown"] and line[-1][0] != k
                    d.rectangle((bb[0] - 8, bb[1] - 6, bb[2] + (space + 2 if nxt_hl else 8), bb[3] + 12), fill=acc)
                    d.text((x, y), shown, font=f, fill=(255, 255, 255) if style == "tabloid" else ink)
            else:
                d.text((x, y), shown, font=f, fill=ink)
            x += ww + space
        y += lh
    if st["shown"] >= len(toks) and st["attribution"]:
        af = font(PLAYI, 40)
        if style == "poll":
            d.text((W // 2, y + 20), st["attribution"].upper(), font=font(MONO, 30), fill=dim, anchor="ma")
        else:
            if style == "tabloid":
                d.line((60, y + 20, W - 60, y + 20), fill=(20, 20, 20), width=6)
            d.text((80 if style == "transcript" else 60, y + 50), st["attribution"], font=af, fill=dim)
        y += 120
    # options
    if st["options"]:
        oy = max(y + 60, 1060 if style != "poll" else y + 120)
        of = font(INTER, 54)
        for i, o in enumerate(st["options"]):
            p = min(1.0, max(0.0, (st["opt_t"] - i * 0.12) / 0.25))
            if p <= 0:
                continue
            dx = int((1 - p) ** 3 * 300)
            box = (80 + dx, oy, W - 80 + dx, oy + 120)
            right = st["reveal"] and i == st["answer"]
            wrong = st["reveal"] and i != st["answer"]
            if style == "transcript":
                d.rectangle(box, outline=acc if right else (90, 90, 90), width=4, fill=acc if right else None)
                c = (255, 255, 255) if right else ((90, 90, 90) if wrong else ink)
                d.text((box[0] + 36, oy + 60), f"{'ABC'[i]}   {o}", font=of, fill=c, anchor="lm")
            else:
                fill = acc if (right and style == "tabloid") else ((15, 15, 15) if right else sk["opt_fill"])
                if wrong:
                    fill = tuple(int(v * 0.55 + 120 * 0.45) for v in sk["opt_fill"])
                tc = (255, 255, 255) if right else sk["opt_ink"]
                if style == "poll":
                    d.rounded_rectangle(box, 60, fill=fill)
                else:
                    d.rectangle(box, fill=fill)
                d.text((box[0] + 40, oy + 60), f"{'ABC'[i]}   {o}", font=of, fill=tc, anchor="lm")
            oy += 150
        if st["timer"] is not None:
            tw = int((W - 160) * (1 - st["timer"]))
            bar_c = (255, 255, 255) if style == "poll" else acc
            d.rectangle((80, oy + 10, 80 + tw, oy + 24), fill=bar_c)
    # call to action
    if st["cta"]:
        cf = font(INTER, 76)
        if style == "transcript":
            d.text((80, 1640), st["cta"], font=cf, fill=ink)
            d.text((80, 1740), "Comment below  ↓", font=font(MONO, 40), fill=dim)
        elif style == "tabloid":
            d.rectangle((60, 1560, W - 60, 1740), fill=(15, 15, 15))
            d.text((W // 2, 1650), st["cta"].upper(), font=font(FRANK, 80), fill=(236, 230, 214), anchor="mm")
        else:
            for x, t in ((W // 4, "FAIR"), (3 * W // 4, "TOO FAR")):
                d.rounded_rectangle((x - 210, 1500, x + 210, 1640), 70, fill="white")
                d.text((x, 1570), t, font=font(INTER, 68), fill=(15, 15, 15), anchor="mm")
            d.text((W // 2, 1700), "Vote in the comments", font=font(MONO, 38), fill="white", anchor="ma")
    return Image.blend(im, grain, SKIN[style]["grain"])


# ---------------- sound ----------------
def tick():
    t = np.arange(int(SR * 0.04)) / SR
    return np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 160) * 0.5


def key_click(seed):
    r = np.random.default_rng(seed)
    n = int(SR * 0.03)
    return r.uniform(-1, 1, n) * np.exp(-np.arange(n) / SR * 220) * 0.18


def ding():
    t = np.arange(int(SR * 0.9)) / SR
    return sum(a * np.sin(2 * np.pi * f * t) for f, a in ((1320, 1), (2640, .3), (3960, .1))) * np.exp(-t * 5) * 0.5


def thud():
    t = np.arange(int(SR * 0.35)) / SR
    return np.sin(2 * np.pi * (90 - 40 * t) * t) * np.exp(-t * 12) * 0.9


def drone(seconds):
    t = np.arange(int(SR * seconds)) / SR
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t)
    x = (np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 82.4 * t) + 0.25 * np.sin(2 * np.pi * 110.3 * t))
    return x * lfo * 0.12


# ---------------- timeline ----------------
def spoken(q, game):
    text = q.get("quote_say") or q["quote"]
    if game.get("type") in ("blank", "number"):
        hidden = game.get("blank_say") or game["blank"]
        if hidden in text:
            text = text.replace(hidden, "blank", 1)
        elif game["blank"] in text:
            text = text.replace(game["blank"], "blank", 1)
    return text


def build(post):
    style = post.get("style") or pick_style(post["date"], post.get("slot", "am"))
    sk = SKIN[style]
    d0 = dt.date.fromisoformat(post["date"])
    events = []  # (start, end, state-builder)
    clips, fx = [], []
    t = 0.25
    maxw = W - 160 if sk["align"] == "left" else W - 200
    for qi, q in enumerate(post["quotes"]):
        game = q.get("game") or {}
        f = font(sk["qfont"], sk["qsize"] if len(q["quote"]) < 110 else int(sk["qsize"] * 0.8))
        toks = tokens(q)
        lines = layout(toks, f, maxw, sk["upper"])
        kicker = f"{d0:%b} {d0.day}  ·  {q['where']}".upper()
        title = GAME_TITLE.get(game.get("type"))
        attribution = "Donald Trump"
        base = dict(style=style, kicker=kicker, title=title, toks=toks, lines=lines, f=f,
                    options=None, answer=game.get("answer"), timer=None, reveal=False, opt_t=0,
                    attribution=attribution, cta=None)
        fx.append((t, thud()))
        if not title:  # plain quote: context first, then the quote
            a = say(q["intro_say"])
            clips.append((t + 0.15, a))
            t += 0.15 + len(a) / SR + 0.15
        b = say(spoken(q, game), speed=1.2)
        qs_, qd = t, len(b) / SR
        clips.append((t, b))
        n = len(toks)
        for k in range(n):
            if style == "transcript":
                fx.append((qs_ + qd * 0.95 * k / n, key_click(k)))
        t += qd + 0.35
        events.append((qs_ - (0.15 + len(a) / SR + 0.15 if not title else 0), t, base, qs_, qd))
        if title:
            o_start = t
            opts_state = dict(base, options=game["options"])
            timer_s = 3.0
            for s in range(3):
                fx.append((o_start + 0.5 + s, tick()))
            events.append((o_start, o_start + 0.5 + timer_s, opts_state, ("timer", o_start + 0.5, timer_s), None))
            t = o_start + 0.5 + timer_s
            fx.append((t, ding()))
            if game["type"] == "topic":
                r = say(q["intro_say"])
            else:
                r = say(f"{game.get('blank_say') or game['options'][game['answer']]}.")
            clips.append((t + 0.2, r))
            rev = dict(opts_state, reveal=True)
            events.append((t, t + 0.2 + len(r) / SR + 0.7, rev, ("reveal", o_start), None))
            t += 0.2 + len(r) / SR + 0.7
        else:
            events.append((t, t + 0.6, base, None, None))
            t += 0.6
    # end card
    cta = sk["cta"]
    nxt = "Part two tonight." if post.get("slot", "am") == "am" else "More tomorrow morning."
    e = say(f"{cta} {nxt}")
    clips.append((t + 0.2, e))
    last = dict(events[-1][2], cta=cta, options=None, reveal=False)
    fx.append((t, thud()))
    events.append((t, t + 0.2 + len(e) / SR + 1.2, last, None, None))
    total = t + 0.2 + len(e) / SR + 1.2
    return style, events, clips, fx, total


def frame_state(ev, t):
    start, end, st, extra, qd = ev
    st = dict(st)
    n = len(st["toks"])
    if isinstance(extra, (int, float)):  # typing phase: extra = quote start
        frac = 0 if t < extra else min(1.0, (t - extra) / max(0.1, qd * 0.95))
        st["shown"] = int(np.ceil(frac * n))
    else:
        st["shown"] = n
        if isinstance(extra, tuple) and extra[0] == "timer":
            st["opt_t"] = t - start
            st["timer"] = min(1.0, max(0.0, (t - extra[1]) / extra[2]))
        elif isinstance(extra, tuple) and extra[0] == "reveal":
            st["opt_t"] = 9
    return st


def caption(post, style):
    d = dt.date.fromisoformat(post["date"])
    part = "1 of 2" if post.get("slot", "am") == "am" else "2 of 2"
    hook = SKIN[style]["cta"]
    lines = [f"What Trump said on {d:%A, %B} {d.day} (part {part}) \U0001F1FA\U0001F1F8", f"{hook} Tell us below \U0001F447", ""]
    for i, q in enumerate(post["quotes"]):
        tag = " (said before)" if q.get("said_before") else ""
        lines.append(f"{i + 1}. “{q['quote']}”{tag}\n   \U0001F4CD {q['where']}")
    log = post.get("day_log", {})
    if post.get("slot", "am") == "am" and log.get("speeches"):
        lines += ["", f"\U0001F4DC EVERYTHING HE SAID ON {d.strftime('%b').upper()} {d.day}"]
        for sp in log["speeches"]:
            lines.append(f"\U0001F3A4 {sp['title']}")
            if sp.get("transcript"):
                lines.append(f"   Transcript: {sp['transcript']}")
    lines.append("\U0001F517 Every transcript, video and post: link in bio")
    lines += ["", "Quotes are word for word. Unofficial recap, not affiliated with Donald Trump or the White House.",
              "", "#trump #donaldtrump #politics #news #quotes"]
    cap = "\n".join(lines)
    while len(cap) > 2200 and "   Transcript:" in cap:  # drop transcript links first if too long
        i = cap.rindex("   Transcript:")
        cap = cap[:i] + cap[cap.index("\n", i) + 1:]
    return cap


def main(post_path, out):
    post = json.load(open(post_path, encoding="utf-8"))
    style, events, clips, fx, total = build(post)
    n_s = int(SR * (total + 1))
    vo, sfxb = np.zeros(n_s), np.zeros(n_s)

    def add(buf, sig, at):
        s0 = int(SR * at)
        e = min(len(buf), s0 + len(sig))
        buf[s0:e] += sig[: e - s0]

    for at, c in clips:
        add(vo, c / (np.max(np.abs(c)) + 1e-9) * 0.9, at)
    for at, c in fx:
        add(sfxb, c, at)
    bed = drone(total + 1)[:n_s]
    mix = (vo + sfxb * 0.7 + bed)[: int(SR * total)]
    mix = mix / np.max(np.abs(mix)) * 0.95
    td = tempfile.mkdtemp()
    wav = os.path.join(td, "a.wav")
    sf.write(wav, np.column_stack([mix, mix]).astype(np.float32), SR)

    bg, gr = make_bg(style), grains()
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                             "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
                             "-movflags", "+faststart", "-shortest", out], stdin=subprocess.PIPE)
    cover, cache = None, {}
    for fi in range(int(total * FPS)):
        t = fi / FPS
        ev = next((e for e in events if e[0] <= t < e[1]), events[-1])
        st = frame_state(ev, t)
        key = (id(ev), st["shown"], st.get("timer") and round(st["timer"], 2), round(st["opt_t"], 2), fi % 8 // 2)
        if key not in cache:
            if len(cache) > 64:
                cache.clear()
            cache[key] = draw_frame(style, bg, gr[fi % 8 // 2], st).tobytes()
        if cover is None and ev is events[0] and st["shown"] >= len(st["toks"]):
            cover = Image.frombytes("RGB", (W, H), cache[key])
        proc.stdin.write(cache[key])
    proc.stdin.close()
    proc.wait()
    if cover is not None:
        cover.save(os.path.splitext(out)[0] + "_cover.jpg", quality=92)
    open(os.path.splitext(out)[0] + "_caption.txt", "w", encoding="utf-8").write(caption(post, style))
    open(os.path.splitext(out)[0] + "_style.txt", "w").write(style)
    print("wrote", out, style, f"{total:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
