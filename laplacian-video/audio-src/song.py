"""The song: "Average of the Neighbors" (v2) - a Laplacian explainer sung by Claude.

Single source of truth for tempo, chords, melody, lyrics, spoken lines, stop-times
and sound-effect cues. vocals.py, music.py and mix.py all read from here, and
mix.py exports the timing the HyperFrames composition animates against.

Melody line format: space-separated tokens "syl:NOTE:slots".
  - a slot is one eighth note (0.25 s at 120 BPM); fractional slots are fine (0.5 = a 16th)
  - a syllable ending in "-" continues the same word ("a-:G4:1 round:E4:2")
  - "_:n" is a rest of n slots
Roles: lead (Claude), harm (Claude harmony), nbr (3-part neighbour harmony, list of melodies),
       gang (all the neighbours shouting in unison).
"""

BPM = 120
BEAT = 60.0 / BPM          # 0.5 s
BAR = 4 * BEAT             # 2.0 s
SLOT = BEAT / 2            # eighth note, 0.25 s
TOTAL_BARS = 41            # 82 s of video
DURATION = TOTAL_BARS * BAR

VOICE = "af_heart"         # Claude's voice (Kokoro)
NEIGHBOR_VOICES = ["af_bella", "am_puck", "af_nicole"]
GANG_VOICES = ["af_bella", "am_puck", "af_nicole", "am_michael"]

# One chord per bar. The final chorus modulates up a whole step (C -> D).
CHORDS = (
    ["F", "G"]                                              # 0-1   cold open (hook)
    + ["C", "G"]                                            # 2-3   "Hey! It's me, Claude!"
    + ["Am", "F", "C", "G", "Am", "F", "C", "G"]            # 4-11  verse 1
    + ["F", "G", "Em", "Am", "F", "G", "G", "C"]            # 12-19 chorus
    + ["F", "G"]                                            # 20-21 post-chorus chant
    + ["Am", "F", "C", "G", "Am", "F", "Dm", "G"]           # 22-29 verse 2
    + ["A"]                                                 # 30    build: "one more time!"
    + ["G", "A", "A", "D"]                                  # 31-34 final chorus (in D)
    + ["G", "A"]                                            # 35-36 post-chorus chant (in D)
    + ["Gm", "A", "D", "D"]                                 # 37-40 tag + ring out
)
assert len(CHORDS) == TOTAL_BARS

SECTIONS = [
    ("cold", 0, 2),
    ("talk", 2, 4),
    ("verse1", 4, 12),
    ("chorus", 12, 20),
    ("post", 20, 22),
    ("verse2", 22, 30),
    ("build", 30, 31),
    ("final", 31, 35),
    ("post2", 35, 37),
    ("tag", 37, 41),
]

# Stop-time: the band drops out (with a tape-stop into it) while Claude sings
# "minus..." alone, and slams back in on "YOU!".  (start_s, end_s)
STOPS = [(19 * BAR, 19 * BAR + 2 * BEAT), (34 * BAR, 34 * BAR + 2 * BEAT)]

# Phoneme overrides (Kokoro/espeak IPA) for words the G2P would mangle
# or pronounce with the wrong syllable count.
PHONEMES = {
    "average": "ˈævɹɪdʒ",
    "eff": "ˈɛf",
    "ex": "ˈɛks",
    "why": "wˈaɪ",
    "dee": "dˈiː",
    "tee": "tˈiː",
    "you": "jˈuː",
    "u": "jˈuː",
    "laplacian": "læplˈeɪʃiən",
    "zero": "zˈiːɹoʊ",
    "harmonic": "hɑːɹmˈɑːnɪk",
    "la": "lˈɑː",
    "hey": "hˈeɪ",
    "positive": "pˈɑːzɪtɪv",
    "negative": "nˈɛɡətɪv",
}

HOOK_C = "La:F4:0.5 la:G4:0.5 La-:A4:1 pla-:C5:3 ci-:A4:1 an:F4:2"
HOOK_D = "La:G4:0.5 la:A4:0.5 La-:B4:1 pla-:D5:3 ci-:B4:1 an:G4:2"
NABLA_C = ["na-:B4:1 bla:B4:1 squared:D5:3", "na-:G4:1 bla:G4:1 squared:B4:3", "na-:D4:1 bla:D4:1 squared:G4:3"]
NABLA_D = ["na-:C#5:1 bla:C#5:1 squared:E5:3", "na-:A4:1 bla:A4:1 squared:C#5:3", "na-:E4:1 bla:E4:1 squared:A4:3"]

# (id, role, bar, slot, words, melody)
LINES = [
    # ---------------- cold open: straight into the hook ----------------
    ("co_a", "lead", 0, 0, "La la Laplacian", HOOK_C),
    ("co_b", "nbr", 1, 0, "nabla squared", NABLA_C),
    # ---------------- verse 1 ----------------
    ("v1a", "lead", 4, 0, "Take a point look around",
     "Take:E4:1 a:E4:1 point:G4:2 look:G4:1 a-:A4:1 round:G4:2"),
    ("v1b", "lead", 5, 0, "check the neighbors on the ground",
     "check:E4:1 the:E4:1 neigh-:G4:1 bors:G4:1 on:A4:1 the:A4:1 ground:C5:2"),
    ("v1c", "lead", 6, 0, "average what they've got",
     "av-:C5:1 rage:C5:1 what:B4:1 they've:A4:1 got:G4:2 _:2"),
    ("v1d", "lead", 7, 0, "then subtract the middle spot",
     "then:E4:1 sub-:G4:1 tract:A4:1 the:A4:1 mid-:C5:1 dle:B4:1 spot:G4:2"),
    ("v1e", "lead", 8, 0, "Sitting in a valley",
     "Sit-:E4:1 ting:E4:1 in:D4:1 a:C4:1 val-:B3:2 ley:A3:2"),
    ("v1f", "gang", 9, 0, "positive",
     "pos-:F4:2 i-:A4:2 tive:C5:3"),
    ("v1g", "lead", 10, 0, "up on top of a peak",
     "up:E4:1 on:F4:1 top:G4:1 of:A4:1 a:B4:1 peak:C5:3"),
    ("v1h", "gang", 11, 0, "negative",
     "neg-:D5:2 a-:B4:2 tive:G4:3"),
    # ---------------- chorus ----------------
    ("c1a", "lead", 12, 0, "La la Laplacian", HOOK_C),
    ("c1b", "nbr", 13, 0, "nabla squared", NABLA_C),
    ("c1c", "lead", 14, 0, "Add the second derivatives",
     "Add:G4:1 the:G4:1 sec-:B4:1 ond:B4:1 de-:B4:1 riv-:C5:1 a-:B4:1 tives:G4:1"),
    ("c1d", "lead", 15, 0, "eff ex ex plus eff why why",
     "eff:A4:1 ex:C5:1 ex:C5:1 plus:B4:1 eff:A4:1 why:C5:1 why:A4:1"),
    ("c1e", "lead", 16, 0, "La la Laplacian", HOOK_C),
    ("c1f", "nbr", 17, 0, "nabla squared", NABLA_C),
    ("c1g", "lead", 18, 0, "It's the average of your neighbors",
     "It's:D4:1 the:G4:1 av-:B4:1 rage:B4:1 of:A4:1 your:G4:1 neigh-:A4:1 bors:B4:1"),
    ("c1h", "lead", 19, 0, "minus you",
     "mi-:C5:1 nus:B4:1 _:2 you:C5:4"),
    ("c1h_h", "harm", 19, 0, "minus you",
     "mi-:A4:1 nus:G4:1 _:2 you:E4:4"),
    ("c1h_g", "gang", 19, 4, "you", "you:C5:4"),
    # ---------------- post-chorus chant ----------------
    ("p1a", "lead", 20, 0, "What's the Laplacian",
     "What's:A4:1 the:G4:1 La-:A4:1 pla-:C5:1 ci-:A4:1 an:C5:2"),
    ("p1h1", "gang", 20, 7, "hey", "hey:G4:1"),
    ("p1b", "gang", 21, 0, "average minus you",
     "av-:D5:1 rage:C5:1 mi-:B4:1 nus:A4:1 you:G4:2"),
    ("p1h2", "gang", 21, 6, "hey", "hey:G4:1"),
    # ---------------- verse 2 ----------------
    ("v2a", "lead", 22, 0, "Heat is just peer pressure",
     "Heat:E4:2 is:E4:1 just:E4:1 peer:A4:2 pres-:G4:1 sure:E4:1"),
    ("v2b", "lead", 23, 0, "hot spots cool cold spots warm",
     "hot:C5:1 spots:C5:1 cool:F4:2 cold:C4:1 spots:C4:1 warm:A4:2"),
    ("v2c", "lead", 24, 0, "dee you dee tee equals",
     "dee:E4:1 you:G4:1 dee:E4:1 tee:G4:1 e-:C5:1 quals:C5:1"),
    ("v2d", "lead", 25, 0, "Laplacian of u",
     "La-:B4:1 pla-:B4:2 ci-:A4:1 an:G4:1 of:A4:1 u:B4:2"),
    ("v2e", "lead", 26, 0, "When it's zero it's balanced",
     "When:C5:1 it's:B4:1 ze-:A4:1 ro:A4:1 it's:A4:1 bal-:A4:1 anced:A4:1"),
    ("v2f", "lead", 26, 7, "each point's the average of its crew",
     "each:F4:1 point's:A4:1 the:C5:1 av-:C5:1 rage:A4:1 of:G4:1 its:F4:1 crew:A4:2"),
    ("v2g", "lead", 28, 0, "soap films steady heat",
     "soap:A4:2 films:F4:2 stea-:A4:1 dy:A4:1 heat:F4:2"),
    ("v2h", "lead", 29, 0, "and electric fields do it too",
     "and:D4:1 e-:G4:1 lec-:G4:1 tric:B4:1 fields:B4:1 do:A4:1 it:G4:1 too:B4:1"),
    # ---------------- final chorus: up a whole step ----------------
    ("f1a", "lead", 31, 0, "La la Laplacian", HOOK_D),
    ("f1a_h", "harm", 31, 0, "La la Laplacian",
     "La:E4:0.5 la:F#4:0.5 La-:G4:1 pla-:B4:3 ci-:G4:1 an:E4:2"),
    ("f1b", "nbr", 32, 0, "nabla squared", NABLA_D),
    ("f1c", "lead", 33, 0, "It's the average of your neighbors",
     "It's:E4:1 the:A4:1 av-:C#5:1 rage:C#5:1 of:B4:1 your:A4:1 neigh-:B4:1 bors:C#5:1"),
    ("f1c_h", "harm", 33, 0, "It's the average of your neighbors",
     "It's:C#4:1 the:F#4:1 av-:A4:1 rage:A4:1 of:G4:1 your:F#4:1 neigh-:G4:1 bors:A4:1"),
    ("f1d", "lead", 34, 0, "minus you",
     "mi-:D5:1 nus:C#5:1 _:2 you:D5:4"),
    ("f1d_h", "harm", 34, 0, "minus you",
     "mi-:B4:1 nus:A4:1 _:2 you:A4:4"),
    ("f1d_g", "gang", 34, 4, "you", "you:D5:4"),
    # ---------------- post-chorus chant (in D) ----------------
    ("p2a", "lead", 35, 0, "What's the Laplacian",
     "What's:B4:1 the:A4:1 La-:B4:1 pla-:D5:1 ci-:B4:1 an:D5:2"),
    ("p2h1", "gang", 35, 7, "hey", "hey:A4:1"),
    ("p2b", "gang", 36, 0, "average minus you",
     "av-:E5:1 rage:D5:1 mi-:C#5:1 nus:B4:1 you:A4:2"),
    ("p2h2", "gang", 36, 6, "hey", "hey:A4:1"),
    # ---------------- tag: iv - V - I in D ----------------
    ("t1", "lead", 37, 0, "And when it's zero",
     "And:D4:1 when:G4:1 it's:A4:1 ze-:Bb4:2 ro:A4:3"),
    ("t2", "lead", 38, 0, "harmonic",
     "har-:A4:2 mo-:C#5:6 nic:D5:4"),
    ("t2_h1", "harm", 38, 0, "harmonic",
     "har-:E4:2 mo-:G4:6 nic:F#4:4"),
    ("t2_h2", "harm", 38, 0, "harmonic",
     "har-:C#4:2 mo-:E4:6 nic:D4:4"),
    ("t2_g", "gang", 38, 0, "harmonic",
     "har-:A4:2 mo-:C#5:6 nic:D5:4"),
]

# Spoken lines (natural TTS, no pitch correction): (id, start_seconds, text, speed)
SPOKEN = [
    ("s1", 4.08, "Hey! It's me, Claude!", 1.08),
    ("s2", 5.3, "Let's learn the Laplacian, with a song!", 1.1),
    ("s3", 7.3, "Hit it!", 1.05),
    ("s4", 60.05, "One more time!", 1.05),
]

# Sound-effect cues. The composition animates on the same list, so every
# "pop" you hear is something popping on screen. (time_s, kind, label)
CUES = [
    (0.00, "impact", "cold-open"),
    (2.00, "pop", "gang1"), (2.125, "pop", "gang2"), (2.25, "pop", "gang3"),
    (3.55, "scratch", "scratch"),
    (4.02, "boing", "clawd-lands"),
    (6.00, "sparkle", "title-nabla"),
    (6.95, "pop", "mic"),
    (7.00, "roll", "fill"),
    (8.00, "crash", "verse1"),
    (8.00, "whoosh", "to-grid"),
    (10.50, "pop", "n-east"), (10.625, "pop", "n-north"), (10.75, "pop", "n-west"), (10.875, "pop", "n-south"),
    (12.00, "whoosh", "values-fly"),
    (13.00, "ding", "avg"),
    (15.50, "ding", "result"),
    (16.00, "whoosh", "to-valley"),
    (16.00, "slide_down", "slide"),
    (18.00, "sparkle", "positive"),
    (20.00, "slide_up", "climb"),
    (22.00, "womp", "negative"),
    (22.00, "riser", "to-chorus"),
    (24.00, "impact", "chorus"),
    (26.00, "pop", "gang1b"), (26.125, "pop", "gang2b"), (26.25, "pop", "gang3b"),
    (28.00, "whoosh", "formula"),
    (30.00, "ding", "fxx"), (31.00, "ding", "fyy"),
    (32.00, "crash", "chorus-b"),
    (34.00, "pop", "gang1c"), (34.125, "pop", "gang2c"), (34.25, "pop", "gang3c"),
    (39.00, "impact", "you"),
    (40.00, "whoosh", "to-dance"),
    (43.50, "whoosh", "to-heat"),
    (46.00, "sizzle", "hot-cool"), (47.00, "chime", "cold-warm"),
    (48.00, "whoosh", "heat-eq"),
    (52.00, "bell", "zero"),
    (56.00, "pop", "soap"), (56.50, "pop", "steady"), (58.75, "zap", "electric"),
    (58.00, "riser", "to-build"),
    (60.00, "crash", "build"),
    (61.50, "sparkle", "key-change"),
    (62.00, "impact", "final"),
    (64.00, "pop", "gang1d"), (64.125, "pop", "gang2d"), (64.25, "pop", "gang3d"),
    (69.00, "impact", "you-2"),
    (70.00, "whoosh", "to-dance-2"),
    (77.00, "revcymbal", "to-harmonic"),
    (78.00, "crash", "harmonic"),
    (78.00, "sparkle", "harmonic"),
    (80.50, "pop", "wink"),
]

NOTE_OFFSETS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_to_midi(name):
    """'A4' -> 69, 'Ab4' -> 68, 'C#5' -> 73."""
    letter, rest = name[0], name[1:]
    acc = 0
    while rest and rest[0] in "#b":
        acc += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + NOTE_OFFSETS[letter] + acc


def midi_to_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def bar_time(bar, slot=0):
    return bar * BAR + slot * SLOT


def parse_melody(bar, slot, melody):
    """-> list of syllables {text, start, dur, midi, word_index, word_end}."""
    t = bar_time(bar, slot)
    out, word = [], 0
    for tok in melody.split():
        syl, *rest = tok.split(":")
        if syl == "_":
            t += float(rest[0]) * SLOT
            continue
        note, slots = rest
        cont = syl.endswith("-")
        dur = float(slots) * SLOT
        out.append(dict(text=syl.rstrip("-"), start=round(t, 4), dur=dur,
                        midi=note_to_midi(note), word_index=word,
                        word_end=not cont))
        t += dur
        if not cont:
            word += 1
    return out


def lines():
    """Expand LINES into dicts with parsed syllables (one entry per voice part)."""
    out = []
    for lid, role, bar, slot, words, melody in LINES:
        parts = melody if isinstance(melody, list) else [melody]
        for pi, mel in enumerate(parts):
            syls = parse_melody(bar, slot, mel)
            n_words = len(words.split())
            assert syls[-1]["word_index"] == n_words - 1, (lid, words, mel)
            out.append(dict(id=lid if len(parts) == 1 else f"{lid}_{pi}", base_id=lid,
                            role=role, part=pi, words=words.split(), syllables=syls))
    return out


if __name__ == "__main__":
    for ln in lines():
        s = ln["syllables"]
        print(f'{ln["id"]:8s} {ln["role"]:5s} {s[0]["start"]:6.2f}-{s[-1]["start"] + s[-1]["dur"]:6.2f}  '
              + " ".join(x["text"] + ("" if x["word_end"] else "-") for x in s))
