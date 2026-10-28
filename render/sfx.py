"""Original synthesized sound effects (no licensing issues). All return mono float arrays at 48 kHz.

Pick per quote with "sfx": cash | gavel | stamp | cheer | applause | chime | drumroll | boing | whoosh_up | ding
"""
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
RNG = np.random.default_rng(11)


def _t(d):
    return np.arange(int(SR * d)) / SR


def _bp(x, lo, hi, order=4):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


def _lp(x, f, order=4):
    return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)


def _bell(f0, d, decay, partials=(1, 2.76, 5.40, 8.93), amps=(1, 0.5, 0.25, 0.12)):
    t = _t(d)
    return sum(a * np.sin(2 * np.pi * f0 * p * t) * np.exp(-t * decay * (1 + 0.6 * i))
               for i, (p, a) in enumerate(zip(partials, amps)))


def _norm(x, peak=0.8):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def _place(out, sig, at):
    s = int(SR * at)
    e = min(len(out), s + len(sig))
    out[s:e] += sig[: e - s]


def cash():
    """Cash register: drawer 'cha' + 'ching' bell + coin jingle."""
    out = np.zeros(int(SR * 1.6))
    cha = _bp(RNG.uniform(-1, 1, int(SR * 0.12)), 1500, 6000) * np.exp(-_t(0.12) * 30)
    _place(out, cha * 0.7, 0.0)
    drawer = _bp(RNG.uniform(-1, 1, int(SR * 0.18)), 300, 1500) * np.linspace(0.2, 1, int(SR * 0.18)) * np.exp(-_t(0.18) * 8)
    _place(out, drawer * 0.5, 0.06)
    _place(out, _bell(2093, 1.3, 3.2) * 0.6, 0.16)
    _place(out, _bell(3136, 0.9, 4.5) * 0.35, 0.18)
    for k in range(7):  # coins
        _place(out, _bell(RNG.uniform(4000, 6500), 0.12, 30, (1, 1.5), (1, 0.4)) * 0.15, 0.25 + k * 0.05 + RNG.uniform(0, 0.03))
    return _norm(out)


def _knock(f_body=170):
    t = _t(0.18)
    click = _bp(RNG.uniform(-1, 1, len(t)), 1200, 5000) * np.exp(-t * 120)
    body = (np.sin(2 * np.pi * f_body * t) + 0.5 * np.sin(2 * np.pi * f_body * 2.4 * t)) * np.exp(-t * 28)
    return click * 0.6 + body


def gavel():
    out = np.zeros(int(SR * 1.0))
    _place(out, _knock(), 0.0)
    _place(out, _knock(160) * 1.1, 0.32)
    return _norm(out)


def stamp():
    """Rubber stamp: paper rustle + deep thump."""
    out = np.zeros(int(SR * 0.6))
    t = _t(0.3)
    thump = np.sin(2 * np.pi * (60 + 90 * np.exp(-t * 40)) * t) * np.exp(-t * 14)
    paper = _bp(RNG.uniform(-1, 1, len(t)), 2000, 8000) * np.exp(-t * 40) * 0.4
    _place(out, thump + paper, 0.02)
    return _norm(out)


def applause(d=2.2, density=55):
    out = np.zeros(int(SR * d))
    n = int(d * density)
    for _ in range(n):
        at = RNG.uniform(0, d - 0.05)
        c = _bp(RNG.uniform(-1, 1, int(SR * 0.012)), RNG.uniform(900, 1600), RNG.uniform(2500, 5000), 2)
        c *= np.exp(-_t(0.012) * 260) * RNG.uniform(0.3, 1.0)
        _place(out, c, at)
    env = np.minimum(1, _t(d) / 0.25) * np.minimum(1, (d - _t(d)) / 0.9)
    return _norm(out * env, 0.7)


def cheer(d=2.4):
    """Crowd cheer: vowel-ish formant noise swells + applause."""
    t = _t(d)
    noise = RNG.uniform(-1, 1, len(t))
    voices = _bp(noise, 350, 900) * 0.9 + _bp(noise, 1000, 1800) * 0.5 + _bp(noise, 2200, 3200) * 0.25
    wobble = 1 + 0.25 * np.sin(2 * np.pi * 3.3 * t) * np.sin(2 * np.pi * 0.7 * t)
    env = np.minimum(1, t / 0.35) * np.minimum(1, (d - t) / 1.1)
    out = _norm(voices * wobble * env, 0.6) + applause(d, 70) * 0.8
    return _norm(out)


def chime():
    """Sparkly rising chime arpeggio (warm moments)."""
    out = np.zeros(int(SR * 1.6))
    for k, f in enumerate([1046.5, 1318.5, 1568, 2093, 2637]):
        _place(out, _bell(f, 0.9, 4, (1, 2.0, 3.0), (1, 0.3, 0.12)) * 0.5, k * 0.07)
    return _norm(out)


def drumroll(d=1.2):
    out = np.zeros(int(SR * (d + 0.5)))
    for k in range(int(d / 0.035)):
        hit = _bp(RNG.uniform(-1, 1, int(SR * 0.04)), 200, 3000) * np.exp(-_t(0.04) * 70)
        _place(out, hit * (0.4 + 0.6 * k / (d / 0.035)), k * 0.035)
    t = _t(0.5)
    crash = _bp(RNG.uniform(-1, 1, len(t)), 3000, 12000) * np.exp(-t * 5)
    _place(out, crash * 0.8, d)
    return _norm(out)


def boing():
    t = _t(0.45)
    f = 220 + 260 * np.exp(-t * 6) * (1 + 0.3 * np.sin(2 * np.pi * 18 * t))
    return _norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6))


def whoosh_up():
    t = _t(0.5)
    x = RNG.uniform(-1, 1, len(t))
    y = np.zeros_like(x)
    for i, (a, b) in enumerate([(300, 900), (900, 2500), (2500, 7000)]):
        seg = slice(int(len(x) * i / 3), int(len(x) * (i + 1) / 3))
        y[seg] = _bp(x, a, b)[seg]
    return _norm(y * np.sin(np.pi * t / 0.5) ** 2)


def ding():
    return _norm(_bell(1760, 1.0, 4, (1, 2.0, 3.0), (1, 0.3, 0.1)))


LIBRARY = dict(cash=cash, gavel=gavel, stamp=stamp, cheer=cheer, applause=applause, chime=chime,
               drumroll=drumroll, boing=boing, whoosh_up=whoosh_up, ding=ding)


def get(name):
    return LIBRARY.get(name, ding)()
