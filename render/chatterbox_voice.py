"""Narrator voice: Chatterbox, alternating between two picks every two videos (Jack, 2026-11-04).
  "turbo" = Chatterbox Turbo default voice (audition clip 2)
  "hype"  = Chatterbox classic, exaggeration 0.95, cfg 0.3 (audition clip 6)
Built-in narrator voice only: never clone or imitate a real person."""
import os
import subprocess
import tempfile

import numpy as np
import soundfile as sf

VOICES = ("turbo", "hype")
SR = 48000
_models = {}


def voice_for(n):
    """Video number n -> voice. Two videos in one voice, then two in the other."""
    return VOICES[(n // 2) % 2]


def _load(voice):
    if voice not in _models:
        import perth  # its native watermarker fails to load on Windows; use the dummy one then
        if getattr(perth, "PerthImplicitWatermarker", None) is None:
            perth.PerthImplicitWatermarker = perth.DummyWatermarker
        import torch
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        if voice == "turbo":
            from chatterbox.tts_turbo import ChatterboxTurboTTS
            _models[voice] = ChatterboxTurboTTS.from_pretrained(device=dev)
        else:
            from chatterbox.tts import ChatterboxTTS
            _models[voice] = ChatterboxTTS.from_pretrained(device=dev)
    return _models[voice]


def say(text, voice):
    """Speak text in the given voice. Returns mono float32 at 48 kHz, trimmed."""
    m = _load(voice)
    if voice == "turbo":
        w = m.generate(text)
    else:
        w = m.generate(text, exaggeration=0.95, cfg_weight=0.3)
    y = w.squeeze().cpu().numpy().astype(np.float32)
    with tempfile.TemporaryDirectory() as td:
        sf.write(f"{td}/i.wav", y, m.sr)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{td}/i.wav", "-af",
                        "aresample=48000:resampler=soxr,highpass=f=70", "-ac", "1", f"{td}/o.wav"], check=True)
        a, _ = sf.read(f"{td}/o.wav", dtype="float32")
    i = np.where(np.abs(a) > 0.01)[0]
    return a[max(0, i[0] - 480): i[-1] + 3000] if len(i) else a
