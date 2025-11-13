# Claude.md - MayaBook Project Documentation

**Internal development documentation for AI assistants and developers**

---

## Project Overview

**MayaBook** is a local EPUB-to-audiobook converter using the Maya1 TTS model. It extracts text from EPUB files, synthesizes speech using GPU-accelerated inference, and produces MP4 files with audio narration.

### Key Technologies
- **Maya1 GGUF Model**: Text-to-speech via llama-cpp-python
- **SNAC Audio Codec**: Neural audio codec for waveform generation
- **GPU Acceleration**: CUDA support via llama-cpp-python
- **Tkinter GUI**: Cross-platform desktop interface

---

## Architecture

### Core Pipeline Flow
```
EPUB File
    ↓
[epub_extract.py] → Extract & clean text
    ↓
[chunking.py] → Split into word-based chunks (70 words default)
    ↓
[tts_maya1_local.py] → Synthesize each chunk to WAV
    ↓ (parallel processing)
[audio_combine.py] → Concatenate WAV files with gaps
    ↓
[video_export.py] → FFmpeg: WAV + cover image → MP4
    ↓
Output: book.mp4 + book.wav
```

### Module Structure

#### `core/epub_extract.py`
- **Purpose**: Extract text from EPUB files
- **Key Function**: `extract_text(epub_path: str) -> str`
- **Critical Fix (2025-11-13)**:
  - Extract each `<p>` tag individually to preserve paragraph breaks
  - Replace non-breaking spaces (`\xa0`) with regular spaces
  - Prevents single-block text extraction that breaks chunking

#### `core/chunking.py`
- **Purpose**: Split text into manageable chunks for TTS
- **Key Function**: `chunk_text(s: str, max_words: int) -> list[str]`
- **Recommended**: 70 words per chunk (prevents token overflow)
- **Features**:
  - Sentence-aware splitting
  - Preserves emotion tags (`<laugh>`, `<cry>`, etc.)
  - Handles long sentences by splitting at commas

#### `core/tts_maya1_local.py`
- **Purpose**: GPU-accelerated TTS synthesis using GGUF model
- **Key Function**: `synthesize_chunk_local(...) -> str` (returns temp WAV path)
- **Critical Components**:
  - **KV Cache Management**: `llm.reset()` before each generation (prevents state bleeding)
  - **RMS Quality Check**: Retries up to 3 times if audio RMS < 0.001
  - **Deterministic Seeding**: CRC32 hash of text + voice for reproducibility
  - **Token Extraction**: Handles llama-cpp-python response format changes

- **Critical Fix (2025-11-13)**:
  - Added `llm.reset()` to prevent KV cache carryover between chunks
  - Previously, model state from chunk N affected chunk N+1, causing wrong speech generation

#### `core/audio_combine.py`
- **Purpose**: Concatenate chunk WAVs into final audio
- **Key Function**: `concat_wavs(wav_paths, out_path, gap_seconds=0.25)`
- **Features**:
  - Handles mono/stereo conversion
  - Configurable silence gaps between chunks
  - Diagnostic logging for chunk shapes and RMS values

#### `core/video_export.py`
- **Purpose**: FFmpeg wrapper to create MP4 with static cover
- **Key Function**: `export_mp4(cover_image, audio_path, output_path)`
- **FFmpeg Command**:
  ```bash
  ffmpeg -loop 1 -i cover.jpg -i audio.wav \
         -c:v libx264 -c:a aac -shortest output.mp4
  ```

#### `core/pipeline.py`
- **Purpose**: Orchestrates end-to-end conversion
- **Key Function**: `run_pipeline(...)`
- **Threading**: Multi-threaded chunk synthesis with queue-based work distribution
- **Thread Safety**: Uses locks for LLM access (llama-cpp-python not thread-safe)

---

## Critical Bug Fixes (2025-11-13)

### Bug #1: EPUB Paragraph Extraction
**Symptom**: Only one paragraph extracted from multi-paragraph EPUBs
**Cause**: Non-breaking spaces (`\xa0`) between `<p>` tags prevented `\n\n` splitting
**Fix**: Extract each `<p>` individually, normalize whitespace
**File**: `core/epub_extract.py` lines 28-44

### Bug #2: KV Cache State Bleeding
**Symptom**: First chunk generated wrong speech despite correct input text
**Cause**: llama.cpp model maintained KV cache state between generations
**Fix**: Added `llm.reset()` before each generation
**File**: `core/tts_maya1_local.py` line 116

### Bug #3: Token Limit Overflow
**Symptom**: Last portion of chunks missing from audio (truncated mid-sentence)
**Cause**: 90-word chunks required ~2500 tokens, hitting `max_tokens` limit exactly
**Fix**: Reduced default chunk size to 70 words (ensures ~1750 tokens max)
**File**: `ui/main_window.py` line 111

---

## Configuration & Parameters

### Recommended Settings

```python
# TTS Synthesis
chunk_size = 70              # words per chunk
temperature = 0.45           # model sampling temperature
top_p = 0.92                 # nucleus sampling threshold
max_tokens = 2500            # per-chunk generation limit
gap_seconds = 0.25           # silence between chunks

# GGUF Model
n_ctx = 4096                 # context window size
n_gpu_layers = -1            # -1 = offload all to GPU

# RMS Quality Check
MIN_AUDIO_RMS = 1e-3         # minimum RMS threshold
MAX_GEN_ATTEMPTS = 3         # retry attempts for silent audio
```

### Token Budget Calculation
- **Rule of thumb**: ~5 audio tokens per character of input text
- **70 words** ≈ 350 chars ≈ 1,750 tokens (safe margin below 2500)
- **90 words** ≈ 500 chars ≈ 2,500 tokens (TOO CLOSE - causes truncation)

---

## Model Details

### Maya1 GGUF Model
- **Type**: Text-to-speech transformer
- **Quantization**: Q5_K_M recommended (~15GB)
- **Input**: Text + voice description
- **Output**: SNAC audio tokens (3 layers: L1, L2, L3)
- **Sample Rate**: 24 kHz

### SNAC Audio Codec
- **Purpose**: Decode SNAC tokens → raw audio waveforms
- **Architecture**: 3-layer hierarchical codec
- **Device**: GPU (CUDA) or CPU fallback
- **Model**: `hubertsiuzdak/snac_24khz`

---

## Development Workflow

### Testing Changes
1. **CLI Testing** (faster iteration):
   ```bash
   python test_cli.py --model assets/models/maya1.i1-Q5_K_M.gguf \
                      --text "Test paragraph..." \
                      --chunk-size 70 --output output/test
   ```

2. **GUI Testing** (end-to-end):
   ```bash
   python app.py
   ```

3. **Audio Diagnostics**:
   ```bash
   python diagnose_audio.py output/test.wav
   ```

### Common Issues & Solutions

**"Only second paragraph audible"**
- Check: EPUB extraction (`epub_extract.py`)
- Fix: Ensure `<p>` tags extracted individually
- Verify: Preview text in GUI shows paragraph breaks

**"Audio cuts off mid-sentence"**
- Check: Token limit (monitor logs for "Generated 2500 total tokens")
- Fix: Reduce chunk_size or increase max_tokens
- Verify: All chunk durations < 15 seconds

**"First chunk sounds wrong"**
- Check: KV cache reset (`llm.reset()` called)
- Fix: Ensure reset happens before generation
- Verify: Logs show "Acquired LLM lock" for each chunk

**"Silent audio generated"**
- Check: RMS values in logs
- Fix: RMS retry logic should trigger automatically
- Verify: "Audio RMS for attempt N" shows retries if needed

---

## File Organization

```
project_root/
├── core/                    # Core processing modules
│   ├── epub_extract.py      # EPUB → text
│   ├── chunking.py          # Text → chunks
│   ├── tts_maya1_local.py   # TTS synthesis (GGUF)
│   ├── audio_combine.py     # WAV concatenation
│   ├── video_export.py      # MP4 creation
│   ├── pipeline.py          # Orchestration
│   └── maya1_constants.py   # SNAC token constants
│
├── ui/
│   └── main_window.py       # Tkinter GUI
│
├── assets/
│   ├── models/              # GGUF models (gitignored)
│   └── test/                # Sample EPUB/images
│
├── app.py                   # GUI entry point
├── test_cli.py              # CLI testing tool
├── diagnose_audio.py        # Audio analysis tool
└── CLAUDE.md                # This file
```

---

## Git Workflow

### Ignored Files (.gitignore)
- `*.gguf` - Model files (too large)
- `*.log` - Runtime logs
- `*.wav`, `*.mp4` - Generated output
- `DEVLOG*.md`, `*_SUMMARY.md` - Dev documentation
- `.claude/`, `.vscode/` - IDE configs

### Commit Message Format
```
type: Brief description

Detailed explanation...

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types**: `fix`, `feat`, `chore`, `docs`, `refactor`, `test`

---

## Performance Considerations

### GPU Acceleration
- **CUDA Required**: Synthesis is ~50x faster on GPU
- **VRAM Usage**: ~6-8GB for Q5_K_M model with n_gpu_layers=-1
- **Fallback**: CPU inference supported but very slow (minutes per chunk)

### Optimization Tips
1. **Parallel Synthesis**: Use workers=1 (single threaded) due to llama-cpp-python thread safety
2. **Batch Processing**: Queue-based chunk processing ensures continuous GPU utilization
3. **Chunk Size**: 70 words balances quality vs. speed (smaller = more chunks but better context)

---

## Known Limitations

1. **Single Voice**: Only one narrator voice per book
2. **No Alignment**: No word-level timestamps or forced alignment
3. **Sequential Processing**: Chunks processed one at a time (llama-cpp-python thread safety)
4. **GGUF Only**: HuggingFace safetensor path incomplete (CPU-only, no GPU)
5. **Emotion Tags**: Manual insertion required (not auto-detected from text)

---

## Future Enhancements (Ideas)

1. **Dynamic Token Limit**: Auto-adjust chunk size based on available token budget
2. **Chapter Markers**: Add MP4 chapter metadata for navigation
3. **Multi-Voice**: Support different voices for dialogue vs. narration
4. **HF GPU Support**: Complete bitsandbytes integration for safetensor models
5. **Streaming Output**: Real-time audio playback during synthesis
6. **Pronunciation Dictionary**: Custom word pronunciations
7. **SSML Support**: More advanced prosody control

---

## Debugging Tips

### Enable Verbose Logging
Check log files: `mayabook_YYYYMMDD_HHMMSS.log`

Key log patterns to search for:
```bash
# Check chunks created
grep "Text chunked into" mayabook_*.log

# Check synthesis inputs
grep "Synthesizing text" mayabook_*.log

# Check token limits
grep "Generated.*tokens" mayabook_*.log

# Check RMS values
grep "Audio RMS" mayabook_*.log

# Check concatenation
grep "Concatenating" mayabook_*.log
```

### Inspect Temporary Files
Temp WAV files preserved in: `C:\Users\<user>\AppData\Local\Temp\tmp*.wav`

Use diagnose_audio.py to check:
```bash
python diagnose_audio.py /path/to/temp/tmp*.wav
```

---

## Dependencies Deep Dive

### Critical Packages
- **llama-cpp-python**: GGUF inference engine (CUDA-enabled)
- **snac**: Audio codec model
- **torch**: Required by SNAC
- **soundfile**: WAV I/O
- **ebooklib**: EPUB parsing
- **beautifulsoup4**: HTML extraction from EPUB

### Installation Notes
```bash
# GPU-enabled llama-cpp-python (CUDA 12.1)
pip install llama-cpp-python --extra-index-url \
    https://abetlen.github.io/llama-cpp-python/whl/cu121

# Standard packages
pip install -r requirements.txt
```

---

## Troubleshooting Decision Tree

```
Audio Issue?
├── No audio at all?
│   ├── Check: Model file exists & correct path
│   ├── Check: FFmpeg installed
│   └── Check: Logs for Python exceptions
│
├── Only last paragraph audible?
│   ├── Check: EPUB extraction (paragraph count)
│   ├── Check: Chunking (number of chunks)
│   └── Fix: Restart GUI after code changes
│
├── Audio cuts off mid-chunk?
│   ├── Check: Token count in logs
│   ├── Reduce: chunk_size to 60-70 words
│   └── Increase: max_tokens to 3000
│
├── First chunk wrong speech?
│   ├── Check: llm.reset() present
│   ├── Verify: "Synthesizing text" logs match chunks
│   └── Restart: Python process to reload modules
│
└── Silent/garbled audio?
    ├── Check: RMS values in logs
    ├── Verify: Retry logic triggered
    └── Test: Different temperature/top_p values
```

---

## Version History

### v2.0 (2025-11-13) - GPU Acceleration + Bug Fixes
- ✅ GPU acceleration via llama-cpp-python CUDA wheels
- ✅ Fixed EPUB paragraph extraction (non-breaking space handling)
- ✅ Fixed KV cache state bleeding (llm.reset())
- ✅ Fixed token limit overflow (reduced chunk size to 70 words)
- ✅ Enhanced diagnostic logging
- ✅ Created audio analysis tool (diagnose_audio.py)

### v1.0 (2025-11-12) - Initial Release
- Basic EPUB → MP4 pipeline
- Tkinter GUI
- GGUF model support
- Emotion tag support
- CPU inference only

---

## Contact & Contributions

This is a personal project. For questions or contributions, refer to the GitHub repository.

---

**Last Updated**: 2025-11-13
**Maintained By**: hebbihebb
**AI Assistant**: Claude (Anthropic)
