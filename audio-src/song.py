"""The song: "Average of the Neighbors" - a Laplacian explainer sung by Claude.

Single source of truth for tempo, chords, melody, lyrics and spoken lines.
vocals.py, music.py and mix.py all read from here, and mix.py exports the
timing data the HyperFrames composition animates against.

Melody line format: space-separated tokens "syl:NOTE:slots".
  - a slot is one eighth note (0.25 s at 120 BPM)
  - a syllable ending in "-" continues the same word ("a-:G4:1 round:E4:2")
  - "_:n" is a rest of n slots
"""

BPM = 120
BEAT = 60.0 / BPM          # 0.5 s
BAR = 4 * BEAT             # 2.0 s
SLOT = BEAT / 2            # eighth note, 0.25 s
TOTAL_BARS = 36            # 72 s of video
DURATION = TOTAL_BARS * BAR

VOICE = "af_heart"         # Claude's voice (Kokoro)
NEIGHBOR_VOICES = ["af_bella", "am_puck", "af_nicole"]

# One chord per bar (bar index -> chord name). Section map below.
CHORDS = (
    ["C", "Am", "F", "G"]                                   # 0-3   intro (spoken)
    + ["Am", "F", "C", "G", "Am", "F", "C", "G"]            # 4-11  verse 1
    + ["F", "G", "Em", "Am", "F", "G", "G", "C"]            # 12-19 chorus
    + ["Am", "F", "C", "G", "Am", "F", "Dm", "G"]           # 20-27 verse 2
    + ["F", "G", "G", "C"]                                  # 28-31 final chorus
    + ["Fm", "G", "C", "C"]                                 # 32-35 tag + ring out
)
assert len(CHORDS) == TOTAL_BARS

SECTIONS = [
    ("intro", 0, 4),
    ("verse1", 4, 12),
    ("chorus", 12, 20),
    ("verse2", 20, 28),
    ("final", 28, 32),
    ("tag", 32, 36),
]

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
}

# (id, role, bar, slot, words, melody)
#   role: lead | harm (lead voice, harmony part) | nbr (neighbor chorus, 3 voices)
LINES = [
    # ---------------- verse 1 ----------------
    ("v1a", "lead", 4, 0, "Take a point look around",
     "Take:E4:1 a:G4:1 point:A4:2 look:A4:1 a-:G4:1 round:E4:2"),
    ("v1b", "lead", 5, 0, "at the neighbors on the ground",
     "at:C4:1 the:E4:1 neigh-:F4:1 bors:F4:1 on:G4:1 the:G4:1 ground:A4:2"),
    ("v1c", "lead", 6, 0, "average what they've got",
     "av-:G4:1 rage:G4:1 what:E4:1 they've:G4:1 got:C5:2 _:2"),
    ("v1d", "lead", 7, 0, "then subtract the middle spot",
     "then:B4:1 sub-:B4:1 tract:A4:1 the:G4:1 mid-:A4:1 dle:B4:1 spot:G4:2"),
    ("v1e", "lead", 8, 0, "Sitting in a valley",
     "Sit-:E4:1 ting:E4:1 in:D4:1 a:C4:1 val-:B3:2 ley:A3:2"),
    ("v1f", "lead", 9, 0, "then it's positive",
     "then:C4:1 it's:C4:1 pos-:F4:1 i-:A4:1 tive:C5:2 _:2"),
    ("v1g", "lead", 10, 0, "up on top of a peak",
     "up:E4:1 on:F4:1 top:G4:1 of:A4:1 a:B4:1 peak:C5:3"),
    ("v1h", "lead", 11, 0, "then it's negative",
     "then:B4:1 it's:A4:1 neg-:G4:1 a-:F4:1 tive:D4:2"),
    # ---------------- chorus ----------------
    ("c1a", "lead", 11, 7, "Laplacian",
     "La-:A4:1 pla-:C5:4 ci-:A4:1 an:F4:2"),
    ("c1b", "nbr", 13, 0, "nabla squared",
     ["na-:B4:1 bla:B4:1 squared:D5:3", "na-:G4:1 bla:G4:1 squared:B4:3", "na-:D4:1 bla:D4:1 squared:G4:3"]),
    ("c1c", "lead", 14, 0, "Add the second derivatives",
     "Add:G4:1 the:G4:1 sec-:B4:1 ond:B4:1 de-:B4:1 riv-:C5:1 a-:B4:1 tives:G4:1"),
    ("c1d", "lead", 15, 0, "eff ex ex plus eff why why",
     "eff:A4:1 ex:C5:1 ex:C5:1 plus:B4:1 eff:A4:1 why:C5:1 why:A4:1"),
    ("c1e", "lead", 15, 7, "Laplacian",
     "La-:A4:1 pla-:C5:4 ci-:A4:1 an:F4:2"),
    ("c1f", "nbr", 17, 0, "nabla squared",
     ["na-:B4:1 bla:B4:1 squared:D5:3", "na-:G4:1 bla:G4:1 squared:B4:3", "na-:D4:1 bla:D4:1 squared:G4:3"]),
    ("c1g", "lead", 18, 0, "It's the average of your neighbors",
     "It's:D4:1 the:G4:1 av-:B4:1 rage:B4:1 of:A4:1 your:G4:1 neigh-:A4:1 bors:B4:1"),
    ("c1h", "lead", 19, 0, "minus you",
     "mi-:C5:1 nus:B4:1 you:C5:4"),
    # ---------------- verse 2 ----------------
    ("v2a", "lead", 20, 0, "Heat is just peer pressure",
     "Heat:E4:2 is:E4:1 just:E4:1 peer:A4:2 pres-:G4:1 sure:E4:1"),
    ("v2b", "lead", 21, 0, "hot spots cool cold spots warm",
     "hot:C5:1 spots:C5:1 cool:F4:2 cold:C4:1 spots:C4:1 warm:A4:2"),
    ("v2c", "lead", 22, 0, "dee you dee tee equals",
     "dee:E4:1 you:G4:1 dee:E4:1 tee:G4:1 e-:C5:1 quals:C5:1"),
    ("v2d", "lead", 23, 0, "Laplacian of u",
     "La-:B4:1 pla-:B4:2 ci-:A4:1 an:G4:1 of:A4:1 u:B4:2"),
    ("v2e", "lead", 24, 0, "When it's zero it's balanced",
     "When:C5:1 it's:B4:1 ze-:A4:1 ro:A4:1 it's:A4:1 bal-:A4:1 anced:A4:1"),
    ("v2f", "lead", 24, 7, "each point's the average of its crew",
     "each:F4:1 point's:A4:1 the:C5:1 av-:C5:1 rage:A4:1 of:G4:1 its:F4:1 crew:A4:2"),
    ("v2g", "lead", 26, 0, "soap films steady heat",
     "soap:A4:2 films:F4:2 stea-:A4:1 dy:A4:1 heat:F4:2"),
    ("v2h", "lead", 27, 0, "and electric fields do it too",
     "and:D4:1 e-:G4:1 lec-:G4:1 tric:B4:1 fields:B4:1 do:A4:1 it:G4:1 too:B4:1"),
    # ---------------- final chorus ----------------
    ("f1a", "lead", 28, 0, "Laplacian",
     "La-:A4:1 pla-:C5:4 ci-:A4:1 an:F4:2"),
    ("f1a_h", "harm", 28, 0, "Laplacian",
     "La-:F4:1 pla-:A4:4 ci-:F4:1 an:C4:2"),
    ("f1b", "nbr", 29, 0, "nabla squared",
     ["na-:B4:1 bla:B4:1 squared:D5:3", "na-:G4:1 bla:G4:1 squared:B4:3", "na-:D4:1 bla:D4:1 squared:G4:3"]),
    ("f1c", "lead", 30, 0, "It's the average of your neighbors",
     "It's:D4:1 the:G4:1 av-:B4:1 rage:B4:1 of:A4:1 your:G4:1 neigh-:A4:1 bors:B4:1"),
    ("f1c_h", "harm", 30, 0, "It's the average of your neighbors",
     "It's:B3:1 the:E4:1 av-:G4:1 rage:G4:1 of:F4:1 your:E4:1 neigh-:F4:1 bors:G4:1"),
    ("f1d", "lead", 31, 0, "minus you",
     "mi-:C5:1 nus:B4:1 you:C5:4"),
    ("f1d_h", "harm", 31, 0, "minus you",
     "mi-:A4:1 nus:G4:1 you:G4:4"),
    # ---------------- tag ----------------
    ("t1", "lead", 32, 0, "And when it's zero",
     "And:C4:1 when:F4:1 it's:G4:1 ze-:Ab4:2 ro:G4:3"),
    ("t2", "lead", 33, 0, "harmonic",
     "har-:G4:2 mo-:B4:6 nic:C5:4"),
    ("t2_h1", "harm", 33, 0, "harmonic",
     "har-:D4:2 mo-:F4:6 nic:E4:4"),
    ("t2_h2", "harm", 33, 0, "harmonic",
     "har-:B3:2 mo-:D4:6 nic:C4:4"),
]

# Spoken intro (natural TTS, no pitch correction): (id, start_seconds, text)
SPOKEN = [
    ("s1", 0.55, "Hey! It's me, Claude."),
    ("s2", 2.35, "Let me explain the Laplacian..."),
    ("s3", 4.75, "with a song!"),
    ("s4", 6.75, "Hit it!"),
]

# Sound-effect cues. The composition animates on the same list, so every
# "pop" you hear is something popping on screen. (time_s, kind, label)
CUES = [
    (0.30, "boing", "clawd-lands"),
    (3.30, "sparkle", "title-nabla"),
    (4.95, "pop", "mic"),
    (7.00, "roll", "fill"),
    (8.00, "crash", "verse1"),
    (8.00, "whoosh", "to-grid"),
    (10.50, "pop", "n-east"), (10.625, "pop", "n-north"), (10.75, "pop", "n-west"), (10.875, "pop", "n-south"),
    (12.00, "whoosh", "values-fly"),
    (13.00, "ding", "avg"),
    (15.50, "ding", "result"),
    (16.00, "whoosh", "to-valley"),
    (16.00, "slide_down", "slide"),
    (19.00, "sparkle", "plus"),
    (20.00, "slide_up", "climb"),
    (23.00, "womp", "minus"),
    (22.00, "riser", "to-chorus"),
    (24.00, "impact", "chorus"),
    (26.00, "pop", "gang1"), (26.125, "pop", "gang2"), (26.25, "pop", "gang3"),
    (28.00, "whoosh", "formula"),
    (30.00, "ding", "fxx"), (31.00, "ding", "fyy"),
    (32.00, "crash", "chorus-b"),
    (34.00, "pop", "gang1b"), (34.125, "pop", "gang2b"), (34.25, "pop", "gang3b"),
    (38.00, "impact", "minus-you"),
    (39.50, "whoosh", "to-heat"),
    (42.00, "sizzle", "hot-cool"), (43.00, "chime", "cold-warm"),
    (44.00, "whoosh", "heat-eq"),
    (48.00, "bell", "zero"),
    (52.00, "pop", "soap"), (52.50, "pop", "steady"), (54.75, "zap", "electric"),
    (54.00, "riser", "to-final"),
    (56.00, "impact", "final"),
    (58.00, "pop", "gang1c"), (58.125, "pop", "gang2c"), (58.25, "pop", "gang3c"),
    (62.00, "impact", "minus-you-2"),
    (67.00, "revcymbal", "to-harmonic"),
    (68.00, "crash", "harmonic"),
    (68.00, "sparkle", "harmonic"),
    (70.50, "pop", "wink"),
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
            t += int(rest[0]) * SLOT
            continue
        note, slots = rest
        cont = syl.endswith("-")
        dur = int(slots) * SLOT
        out.append(dict(text=syl.rstrip("-"), start=t, dur=dur,
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
