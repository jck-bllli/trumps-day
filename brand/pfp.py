import math, sys
sys.path.insert(0, "../render")
from PIL import Image, ImageDraw
import make_video as mv
S = 1080
BLUE, INK, WHITE, RED, YEL = mv.BLUE, mv.INK, mv.WHITE, mv.RED, mv.YEL

def sunburst(c1, c2, n=24):
    im = Image.new("RGB", (S, S), c1); d = ImageDraw.Draw(im)
    for k in range(n):
        if k % 2: continue
        a0, a1 = 2*math.pi*k/n, 2*math.pi*(k+1)/n
        d.polygon([(S/2, S/2), (S/2+S*math.cos(a0), S/2+S*math.sin(a0)), (S/2+S*math.cos(a1), S/2+S*math.sin(a1))], fill=c2)
    return im.convert("RGBA")

def bubble(w, h, fill):
    from PIL import ImageFilter
    s = 2; pad = 20
    m = Image.new("L", ((w+2*pad+30)*s, (h+2*pad+160)*s), 0); d = ImageDraw.Draw(m)
    d.rounded_rectangle((pad*s, pad*s, (w+pad)*s, (h+pad)*s), 80*s, fill=255)
    d.polygon([((pad+150)*s, (h+pad-40)*s), ((pad+290)*s, (h+pad-40)*s), ((pad+110)*s, (h+pad+130)*s)], fill=255)
    ol = m.filter(ImageFilter.MaxFilter(29))
    im = Image.new("RGBA", m.size, (0,0,0,0))
    shadow = Image.new("L", m.size, 0); shadow.paste(ol, (22*s, 22*s))
    im.paste(INK, (0,0), shadow); im.paste(INK, (0,0), ol); im.paste(fill, (0,0), m)
    return im.resize((im.width//s, im.height//s), Image.LANCZOS)

def centered(base, el, dy=0):
    base.alpha_composite(el, ((S-el.width)//2, (S-el.height)//2 + dy))

def text(t, size, color, fname="LilitaOne"):
    from PIL import ImageFont
    f = ImageFont.truetype("Merri900.woff", size) if fname == "Merri" else mv.font(fname, size)
    bb = f.getbbox(t); im = Image.new("RGBA", (bb[2]-bb[0]+20, bb[3]-bb[1]+20), (0,0,0,0))
    ImageDraw.Draw(im).text((10-bb[0], 10-bb[1]), t, font=f, fill=color); return im

# A: speech bubble with big red quote marks
a = sunburst(BLUE, mv.BLUE2); b = bubble(700, 520, WHITE); centered(a, b, -40)
q = text("“”", 560, RED, "Merri"); a.alpha_composite(q, ((S-q.width)//2, 300))
a.convert("RGB").save("pfp_A.png")
# B: bubble with "24H"
a = sunburst(RED, (225, 40, 55)); b = bubble(700, 520, WHITE); centered(a, b, -40)
t = text("24H", 330, INK); a.alpha_composite(t, ((S-t.width)//2, 300))
a.convert("RGB").save("pfp_B.png")
# C: calendar page with a quote mark
a = sunburst(BLUE, mv.BLUE2)
cal = Image.new("RGBA", (S, S), (0,0,0,0)); d = ImageDraw.Draw(cal)
x0, y0, x1, y1 = 230, 250, 850, 860
d.rounded_rectangle((x0+20, y0+20, x1+20, y1+20), 70, fill=INK)
d.rounded_rectangle((x0, y0, x1, y1), 70, fill=WHITE, outline=INK, width=16)
d.rounded_rectangle((x0, y0, x1, y0+190), 70, fill=RED, outline=INK, width=16)
d.rectangle((x0+16, y0+100, x1-16, y0+182), fill=RED); d.line((x0, y0+190, x1, y0+190), fill=INK, width=16)
for x in (380, 700): d.rounded_rectangle((x-22, y0-60, x+22, y0+60), 22, fill=INK)
a.alpha_composite(cal)
t = text("TODAY", 120, WHITE); a.alpha_composite(t, ((S-t.width)//2, y0+40))
q = text("“”", 440, INK, "Merri"); a.alpha_composite(q, ((S-q.width)//2, y0+270))
a.convert("RGB").save("pfp_C.png")
