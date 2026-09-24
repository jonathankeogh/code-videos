"""Mix the stems into the master track and export timing data for the composition.

  stems/*.wav  ->  ../assets/audio/laplacian-song.wav      (48 kHz / 24-bit, ~-14 LUFS)
  stems/vocal_timing.json + song.CUES  ->  ../assets/data/song-data.js  (window.SONG)
"""
import json
import os

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.signal import butter, fftconvolve, lfilter, sosfilt

import song
from music import make_ir

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
STEMS = os.path.join(HERE, "stems")
PROJECT = os.path.dirname(HERE)
OUT_AUDIO = os.path.join(PROJECT, "assets", "audio", "laplacian-song.wav")
OUT_DATA = os.path.join(PROJECT, "assets", "data", "song-data.js")
meter = pyln.Meter(SR)


def load(name):
    x, sr = sf.read(os.path.join(STEMS, name + ".wav"), dtype="float64")
    assert sr == SR, (name, sr)
    return x


def fit(x, n):
    if len(x) >= n:
        return x[:n]
    pad = [(0, n - len(x))] + [(0, 0)] * (x.ndim - 1)
    return np.pad(x, pad)


def stereo(m, p=0.0):
    a = (p + 1) * np.pi / 4
    return np.stack([m * np.cos(a), m * np.sin(a)], 1) * np.sqrt(2)


def sos(kind, f, order=2):
    return butter(order, f, kind, fs=SR, output="sos")


def peq(x, f0, gain_db, q=1.0):
    A = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]; a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)


def shelf_hi(x, f0, gain_db):
    A = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / 2 * np.sqrt(2)
    c = np.cos(w); sA = 2 * np.sqrt(A) * al
    b = [A * ((A + 1) + (A - 1) * c + sA), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sA)]
    a = [(A + 1) - (A - 1) * c + sA, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sA]
    return lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)


def compress(x, thr_db=-20.0, ratio=3.0, win=0.012, smooth=0.02):
    mono = x if x.ndim == 1 else x.mean(1)
    rms = np.sqrt(uniform_filter1d(mono ** 2, int(win * SR)) + 1e-12)
    lvl = 20 * np.log10(rms)
    gr = np.minimum(0.0, (thr_db - lvl) * (1 - 1 / ratio))
    gr = uniform_filter1d(gr, int(smooth * SR))
    g = 10 ** (gr / 20)
    return x * (g if x.ndim == 1 else g[:, None])


def limiter(x, ceiling_db=-1.0, look=0.004, release=0.09, hop=32):
    c = 10 ** (ceiling_db / 20)
    pk = np.abs(x).max(1)
    need = np.minimum(1.0, c / np.maximum(pk, 1e-9))
    la = int(look * SR)
    g = uniform_filter1d(minimum_filter1d(need, 2 * la + 1), la)
    # decimated release follower
    gd = g[::hop].copy()
    k = np.exp(-hop / (release * SR))
    out = np.empty_like(gd); cur = 1.0
    for i, v in enumerate(gd):
        cur = v if v < cur else cur * k + v * (1 - k)
        out[i] = cur
    g2 = np.minimum(np.interp(np.arange(len(g)), np.arange(len(gd)) * hop, out), g)
    return x * g2[:, None]


def lufs(x):
    return meter.integrated_loudness(x if x.ndim == 2 else stereo(x))


def gain_to(x, target):
    return x * 10 ** ((target - lufs(x)) / 20)


def main():
    n = int(song.DURATION * SR)
    V = {k: fit(load("vox_" + k), n) for k in ["lead", "double", "harm", "nbr0", "nbr1", "nbr2", "speech"]}
    M = {k: fit(load(k), n) for k in ["drums", "bass", "chords", "lead", "fx"]}

    # ---------------- vocal chain
    def chain(m, presence=2.5):
        y = sosfilt(sos("highpass", 95), m)
        y = peq(y, 330, -2.0, 1.0)
        y = peq(y, 3100, presence + 1.0, 0.9)
        y = shelf_hi(y, 7500, -2.5)
        y = sosfilt(sos("lowpass", 12500), y)
        return compress(y, -24, 3.0)

    lead = chain(V["lead"]); speech = chain(V["speech"], 1.5)
    dbl = chain(V["double"], 1.0); harm = chain(V["harm"], 1.0)
    nbr = [chain(V[f"nbr{i}"], 1.5) for i in range(3)]

    lead_st = gain_to(stereo(lead), -18.0)
    speech_st = gain_to(stereo(speech), -17.5)
    dbl_d = np.roll(dbl, int(0.017 * SR))
    dbl_st = gain_to(stereo(dbl, -0.65) + 0.8 * stereo(dbl_d, 0.65), -29.5)
    harm_st = gain_to(stereo(harm, 0.25) + 0.7 * stereo(np.roll(harm, int(0.011 * SR)), -0.35), -23.5)
    nbr_st = sum(gain_to(stereo(x, p), -24.0) for x, p in zip(nbr, (0.55, -0.55, 0.0)))

    sung = lead_st + dbl_st + harm_st + nbr_st
    # ping-pong 1/8 delay on the sung parts
    d = int(song.SLOT * SR)
    src = sosfilt(sos("bandpass", [500, 5000]), lead_st.mean(1))
    dl = np.zeros(n); dr = np.zeros(n)
    tap = src.copy()
    for i in range(1, 5):
        tap = np.roll(tap, d) * 0.38
        tap[:d * i] = 0
        (dl if i % 2 else dr)[:] += tap
    delay = np.stack([dl, dr], 1) * 0.14
    ir = make_ir(rt60=1.25, predelay=0.025)
    rv_send = sung * 0.22 + speech_st * 0.06 + nbr_st * 0.25
    verb = np.stack([fftconvolve(rv_send[:, c], ir[:, c])[:n] for c in (0, 1)], 1)
    vox = sung + speech_st + delay + 0.5 * verb
    vox_l = lufs(vox)

    # ---------------- music bus
    rel = {"drums": -3.0, "bass": -5.0, "chords": -7.0, "lead": -9.5, "fx": -6.5}
    mus = {k: gain_to(M[k], -23.0 + rel[k]) for k in M}
    # carve: duck pads/arps under the voice (up to ~3.5 dB)
    venv = uniform_filter1d(np.abs((lead + speech + 0.5 * harm)), int(0.06 * SR))
    venv = np.clip(venv / (np.percentile(venv[venv > 1e-4], 90) + 1e-9), 0, 1)
    duck = 1 - 0.3 * venv
    band = sos("bandpass", [700, 4200])
    for k in ("chords", "lead"):
        mid = np.stack([sosfilt(band, mus[k][:, c]) for c in (0, 1)], 1)
        # frequency-selective carve: the speech band of pads/arps drops ~9 dB under the voice
        mus[k] = (mus[k] - mid * 0.65 * venv[:, None]) * duck[:, None]
    music = sum(mus.values())
    music = gain_to(music, vox_l - 3.5)

    mix = vox + music
    mix = compress(mix, -14.0, 1.8, win=0.03, smooth=0.05)
    mix = gain_to(mix, -14.0)
    mix = limiter(mix, -1.0)
    mix = limiter(mix, -1.0)
    # tail fade
    f0 = int((song.DURATION - 0.8) * SR)
    mix[f0:] *= np.linspace(1, 0, n - f0)[:, None] ** 1.5
    os.makedirs(os.path.dirname(OUT_AUDIO), exist_ok=True)
    sf.write(OUT_AUDIO, mix.astype(np.float32), SR, subtype="PCM_24")
    print(f"master: {lufs(mix):.1f} LUFS, peak {20 * np.log10(np.abs(mix).max()):.2f} dBFS, "
          f"vocals {vox_l:.1f} LUFS, len {n / SR:.1f}s -> {OUT_AUDIO}")

    # ---------------- timing data for the composition
    fps = 30
    hopn = SR // fps

    def env(x):
        m = x if x.ndim == 1 else x.mean(1)
        r = np.sqrt(np.array([np.mean(m[i * hopn:(i + 1) * hopn] ** 2) for i in range(len(m) // hopn)]))
        ref = np.percentile(r[r > 1e-4], 95) if (r > 1e-4).any() else 1.0
        return [round(float(v), 2) for v in np.clip(r / ref, 0, 1)]

    timing = json.load(open(os.path.join(STEMS, "vocal_timing.json")))
    data = dict(
        bpm=song.BPM, beat=song.BEAT, bar=song.BAR, duration=song.DURATION,
        sections=[dict(name=a, start=b * song.BAR, end=c * song.BAR) for a, b, c in song.SECTIONS],
        chords=song.CHORDS,
        lines=timing["lines"], spoken=timing["spoken"],
        cues=[dict(t=t, kind=k, label=l) for t, k, l in song.CUES],
        env=dict(fps=fps, claude=env(V["lead"] + V["speech"] + 0.6 * V["harm"]),
                 neighbors=env(V["nbr0"] + V["nbr1"] + V["nbr2"])),
    )
    os.makedirs(os.path.dirname(OUT_DATA), exist_ok=True)
    with open(OUT_DATA, "w") as f:
        f.write("// Generated by audio-src/mix.py - timing for every sung syllable, cue and mouth envelope.\n")
        f.write("window.SONG = " + json.dumps(data, separators=(",", ":")) + ";\n")
    print("wrote", OUT_DATA, os.path.getsize(OUT_DATA), "bytes")


if __name__ == "__main__":
    main()
