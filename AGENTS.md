# Repository Guidelines

## Project Structure & Module Organization
- `app.py` launches the Tkinter desktop UI; `webui.py` opens the NiceGUI browser UI. Keep both entry points runnable from the repo root.
- `core/` hosts the TTS pipeline (`epub_extract.py`, `chunking.py`, `tts_maya1_*`, `audio_combine.py`, `m4b_export.py`, `gpu_utils.py`). Add new processing steps here and keep helpers isolated in `core/utils.py`.
- `ui/` and `webui/` contain GUI layouts, themes, and dialogs; mirror their patterns when adding controls.
- `assets/` holds sample EPUBs/covers and downloaded models under `assets/models/`. Do not commit large model files.
- `output/` is git-ignored for generated WAV/M4B artifacts; `docs/` captures test reports and status notes; legacy experiments live in `test_archive/`.

## Build, Test, and Development Commands
- Create a virtual env and install deps: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- GPU wheel for llama.cpp (CUDA 12.1): `pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121`.
- Run desktop UI: `python app.py`. Run web UI (default :8080): `python webui.py --dev --port 8000`.
- Smoke the pipeline on sample text: `python test_cli.py --text "Hello world" --model assets/models/maya1.i1-Q4_K_M.gguf`.
- Validate audio + M4B flow: `python test_q4k_model.py` (chunked GGUF synthesis) and `python test_m4b_combination.py` (merge/export). Logs drop next to the script; outputs land in `output/`.

## Coding Style & Naming Conventions
- Python 3.10+ with 4-space indents, type hints where parameters or returns are non-trivial, and docstrings for public helpers. Prefer `snake_case` for functions/vars and `CapWords` for classes.
- Follow existing logging style (`logging.basicConfig` with file + stdout handlers). Avoid prints in reusable modules; reserve them for CLI scripts.
- Keep functions small, pure where possible, and colocate UI-related logic under `ui/` or `webui/` rather than `core/`.

## Testing Guidelines
- Tests are script-driven rather than pytest; run them directly with `python test_<name>.py` from the repo root.
- Use bundled fixtures in `assets/test/` to avoid external downloads; expect outputs in `output/` (git-ignored). Clean large artifacts before pushing.
- When adding new scripts, accept `--model`, `--chunk-size`, and output path flags to match existing ergonomics.

## Commit & Pull Request Guidelines
- Write imperative, scoped commits (`feat: add vllm backend chunking guard`) and keep them small. Reference related issues in the body.
- PRs should explain the user impact, list test commands run, and include screenshots or terminal output for UI/UX or audio-facing changes.
- Avoid committing model weights or generated audio; confirm `.gitignore` coverage for new output directories.
