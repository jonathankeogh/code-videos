"""Backing track + sound effects, synthesised from scratch with numpy.

Chiptune-pop at 120 BPM: supersaw pads, 16th-note chip arpeggios, bouncy bass,
four-on-the-floor choruses, plus the SFX in song.CUES (pitched to the chord).
Writes 48 kHz stereo stems to stems/: drums, bass, chords, lead, fx.
"""
import os

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

import song

SR = 48000
N = int((song.DURATION + 1.0) * SR)
HERE = os.path.dirname(os.path.abspath(__file__))
STEMS = os.path.join(HERE, "stems")
rng = np.random.default_rng(42)


def T(bar, beat=0.0):
    return bar * song.BAR + beat * song.BEAT


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


class Bus:
    def __init__(self):
        self.x = np.zeros((N, 2))

    def add(self, sig, t0, gain=1.0, pan=0.0):
        i0 = int(round(t0 * SR))
        if i0 >= N or len(sig) == 0:
            return
        if sig.ndim == 1:
            a = (pan + 1) * np.pi / 4
            sig = np.stack([sig * np.cos(a), sig * np.sin(a)], 1) * np.sqrt(2)
        if i0 < 0:
            sig = sig[-i0:]; i0 = 0
        n = min(len(sig), N - i0)
        self.x[i0:i0 + n] += gain * sig[:n]


# ---------------------------------------------------------------- oscillators
_tables = {}
_HARM_STEPS = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256]


def _table(kind, H):
    key = (kind, H)
    if key not in _tables:
        L = 4096
        ph = np.arange(L) / L
        y = np.zeros(L)
        for k in range(1, H + 1):
            if kind == "saw":
                a = 1.0 / k
            elif kind == "square":
                a = 1.0 / k if k % 2 else 0.0
            elif kind == "pulse25":
                a = np.sin(np.pi * k * 0.25) / k
            elif kind == "pulse12":
                a = np.sin(np.pi * k * 0.125) / k
            elif kind == "tri":
                a = ((-1) ** ((k - 1) // 2)) / k ** 2 if k % 2 else 0.0
            else:
                a = 1.0 if k == 1 else 0.0
            y += a * np.sin(2 * np.pi * k * ph)
        y /= np.abs(y).max()
        _tables[key] = np.append(y, y[0])
    return _tables[key]


def osc(kind, freq, n, cents=0.0, vib_rate=0.0, vib_cents=0.0, phase0=None):
    """Band-limited wavetable oscillator. freq may be a scalar or per-sample array."""
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,)) * 2 ** (cents / 1200.0)
    if vib_cents:
        t = np.arange(n) / SR
        f = f * 2 ** (vib_cents * np.sin(2 * np.pi * vib_rate * t) / 1200.0)
    H = int(18000 / max(f.max(), 20))
    Hq = max([h for h in _HARM_STEPS if h <= max(H, 1)])
    tb = _table(kind, Hq)
    p0 = rng.random() if phase0 is None else phase0
    ph = (p0 + np.cumsum(f) / SR) % 1.0
    return np.interp(ph * (len(tb) - 1), np.arange(len(tb)), tb)


def env(dur, a=0.005, d=0.15, s=0.7, r=0.12):
    """Attack/decay/sustain for `dur` seconds, then an exponential release tail."""
    n = int((dur + r) * SR)
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    k = min(int(dur * SR), n - 1)
    rel = t >= dur
    e[rel] = e[k] * np.exp(-(t[rel] - dur) / max(r / 5, 1e-4))
    return e


def perc(dur, tau, a=0.001):
    t = np.arange(int(dur * SR)) / SR
    return np.minimum(t / a, 1.0) * np.exp(-t / tau)


def filt(x, kind, fc, order=2):
    if kind == "bp":
        sos = butter(order, [max(fc[0], 20), min(fc[1], SR / 2 - 100)], "bandpass", fs=SR, output="sos")
    else:
        sos = butter(order, min(fc, SR / 2 - 100), {"lp": "lowpass", "hp": "highpass"}[kind], fs=SR, output="sos")
    if x.ndim == 2:
        return np.stack([sosfilt(sos, x[:, 0]), sosfilt(sos, x[:, 1])], 1)
    return sosfilt(sos, x)


def noise(n):
    return rng.standard_normal(n)


# ---------------------------------------------------------------- drums
def kick(v=1.0):
    n = int(0.5 * SR); t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t / 0.028)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.32)
    click = filt(noise(n), "hp", 2500) * np.exp(-t / 0.004) * 0.35
    return np.tanh(1.6 * (body + click)) * v


def snare(v=1.0):
    n = int(0.32 * SR); t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.06) * 0.7
    nz = filt(noise(n), "bp", (1200, 9000)) * np.exp(-t / 0.11)
    return (tone + nz * 1.1) * v


def clap(v=1.0):
    n = int(0.35 * SR); t = np.arange(n) / SR
    e = np.zeros(n)
    for d in (0.0, 0.011, 0.023):
        e += np.where(t >= d, np.exp(-(t - d) / 0.006), 0)
    e += np.where(t >= 0.03, 0.55 * np.exp(-(t - 0.03) / 0.13), 0)
    return filt(noise(n), "bp", (900, 3200)) * e * 1.4 * v


def hat(v=1.0, open_=False):
    n = int((0.4 if open_ else 0.09) * SR); t = np.arange(n) / SR
    metal = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (3140, 4270, 5510, 6810)) * 0.12
    x = filt(noise(n) + metal, "hp", 7000)
    return x * np.exp(-t / (0.21 if open_ else 0.028)) * v


def crash(v=1.0, dur=2.2):
    n = int(dur * SR); t = np.arange(n) / SR
    metal = sum(np.sin(2 * np.pi * f * t + rng.random() * 6) for f in (2310, 3190, 4870, 6230, 7710, 9120)) * 0.15
    x = filt(noise(n) * 0.9 + metal, "hp", 4200)
    return x * np.minimum(t / 0.002, 1) * np.exp(-t / 0.85) * v


# ---------------------------------------------------------------- tonal instruments
VOICING = {
    "C": [60, 64, 67, 72], "Am": [57, 60, 64, 69], "F": [57, 60, 65, 69], "G": [59, 62, 67, 71],
    "Em": [59, 64, 67, 71], "Dm": [57, 62, 65, 69], "Fm": [56, 60, 65, 68],
}
VOICING_LUSH = {   # chorus colours (royal road with 7ths)
    "F": [53, 57, 60, 64], "G": [55, 59, 62, 65], "Em": [55, 59, 62, 64], "Am": [55, 60, 64, 69],
    "C": [55, 60, 64, 67],
}
ROOT = {"C": 36, "Dm": 38, "Em": 40, "F": 41, "G": 43, "Am": 33, "Fm": 41,
        "D": 38, "A": 33, "F#m": 42, "Bm": 35, "Gm": 43}
VOICING.update({"D": [62, 66, 69, 74], "A": [61, 64, 69, 73], "F#m": [61, 66, 69, 73],
                "Bm": [62, 66, 71, 74], "Gm": [62, 67, 70, 74]})
VOICING_LUSH_D = {   # final chorus colours after the key change
    "G": [55, 59, 62, 66], "A": [57, 61, 64, 67], "D": [57, 62, 66, 69], "F#m": [57, 61, 64, 66], "Bm": [57, 62, 66, 71],
}


def section_of(bar):
    for name, a, b in song.SECTIONS:
        if a <= bar < b:
            return name
    return "tag"


def supersaw(m, dur, bright=4000, a=0.03, r=0.35, detune=11.0):
    n = int((dur + r) * SR)
    e = env(dur, a=a, d=0.4, s=0.85, r=r)[:n]
    L = sum(osc("saw", hz(m), n, cents=c) for c in (-detune, 0.0, detune * 0.6)) / 3
    R = sum(osc("saw", hz(m), n, cents=c) for c in (-detune * 0.7, 0.0, detune)) / 3
    x = np.stack([L, R], 1) * e[:, None]
    return filt(x, "lp", bright)


def pluck(m, v=1.0, kind="saw", dur=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    x = osc(kind, hz(m), n)
    bright = filt(x, "lp", 6500) * np.exp(-t / 0.045)
    dark = filt(x, "lp", 1400) * np.exp(-t / 0.2)
    return (0.6 * bright + dark) * np.minimum(t / 0.002, 1) * v


def chip(m, dur, v=1.0, kind="pulse25"):
    n = int((dur + 0.05) * SR)
    e = env(dur, a=0.002, d=0.08, s=0.45, r=0.05)[:n]
    return osc(kind, hz(m), n, vib_rate=6.0, vib_cents=8) * e * v


def bass_note(m, dur, v=1.0):
    n = int((dur + 0.06) * SR); t = np.arange(n) / SR
    e = env(dur, a=0.004, d=0.12, s=0.75, r=0.06)[:n]
    body = filt(osc("square", hz(m), n), "lp", 900 + 1600 * np.exp(-0.0)) * 0.55
    sub = np.sin(2 * np.pi * hz(m) * t) * 0.8
    return np.tanh(1.3 * (body + sub)) * e * v


def bell(m, dur=1.6, v=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    f = hz(m)
    parts = [(1.0, 1.0, 1.0), (2.0, 0.35, 0.6), (2.76, 0.5, 0.45), (5.4, 0.25, 0.25), (8.93, 0.12, 0.15)]
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (dur * d)) for r, a, d in parts)
    return x * np.minimum(t / 0.001, 1) * v * 0.5


# ---------------------------------------------------------------- SFX
def sfx(kind, t0, label):
    bar = int(t0 // song.BAR)
    chord = song.CHORDS[min(bar, len(song.CHORDS) - 1)]
    tones = VOICING[chord]
    if kind == "boing":
        n = int(0.7 * SR); t = np.arange(n) / SR
        f = 220 * (1 + 0.9 * t) * (1 + 0.28 * np.sin(2 * np.pi * 13 * t) * np.exp(-t / 0.3))
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.3)
        return [(x * 0.5, 0.0, 0.0)]
    if kind == "pop":
        idx = {"n-east": 0, "n-north": 1, "n-west": 2, "n-south": 3}.get(label, 0)
        if label.startswith("gang"):
            idx = int(label[4]) - 1 if label[4].isdigit() else 0
        m = tones[idx % 4] + 24 if label != "wink" else 84
        n = int(0.18 * SR); t = np.arange(n) / SR
        f = hz(m) * (0.55 + 0.45 * np.minimum(t / 0.03, 1))
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.06)
        return [(x * 0.45, 0.0, [-0.5, 0.4, -0.2, 0.6][idx % 4])]
    if kind == "whoosh":
        n = int(0.7 * SR); t = np.arange(n) / SR
        nz = noise(n)
        out = np.zeros(n)
        blk = 1024
        for i in range(0, n, blk):   # swept band-pass, block-wise
            fc = 300 * (12 ** (i / n))
            seg = filt(nz[max(0, i - 2048):i + blk], "bp", (fc * 0.6, fc * 1.6))
            out[i:i + blk] = seg[-min(blk, n - i):]
        e = np.sin(np.pi * np.clip(t / 0.7, 0, 1)) ** 2
        x = out * e
        pan = np.linspace(-0.7, 0.7, n)
        st = np.stack([x * np.cos((pan + 1) * np.pi / 4), x * np.sin((pan + 1) * np.pi / 4)], 1) * 1.4
        return [(st * 0.35, -0.35, None)]
    if kind == "sparkle":
        out = []
        for i, m in enumerate([tones[0] + 24, tones[1] + 24, tones[2] + 24, tones[3] + 24, tones[1] + 36]):
            out.append((bell(m, 1.0, 0.35), i * 0.055, [-0.6, -0.2, 0.2, 0.6, 0.0][i]))
        return out
    if kind == "ding":
        return [(bell(tones[-1] + 12, 1.8, 0.55), 0.0, 0.0)]
    if kind == "bell":
        return [(bell(67, 3.0, 0.5), 0.0, 0.0), (bell(79, 2.4, 0.25), 0.0, 0.0)]
    if kind == "chime":
        return [(bell(m, 1.4, 0.22), i * 0.04, (i - 2) * 0.3) for i, m in enumerate([88, 91, 95, 96, 100])]
    if kind in ("slide_down", "slide_up"):
        n = int(1.5 * SR); t = np.arange(n) / SR
        a, b = (hz(84), hz(69)) if kind == "slide_down" else (hz(67), hz(86))
        f = a * (b / a) ** (t / 1.5) * 2 ** (25 * np.sin(2 * np.pi * 6 * t) / 1200)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.08 * filt(noise(n), "bp", (1500, 5000))
        e = np.minimum(t / 0.05, 1) * np.minimum((1.5 - t) / 0.15, 1)
        return [(x * e * 0.28, 0.0, 0.0)]
    if kind == "womp":
        n = int(0.9 * SR); t = np.arange(n) / SR
        f = hz(46) * 2 ** (-2.5 * t / 12)
        x = osc("saw", f, n)
        y = np.zeros(n)
        blk = 512
        for i in range(0, n, blk):
            fc = 300 + 1400 * np.sin(np.pi * min(i / n * 1.2, 1)) ** 2
            y[i:i + blk] = filt(x[max(0, i - 2048):i + blk], "lp", fc)[-min(blk, n - i):]
        return [(y * np.exp(-t / 0.45) * 0.55, 0.0, 0.0)]
    if kind == "riser":
        dur = 2.0
        n = int(dur * SR); t = np.arange(n) / SR
        nz = noise(n); y = np.zeros(n); blk = 1024
        for i in range(0, n, blk):
            fc = 400 * (16 ** (i / n))
            y[i:i + blk] = filt(nz[max(0, i - 2048):i + blk], "bp", (fc * 0.7, fc * 1.4))[-min(blk, n - i):]
        sweep = np.sin(2 * np.pi * np.cumsum(200 * (8 ** (t / dur))) / SR) * 0.25
        e = (t / dur) ** 2.2
        return [((y * 0.5 + sweep) * e * 0.5, 0.0, 0.0)]
    if kind == "impact":
        n = int(1.4 * SR); t = np.arange(n) / SR
        f = 30 + 60 * np.exp(-t / 0.08)
        sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.5)
        nz = filt(noise(n), "lp", 2500) * np.exp(-t / 0.08) * 0.5
        return [(np.tanh(1.5 * (sub + nz)) * 0.8, 0.0, 0.0), (crash(0.7), 0.0, 0.0)]
    if kind == "crash":
        return [(crash(0.8), 0.0, 0.0)]
    if kind == "roll":
        out = []
        for i in range(8):
            out.append((snare(0.25 + 0.6 * i / 7), i * song.SLOT / 2, 0.0))
        return out
    if kind == "sizzle":
        n = int(1.0 * SR); t = np.arange(n) / SR
        crackle = (rng.random(n) > 0.9965).astype(float)
        crackle = np.convolve(crackle, np.exp(-np.arange(200) / 30), mode="same")
        x = filt(noise(n), "hp", 3000) * (0.3 + crackle) * np.sin(np.pi * t / 1.0) ** 0.5
        return [(x * 0.3, 0.0, 0.3)]
    if kind == "zap":
        n = int(0.4 * SR); t = np.arange(n) / SR
        f = 1800 * np.exp(-t / 0.12) + 120 + 300 * rng.standard_normal(n).cumsum() / np.sqrt(n)
        x = osc("square", np.abs(f), n) * np.exp(-t / 0.15)
        return [(filt(x, "hp", 300) * 0.3, 0.0, -0.3)]
    if kind == "scratch":
        n = int(0.4 * SR); t = np.arange(n) / SR
        f = 900 * (1 + 0.7 * np.sin(2 * np.pi * 7 * t))
        x = filt(noise(n), "bp", (500, 3500)) * 0.4 + 0.3 * osc("saw", f, n)
        return [(filt(x, "bp", (300, 5000)) * np.exp(-t / 0.2) * 0.25, 0.0, 0.0)]
    if kind == "revcymbal":
        c = crash(0.8, dur=1.0)[::-1]
        return [(c * np.linspace(0, 1, len(c)) ** 2, 0.0, 0.0)]
    raise ValueError(kind)


def make_ir(rt60=1.5, predelay=0.018):
    n = int(rt60 * 1.3 * SR); t = np.arange(n) / SR
    base = noise(n * 2).reshape(n, 2)
    bright = filt(base, "lp", 7000)
    dark = filt(base, "lp", 1800)
    w = np.exp(-t / 0.35)[:, None]
    ir = (bright * w + dark * (1 - w)) * np.exp(-6.9 * t / rt60)[:, None]
    ir[: int(predelay * SR)] = 0
    return ir / np.sqrt(np.sum(ir ** 2) / 2)


def main():
    import json
    os.makedirs(STEMS, exist_ok=True)
    drums, bass, chords, lead, fx = Bus(), Bus(), Bus(), Bus(), Bus()
    kick_times = []

    def K(bar, beat, v=1.0):
        drums.add(kick(v), T(bar, beat)); kick_times.append(round(T(bar, beat), 3))

    stop_bars = {int(a // song.BAR) for a, b in song.STOPS}
    gang_hits = {}   # bar -> syllable start times of the shouted lines (for stabs)
    for ln in song.lines():
        if ln["role"] == "gang" and ln["base_id"] in ("v1f", "v1h"):
            for s_ in ln["syllables"]:
                gang_hits.setdefault(int(s_["start"] // song.BAR), []).append(s_["start"])

    for bar in range(song.TOTAL_BARS):
        sec = section_of(bar)
        ch = song.CHORDS[bar]
        t0 = T(bar)
        root = ROOT[ch]
        key_d = bar >= 30
        full = sec in ("cold", "chorus", "final")
        dance = sec in ("post", "post2")
        stop = bar in stop_bars
        breakdown = sec == "verse2" and bar in (26, 27)
        lush = (VOICING_LUSH_D if key_d else VOICING_LUSH)
        voic = (lush if (full or dance) else VOICING).get(ch, VOICING[ch])

        # ================= drums
        if full or dance:
            first = 2 if stop else 0          # stop-time: silent until beat 3 ("YOU!")
            for b in range(first, 4):
                K(bar, b, 1.0)
            for b in (1, 3):
                if b >= first:
                    drums.add(snare(0.75), T(bar, b)); drums.add(clap(0.6), T(bar, b), pan=0.1)
            if dance:
                for b in (0, 2):
                    drums.add(clap(0.5), T(bar, b), pan=-0.15)
            for i in range(4):
                if i + 0.5 >= first:
                    drums.add(hat(0.45, open_=True), T(bar, i + 0.5), pan=0.25)
            for i in range(16):
                if i * 0.25 >= first:
                    drums.add(hat(0.18 if i % 2 else 0.26), T(bar, i * 0.25), pan=-0.3)
            if stop:
                drums.add(clap(0.8), T(bar, 2), pan=0.0)
            if sec == "chorus" and bar == 15 or sec == "final" and bar == 32:
                for b in (3.0, 3.25, 3.5, 3.75):
                    drums.add(snare(0.3 + 0.1 * (b - 3) * 4), T(bar, b))
        elif sec == "talk":
            for i in range(8):
                drums.add(hat(0.3 if i % 2 else 0.42), T(bar, i * 0.5), pan=0.25)
            K(bar, 0, 0.7)
            if bar == 3:
                K(bar, 2, 0.7)
        elif sec in ("verse1", "verse2") and not breakdown:
            for b in (0, 1.5, 2):
                K(bar, b, 0.95)
            for b in (1, 3):
                drums.add(snare(0.7), T(bar, b)); drums.add(clap(0.35), T(bar, b), pan=-0.1)
            for i in range(8):
                drums.add(hat(0.5 if i % 2 == 0 else 0.32), T(bar, i * 0.5), pan=0.3)
            for tt in gang_hits.get(bar, []):      # claps land on every shouted syllable
                drums.add(clap(0.7), tt, pan=0.0)
            if bar == 11:
                for i, b in enumerate((3.5, 3.625, 3.75, 3.875)):
                    drums.add(snare(0.35 + 0.15 * i), T(bar, b))
        elif breakdown:
            for i in range(8):
                drums.add(hat(0.3 if i % 2 else 0.4), T(bar, i * 0.5), pan=0.3)
            if bar == 27:
                for b in (2, 2.5, 3, 3.25, 3.5, 3.75):
                    K(bar, b, 0.55)
        elif sec == "build":
            for b in (0, 1, 2, 3):
                K(bar, b, 0.9)
            for i in range(14):                    # 16th snare roll, crescendo, gap before the drop
                drums.add(snare(0.2 + 0.6 * i / 13), T(bar, i * 0.25), pan=0.0)
        elif sec == "tag":
            if bar == 38:
                for b in (3.0, 3.25, 3.5, 3.75):
                    drums.add(snare(0.25 + 0.12 * (b - 3) * 4), T(bar, b))
            if bar == 39:
                K(bar, 0, 1.0)

        # ================= bass
        if full or dance:
            if stop:
                bass.add(bass_note(root, song.BAR * 0.48, 0.85), T(bar, 2))
            else:
                for i, off in enumerate([0, 12, 0, 12, 0, 12, 0, 12]):
                    bass.add(bass_note(root + off, song.SLOT * 0.8, 0.8 if i % 2 == 0 else 0.62), T(bar, i * 0.5))
        elif sec == "talk":
            bass.add(bass_note(root, song.BAR * 0.9, 0.5), t0)
        elif breakdown or sec == "tag" and bar in (37, 38):
            bass.add(bass_note(root, song.BAR * 0.98, 0.6), t0)
        elif sec == "tag" and bar == 39:
            bass.add(bass_note(root, song.BAR * 1.9, 0.75), t0)
        elif sec == "build":
            for i in range(7):
                bass.add(bass_note(root, song.SLOT * 0.8, 0.4 + 0.4 * i / 6), T(bar, i * 0.5))
        elif sec in ("verse1", "verse2"):
            for i, off in enumerate([0, 0, 12, 0, 0, 0, 12, 0]):
                bass.add(bass_note(root + off, song.SLOT * 0.8, 0.8 if i % 2 == 0 else 0.62), T(bar, i * 0.5))

        # ================= chords
        if full:
            if stop:   # the "YOU!" chord: one big stab that rings to the end of the bar
                for m in voic:
                    chords.add(supersaw(m, song.BAR * 0.5, bright=5600, a=0.005, r=0.25), T(bar, 2), gain=0.16)
            else:
                for m in voic:
                    chords.add(supersaw(m, song.BAR * 0.98, bright=5200, a=0.02, r=0.3), t0, gain=0.13)
        elif dance:
            for m in voic:
                chords.add(supersaw(m, song.BAR, bright=1800, a=0.05, r=0.3), t0, gain=0.07)
            for b in (0.5, 1.5, 2.5, 3.5):         # pumping off-beat stabs
                for m in voic:
                    chords.add(supersaw(m, 0.16, bright=6000, a=0.003, r=0.08), T(bar, b), gain=0.12)
        elif sec == "talk":
            for m in VOICING[ch]:
                chords.add(supersaw(m, song.BAR, bright=1700, a=0.15, r=0.4), t0, gain=0.08)
        elif breakdown:
            for m in voic:
                chords.add(supersaw(m, song.BAR, bright=1600, a=0.3, r=0.6), t0, gain=0.12)
        elif sec == "build":
            for m in VOICING["A"]:
                chords.add(supersaw(m, song.BAR * 0.86, bright=3200, a=1.4, r=0.05), t0, gain=0.13)
        elif sec == "tag":
            if bar == 37:
                for m in VOICING["Gm"]:
                    chords.add(supersaw(m, song.BAR, bright=1800, a=0.5, r=0.4), t0, gain=0.12)
            elif bar == 38:   # dominant swell under "har-mooo-"
                for m in [57, 61, 64, 67]:
                    chords.add(supersaw(m, song.BAR, bright=2600, a=0.6, r=0.15), t0, gain=0.12)
            elif bar == 39:   # the "-nic!" resolution: big D add9
                for m in [50, 57, 62, 66, 69, 76]:
                    chords.add(supersaw(m, song.BAR * 1.5, bright=4200, a=0.01, r=1.2), t0, gain=0.10)
                for i, m in enumerate([74, 78, 81, 86, 90]):
                    lead.add(bell(m, 2.2, 0.16), t0 + i * 0.09, pan=(i - 2) * 0.3)
        else:  # verses: soft pad + off-beat plucks, stabs on the gang shouts
            for m in voic:
                chords.add(supersaw(m, song.BAR, bright=1300, a=0.2, r=0.4), t0, gain=0.05)
            for b in (0.5, 1.5, 2.5, 3.5):
                for j, m in enumerate(voic[:3]):
                    chords.add(pluck(m + 12, 0.16), T(bar, b), pan=[-0.4, 0.0, 0.4][j])
            for tt in gang_hits.get(bar, []):
                for m in voic:
                    chords.add(supersaw(m + 12, 0.22, bright=6500, a=0.003, r=0.1), tt, gain=0.1)

        # ================= chip arpeggios / lead colour
        up = [voic[0], voic[1], voic[2], voic[3], voic[0] + 12, voic[3], voic[2], voic[1]]
        if (full or dance) and not stop:
            for i in range(16):
                lead.add(chip(up[i % 8] + 12, 0.25 * song.BEAT * 0.7, 0.16, kind="pulse12"),
                         T(bar, i * 0.25), pan=0.35 if i % 2 else -0.35)
        if sec == "talk":
            for i in range(8):
                lead.add(chip(up[i % 8] + 12, 0.5 * song.BEAT * 0.7, 0.1, kind="pulse25"),
                         T(bar, i * 0.5), pan=0.35 if i % 2 else -0.35)
        if sec == "verse2" and not breakdown:
            for i in range(16):
                if rng.random() < 0.3:
                    m = voic[rng.integers(0, 4)] + 24
                    lead.add(pluck(m, 0.10, kind="sine", dur=0.2), T(bar, i * 0.25), pan=rng.uniform(-0.7, 0.7))
        if breakdown:
            for i, m in enumerate([voic[0] + 24, voic[2] + 24, voic[1] + 24, voic[3] + 24]):
                lead.add(bell(m, 1.4, 0.18), T(bar, i), pan=(i - 1.5) * 0.3)

    # soft synth doubling the sung hook/chant melodies (helps the pitch read)
    for ln in song.lines():
        dbl = (ln["role"] == "lead" and ln["base_id"][:2] in ("co", "c1", "f1", "p1", "p2", "t1", "t2")) or \
              (ln["role"] == "gang" and ln["base_id"] in ("p1b", "p2b", "v1f", "v1h"))
        if not dbl:
            continue
        for s_ in ln["syllables"]:
            lead.add(chip(s_["midi"] + 12, s_["dur"] * 0.92, 0.07, kind="tri"), s_["start"])

    # ================= sound effects
    for t0, kind, label in song.CUES:
        for sig, dt, pan in sfx(kind, t0, label):
            if pan is None:
                fx.add(sig, t0 + dt)
            else:
                fx.add(sig, t0 + dt, pan=pan)

    # ================= sidechain duck on pads/bass/arps from the kick
    duck = np.ones(N)
    for tk in kick_times:
        i0 = int(tk * SR); n = int(0.35 * SR)
        t = np.arange(n) / SR
        d = 1 - 0.55 * np.minimum(t / 0.004, 1) * np.exp(-t / 0.13)
        seg = duck[i0:i0 + n]
        duck[i0:i0 + len(seg)] = np.minimum(seg, d[:len(seg)])
    chords.x *= duck[:, None]
    bass.x *= (0.35 + 0.65 * duck)[:, None]
    lead.x *= (0.4 + 0.6 * duck)[:, None]

    # ================= reverb (send)
    from scipy.signal import fftconvolve
    ir = make_ir()
    for bus, send in ((chords, 0.28), (lead, 0.35), (fx, 0.25), (drums, 0.06)):
        wet = np.stack([fftconvolve(bus.x[:, 0], ir[:, 0])[:N], fftconvolve(bus.x[:, 1], ir[:, 1])[:N]], 1)
        bus.x += send * wet

    for name, bus in (("drums", drums), ("bass", bass), ("chords", chords), ("lead", lead), ("fx", fx)):
        fade = np.ones(N)
        e0 = int((song.DURATION - 0.6) * SR)
        fade[e0:] = np.linspace(1, 0, N - e0) ** 2
        bus.x *= fade[:, None]
        peak = np.abs(bus.x).max()
        sf.write(os.path.join(STEMS, f"{name}.wav"), bus.x.astype(np.float32), SR, subtype="FLOAT")
        print(f"{name:7s} peak {20 * np.log10(peak + 1e-9):6.1f} dBFS")
    with open(os.path.join(STEMS, "kicks.json"), "w") as f:
        json.dump(sorted(set(kick_times)), f)
    print("kicks", len(kick_times))


if __name__ == "__main__":
    main()
