#!/usr/bin/env python3
"""Daily 'Trump's day in 5 quotes' Reel: playful sticker style, verified quotes, narrator voice.

  python3 render/make_video.py days/2026-10-27.json out.mp4
"""
import json
import math
import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
W, H, FPS, SS, SR = 1080, 1920, 30, 2, 48000
BLUE, BLUE2 = (37, 99, 235), (59, 120, 245)
INK, WHITE = (18, 20, 32), (255, 255, 255)
RED, YEL, GREY = (239, 51, 64), (255, 205, 41), (196, 202, 214)
EMOJI_FONT = next((p for p in (os.path.join(HERE, "fonts", "NotoColorEmoji.ttf"),
                    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf") if os.path.exists(p)),
                   "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf")
_fonts = {}


def font(name, size):
    if (name, size) not in _fonts:
        _fonts[(name, size)] = ImageFont.truetype(os.path.join(HERE, "fonts", f"{name}.woff"), size)
    return _fonts[(name, size)]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_back(t):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out(t):
    return 1 - (1 - t) ** 3


def shrink(im):
    return im.resize((im.width // SS, im.height // SS), Image.LANCZOS)


def emoji(ch, size):
    """Color emoji rendered at Noto's native size, scaled to `size` px."""
    f = ImageFont.truetype(EMOJI_FONT, 109)
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    r = size / max(im.size)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)


def sticker(w, h, fill, radius=30, ow=8, sh=12):
    s = SS
    im = Image.new("RGBA", ((w + sh) * s, (h + sh) * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if sh:
        d.rounded_rectangle((sh * s, sh * s, (w + sh) * s - 1, (h + sh) * s - 1), radius * s, fill=INK)
    d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius * s, fill=fill, outline=INK, width=ow * s)
    return im, d


def text_sticker(text, fsize, fill, color=INK, angle=0, pad=44, h=None, fname="LilitaOne"):
    f = font(fname, fsize * SS)
    tw = int(f.getlength(text) / SS)
    h = h or int(fsize * 1.35)
    im, d = sticker(tw + pad * 2, h, fill)
    d.text(((tw + pad * 2) * SS // 2, h * SS // 2 + 4 * SS), text, font=f, fill=color, anchor="mm")
    im = shrink(im)
    return im.rotate(angle, resample=Image.BICUBIC, expand=True) if angle else im


# ---------------- voice ----------------
VOICE_CHAIN = ("aresample=48000:resampler=soxr:precision=28,"
               "rubberband=pitch=0.93:formant=preserved:pitchq=quality:transients=crisp:detector=compound:window=standard,"
               "highpass=f=90:poles=2,equalizer=f=280:t=q:w=1.0:g=-6,equalizer=f=650:t=q:w=1.4:g=-2,"
               "equalizer=f=2500:t=q:w=1.0:g=6,equalizer=f=4500:t=q:w=1.2:g=3,highshelf=f=9500:g=4,"
               "deesser=i=0.25:m=0.5:f=0.6,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=60:makeup=2,"
               "alimiter=limit=0.95")
_k = None


def say(text, speed=1.32):
    global _k
    if _k is None:
        from kokoro_onnx import Kokoro
        md = os.environ.get("KOKORO_DIR", os.path.join(HERE, "tts_model"))
        _k = Kokoro(os.path.join(md, "kokoro-v1.0.onnx"), os.path.join(md, "voices-v1.0.bin"))
    y, sr = _k.create(text, voice="am_echo", speed=speed)
    with tempfile.TemporaryDirectory() as td:
        sf.write(f"{td}/i.wav", y, sr)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{td}/i.wav", "-af", VOICE_CHAIN, "-ac", "1",
                        f"{td}/o.wav"], check=True)
        a, _ = sf.read(f"{td}/o.wav", dtype="float32")
    i = np.where(np.abs(a) > 0.01)[0]
    return a[max(0, i[0] - 480): i[-1] + 3000] if len(i) else a


# ---------------- graphics ----------------
def star_pts(cx, cy, r, inner=0.45, rot=-math.pi / 2):
    return [(cx + (r if k % 2 == 0 else r * inner) * math.cos(rot + k * math.pi / 5),
             cy + (r if k % 2 == 0 else r * inner) * math.sin(rot + k * math.pi / 5)) for k in range(10)]


def make_bg():
    sp = 160
    big = Image.new("RGB", (W + sp, H + sp), BLUE)
    d = ImageDraw.Draw(big)
    for row, y in enumerate(range(0, H + sp * 2, sp)):
        off = sp // 2 if row % 2 else 0
        for x in range(-sp, W + sp * 2, sp):
            d.polygon(star_pts(x + off, y, 22), fill=BLUE2)
    return big, sp


def el_calendar(date_iso):
    import datetime as dt
    d0 = dt.date.fromisoformat(date_iso)
    s = SS
    w, h, sh = 176, 206, 10
    im = Image.new("RGBA", ((w + sh) * s, (h + sh + 16) * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    top = 16 * s
    d.rounded_rectangle((sh * s, top + sh * s, (w + sh) * s, top + (h + sh) * s), 26 * s, fill=INK)
    d.rounded_rectangle((0, top, w * s, top + h * s), 26 * s, fill=WHITE, outline=INK, width=7 * s)
    d.rounded_rectangle((0, top, w * s, top + 62 * s), 26 * s, fill=RED, outline=INK, width=7 * s)
    d.rectangle((7 * s, top + 34 * s, (w - 7) * s, top + 58 * s), fill=RED)
    d.line((0, top + 62 * s, w * s, top + 62 * s), fill=INK, width=7 * s)
    for x in (52, w - 52):  # binder rings
        d.rounded_rectangle(((x - 9) * s, 0, (x + 9) * s, 40 * s), 9 * s, fill=INK)
    d.text((w * s // 2, top + 34 * s), d0.strftime("%b").upper(), font=font("LilitaOne", 42 * s), fill=WHITE, anchor="mm")
    d.text((w * s // 2, top + 118 * s), str(d0.day), font=font("LilitaOne", 100 * s), fill=INK, anchor="mm")
    d.text((w * s // 2, top + 182 * s), d0.strftime("%A").upper(), font=font("NunitoBlack", 24 * s), fill=(90, 96, 112),
           anchor="mm")
    return shrink(im).rotate(8, resample=Image.BICUBIC, expand=True)


def el_header(date_iso, n=5):
    im = Image.new("RGBA", (W, 420), (0, 0, 0, 0))
    a = text_sticker("TRUMP'S DAY", 118, RED, WHITE, angle=-3)
    b = text_sticker(f"IN {n} QUOTES", 72, YEL, INK, angle=2)
    im.alpha_composite(a, ((W - a.width) // 2 + 40, 0))
    im.alpha_composite(b, ((W - b.width) // 2 + 170, a.height - 34))
    cal = el_calendar(date_iso)
    im.alpha_composite(cal, (28, a.height - 120))
    d = ImageDraw.Draw(im)
    d.text((W // 2 + 170, a.height + b.height - 4), "UNOFFICIAL RECAP  ·  WORD FOR WORD",
           font=font("NunitoBlack", 26), fill=WHITE, anchor="mm")
    return im


def el_stars(i, n):
    im = Image.new("RGBA", (W * SS, 90 * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = SS
    gap = 118
    x0 = W // 2 - gap * (n - 1) / 2
    for k in range(n):
        cx, cy = (x0 + k * gap) * s, 45 * s
        r = (40 if k == i else 32) * s
        d.polygon([(x + 6 * s, y + 6 * s) for x, y in star_pts(cx, cy, r)], fill=INK)
        d.polygon(star_pts(cx, cy, r), fill=YEL if k <= i else WHITE, outline=INK, width=5 * s)
    return shrink(im)


def wrap(text, f, max_w):
    words, lines, cur = text.split(), [], []
    for w in words:
        if f.getlength(" ".join(cur + [w])) <= max_w or not cur:
            cur.append(w)
        else:
            lines.append(cur)
            cur = [w]
    return lines + ([cur] if cur else [])


BUBBLE_TOP, BUBBLE_BOTTOM = 815, 1300   # room between the topic sticker and the location/reaction rows


def bubble_layout(text):
    """Largest font whose bubble fills the box without overflowing."""
    avail = BUBBLE_BOTTOM - BUBBLE_TOP - 90   # minus the tail
    for size in range(124, 50, -4):
        f = font("NunitoBlack", size * SS)
        lines = wrap("“" + text + "”", f, 880 * SS)
        h = len(lines) * int(f.size * 1.14) / SS + 110
        if len(lines) <= 5 and h <= avail:
            return f, lines
    return f, lines


def el_bubble(f, lines, words_lit):
    """Speech bubble; the first `words_lit` words are dark, the rest pale (karaoke reveal)."""
    s = SS
    lh = int(f.size * 1.14)
    w, h = 980, int(len(lines) * lh / s) + 110
    tail = 90
    sh = 14
    im = Image.new("RGBA", ((w + sh) * s, (h + tail + sh) * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    tail_pts = [(150 * s, (h - 10) * s), (110 * s, (h + tail) * s), (290 * s, (h - 10) * s)]
    for off, fill in ((sh, INK), (0, WHITE)):
        d.rounded_rectangle((off * s, off * s, (w + off) * s - 1, (h + off) * s - 1), 54 * s, fill=fill if off else INK)
        d.polygon([(x + off * s, y + off * s) for x, y in tail_pts], fill=INK)
    # white body with ink outline drawn by layering
    d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), 54 * s, fill=INK)
    d.rounded_rectangle((8 * s, 8 * s, w * s - 8 * s, h * s - 8 * s), 48 * s, fill=WHITE)
    d.polygon([(150 * s + 10 * s, (h - 18) * s), (124 * s, (h + tail - 22) * s), (290 * s - 12 * s, (h - 18) * s)],
              fill=WHITE)
    y = 52 * s
    k = 0
    for line in lines:
        x = (w * s - f.getlength(" ".join(line))) / 2
        for wd in line:
            d.text((x, y), wd, font=f, fill=INK if k < words_lit else GREY)
            x += f.getlength(wd + " ")
            k += 1
        y += lh
    return shrink(im)


def el_topic(q):
    t = text_sticker(q["topic"], 64, YEL, INK, pad=38)
    e = emoji(q.get("emoji", "💬"), 86)
    im = Image.new("RGBA", (t.width + e.width + 20, max(t.height, e.height) + 10), (0, 0, 0, 0))
    im.alpha_composite(t, (0, (im.height - t.height) // 2))
    im.alpha_composite(e, (t.width + 8, (im.height - e.height) // 2))
    return im.rotate(-3, resample=Image.BICUBIC, expand=True)


def el_where(text):
    f = font("NunitoBlack", 34)
    im = Image.new("RGBA", (int(f.getlength(text)) + 110, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, 63), 32, fill=(20, 40, 120))
    pin = emoji("📍", 38)
    im.alpha_composite(pin, (22, (64 - pin.height) // 2))
    d.text((72, 32), text, font=f, fill=WHITE, anchor="lm")
    return im


def el_react():
    im = Image.new("RGBA", (W, 216), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font("LilitaOne", 46)
    label = "YOUR REACTION?"
    tw = f.getlength(label)
    hand = emoji("\U0001F447", 48)
    cx0 = 690
    x0 = cx0 - (tw + hand.width + 12) / 2
    d.text((x0, 30), label, font=f, fill=WHITE, anchor="lm")
    im.alpha_composite(hand, (int(x0 + tw + 12), 30 - hand.height // 2))
    for k, ch in enumerate(["\U0001F602", "\U0001F525", "\U0001F62C"]):
        cx = cx0 + (k - 1) * 150
        c, _ = sticker(124, 124, WHITE, radius=62, ow=7, sh=9)
        im.alpha_composite(shrink(c), (cx - 62, 66))
        e = emoji(ch, 80)
        im.alpha_composite(e, (cx - e.width // 2, 66 + 62 - e.height // 2))
    return im


def el_intro(n):
    im = Image.new("RGBA", (W, 860), (0, 0, 0, 0))
    a = text_sticker(f"{n} QUOTES", 200, WHITE, INK, angle=-4, h=270)
    b = text_sticker("STRAIGHT FROM THE MIC", 62, YEL, INK, angle=3)
    im.alpha_composite(a, ((W - a.width) // 2, 60))
    im.alpha_composite(b, ((W - b.width) // 2 - 40, 60 + a.height - 24))
    mic = emoji("🎤", 120)
    im.alpha_composite(mic, ((W + b.width) // 2 - 60, 60 + a.height - 60))
    c = el_receipts(46)
    im.alpha_composite(c, ((W - c.width) // 2, 60 + a.height + b.height + 10))
    return im


def el_receipts(size=46, text="EVERY SPEECH + POST IN THE CAPTION"):
    """Callout that the full day (transcripts + posts) is in the caption."""
    t = text_sticker(text, size, WHITE, INK, pad=30)
    e = emoji("\U0001F4DC", int(size * 1.7))
    im = Image.new("RGBA", (t.width + e.width + 14, max(t.height, e.height) + 6), (0, 0, 0, 0))
    im.alpha_composite(e, (0, (im.height - e.height) // 2))
    im.alpha_composite(t, (e.width + 14, (im.height - t.height) // 2))
    return im.rotate(2, resample=Image.BICUBIC, expand=True)


def el_again():
    """Tag for lines he has said before, so a repeat isn't passed off as new."""
    return text_sticker("SAID BEFORE", 40, RED, WHITE, angle=-6, pad=26)


def el_end():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    flag = emoji("🇺🇸", 150)
    a = text_sticker("FOLLOW FOR", 128, WHITE, INK, angle=-3)
    b = text_sticker("TOMORROW'S 5", 128, RED, WHITE, angle=2)
    c1 = text_sticker("EVERY SPEECH + POST", 58, YEL, INK, angle=-2, pad=34)
    c2 = text_sticker("FROM TODAY IN THE CAPTION", 50, WHITE, INK, angle=1, pad=30)
    y = 480
    im.alpha_composite(flag, ((W - flag.width) // 2, y))
    y += flag.height + 30
    for el in (a, b):
        im.alpha_composite(el, ((W - el.width) // 2, y))
        y += el.height - 14
    y += 40
    scroll = emoji("\U0001F4DC", 96)
    im.alpha_composite(c1, ((W - c1.width) // 2, y))
    im.alpha_composite(scroll, ((W + c1.width) // 2 - 30, y - 40))
    y += c1.height - 6
    im.alpha_composite(c2, ((W - c2.width) // 2, y))
    y += c2.height
    d = ImageDraw.Draw(im)
    d.text((W // 2, y + 50), "Unofficial recap · Not affiliated with Donald Trump or the White House",
           font=font("NunitoBlack", 30), fill=WHITE, anchor="mm")
    return im


# ---------------- neutral speaker figure (idle only: breathing, sway, blink) ----------------
SKIN, HAIR, SUIT, TIE, SHIRT = (247, 205, 170), (242, 200, 90), (28, 38, 74), (220, 38, 52), (255, 255, 255)


def el_figure(t):
    s = 2
    w, h = 300, 420
    im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    breathe = 1 + 0.012 * math.sin(2 * math.pi * t / 3.2)
    sway = 3 * math.sin(2 * math.pi * t / 5.0)
    blink = (t % 3.7) < 0.12
    cx = w / 2 + sway
    ow = 6 * s
    # legs + shoes
    for dx in (-26, 26):
        d.line(((cx + dx * 0.6) * s, 300 * s, (cx + dx) * s, 392 * s), fill=INK, width=14 * s)
        d.rounded_rectangle(((cx + dx - 24) * s, 384 * s, (cx + dx + 24) * s, 404 * s), 10 * s, fill=INK)
    # torso (suit jacket), slightly breathing
    top = 168 - 6 * (breathe - 1) * 100
    d.polygon([((cx - 62) * s, top * s), ((cx + 62) * s, top * s), ((cx + 54) * s, 312 * s), ((cx - 54) * s, 312 * s)],
              fill=SUIT, outline=INK, width=ow)
    d.polygon([((cx - 22) * s, top * s), ((cx + 22) * s, top * s), (cx * s, (top + 58) * s)], fill=SHIRT)
    d.polygon([((cx - 8) * s, (top + 6) * s), ((cx + 8) * s, (top + 6) * s), ((cx + 12) * s, (top + 120) * s),
               (cx * s, (top + 136) * s), ((cx - 12) * s, (top + 120) * s)], fill=TIE, outline=INK, width=3 * s)
    # arms resting at the sides
    for side in (-1, 1):
        d.line(((cx + side * 58) * s, (top + 10) * s, (cx + side * 74) * s, (top + 120) * s), fill=SUIT, width=26 * s)
        d.line(((cx + side * 58) * s, (top + 10) * s, (cx + side * 74) * s, (top + 120) * s), fill=INK, width=4 * s)
        d.ellipse(((cx + side * 74 - 13) * s, (top + 112) * s, (cx + side * 74 + 13) * s, (top + 138) * s),
                  fill=SKIN, outline=INK, width=4 * s)
    # head
    hy = top - 70
    d.ellipse(((cx - 54) * s, (hy - 58) * s, (cx + 54) * s, (hy + 58) * s), fill=SKIN, outline=INK, width=ow)
    # hair: neat side swoop
    # hair: one merged swoop shape with a single outline (no seams)
    from PIL import ImageFilter
    mask = Image.new("L", im.size, 0)
    md = ImageDraw.Draw(mask)
    md.chord(((cx - 58) * s, (hy - 72) * s, (cx + 60) * s, (hy + 4) * s), 180, 360, fill=255)
    md.polygon([((cx - 58) * s, (hy - 34) * s), ((cx + 68) * s, (hy - 42) * s), ((cx + 42) * s, (hy - 18) * s),
                ((cx - 52) * s, (hy - 16) * s)], fill=255)
    im.paste(INK, (0, 0), mask.filter(ImageFilter.MaxFilter(ow // 2 * 2 + 1)))
    im.paste(HAIR, (0, 0), mask)
    d = ImageDraw.Draw(im)
    # neutral face
    for ex in (-19, 19):
        if blink:
            d.line(((cx + ex - 7) * s, (hy + 6) * s, (cx + ex + 7) * s, (hy + 6) * s), fill=INK, width=4 * s)
        else:
            d.ellipse(((cx + ex - 6) * s, hy * s, (cx + ex + 6) * s, (hy + 12) * s), fill=INK)
    d.line(((cx - 14) * s, (hy + 32) * s, (cx + 14) * s, (hy + 32) * s), fill=INK, width=4 * s)
    return im.resize((w, h), Image.LANCZOS)


def paste(frame, el, cx, cy, scale=1.0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0.01:
        return
    if abs(scale - 1) > 0.005:
        el = el.resize((max(1, int(el.width * scale)), max(1, int(el.height * scale))), Image.BICUBIC)
    if alpha < 0.99:
        el = el.copy()
        el.putalpha(el.getchannel("A").point(lambda v: int(v * alpha)))
    frame.alpha_composite(el, (int(cx - el.width / 2), int(cy - el.height / 2)))


def pop(t, delay=0.0, dur=0.38):
    p = clamp((t - delay) / dur)
    return (0.6 + 0.4 * ease_out_back(p)) if p > 0 else 0.0, ease_out(p)


# ---------------- sound ----------------
def whoosh():
    n = int(SR * 0.32)
    sm = np.convolve(np.random.default_rng(4).uniform(-1, 1, n), np.ones(30) / 30, mode="same")
    return sm * np.sin(np.linspace(0, np.pi, n)) ** 2 * 0.8


def boing():
    t = np.arange(int(SR * 0.25)) / SR
    return np.sin(2 * np.pi * (500 + 500 * t / 0.25) * t) * np.exp(-t * 14) * 0.3


def build_caption(data):
    """Quotes, then the full day: every speech (transcript + video) and every post. IG max is 2,200 chars,
    and links in captions aren't clickable, so they're written as plain short addresses."""
    import datetime as _dt
    qs, log = data["quotes"], data.get("day_log", {})
    d = _dt.date.fromisoformat(data["date"])
    lines = [f"Trump's day in {len(qs)} quotes ({d:%A, %B} {d.day}) 🇺🇸",
             "Love it or hate it? Tell us which one got you 👇", ""]
    for i, q in enumerate(qs):
        tag = " (said before)" if q.get("said_before") else ""
        lines.append(f"{i + 1}. “{q['quote']}”{tag}\n   📍 {q['where']}")
    lines += ["", f"📜 EVERYTHING HE SAID ON {d.strftime('%b').upper()} {d.day}"]
    for sp in log.get("speeches", []):
        lines.append(f"🎤 {sp['title']}")
        if sp.get("transcript"):
            lines.append(f"   Transcript: {sp['transcript']}")
        if sp.get("video"):
            lines.append(f"   Video: {sp['video']}")
    if log.get("post_count"):
        lines.append(f"📱 {log['post_count']} Truth Social posts")
    lines.append("🔗 Clickable links to every transcript, video and post: link in bio")
    lines += ["", "Quotes are word for word. Unofficial recap, not affiliated with Donald Trump or the White House.",
              "", "#trump #donaldtrump #politics #news #dailyrecap #quotes"]
    cap = "\n".join(lines)
    if len(cap) > 2200:
        print(f"WARNING: caption is {len(cap)} chars (Instagram max 2,200)")
    return cap


def main(data_path, out):
    import music
    import sfx
    data = json.load(open(data_path))
    qs = data["quotes"]
    n = len(qs)
    intro = say(data["intro_say"])
    clips = [(0.2, intro)]
    t = 0.2 + len(intro) / SR + 0.35
    segs = []
    for q in qs:
        a = say(q["intro_say"])
        b = say(q.get("quote_say") or q["quote"], speed=1.25)
        start = t
        clips.append((start + 0.3, a))
        qstart = start + 0.3 + len(a) / SR + 0.2
        clips.append((qstart, b))
        fx_t = qstart + len(b) / SR + 0.12
        fx_sig = sfx.get(q.get("sfx", "ding"))
        end = fx_t + min(len(fx_sig) / SR, 1.5) + 0.35
        segs.append(dict(start=start, qstart=qstart, qdur=len(b) / SR, end=end, fx_t=fx_t, fx=fx_sig))
        t = end
    outro = say(data["outro_say"])
    end_start = t
    clips.append((end_start + 0.35, outro))
    total = end_start + 0.35 + len(outro) / SR + 1.3

    n_s = int(SR * (total + 1))
    vo, fx = np.zeros(n_s), np.zeros(n_s)

    def add(buf, sig, at):
        s0 = int(SR * at)
        e = min(len(buf), s0 + len(sig))
        buf[s0:e] += sig[: e - s0]

    for at, c in clips:
        add(vo, c / (np.max(np.abs(c)) + 1e-9) * 0.9, at)
    for sg in segs:
        add(fx, whoosh(), sg["start"])
        add(fx, boing(), sg["start"] + 0.12)
        add(fx, sg["fx"] * 1.25, sg["fx_t"])
    add(fx, whoosh(), end_start)
    m = music.make_loop(total + 1)[:n_s]
    m = np.pad(m, (0, n_s - len(m)))
    env = np.convolve(np.abs(vo), np.ones(5760) / 5760, mode="same")
    duck = np.convolve(np.where(env > 0.008, 0.3, 1.0), np.ones(4800) / 4800, mode="same")
    mix = (vo + fx * 0.6 + m * 0.2 * duck)[: int(SR * total)]
    mix = mix / np.max(np.abs(mix)) * 0.95
    td = tempfile.mkdtemp()
    wav = os.path.join(td, "a.wav")
    sf.write(wav, np.column_stack([mix, mix]).astype(np.float32), SR)

    bg, sp = make_bg()
    header = el_header(data["date"], n)
    react = el_react()
    intro_el = el_intro(n)
    end_el = el_end()
    stars = [el_stars(i, n) for i in range(n)]
    topics = [el_topic(q) for q in qs]
    bursts = [emoji(q.get("emoji", "\u2728"), 90) for q in qs]
    wheres = [el_where(q["where"]) for q in qs]
    again = el_again()
    layouts = [bubble_layout(q["quote"]) for q in qs]
    nwords = [sum(len(l) for l in L[1]) for L in layouts]
    bubbles = {}

    def bubble(i, k):
        if (i, k) not in bubbles:
            bubbles[(i, k)] = el_bubble(*layouts[i], k)
        return bubbles[(i, k)]

    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                             "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
                             "-movflags", "+faststart", "-shortest", out], stdin=subprocess.PIPE)
    cover = None
    for fi in range(int(total * FPS)):
        t = fi / FPS
        off = int((t * 30) % sp)
        fr = bg.crop((off, off, off + W, off + H)).convert("RGBA")
        if t < end_start:
            fr.alpha_composite(header, (0, 240))
            paste(fr, react, W / 2, 1515)
            if t < segs[0]["start"]:
                sc, al = pop(t, 0.0, 0.45)
                paste(fr, intro_el, W / 2, 1010, sc, al)
            else:
                qi = max(i for i, s in enumerate(segs) if s["start"] <= t)
                sg = segs[qi]
                lt = t - sg["start"]
                paste(fr, stars[qi], W / 2, 630)
                tsc, tal = pop(lt, 0.0)
                paste(fr, topics[qi], W / 2, 750, tsc, tal)
                if t < sg["qstart"]:
                    lit = 0
                else:
                    frac = clamp((t - sg["qstart"]) / max(0.1, sg["qdur"] * 0.95))
                    lit = int(math.ceil(frac * nwords[qi]))
                b = bubble(qi, lit)
                bsc, bal = pop(lt, 0.08, 0.42)
                by = BUBBLE_TOP + (BUBBLE_BOTTOM - BUBBLE_TOP) / 2
                paste(fr, b, W / 2 + 7, by, bsc, bal)
                wsc, wal = pop(lt, 0.2)
                paste(fr, wheres[qi], W / 2 + 140, by + b.height / 2 - 34, 1, wal)
                if qs[qi].get("said_before"):
                    asc, aal = pop(lt, 0.3)
                    paste(fr, again, W / 2 - 300, by - b.height / 2 + 6, asc, aal)
                fig_el = el_figure(t)
                fig_el = fig_el.resize((int(fig_el.width * 0.8), int(fig_el.height * 0.8)), Image.LANCZOS)
                fr.alpha_composite(fig_el, (58, 1628 - fig_el.height))
                bt = t - sg["fx_t"]
                if 0 <= bt < 1.1:  # emoji burst out of the bubble's top-right corner when the effect plays
                    for k in range(6):
                        ang = math.radians(-150 + k * 28)
                        dist = 40 + 260 * ease_out(clamp(bt / 0.9))
                        ex = W / 2 + 330 + math.cos(ang) * dist * 0.9
                        ey = by - b.height / 2 + 30 + math.sin(ang) * dist * 0.7
                        sc = 0.5 + 0.7 * ease_out_back(clamp(bt / 0.35))
                        paste(fr, bursts[qi], ex, ey, sc * (1.0 if k % 2 else 0.75), 1 - clamp((bt - 0.6) / 0.5))
                if qi == 0 and cover is None and lit >= nwords[0]:
                    cover = fr.copy()
        else:
            sc, al = pop(t - end_start, 0.0, 0.45)
            paste(fr, end_el, W / 2, H / 2, sc, al)
        proc.stdin.write(fr.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    if cover is not None:
        cover.convert("RGB").save(os.path.splitext(out)[0] + "_cover.jpg", quality=92)
    cap = build_caption(data)
    open(os.path.splitext(out)[0] + "_caption.txt", "w").write(cap)
    print("wrote", out, f"{total:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
