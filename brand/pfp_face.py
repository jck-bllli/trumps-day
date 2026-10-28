import sys
sys.path.insert(0, "../render")
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import make_video as mv
from pfp import sunburst, bubble, S, BLUE, INK, WHITE, RED
SKIN, HAIR, SUIT, TIE, SHIRT = mv.SKIN, mv.HAIR, mv.SUIT, mv.TIE, mv.SHIRT

def face(k):
    """The video's neutral figure, head and shoulders, scaled up by k."""
    W2 = int(300 * k); im = Image.new("RGBA", (W2, int(330 * k)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, hy, top, ow = 150, 110, 180, 6
    P = lambda x, y: (x * k, y * k)
    # shoulders / suit with shirt + tie
    d.rounded_rectangle((*P(cx - 120, top), *P(cx + 120, top + 200)), int(60 * k), fill=SUIT, outline=INK, width=int(ow * k))
    d.polygon([P(cx - 30, top + 3), P(cx + 30, top + 3), P(cx, top + 70)], fill=SHIRT)
    d.polygon([P(cx - 10, top + 8), P(cx + 10, top + 8), P(cx + 15, top + 110), P(cx, top + 130), P(cx - 15, top + 110)],
              fill=TIE, outline=INK, width=int(3 * k))
    # head
    d.ellipse((*P(cx - 54, hy - 58), *P(cx + 54, hy + 58)), fill=SKIN, outline=INK, width=int(ow * k))
    # hair (same merged swoop as the video)
    mask = Image.new("L", im.size, 0); md = ImageDraw.Draw(mask)
    md.chord((*P(cx - 58, hy - 72), *P(cx + 60, hy + 4)), 180, 360, fill=255)
    md.polygon([P(cx - 58, hy - 34), P(cx + 68, hy - 42), P(cx + 42, hy - 18), P(cx - 52, hy - 16)], fill=255)
    im.paste(INK, (0, 0), mask.filter(ImageFilter.MaxFilter(int(ow * k) // 2 * 2 + 1)))
    im.paste(HAIR, (0, 0), mask)
    d = ImageDraw.Draw(im)
    for ex in (-19, 19):
        d.ellipse((*P(cx + ex - 6, hy), *P(cx + ex + 6, hy + 12)), fill=INK)
    d.line((*P(cx - 14, hy + 32), *P(cx + 14, hy + 32)), fill=INK, width=int(4 * k))
    return im

# D: face alone, big, on the blue sunburst
a = sunburst(BLUE, mv.BLUE2); f = face(2.9)
a.alpha_composite(f, ((S - f.width) // 2, S - f.height + 40)); a.convert("RGB").save("pfp_D.png")
# E: face plus a small quote bubble
a = sunburst(BLUE, mv.BLUE2); f = face(2.5)
a.alpha_composite(f, (60, S - f.height + 40))
b = bubble(360, 260, WHITE); a.alpha_composite(b, (S - b.width - 70, 110))
q = ImageFont.truetype("Merri900.woff", 300); d = ImageDraw.Draw(a)
d.text((S - b.width - 70 + 20 + 180, 110 + 20 + 165), "“”", font=q, fill=RED, anchor="mm")
a.convert("RGB").save("pfp_E.png")
