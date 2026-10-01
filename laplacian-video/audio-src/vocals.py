"""Make Claude sing: Kokoro TTS -> phoneme timings -> WORLD vocoder re-timing + re-pitching.

For every melody line the words are spoken by Kokoro (with per-phoneme durations),
split into syllables, and then each syllable is re-synthesised so that
  * its vowel starts exactly on the note,
  * onset/coda consonants keep (roughly) their natural length,
  * the vowel is sustained to fill the note (with a ping-pong loop so it keeps moving),
  * f0 follows the melody with short portamento and vibrato on long notes.

Outputs (48 kHz):  stems/vox_<role>.wav  +  stems/vocal_timing.json
"""
import json
import os
import sys

import numpy as np
import pyworld as pw
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfilt

import song

KOKORO_DIR = os.environ.get("KOKORO_DIR", os.path.expanduser("~/.cache/kokoro"))
MODEL = os.path.join(KOKORO_DIR, "kokoro-v1.0-v11.onnx")   # export with a `duration` output
VOICES = os.path.join(KOKORO_DIR, "voices-v1.0.bin")
TTS_SR = 24000
OUT_SR = 48000
FP = 5.0                      # WORLD frame period (ms)
FPS_W = 1000.0 / FP           # WORLD frames per second
HERE = os.path.dirname(os.path.abspath(__file__))
STEMS = os.path.join(HERE, "stems")

VOWELS = set("aeiouæɐɑɒɔəɚɛɜɝɪʊʌᵻɨyøœɵɤɯʏᵊAIOWYQ")
DIPHTHONG_2ND = set("ɪʊə")    # e.g. eɪ aɪ ɔɪ aʊ oʊ ; "iə" is NOT merged (two syllables)
DIPHTHONG_1ST = set("eaoɔ")
MARKS = set("ˈˌː")

rng = np.random.default_rng(7)


def is_vowel(c):
    return c in VOWELS


def get_kokoro():
    from kokoro_onnx import Kokoro
    return Kokoro(MODEL, VOICES)


def word_phonemes(k, words):
    """Phonemes per word, using overrides from song.PHONEMES."""
    text = " ".join(words)
    auto = k.tokenizer.phonemize(text, "en-us").split()
    out = []
    for i, w in enumerate(words):
        key = w.lower().strip(".,!?")
        if key in song.PHONEMES:
            out.append(song.PHONEMES[key])
        elif len(auto) == len(words):
            out.append(auto[i])
        else:  # word-by-word fallback if the phonemizer merged/split words
            out.append(k.tokenizer.phonemize(w, "en-us").strip())
    return out


def nuclei(ph):
    """Indices groups of vowel nuclei in a phoneme string (list of lists of char idx)."""
    groups, i = [], 0
    while i < len(ph):
        if is_vowel(ph[i]):
            g = [i]
            j = i + 1
            while j < len(ph) and (ph[j] == "ː"):
                g.append(j); j += 1
            # merge diphthong second element
            if j < len(ph) and ph[j] in DIPHTHONG_2ND and ph[i] in DIPHTHONG_1ST:
                g.append(j); j += 1
            groups.append(g)
            i = j
        else:
            i += 1
    return groups


def syllabify(ph, n_syl):
    """Split a word's phoneme string into n_syl syllables.

    Returns list of dicts with char index lists: onset, nucleus, coda.
    """
    groups = nuclei(ph)
    # reconcile count
    while len(groups) > n_syl:          # merge the two closest (shortest gap) groups
        gaps = [groups[i + 1][0] - groups[i][-1] for i in range(len(groups) - 1)]
        m = int(np.argmin(gaps))
        groups[m] = list(range(groups[m][0], groups[m + 1][-1] + 1))
        del groups[m + 1]
    if len(groups) < n_syl:
        raise ValueError(f"{ph!r}: found {len(groups)} vowel nuclei, need {n_syl}")
    sylls = []
    bounds = []
    for gi, g in enumerate(groups):
        # consonants between this nucleus and the next: split (max onset = 1 consonant + marks)
        if gi + 1 < len(groups):
            between = list(range(g[-1] + 1, groups[gi + 1][0]))
            cons = [c for c in between if ph[c] not in MARKS]
            if len(cons) <= 1:
                split = between[0] if between else g[-1] + 1
            else:
                split = cons[1] if len(cons) >= 2 else cons[0]
                # keep a stress mark with the following onset
                while split - 1 >= between[0] and ph[split - 1] in MARKS:
                    split -= 1
            bounds.append(split)
    starts = [0] + bounds
    ends = bounds + [len(ph)]
    for gi, g in enumerate(groups):
        s, e = starts[gi], ends[gi]
        sylls.append(dict(onset=list(range(s, g[0])), nucleus=list(range(g[0], g[-1] + 1)),
                          coda=list(range(g[-1] + 1, e))))
    return sylls


FRIC = set("sʃfθzʒvh")
_HP = butter(4, 4000, "hp", fs=TTS_SR, output="sos")
_LP = butter(4, 1000, "lp", fs=TTS_SR, output="sos")


def band_energy(audio, hop=120):
    """Per-5ms high-band (>4k, frication) and low-band (<1k, vowel) energy in dB."""
    hi, lo = sosfilt(_HP, audio), sosfilt(_LP, audio)
    n = len(audio) // hop
    eh = 10 * np.log10(np.array([np.mean(hi[i * hop:(i + 1) * hop] ** 2) for i in range(n)]) + 1e-12)
    el = 10 * np.log10(np.array([np.mean(lo[i * hop:(i + 1) * hop] ** 2) for i in range(n)]) + 1e-12)
    return np.arange(n) * hop / TTS_SR, eh, el


def estimate_lag(timing, tt, eh, el):
    """Kokoro's duration-derived phoneme times run ~45-90 ms late vs. the audio.
    Find the shift that best matches fricative/vowel labels to band-energy classes."""
    obs = np.where((eh > el - 3) & (eh > -60), 1, np.where(el > el.max() - 25, 0, -1))
    best = (-1.0, -0.06)
    for off in np.arange(-0.13, 0.021, 0.005):
        agree = tot = 0
        for tk in timing[:-1]:
            m = (tt >= tk.start + off) & (tt < tk.end + off)
            if not m.any():
                continue
            if tk.phoneme in FRIC:
                agree += (obs[m] == 1).sum(); tot += m.sum()
            elif is_vowel(tk.phoneme):
                agree += (obs[m] == 0).sum(); tot += m.sum()
        acc = agree / max(tot, 1)
        if acc > best[0] + 1e-9:
            best = (acc, off)
    return best[1], best[0]


def vowel_class(ph_nucleus):
    c = ph_nucleus[0] if ph_nucleus else "ə"
    if c in "aæɑɒɐʌ":
        return "A"      # wide open
    if c in "oɔuʊ":
        return "O"      # round
    if c in "eɛiɪ":
        return "E"      # wide, less open
    return "U"          # neutral (ə ɚ ɜ)


def synth_line(k, words, syllables, voice, speed=0.85, formant=1.0, detune_cents=0.0,
               time_offset=0.0, legato_glide=0.05, cons_gain=1.5):
    """Synthesise one sung line. Returns (audio_24k, t_begin_abs, syllable_timing_list)."""
    wph = word_phonemes(k, words)
    # group syllables by word
    per_word = [[] for _ in words]
    for s in syllables:
        per_word[s["word_index"]].append(s)
    word_sylls = [syllabify(wph[i], len(per_word[i])) for i in range(len(words))]

    P = " ".join(wph)
    audio, sr, timing = k.create_timed(P, voice=voice, speed=speed, is_phonemes=True, trim=False,
                                       sentence_pause=0.0, clause_pause=0.0)
    assert sr == TTS_SR
    known = [c for c in P if c in k.tokenizer.vocab]
    assert len(timing) == len(known), (len(timing), len(known), P)
    tt_b, eh, el = band_energy(audio.astype(np.float64))
    lag, acc = estimate_lag(timing, tt_b, eh, el)
    print(f"   [{' '.join(words)}] label lag {lag*1000:+.0f} ms (agreement {acc:.2f})", flush=True)
    # char index in P -> (start, end), corrected for the label lag
    tpos, ci = {}, 0
    for pi, c in enumerate(P):
        if c not in k.tokenizer.vocab:
            continue
        tpos[pi] = (timing[ci].start + lag, timing[ci].end + lag)
        ci += 1

    # word offsets within P
    offs, o = [], 0
    for w in wph:
        offs.append(o)
        o += len(w) + 1

    def span(word_i, idxs):
        ts = [tpos[offs[word_i] + j] for j in idxs if offs[word_i] + j in tpos]
        if not ts:
            return None
        return (min(t[0] for t in ts), max(t[1] for t in ts))

    # WORLD analysis
    x = audio.astype(np.float64)
    f0, tt = pw.harvest(x, TTS_SR, f0_floor=70.0, f0_ceil=900.0, frame_period=FP)
    sp = pw.cheaptrick(x, f0, tt, TTS_SR)
    ap = pw.d4c(x, f0, tt, TTS_SR)
    nfr = len(f0)
    logsp = np.log(np.maximum(sp, 1e-16))
    voiced_src = f0 > 0

    # Build a flat list of syllable segments with source + target times
    segs = []
    for s in syllables:
        wi = s["word_index"]
        k_in_word = per_word[wi].index(s)
        syl = word_sylls[wi][k_in_word]
        nu = list(span(wi, syl["nucleus"]))
        on = span(wi, syl["onset"]) if syl["onset"] else None
        co = span(wi, syl["coda"]) if syl["coda"] else None
        j0 = syl["nucleus"][0]
        if j0 > 0 and wph[wi][j0 - 1] in "ˈˌ":       # a stress mark's slot holds the vowel onset
            st = span(wi, [j0 - 1])
            nu[0] = st[0] + 0.5 * (st[1] - st[0])
        # refine the vowel to its loud low-band core (bounded to +-40 ms of the label)
        w = (tt_b >= nu[0] - 0.04) & (tt_b < nu[1] + 0.04)
        loop = None
        if w.sum() > 3:
            idx = np.where(w)[0]
            pk = idx[np.argmax(el[idx])]
            core = el >= el[pk] - 12.0
            a = pk
            while a - 1 >= idx[0] and core[a - 1]:
                a -= 1
            b = pk
            while b + 1 <= idx[-1] and core[b + 1]:
                b += 1
            nu = [max(tt_b[a], nu[0] - 0.04), min(tt_b[b] + 0.005, nu[1] + 0.04)]
            steady = np.where((el >= el[pk] - 5.0) & (tt_b >= nu[0]) & (tt_b < nu[1]))[0]
            if len(steady) >= 4:
                loop = (tt_b[steady[0]], tt_b[steady[-1]] + 0.005)
        on_s = min(on[0], nu[0]) if on else nu[0]
        co_e = max(co[1], nu[1]) if co else nu[1]
        # first vowel token of nucleus (for diphthong hold)
        first = span(wi, [syl["nucleus"][0]] + [j for j in syl["nucleus"][1:] if wph[wi][j] == "ː"])
        v1_e = min(max(first[1], nu[0] + 0.03), nu[1]) if first else nu[1]
        if loop is None or (v1_e < nu[1] - 0.02 and loop[1] > v1_e):   # diphthong: hold 1st element
            lo_ = nu[0] + 0.3 * (v1_e - nu[0])
            loop = (lo_, max(lo_ + 0.02, nu[0] + 0.8 * (v1_e - nu[0])))
        segs.append(dict(syl=s, on_s=on_s, nu_s=nu[0], nu_e=nu[1], co_e=co_e, loop=loop,
                         v1_e=v1_e,
                         vclass=vowel_class([wph[wi][j] for j in syl["nucleus"]]),
                         phon=wph[wi], word=words[wi]))

    # Target layout
    for i, g in enumerate(segs):
        s = g["syl"]
        n_s = s["start"] + time_offset
        n_e = n_s + s["dur"]
        on_len = min(g["nu_s"] - g["on_s"], 0.16)
        g["on_len"] = max(on_len, 0.0)
        g["n_s"], g["n_e"] = n_s, n_e
    for i, g in enumerate(segs):
        nxt = segs[i + 1] if i + 1 < len(segs) else None
        contiguous_next = nxt is not None and abs(nxt["n_s"] - g["n_e"]) < 1e-6
        avail_end = g["n_e"] - (nxt["on_len"] if contiguous_next else 0.0)
        if not contiguous_next:
            avail_end = g["n_e"] - 0.02      # tiny breath before rests
        room = max(avail_end - g["n_s"], 0.05)
        co_len = min(g["co_e"] - g["nu_e"], 0.35 * room, 0.14)
        g["co_len"] = max(co_len, 0.0)
        g["v_end"] = avail_end - g["co_len"]          # end of sung vowel
        g["end"] = avail_end
        prev = segs[i - 1] if i > 0 else None
        g["glide_from"] = prev["syl"]["midi"] if (prev is not None and abs(prev["n_e"] - g["n_s"]) < 1e-6) else None

    t_begin = segs[0]["n_s"] - segs[0]["on_len"] - 0.04
    t_end = segs[-1]["end"] + 0.12
    n_out = int(np.ceil((t_end - t_begin) * FPS_W)) + 1
    o_t = t_begin + np.arange(n_out) / FPS_W
    src = np.full(n_out, -1.0)        # source time (s) per output frame, -1 = silence
    region = np.zeros(n_out, dtype=np.int8)   # 0 silence, 1 onset, 2 nucleus, 3 coda
    f0_tgt = np.zeros(n_out)
    seg_of = np.full(n_out, -1)

    for i, g in enumerate(segs):
        hz = song.midi_to_hz(g["syl"]["midi"]) * 2 ** (detune_cents / 1200)
        # onset
        a, b = g["n_s"] - g["on_len"], g["n_s"]
        m = (o_t >= a) & (o_t < b)
        if g["on_len"] > 0 and m.any():
            # natural speed; an over-long onset keeps only its last 0.16 s
            src[m] = (g["nu_s"] - g["on_len"]) + (o_t[m] - a)
            region[m] = 1
        # nucleus
        a, b = g["n_s"], g["v_end"]
        m = (o_t >= a) & (o_t < b)
        L = b - a
        vs, ve, v1e = g["nu_s"], g["nu_e"], g["v1_e"]
        lsrc = ve - vs
        if m.any():
            tau = o_t[m] - a
            if L <= lsrc * 1.15 or lsrc < 0.03:
                s_t = vs + tau / max(L, 1e-6) * lsrc
            else:
                loop_src = g["loop"]
                head_src = (vs, loop_src[0])
                rel_src = (loop_src[1], ve)
                h_len = head_src[1] - head_src[0]
                r_len = min(rel_src[1] - rel_src[0], max(0.3 * L, 0.04))
                sus_len = L - h_len - r_len
                s_t = np.empty_like(tau)
                if sus_len <= 0.01:
                    s_t = vs + tau / L * lsrc
                else:
                    hm = tau < h_len
                    s_t[hm] = head_src[0] + tau[hm]
                    sm = (tau >= h_len) & (tau < h_len + sus_len)
                    lw = max(loop_src[1] - loop_src[0], 0.01)
                    ph = (tau[sm] - h_len) * 0.55          # traverse loop at 0.55x speed
                    tri = np.abs(((ph / lw) % 2.0) - 1.0)  # ping-pong 1..0..1
                    s_t[sm] = loop_src[0] + (1.0 - tri) * lw
                    # make release start from wherever the loop is: blend into release
                    rm = tau >= h_len + sus_len
                    s_t[rm] = rel_src[0] + (tau[rm] - h_len - sus_len) / r_len * (rel_src[1] - rel_src[0])
            src[m] = s_t
            region[m] = 2
        # coda
        a, b = g["v_end"], g["end"]
        m = (o_t >= a) & (o_t < b)
        if g["co_len"] > 0 and m.any():
            src[m] = g["nu_e"] + (o_t[m] - a) / g["co_len"] * (g["co_e"] - g["nu_e"])
            region[m] = 3
        # pitch target over the whole syllable
        a, b = g["n_s"] - g["on_len"], g["end"]
        m = (o_t >= a) & (o_t < b)
        seg_of[m] = i
        tau = o_t[m] - g["n_s"]
        cents = np.zeros(m.sum())
        if g["glide_from"] is not None:
            d = (g["glide_from"] - g["syl"]["midi"]) * 100.0
            gl = np.clip(1.0 - (tau + g["on_len"]) / (g["on_len"] + legato_glide), 0, 1)
            cents += d * gl ** 1.5
        else:
            # small scoop into isolated notes
            cents += -40.0 * np.clip(1.0 - tau / 0.06, 0, 1) * (tau > -1)
        vib_len = g["v_end"] - g["n_s"]
        if vib_len > 0.34:
            depth = 32.0 * np.clip((tau - 0.18) / 0.3, 0, 1)
            cents += depth * np.sin(2 * np.pi * 5.6 * np.maximum(tau - 0.18, 0))
        cents += rng.normal(0, 2.0)  # per-note tiny offset (human-ish)
        f0_tgt[m] = hz * 2 ** (cents / 1200.0)

    # sample source params
    have = src >= 0
    fi = np.clip(src * FPS_W, 0, nfr - 1)
    i0 = np.floor(fi).astype(int)
    i1 = np.minimum(i0 + 1, nfr - 1)
    w = (fi - i0)[:, None]
    out_logsp = (1 - w) * logsp[i0] + w * logsp[i1]
    out_ap = (1 - w) * ap[i0] + w * ap[i1]
    v_src = voiced_src[np.rint(fi).astype(int)]

    # nucleus frames: force voiced; borrow ap from nearest voiced source frame
    nuc = region == 2
    fix = nuc & ~v_src
    if fix.any():
        vidx = np.where(voiced_src)[0]
        if len(vidx):
            near = vidx[np.clip(np.searchsorted(vidx, np.rint(fi[fix]).astype(int)), 0, len(vidx) - 1)]
            out_ap[fix] = ap[near]
    voiced = have & (nuc | v_src)
    out_f0 = np.where(voiced, f0_tgt, 0.0)
    # formant shift (frequency-axis warp of the spectral envelope)
    out_sp = np.exp(out_logsp)
    if abs(formant - 1.0) > 1e-3:
        freqs = np.linspace(0, TTS_SR / 2, out_sp.shape[1])
        for r in range(out_sp.shape[0]):
            out_sp[r] = np.exp(np.interp(freqs / formant, freqs, out_logsp[r]))
    silent = ~have
    out_sp[silent] = 1e-12
    out_ap[silent] = 1.0
    out_f0[silent] = 0.0

    y = pw.synthesize(np.ascontiguousarray(out_f0), np.ascontiguousarray(out_sp),
                      np.ascontiguousarray(out_ap), TTS_SR, FP)
    # soft gate at the silent boundaries (5 ms ramps) to kill vocoder edge noise
    env = np.repeat(have.astype(float), int(TTS_SR * FP / 1000))[: len(y)]
    if len(env) < len(y):
        env = np.pad(env, (0, len(y) - len(env)))
    ker = np.hanning(int(0.01 * TTS_SR)); ker /= ker.sum()
    env = np.convolve(env, ker, mode="same")
    y = y * env
    # consonant emphasis (+3.5 dB on onsets/codas), smoothed over ~15 ms
    if cons_gain != 1.0:
        hop = int(TTS_SR * FP / 1000)
        g = np.where((region == 1) | (region == 3), cons_gain, 1.0)
        g = np.repeat(g, hop)[: len(y)]
        if len(g) < len(y):
            g = np.pad(g, (0, len(y) - len(g)), constant_values=1.0)
        kk = np.hanning(int(0.015 * TTS_SR)); kk /= kk.sum()
        y = y * np.convolve(g, kk, mode="same")

    timing = []
    for g in segs:
        timing.append(dict(text=g["syl"]["text"], word=g["word"], word_end=g["syl"]["word_end"],
                           onset=round(g["n_s"] - g["on_len"], 3), start=round(g["n_s"], 3),
                           vowel_end=round(g["v_end"], 3), end=round(g["end"], 3),
                           midi=g["syl"]["midi"], vclass=g["vclass"]))
    return y, t_begin, timing


CACHE_VERSION = 4   # bump when synth_line's algorithm changes


def cached_synth(k, words, syllables, voice, **kw):
    """synth_line with an on-disk cache keyed by everything that affects the output."""
    import hashlib
    key = json.dumps([CACHE_VERSION, words, syllables, voice, kw, song.PHONEMES], sort_keys=True)
    h = hashlib.sha1(key.encode()).hexdigest()[:16]
    path = os.path.join(STEMS, "cache", h + ".npz")
    if os.path.exists(path):
        d = np.load(path, allow_pickle=False)
        return d["y"], float(d["t0"]), json.loads(str(d["timing"]))
    y, t0, tim = synth_line(k, words, syllables, voice, **kw)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez(path, y=y, t0=t0, timing=json.dumps(tim))
    return y, t0, tim


def place(track, y24, t0, gain=1.0):
    y = resample_poly(y24, 2, 1)
    i0 = int(round(t0 * OUT_SR))
    if i0 < 0:
        y = y[-i0:]; i0 = 0
    n = min(len(y), len(track) - i0)
    track[i0:i0 + n] += gain * y[:n]


def rms_norm(y, target_db=-18.0):
    r = np.sqrt(np.mean(y[np.abs(y) > 1e-4] ** 2) + 1e-12)
    return y * (10 ** (target_db / 20) / r)


def main():
    os.makedirs(STEMS, exist_ok=True)
    k = get_kokoro()
    N = int(song.DURATION * OUT_SR) + OUT_SR
    tracks = {name: np.zeros(N) for name in ["lead", "double", "harm", "nbr0", "nbr1", "nbr2", "speech",
                                               "gang0", "gang1", "gang2", "gang3", "gangC"]}
    timing_out = {"lines": [], "spoken": []}
    only = set(sys.argv[1:])

    for ln in song.lines():
        if only and ln["base_id"] not in only and ln["id"] not in only:
            continue
        role = ln["role"]
        if role == "lead":
            y, t0, tim = cached_synth(k, ln["words"], ln["syllables"], song.VOICE, speed=0.85)
            y = rms_norm(y)
            place(tracks["lead"], y, t0)
            # choruses get a detuned double (placed a hair late) for width
            if ln["base_id"][0] in "cft":
                y2, t2, _ = cached_synth(k, ln["words"], ln["syllables"], song.VOICE, speed=0.87,
                                       formant=1.02, detune_cents=9.0, time_offset=0.012)
                place(tracks["double"], rms_norm(y2), t2)
        elif role == "harm":
            fmt = {"t2_h1": 1.04, "t2_h2": 0.97}.get(ln["id"], 1.03)
            y, t0, tim = cached_synth(k, ln["words"], ln["syllables"], song.VOICE, speed=0.86,
                                    formant=fmt, detune_cents=-6.0, time_offset=0.008)
            place(tracks["harm"], rms_norm(y), t0)
        elif role == "gang":  # every neighbour shouting the same line: unison crowd
            tim = None
            # Claude leads the shout dead-centre (clear words); the neighbours thicken it
            y, t0, tim = cached_synth(k, ln["words"], ln["syllables"], song.VOICE, speed=0.9, cons_gain=1.7)
            place(tracks["gangC"], rms_norm(y), t0)
            for gi, voice in enumerate(song.GANG_VOICES):
                y, t0, tg = cached_synth(k, ln["words"], ln["syllables"], voice, speed=0.95,
                                         formant=[1.1, 1.06, 1.14, 1.04][gi], detune_cents=[5.0, -4.0, 7.0, -6.0][gi],
                                         time_offset=[0.0, 0.008, 0.014, 0.004][gi], cons_gain=1.7)
                place(tracks[f"gang{gi}"], rms_norm(y), t0)
        else:  # neighbor chorus: 3 different voices, formant-shifted up = tiny singers
            part = ln["part"]
            voice = song.NEIGHBOR_VOICES[part]
            y, t0, tim = cached_synth(k, ln["words"], ln["syllables"], voice, speed=0.9,
                                    formant=[1.28, 1.22, 1.32][part], time_offset=[0.0, 0.01, 0.018][part])
            place(tracks[f"nbr{part}"], rms_norm(y), t0)
        timing_out["lines"].append(dict(id=ln["id"], base_id=ln["base_id"], role=role,
                                        part=ln["part"], words=ln["words"], syllables=tim))
        print(f"sang {ln['id']:8s} {t0:6.2f}s  " + " ".join(s["text"] for s in tim), flush=True)

    if not only or "spoken" in only:
        for sid, t_start, text, spd in song.SPOKEN:
            audio, sr, tim = k.create_timed(text, voice=song.VOICE, speed=spd, trim=False)
            nz = np.where(np.abs(audio) > 0.01)[0]
            a0 = nz[0] / sr - 0.02
            y = audio[int(a0 * sr): int((nz[-1] / sr + 0.08) * sr)]
            place(tracks["speech"], rms_norm(y.astype(np.float64), -17.0), t_start)
            ph = [dict(p=x.phoneme, s=round(t_start + x.start - a0, 3), e=round(t_start + x.end - a0, 3))
                  for x in tim if x.phoneme.strip() and x.phoneme not in "ˈˌ,.!?"]
            timing_out["spoken"].append(dict(id=sid, text=text, start=t_start,
                                             end=round(t_start + len(y) / sr, 3), phonemes=ph))
            print(f"said {sid} {t_start:.2f}-{t_start + len(y) / sr:.2f}s  {text}", flush=True)

    suffix = "_partial" if only else ""
    for name, tr in tracks.items():
        sf.write(os.path.join(STEMS, f"vox_{name}{suffix}.wav"), tr.astype(np.float32), OUT_SR, subtype="FLOAT")
    with open(os.path.join(STEMS, f"vocal_timing{suffix}.json"), "w") as f:
        json.dump(timing_out, f, indent=1)


if __name__ == "__main__":
    main()
