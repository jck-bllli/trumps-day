"""Original upbeat background loop, generated in code (no licensing issues).

124 BPM, C - G - Am - F, kick / clap / hats / bass / plucky chords / light arp,
with a sidechain 'pump' on every kick.
"""
import numpy as np

SR = 48000
BPM = 124
BEAT = 60 / BPM

NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def hz(name, octave):
    return 440.0 * 2 ** ((NOTE[name] + 12 * (octave + 1) - 69) / 12)


CHORDS = [("C", ["C", "E", "G"]), ("G", ["G", "B", "D"]), ("A", ["A", "C", "E"]), ("F", ["F", "A", "C"])]


def _env(n, attack, decay):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-t * decay)


def _kick():
    n = int(SR * 0.3)
    t = np.arange(n) / SR
    f = 50 + 110 * np.exp(-t * 35)
    phase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(phase) * np.exp(-t * 9) * 0.9


def _clap(rng):
    n = int(SR * 0.16)
    noise = rng.uniform(-1, 1, n)
    hp = noise - np.convolve(noise, np.ones(8) / 8, mode="same")
    return hp * _env(n, 0.002, 28) * 0.55


def _hat(rng):
    n = int(SR * 0.05)
    noise = rng.uniform(-1, 1, n)
    hp = noise - np.convolve(noise, np.ones(3) / 3, mode="same")
    return hp * _env(n, 0.001, 90) * 0.22


def _pluck(freqs, dur, vol, bright=4):
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for f in freqs:
        for detune in (-0.004, 0.004):
            ff = f * (1 + detune)
            for h in range(1, bright + 1):
                sig += np.sin(2 * np.pi * ff * h * t) / (h ** 1.6)
    return sig / (len(freqs) * 2) * _env(n, 0.004, 7) * vol


def _bass(f, dur):
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = sum(np.sin(2 * np.pi * f * h * t) / h ** 2 for h in range(1, 5))
    return sig * _env(n, 0.003, 6) * 0.45


def make_loop(seconds, seed=7):
    rng = np.random.default_rng(seed)
    n = int(SR * seconds)
    out = np.zeros(n + SR)
    pump = np.ones(n + SR)

    def add(sig, at):
        st = int(SR * at)
        if st >= len(out):
            return
        end = min(len(out), st + len(sig))
        out[st:end] += sig[: end - st]

    kick = _kick()
    beats = int(seconds / BEAT) + 1
    for b in range(beats):
        t0 = b * BEAT
        bar = b // 4
        root, triad = CHORDS[bar % 4]
        add(kick, t0)
        # sidechain pump
        st = int(SR * t0)
        L = int(SR * BEAT)
        seg = np.linspace(0, 1, L) ** 0.5
        pump[st: st + L] = np.minimum(pump[st: st + L], 0.45 + 0.55 * seg[: len(pump[st: st + L])])
        if b % 4 in (1, 3):
            add(_clap(rng), t0)
        add(_hat(rng), t0 + BEAT / 2)
        # bass on 8ths, octave jump on the offbeat
        add(_bass(hz(root, 2), BEAT / 2), t0)
        add(_bass(hz(root, 3), BEAT / 2), t0 + BEAT / 2)
        # syncopated chord stabs
        chord = [hz(x, 4) for x in triad]
        if b % 4 == 0:
            add(_pluck(chord, 0.5, 0.35), t0)
        if b % 4 in (1, 2):
            add(_pluck(chord, 0.35, 0.28), t0 + BEAT * 0.5)
        if b % 4 == 3:
            add(_pluck(chord, 0.35, 0.28), t0 + BEAT * 0.75)
        # light arp on 16ths
        arp = [hz(triad[i % 3], 5 + (i // 3)) for i in range(4)]
        for i, f in enumerate(arp):
            add(_pluck([f], 0.18, 0.08, bright=2), t0 + i * BEAT / 4)
    out = (out * pump)[:n]
    # fade in/out
    fade = int(SR * 0.4)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out / (np.max(np.abs(out)) + 1e-9) * 0.9
