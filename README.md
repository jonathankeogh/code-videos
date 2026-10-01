# The Laplacian Song — "Average of the Neighbors"

**v2 (82 s)**: cold-open stutter hook, neighbours shouting POSITIVE!/NEGATIVE!, stop-time freeze on "minus… YOU!", disco post-chorus chant ("What's the Laplacian?" / "AVERAGE MINUS YOU!"), "one more time!" key change up to D. Render: `renders/laplacian-song-v2.mp4`; v1 kept as `renders/laplacian-song-v1.mp4` (git tag history in this repo).

A ~72 s music video, written, sung, animated and rendered by Claude, with
Clawd (the Claude Code mascot) explaining the Laplacian:

- **Verse 1** — at a point, the Laplacian compares the *average of the neighbors* to the value there
  (5-point stencil: `+1` on each neighbor, `−4` in the middle, divided by `h²`).
  Valley ⇒ positive, peak ⇒ negative.
- **Chorus** — `∇²f = f_xx + f_yy`: "it's the average of your neighbors… minus YOU!"
- **Verse 2** — the heat equation `∂u/∂t = ∇²u` as peer pressure (the heat map is the exact
  heat-kernel solution, drawn live), then `∇²f = 0`: harmonic functions (soap films, steady
  heat, electric fields). The wireframe is the monkey saddle `x³ − 3xy²`, which is exactly harmonic.
- **Tag** — "and when it's zero… HAR-MO-NIC!" in three-part harmony.

Output: `renders/laplacian-song-v2.mp4` (1920×1080, 30 fps, AAC audio).

## How it was made

| Layer | Tool |
| --- | --- |
| Composition + render | [HyperFrames](https://github.com/heygen-com/hyperframes) — `index.html` is the whole video (GSAP timeline + an `hf-seek` handler for lip-sync, beat hops and canvases) |
| Voice | Kokoro-82M TTS (local) → per-phoneme timings (label lag auto-corrected) |
| Singing | WORLD vocoder (`pyworld`): each syllable re-timed so its vowel lands on the note and re-pitched to the melody, with portamento + vibrato |
| Music + SFX | synthesized from scratch with numpy (`audio-src/music.py`) |
| Mix | `audio-src/mix.py` — vocal chain, ping-pong delay, reverb, speech-band carve, limiter, −14 LUFS |

All timing (syllables, cues, mouth envelope) flows from `audio-src/song.py` →
`assets/data/song-data.js`, so the picture is locked to the audio.

## Re-render the video

```bash
cd ~/code-videos/laplacian-video
hyperframes render --output renders/laplacian-song.mp4   # or: hyperframes preview
```

`~/.local/bin/hyperframes` is a small wrapper that adds the user-space Chrome libraries
(`~/.local/opt/chrome-libs`) to `LD_LIBRARY_PATH` — this machine has no system Chrome deps.

## Regenerate the audio

```bash
uv venv audio-src/.venv && VIRTUAL_ENV=audio-src/.venv uv pip install -r audio-src/requirements.txt
# Kokoro model with a duration output (needed for phoneme timings):
#   ~/.cache/kokoro/kokoro-v1.0-v11.onnx   (github.com/thewh1teagle/kokoro-onnx, release model-files-v1.1)
#   ~/.cache/kokoro/voices-v1.0.bin
cd audio-src
../audio-src/.venv/bin/python vocals.py   # sings every line (cached per line in stems/cache)
../audio-src/.venv/bin/python music.py    # backing track + SFX stems
../audio-src/.venv/bin/python mix.py      # master wav + assets/data/song-data.js
```

Edit lyrics/melody in `audio-src/song.py` (`"syl:NOTE:eighths"` tokens), re-run the three
scripts, then re-render.

Credits: Kokoro-82M (Apache-2.0), WORLD/pyworld, GSAP, KaTeX, Fredoka & Nunito (SIL OFL).
