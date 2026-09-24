"""QA for the sung vocals (I can't listen, so measure):
  - pitch accuracy per syllable (cents error vs. target note)
  - optional spectrogram PNG with the target melody overlaid
usage: analyze.py <vox.wav> <timing.json> [png_out] [t0 t1]
"""
import json
import sys

import numpy as np
import pyworld as pw
import soundfile as sf
from scipy.signal import resample_poly

import song

wav, tj = sys.argv[1], sys.argv[2]
png = sys.argv[3] if len(sys.argv) > 3 else None
x, sr = sf.read(wav)
if x.ndim > 1:
    x = x.mean(1)
x = resample_poly(x, 1, 2) if sr == 48000 else x
sr2 = 24000
timing = json.load(open(tj))
f0, t = pw.harvest(x.astype(np.float64), sr2, f0_floor=70, f0_ceil=1000, frame_period=5.0)

errs = []
for ln in timing["lines"]:
    if ln["role"] != "lead":
        continue
    row = []
    for s in ln["syllables"]:
        a, b = s["start"] + 0.03, s["vowel_end"] - 0.03
        m = (t >= a) & (t < b) & (f0 > 0)
        if m.sum() < 2:
            row.append(f'{s["text"]}:??')
            continue
        med = np.median(f0[m])
        c = 1200 * np.log2(med / song.midi_to_hz(s["midi"]))
        errs.append(abs(c))
        vf = m.sum() / max(((t >= a) & (t < b)).sum(), 1)
        row.append(f'{s["text"]}:{c:+.0f}c/{vf:.0%}v')
    print(ln["id"], " ".join(row))
if errs:
    e = np.array(errs)
    print(f"pitch error: median {np.median(e):.1f} cents, 95% {np.percentile(e, 95):.1f}, max {e.max():.1f}; n={len(e)}")

if png:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t0 = float(sys.argv[4]) if len(sys.argv) > 4 else 0
    t1 = float(sys.argv[5]) if len(sys.argv) > 5 else len(x) / sr2
    seg = x[int(t0 * sr2):int(t1 * sr2)]
    fig, ax = plt.subplots(2, 1, figsize=(16, 8), sharex=True)
    ax[0].specgram(seg, NFFT=1024, Fs=sr2, noverlap=768, cmap="magma", xextent=(t0, t1), vmin=-140)
    ax[0].set_ylim(0, 6000)
    ax[1].plot(t, np.where(f0 > 0, f0, np.nan), lw=1.5, label="sung f0")
    for ln in timing["lines"]:
        for s in ln["syllables"]:
            hz = song.midi_to_hz(s["midi"])
            ax[1].hlines(hz, s["start"], s["vowel_end"], colors="r", lw=3, alpha=0.5)
            ax[1].text(s["start"], hz * 1.03, s["text"], fontsize=8)
    ax[1].set_xlim(t0, t1)
    ax[1].set_ylim(150, 700)
    ax[1].set_yscale("log")
    plt.tight_layout()
    plt.savefig(png, dpi=70)
    print("wrote", png)
