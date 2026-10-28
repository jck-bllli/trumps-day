"""Classic TV-quiz look for an older audience: navy + gold + cream, big serif type, no cartoon stickers."""
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, SS = 1080, 1920, 2
NAVY, NAVY2, INKN = (14, 30, 62), (6, 14, 30), (19, 33, 63)
GOLD, GOLD2 = (212, 175, 90), (240, 210, 140)
CREAM = (247, 241, 227)
GREEN, RED = (38, 140, 76), (170, 40, 45)
_f = {}


def font(name, size):
    if (name, size) not in _f:
        _f[(name, size)] = ImageFont.truetype(os.path.join(HERE, "fonts", f"{name}.woff"), size)
    return _f[(name, size)]


def wrap(text, f, max_w):
    words, lines, cur = text.split(), [], []
    for w in words:
        if cur and f.getlength(" ".join(cur + [w])) > max_w:
            lines.append(cur)
            cur = []
        cur.append(w)
    return lines + [cur] if cur else lines


def spaced(d, xy, text, f, fill, spacing, anchor="mm"):
    total = sum(f.getlength(c) for c in text) + spacing * (len(text) - 1)
    x, y = xy
    x = x - total / 2 if anchor == "mm" else x
    for c in text:
        d.text((x, y), c, font=f, fill=fill, anchor="lm")
        x += f.getlength(c) + spacing


def background():
    im = Image.new("RGB", (W, H), NAVY2)
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((-200, 200, W + 200, H - 200), fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(220))
    im = Image.composite(Image.new("RGB", (W, H), NAVY), im, glow)
    d = ImageDraw.Draw(im)
    for inset, wdt in ((34, 3), (46, 1)):  # double gold frame
        d.rounded_rectangle((inset, inset, W - inset, H - inset), 26, outline=GOLD, width=wdt)
    return im.convert("RGBA")


def header(date_text, round_text):
    im = Image.new("RGBA", (W, 330), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    spaced(d, (W / 2, 30), date_text.upper(), font("Franklin800", 30), GOLD, 5)
    d.text((W / 2, 140), "Did He Say It?", font=font("Playfair900", 112), fill=CREAM, anchor="mm")
    fw = font("Playfair900", 112).getlength("Did He Say It?")
    for sgn in (-1, 1):
        x0 = W / 2 + sgn * (fw / 2 + 24)
        d.line((x0, 150, x0 + sgn * 60, 150), fill=GOLD, width=3)
    d.line((W / 2 - 160, 232, W / 2 + 160, 232), fill=GOLD, width=2)
    spaced(d, (W / 2, 270), round_text.upper(), font("Franklin800", 34), GOLD2, 6)
    return im


def question(text):
    f = font("Merri700", 46)
    lines = wrap(text, f, 900)
    im = Image.new("RGBA", (W, 70 * len(lines) + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        d.text((W / 2, 40 + i * 68), " ".join(ln), font=f, fill=CREAM, anchor="mm")
    return im


def _check(d, cx, cy, r, s, good):
    d.ellipse(((cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s), fill=GREEN if good else RED)
    if good:
        d.line([((cx - r * 0.45) * s, cy * s), ((cx - r * 0.1) * s, (cy + r * 0.35) * s),
                ((cx + r * 0.5) * s, (cy - r * 0.35) * s)], fill=CREAM, width=int(r * 0.28 * s), joint="curve")
    else:
        k = r * 0.38
        d.line(((cx - k) * s, (cy - k) * s, (cx + k) * s, (cy + k) * s), fill=CREAM, width=int(r * 0.26 * s))
        d.line(((cx - k) * s, (cy + k) * s, (cx + k) * s, (cy - k) * s), fill=CREAM, width=int(r * 0.26 * s))


def card(letter, quote, state="open", cw=940, ch=300):
    """state: open | right | wrong"""
    s = SS
    im = Image.new("RGBA", ((cw + 20) * s, (ch + 20) * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((10 * s, 14 * s, (cw + 10) * s, (ch + 14) * s), 22 * s, fill=(0, 0, 0, 110))  # shadow
    border = {"open": GOLD, "right": GREEN, "wrong": (150, 140, 120)}[state]
    d.rounded_rectangle((0, 0, cw * s, ch * s), 22 * s, fill=CREAM, outline=border, width=(12 if state == "right" else 5) * s)
    # letter medallion
    cx, cy, r = 92, ch / 2, 54
    d.ellipse(((cx - r - 6) * s, (cy - r - 6) * s, (cx + r + 6) * s, (cy + r + 6) * s), fill=GOLD)
    d.ellipse(((cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s), fill=NAVY)
    d.text((cx * s, (cy + 2) * s), letter, font=font("Playfair900", 74 * s), fill=GOLD2, anchor="mm")
    # quote text: largest size that fits
    for size in range(60, 36, -2):
        f = font("Merri700", size * s)
        lines = wrap("“" + quote + "”", f, (cw - 220) * s)
        lh = f.size * 1.28
        if len(lines) * lh <= (ch - 50) * s:
            break
    y = (ch * s - len(lines) * lh) / 2 + lh * 0.12
    for ln in lines:
        d.text((182 * s, y), " ".join(ln), font=f, fill=INKN)
        y += lh
    if state == "wrong":
        veil = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(veil).rounded_rectangle((0, 0, cw * s, ch * s), 22 * s, fill=NAVY2 + (130,))
        im.alpha_composite(veil)
    return im.resize((im.width // s, im.height // s), Image.LANCZOS)


def who(text, good):
    s = SS
    f = font("Franklin800", 34 * s)
    w = int(f.getlength(text) / s) + 120
    im = Image.new("RGBA", (w * s, 72 * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * s - 1, 72 * s - 1), 36 * s, fill=GREEN if good else NAVY, outline=GOLD, width=3 * s)
    _check(d, 38, 36, 22, s, good)
    d.text((76 * s, 37 * s), text, font=f, fill=CREAM, anchor="lm")
    return im.resize((w, 72), Image.LANCZOS)


def timer(p, secs_left):
    """Gold ring that empties clockwise + big number, with the prompt beside it."""
    s = SS
    im = Image.new("RGBA", (W * s, 200 * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy, r = 300, 100, 78
    d.ellipse(((cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s), outline=(60, 74, 110), width=12 * s)
    if p < 1:
        d.arc(((cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s), -90, -90 + 360 * (1 - p), fill=GOLD, width=12 * s)
    d.text((cx * s, (cy + 4) * s), str(secs_left), font=font("Playfair900", 92 * s), fill=CREAM, anchor="mm")
    d.text(((cx + 120) * s, (cy - 26) * s), "Make your guess", font=font("Merri700", 44 * s), fill=CREAM, anchor="lm")
    d.text(((cx + 120) * s, (cy + 34) * s), "Comment A or B below", font=font("Franklin800", 34 * s), fill=GOLD2,
           anchor="lm")
    return im.resize((W, 200), Image.LANCZOS)


def footer(text="Every quote is real. Sources in the caption."):
    im = Image.new("RGBA", (W, 60), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((W / 2, 30), text, font=font("Franklin800", 28), fill=(170, 160, 135), anchor="mm")
    return im


def end_card(n):
    im = Image.new("RGBA", (W, 900), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((W / 2, 120), "How many", font=font("Playfair900", 120), fill=CREAM, anchor="mm")
    d.text((W / 2, 260), "did you get?", font=font("Playfair900", 120), fill=CREAM, anchor="mm")
    d.line((W / 2 - 200, 360, W / 2 + 200, 360), fill=GOLD, width=3)
    d.text((W / 2, 450), f"Share your score out of {n}", font=font("Merri700", 50), fill=GOLD2, anchor="mm")
    d.text((W / 2, 530), "in the comments.", font=font("Merri700", 50), fill=GOLD2, anchor="mm")
    spaced(d, (W / 2, 680), "FOLLOW FOR A NEW ROUND EVERY DAY", font("Franklin800", 34), CREAM, 4)
    return im


def frame(date_text, round_text, q, cards, timer_im=None, labels=()):
    """cards: [(letter, quote, state)], labels: [(card_index, text, good)]"""
    im = background()
    im.alpha_composite(header(date_text, round_text), (0, 220))
    qi = question(q)
    im.alpha_composite(qi, (0, 590))
    ys = (760, 1110)
    for (L, quote, st), y in zip(cards, ys):
        c = card(L, quote, st)
        im.alpha_composite(c, ((W - c.width) // 2 + 5, y))
    for idx, text, good in labels:
        lab = who(text, good)
        im.alpha_composite(lab, ((W - lab.width) // 2, ys[idx] + 300 - 22))
    if timer_im is not None:
        im.alpha_composite(timer_im, (0, 1440))
    im.alpha_composite(footer(), (0, 1660))
    return im


if __name__ == "__main__":
    q = "Which of these did Donald Trump say yesterday?"
    A = "We're thinking about renaming it the Trump Strait."
    B = "Am considering taking Tesla private at $420. Funding secured."
    f1 = frame("Tuesday, October 27", "Round 1 of 3", q, [("A", A, "open"), ("B", B, "open")], timer(0.35, 2))
    f2 = frame("Tuesday, October 27", "Round 1 of 3", q, [("A", A, "right"), ("B", B, "wrong")], None,
               [(0, "Donald Trump · Rally, Oct. 27", True), (1, "Elon Musk · Tweet, 2018", False)])
    out = Image.new("RGB", (W * 2 + 60, H), (255, 255, 255))
    out.paste(f1.convert("RGB"), (0, 0))
    out.paste(f2.convert("RGB"), (W + 60, 0))
    out.save("/tmp/claude-0/classic_style.png")
    out.resize((out.width // 2, out.height // 2), Image.LANCZOS).save("/tmp/claude-0/classic_style_small.png")
    print("ok")
