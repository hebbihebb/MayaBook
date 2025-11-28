# MayaBook (HF-only)

MayaBook converts EPUBs into narrated audiobooks using the Maya1 HuggingFace model in full precision (bf16/fp16 on GPU). The app ships with a Tkinter desktop UI and a NiceGUI web UI; both share the same HF-only pipeline.

## Setup
- Python 3.10+
- `python -m venv .venv && source .venv/bin/activate`
- `pip install -r requirements.txt`
- Download the full Maya1 model from https://huggingface.co/maya-research/maya1 and place it at `assets/models/maya1_full/` (config.json + safetensor shards).

## Run
- Desktop UI: `python app.py`
- Web UI: `python webui.py --dev --port 8000`
- CLI smoke test: `python test_cli.py --model assets/models/maya1_full --text "Hello from Maya1."`
- HF full-model test: `python test_hf_full_model.py --model assets/models/maya1_full`

## Pipeline (EPUB ➜ WAV/M4B)
1) Extract chapters (`core/epub_extract.py`).
2) Clean text (`core/utils.clean_text`): normalize whitespace/newlines; preserve double newlines.
3) Annotate chapters with `<<CHAPTER: title>>`.
4) Chunk text (dual word/char constraints) via `core/chunking.py`.
5) Synthesize chunks with HF Maya1 (`core/tts_maya1_hf.py`, full precision).
6) SNAC decode to WAV; trim/fade joins.
7) Concatenate chunks; add silence between chapters (default 2s, chunk gap default 0).
8) Export WAV or M4B (`core/audio_combine.py`, `core/m4b_export.py`).

## Defaults
- Model path: `assets/models/maya1_full`
- Chunk gap: 0s; Chapter silence: 2s
- Temp/top_p: 0.4/0.9 (CLI/UI configurable)
- Full precision only (no quantized backends)

## Notes
- Voice previews use the same HF path and cache under `~/.mayabook/voice_previews`.
- Generated audio goes to `output/` (git-ignored).
