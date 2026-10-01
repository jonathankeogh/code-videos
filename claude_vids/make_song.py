"""Build 'L-B-J (All the Way)' — backing track, autotuned rap verses, and sung
choruses from Kokoro TTS + WORLD vocoder. Writes the mix plus timing/mouth data
for the HyperFrames composition."""
import json
import os
import numpy as np
import soundfile as sf
import pyworld as pw
from scipy.signal import resample_poly, butter, sosfilt, lfilter, fftconvolve
from kokoro_onnx import Kokoro

os.chdir(os.path.dirname(os.path.abspath(__file__)))  # paths below are relative to this script

SR = 44100
VSR = 24000
BPM = 100
BEAT = 60 / BPM
BAR = 4 * BEAT
S8 = BEAT / 2
VOICE = "af_heart"
rng = np.random.default_rng(36)  # LBJ was the 36th president

OUT = "lbj/assets"
kok = Kokoro("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")

# ---------------------------------------------------------------- structure
SECTIONS = [
    ("intro", ["G", "D"]),
    ("v1", ["G", "C", "G", "D", "G", "C", "D", "G"]),
    ("ch1", ["G", "C", "D", "G"]),
    ("v2", ["G", "C", "G", "D", "Em", "C", "D", "G"]),
    ("ch2", ["G", "C", "D", "G"]),
    ("tag", ["G", "G", "G"]),
]
bars = []  # (section, chord, start)
t = 0.0
sec_start = {}
for name, chords in SECTIONS:
    sec_start[name] = t
    for c in chords:
        bars.append((name, c, t))
        t += BAR
SONG_END = t + 1.6 + 0.8
N = int(SONG_END * SR)

CHORDS = {  # bass root midi, fifth midi, chord tones
    "G": (43, 38, [55, 59, 62]),
    "C": (48, 43, [55, 60, 64]),
    "D": (38, 45, [54, 57, 62]),
    "Em": (40, 47, [52, 55, 59]),
}


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def nm(s):
    return NOTE[s[:-1]] + 12 * (int(s[-1]) + 1)


# ---------------------------------------------------------------- mix bus
mixL = np.zeros(N)
mixR = np.zeros(N)


def add(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    mixL[i : i + len(sig)] += sig * gain * l * 1.414
    mixR[i : i + len(sig)] += sig * gain * r * 1.414


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "hp", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "lp", fs=SR, output="sos"), x)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "bp", fs=SR, output="sos"), x)


# ---------------------------------------------------------------- instruments
def kick():
    n = int(0.35 * SR)
    tt = np.arange(n) / SR
    f = 45 + 95 * np.exp(-tt * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env_exp(n, 0.12) + 0.3 * rng.standard_normal(n) * env_exp(n, 0.004)


def snare():
    n = int(0.22 * SR)
    tt = np.arange(n) / SR
    body = np.sin(2 * np.pi * 185 * tt) * env_exp(n, 0.04)
    noise = bp(rng.standard_normal(n), 1200, 8000) * env_exp(n, 0.07)
    return 0.5 * body + 0.9 * noise


def clap():
    n = int(0.25 * SR)
    x = np.zeros(n)
    for k, d in enumerate([0, 0.011, 0.022]):
        i = int(d * SR)
        m = n - i
        x[i:] += rng.standard_normal(m) * env_exp(m, 0.012 if k < 2 else 0.08)
    return bp(x, 900, 5000)


def hat(open_=False):
    n = int((0.25 if open_ else 0.05) * SR)
    return hp(rng.standard_normal(n), 7000) * env_exp(n, 0.07 if open_ else 0.012)


def crash():
    n = int(2.2 * SR)
    return hp(rng.standard_normal(n), 4000) * env_exp(n, 0.6)


def pluck(freq, dur, bright=0.6, decay=0.996):
    n = int(dur * SR)
    P = max(2, int(round(SR / freq - 0.5)))
    x = np.zeros(n)
    burst = rng.uniform(-1, 1, P)
    burst = lfilter([bright], [1, -(1 - bright)], burst)
    x[:P] = burst
    a = np.zeros(P + 2)
    a[0] = 1
    a[P] = -decay / 2
    a[P + 1] = -decay / 2
    y = lfilter([1.0], a, x)
    fade = np.ones(n)
    k = min(n, int(0.02 * SR))
    fade[-k:] = np.linspace(1, 0, k)
    return y * fade / (np.max(np.abs(y)) + 1e-9)


def bass(freq, dur):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    saw = 2 * ((tt * freq) % 1) - 1
    tri = np.sin(2 * np.pi * freq * tt)
    y = lp(0.5 * saw + 0.8 * tri, 900)
    e = np.minimum(1, tt / 0.005) * env_exp(n, 0.35)
    return y * e


def lead(freq, dur):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * tt) * np.minimum(1, tt / 0.3)
    ph = 2 * np.pi * np.cumsum(freq * vib) / SR
    sq = np.sign(np.sin(ph)) * 0.5 + 0.5 * np.sin(ph)
    e = np.minimum(1, tt / 0.02) * np.minimum(1, (n - np.arange(n)) / (0.05 * SR))
    return lp(sq, 2600) * e


def riser(dur):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n)
    seg = 2048
    for i in range(0, n, seg):
        f = 400 + 6000 * (i / n) ** 2
        out[i : i + seg] = bp(x[i : i + seg], f, min(f * 2.5, 18000))
    return out * (tt / dur) ** 2


def whoosh(dur=0.6):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    e = np.sin(np.pi * tt / dur) ** 2
    return bp(rng.standard_normal(n), 800, 5000) * e


# ---------------------------------------------------------------- arrangement
KICK, SNARE, CLAP = kick(), snare(), clap()
HAT, OHAT, CRASH = hat(), hat(True), crash()

for bi, (sec, ch, b0) in enumerate(bars):
    root, fifth, tones = CHORDS[ch]
    local = int(round((b0 - sec_start[sec]) / BAR))
    stop_time = sec == "tag"
    vietnam = sec == "v2" and local in (4, 5)
    if sec == "intro" and local == 0:
        # banjo pickup alone
        pass
    elif stop_time:
        if local == 0:
            add(KICK, b0, 0.9)
            add(CRASH, b0, 0.35, 0.2)
            add(bass(mtof(root), 1.5), b0, 0.8)
            for k, m in enumerate(tones):
                add(pluck(mtof(m), 1.8, 0.5, 0.998), b0 + k * 0.012, 0.25, -0.3)
        if local == 99:
            add(KICK, b0, 1.0)
            add(CRASH, b0, 0.45)
            add(bass(mtof(root), 2.5), b0, 0.9)
            for k, m in enumerate(tones + [67, 71, 74]):
                add(pluck(mtof(m), 2.8, 0.5, 0.999), b0 + k * 0.018, 0.25, -0.3 + k * 0.1)
    else:
        for s in range(8):
            ts = b0 + s * S8
            if s in (0, 4) or (s == 3 and sec != "intro"):
                add(KICK, ts, 0.95 if s != 3 else 0.6)
            if s in (2, 6) and sec != "intro":
                add(SNARE, ts, 0.45)
                add(CLAP, ts, 0.35, 0.1)
            add(OHAT if s == 7 else HAT, ts, 0.12 if s % 2 else 0.18, 0.4)
            if vietnam:  # marching snare
                for q in range(2):
                    add(SNARE, ts + q * S8 / 2, 0.12, -0.2)
        # boom-chick bass
        add(bass(mtof(root), BEAT * 0.9), b0, 0.7)
        add(bass(mtof(fifth), BEAT * 0.9), b0 + 2 * BEAT, 0.65)
        if sec in ("ch1", "ch2"):
            add(bass(mtof(root + 12), S8 * 0.8), b0 + 3.5 * BEAT, 0.4)
        # guitar chick on 2 and 4
        for beat in (1, 3):
            for k, m in enumerate(tones):
                add(pluck(mtof(m), 0.25, 0.7, 0.985), b0 + beat * BEAT + k * 0.01, 0.16, -0.35)
    # banjo roll (intro, choruses, last verse bar)
    if sec in ("intro", "ch1", "ch2") or (sec in ("v1", "v2") and local in (0, 7)):
        pattern = [0, 1, 2, 3, 1, 2, 3, 1, 0, 2, 3, 1, 2, 3, 1, 2]
        banjo = [tones[0] + 12, tones[1] + 12, tones[2] + 12, tones[0] + 24]
        for s, p in enumerate(pattern):
            add(pluck(mtof(banjo[p]), 0.5, 0.85, 0.992), b0 + s * S8 / 2, 0.09, 0.45)

# section crashes / risers / whooshes
for name in ["v1", "ch1", "v2", "ch2"]:
    add(CRASH, sec_start[name], 0.3, -0.2)
    add(whoosh(0.7), sec_start[name] - 0.5, 0.25)
for name in ["ch1", "ch2"]:
    add(riser(BAR), sec_start[name] - BAR, 0.18)

# ---------------------------------------------------------------- vocals
vox = np.zeros(N)  # dry lead vocal (for mouth + main)
dbl = np.zeros(N)  # chorus double


import hashlib, os, pickle
os.makedirs(".cache", exist_ok=True)


def cached(key, fn):
    p = ".cache/" + hashlib.md5(repr(key).encode()).hexdigest() + ".pkl"
    if os.path.exists(p):
        return pickle.load(open(p, "rb"))
    v = fn()
    pickle.dump(v, open(p, "wb"))
    return v


def tts(text, speed=1.0, voice=VOICE):
    a, sr = cached(("tts", text, round(speed, 4), voice), lambda: kok.create(text, voice=voice, speed=speed, lang="en-us"))
    return trim(np.asarray(a, dtype=np.float64))


def trim(a, th=0.02):
    e = np.convolve(np.abs(a), np.ones(240) / 240, mode="same")
    idx = np.where(e > th * np.max(e))[0]
    if len(idx) == 0:
        return a
    return a[max(0, idx[0] - 120) : idx[-1] + 240]


def analyze(x):
    return cached(("world", hashlib.md5(x.tobytes()).hexdigest()), lambda: _analyze(x))


def _analyze(x):
    f0, tpos = pw.harvest(x, VSR, frame_period=5.0, f0_floor=70, f0_ceil=700)
    sp = pw.cheaptrick(x, f0, tpos, VSR)
    ap = pw.d4c(x, f0, tpos, VSR)
    return f0, sp, ap


def remap(f0, sp, ap, idx):
    idx = np.clip(idx, 0, len(f0) - 1)
    i0 = np.floor(idx).astype(int)
    i1 = np.minimum(i0 + 1, len(f0) - 1)
    w = (idx - i0)[:, None]
    sp2 = sp[i0] * (1 - w) + sp[i1] * w
    ap2 = ap[i0] * (1 - w) + ap[i1] * w
    f02 = f0[np.round(idx).astype(int)]
    return f02, np.ascontiguousarray(sp2), np.ascontiguousarray(ap2)


def to_sr(y):
    return resample_poly(y, 147, 80)


PENTA = np.array([7, 9, 11, 2, 4])


def autotune(f0):
    out = f0.copy()
    v = f0 > 0
    m = 69 + 12 * np.log2(f0[v] / 440)
    base = np.floor(m / 12) * 12
    cand = base[:, None] + np.concatenate([PENTA - 12, PENTA, PENTA + 12])[None, :]
    snapped = cand[np.arange(len(m)), np.argmin(np.abs(cand - m[:, None]), axis=1)]
    out[v] = mtof(snapped)
    return out


def rap_line(text, start, target=BAR - 0.3):
    d0 = len(tts(text)) / VSR
    speed = float(np.clip(d0 / target, 0.85, 1.45))
    x = tts(text, speed)
    d1 = len(x) / VSR
    r = float(np.clip(target / d1, 0.88, 1.12))
    f0, sp, ap = analyze(x)
    M = int(len(f0) * r)
    f0, sp, ap = remap(f0, sp, ap, np.linspace(0, len(f0) - 1, M))
    y = pw.synthesize(autotune(f0), sp, ap, VSR, 5.0)
    y = to_sr(y)
    y /= np.sqrt(np.mean(y**2)) + 1e-9
    i = int((start + 0.04) * SR)
    vox[i : i + len(y)] += y[: N - i] * 0.11
    return len(y) / SR


WORDFIX = {"L": "Ell", "B": "Bee", "J": "Jay", "ol'": "old"}


def sing_word(word, start, slots, notes, legato=0.92):
    notes = [nm(n) for n in notes]
    x = tts(WORDFIX.get(word, word), 1.0)
    f0, sp, ap = analyze(x)
    dur = slots * S8 * legato
    M = max(4, int(dur / 0.005))
    voiced = np.where(f0 > 0)[0]
    v0 = voiced[0] if len(voiced) else 0
    vend = voiced[-1] + 1 if len(voiced) else len(f0)
    onset = min(v0, int(M * 0.3))
    tail = min(len(f0) - vend, int(M * 0.15))
    body = M - onset - tail
    idx = np.concatenate([
        np.linspace(0, v0, onset, endpoint=False),
        np.linspace(v0, vend - 1, body),
        np.linspace(vend, len(f0) - 1, tail),
    ])
    f0, sp, ap = remap(f0, sp, ap, idx)
    # melody contour over the stretched body
    tgt = np.full(M, float(notes[0]))
    bstart = onset
    for k, n in enumerate(notes):
        a = bstart + int(k * body / len(notes))
        tgt[a:] = n
    k = 5  # ~25ms portamento
    tgt = np.convolve(np.pad(tgt, (k, k), mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), mode="valid")
    tt = np.arange(M) * 0.005
    vib = 0.25 * np.sin(2 * np.pi * 5.6 * tt) * np.clip((tt - 0.22) / 0.2, 0, 1)
    f0n = np.where(f0 > 0, mtof(tgt + vib), 0.0)
    # keep sustained vowels voiced through tiny harvest dropouts
    y = pw.synthesize(f0n, sp, ap, VSR, 5.0)
    y = to_sr(y)
    y /= np.sqrt(np.mean(y**2)) + 1e-9
    fade = min(len(y), int(0.015 * SR))
    y[-fade:] *= np.linspace(1, 0, fade)
    i = int(start * SR)
    vox[i : i + len(y)] += y[: N - i] * 0.10
    # detuned double
    f0d = np.where(f0 > 0, mtof(tgt + vib * 0.6 + 0.09), 0.0)
    yd = to_sr(pw.synthesize(f0d, sp, ap, VSR, 5.0))
    yd /= np.sqrt(np.mean(yd**2)) + 1e-9
    j = i + int(0.018 * SR)
    dbl[j : j + len(yd)] += yd[: N - j] * 0.05
    return notes


def speak(text, start, speed=1.0, gain=0.11):
    x = to_sr(tts(text, speed))
    x /= np.sqrt(np.mean(x**2)) + 1e-9
    i = int(start * SR)
    vox[i : i + len(x)] += x[: N - i] * gain
    return len(x) / SR


# ---------------------------------------------------------------- lyrics
V1 = [
    "November sixty-three, a dark day in Dallas.",
    "Sworn in on a plane, not a White House palace.",
    "Six foot four from Texas, gets right in your face.",
    "That's the Johnson Treatment! Congress, know your place!",
    "Sixty-four: the Civil Rights Act becomes the law.",
    "Then he crushed Goldwater, forty-four states in all!",
    "Sixty-five: the Voting Rights Act, for real.",
    "Protecting the ballot, now that's a big deal!",
]
V2 = [
    "War on Poverty! Head Start for the kids.",
    "Medicare, Medicaid, yeah, that's what he did.",
    "Opened up immigration, funded the schools.",
    "Named Thurgood Marshall, the first Black justice. Cool!",
    "But then, Vietnam. The war just grew and grew.",
    "Half a million troops, and the protests too.",
    "Sixty-eight, he says, I'm done. I will not run.",
    "Back to the Texas ranch. His presidency's done.",
]
# (word, slots in 8ths, notes) — melody sits in G major, G3..E4
CH_A = [
    [("L", 1, ["G3"]), ("B", 1, ["B3"]), ("J", 2, ["D4"]), ("all", 1, ["D4"]), ("the", 1, ["E4"]), ("way!", 2, ["D4"])],
    [("Great", 1, ["E4"]), ("Society,", 4, ["E4", "D4", "C4", "E4"]), ("hip", 1, ["C4"]), ("hooray!", 2, ["A3", "G3"])],
    [("L", 1, ["A3"]), ("B", 1, ["C4"]), ("J", 2, ["D4"]), ("what", 1, ["C4"]), ("can", 1, ["B3"]), ("I", 1, ["A3"]), ("say?", 1, ["F#3"])],
    [("Big", 1, ["B3"]), ("dreams", 1, ["D4"]), ("from", 1, ["D4"]), ("the", 1, ["B3"]), ("Lone", 1, ["B3"]), ("Star", 1, ["A3"]), ("way!", 2, ["G3"])],
]
CH_B = [
    CH_A[0],
    [("Big", 1, ["E4"]), ("wins,", 1, ["E4"]), ("big", 1, ["D4"]), ("war,", 1, ["C4"]), ("shades", 1, ["A3"]), ("of", 1, ["B3"]), ("gray.", 2, ["C4"])],
    CH_A[2],
    [("History's", 3, ["B3", "A3", "G3"]), ("complicated,", 4, ["B3", "D4", "D4", "B3"]), ("hey!", 1, ["G4"])],
]

timing = {"bpm": BPM, "bar": BAR, "sections": sec_start, "lines": [], "words": [], "end": SONG_END}

speak_intro = "Howdy, y'all! I'm Claude. And this... is L. B. J.!"
d = speak(speak_intro, 0.35, 1.05)
timing["lines"].append({"sec": "intro", "t": 0.35, "d": d, "text": speak_intro})

for sec, lines in (("v1", V1), ("v2", V2)):
    for i, line in enumerate(lines):
        st = sec_start[sec] + i * BAR
        d = rap_line(line, st)
        timing["lines"].append({"sec": sec, "i": i, "t": st, "d": d, "text": line})
        print(f"{sec}[{i}] {st:6.2f} {d:.2f}s  {line}")

melody_lead = []
for sec, chorus in (("ch1", CH_A), ("ch2", CH_B)):
    for li, line in enumerate(chorus):
        st = sec_start[sec] + li * BAR
        slot = 0
        text = []
        for w, slots, notes in line:
            ws = st + slot * S8
            ms = sing_word(w, ws, slots, notes)
            per = slots * S8 / len(ms)
            for k, m in enumerate(ms):
                melody_lead.append((ws + k * per, per, m))
            timing["words"].append({"sec": sec, "line": li, "t": ws, "d": slots * S8, "w": w})
            text.append(w)
            slot += slots
        timing["lines"].append({"sec": sec, "i": li, "t": st, "d": BAR, "text": " ".join(text)})

for ts, dd, m in melody_lead:  # whistle doubles the sung melody an octave up
    add(lead(mtof(m + 12), dd * 0.9), ts, 0.07, -0.25)

tag0 = sec_start["tag"]
tagA = "Fun fact! His wife, Lady Bird. His daughters, Lynda Bird and Luci Baines. All... L. B. J."
dA = speak(tagA, tag0 + 0.25, 1.1)
tB = tag0 + 0.25 + dA + 0.35
tagB = "Even the dog!"
dB = speak(tagB, tB, 1.0, 0.13)
HIT = tB + dB + 0.15
root, fifth, tones = CHORDS["G"]
add(KICK, HIT, 1.0)
add(CRASH, HIT, 0.45)
add(bass(mtof(root), 2.5), HIT, 0.9)
for k, m in enumerate(tones + [67, 71, 74]):
    add(pluck(mtof(m), 2.8, 0.5, 0.999), HIT + k * 0.018, 0.25, -0.3 + k * 0.1)
timing["hit"] = HIT
timing["lines"].append({"sec": "tag", "i": 0, "t": tag0 + 0.25, "d": dA, "text": tagA})
timing["lines"].append({"sec": "tag", "i": 1, "t": tB, "d": dB, "text": tagB})
print("tagA", tag0 + 0.25, dA, "tagB", tB, dB)

# ---------------------------------------------------------------- vocal chain + master
def vchain(x):
    x = hp(x, 110)
    x = x + 0.25 * bp(x, 2500, 6000)
    return x


vl = vchain(vox) * 1.8
dl = vchain(dbl) * 1.8
ir_n = int(1.3 * SR)
irL = rng.standard_normal(ir_n) * env_exp(ir_n, 0.28)
irR = rng.standard_normal(ir_n) * env_exp(ir_n, 0.28)
irL /= np.sqrt(np.sum(irL**2))
irR /= np.sqrt(np.sum(irR**2))
send = hp(vl + dl, 300)
revL = fftconvolve(send, irL)[:N] * 0.18
revR = fftconvolve(send, irR)[:N] * 0.18

# duck the band a touch under the vocal
venv = np.convolve(np.abs(vl), np.ones(2205) / 2205, mode="same")
duck = 1 - 0.4 * np.clip(venv / (np.percentile(venv, 99) + 1e-9), 0, 1)

L = mixL * duck + vl + dl * 1.1 + revL
R = mixR * duck + vl + dl * 0.9 + revR
st = np.stack([L, R], 1)
st /= np.max(np.abs(st))
st = np.tanh(st * 1.6) / np.tanh(1.6)
st *= 0.78 / np.max(np.abs(st))
fade = int(1.2 * SR)
st[-fade:] *= np.linspace(1, 0, fade)[:, None]
sf.write(f"{OUT}/lbj_song.wav", st, SR)
sf.write(".cache/vox_stem.wav", vox, SR)
sf.write(".cache/band_stem.wav", (mixL + mixR) / 2, SR)

# mouth envelope at 30fps from the dry vocal
fps = 30
hop = SR // fps
frames = int(SONG_END * fps)
env = np.array([np.sqrt(np.mean(vox[i * hop : (i + 1) * hop] ** 2)) for i in range(frames)])
env = np.clip(env / (np.percentile(env[env > 0], 95) + 1e-9), 0, 1)
env = np.round(env, 2)
with open(f"{OUT}/song_data.js", "w") as f:
    f.write("window.MOUTH=" + json.dumps(env.tolist()) + ";\n")
    f.write("window.SONG=" + json.dumps(timing) + ";\n")
print("done", SONG_END)
