# code-videos

Music videos made with code: the songs are synthesized and sung in Python (Kokoro TTS + WORLD vocoder),
and the visuals are [HyperFrames](https://www.npmjs.com/package/hyperframes) compositions rendered to MP4.

| Folder | Video |
| --- | --- |
| [`laplacian-video/`](laplacian-video/) | *Average of the Neighbors* — Clawd sings an explainer on the Laplacian |
| [`claude_vids/`](claude_vids/) | *L-B-J (All the Way)* — Clawd raps through Lyndon B. Johnson's presidency |

## Setup

```bash
uv sync    # one shared Python env for every project (Python 3.12)
```

Rendering uses the HyperFrames CLI via `npx hyperframes` (needs Node + Chrome).
Rendered videos, audio stems and model files are gitignored — regenerate them with the scripts.

## Laplacian

See [`laplacian-video/README.md`](laplacian-video/README.md) for the full pipeline.

## LBJ

Needs the Kokoro model in `claude_vids/models/` (`kokoro-v1.0.onnx`, `voices-v1.0.bin`,
from [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx/releases)).

```bash
uv run claude_vids/make_song.py    # song + timing data -> claude_vids/lbj/assets/
uv run claude_vids/build_html.py   # timing data -> claude_vids/lbj/index.html
cd claude_vids/lbj && npx hyperframes render
```
