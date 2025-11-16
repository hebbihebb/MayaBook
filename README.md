# **MayaBook**

**EPUB → TTS → M4B Audiobook Generator**

MayaBook is a work in progress application that converts EPUB books into high-quality narrated audiobooks (M4B/WAV formats).
It uses the **[Maya1](https://huggingface.co/maya-research/maya1)** voice model running locally via **GGUF quantized models** and `llama-cpp-python` to generate expressive, human-like speech with GPU acceleration.

![MayaBook GUI](screenshot.jpg)

**Version:** 2.1 Audiobook Focus
**Status:** Production Ready ✓

---

## ✨ **Overview**

**Input:** EPUB file(s)
**Process:** extract text → synthesize with local Maya1 GGUF → generate WAV audio → merge → create M4B
**Output:** Professional audiobook with chapters, metadata, and optional cover art

### Key Features

* **100% Local Processing** - No cloud services, API keys, or internet required
* **GPU Acceleration** - Automatic GPU detection with intelligent VRAM management
* **Voice Presets Library** - 15+ curated professional voices with instant preview
* **Batch Processing** - Queue multiple books for overnight processing
* **Chapter Support** - Automatic chapter detection with M4B export
* **Configuration Profiles** - Genre-specific presets (Fiction, Non-Fiction, Poetry, etc.)
* **Advanced Audio Tools** - Normalization, silence detection, speech rate control
* **Smart Defaults** - Auto-detection of models, files, and optimal settings
* **Expressive Speech** - Emotion tag support (`<laugh>`, `<cry>`, `<angry>`, etc.)

---

## 🧠 **How It Works**

1. **Extract Text**
   The app reads an EPUB, cleans it to plain text, and splits it into small chunks (recommended: 70-80 words per chunk for optimal TTS quality and to avoid token limit issues).

2. **Generate Audio Locally**
   Each chunk is synthesized using either:

   **GGUF Model (Recommended)** via `llama-cpp-python`:
   * Fast GPU-accelerated inference with CUDA
   * Uses quantized models (Q4_K_M, Q5_K_M, Q8_0)
   * Lower VRAM usage (~6-8GB for Q5_K_M)
   * Proven stable for production use

   **HuggingFace Transformers (Experimental)** via `transformers` + `bitsandbytes`:
   * 4-bit quantized safetensor models
   * Higher quality potential with full precision weights
   * Requires more VRAM (~10-12GB)
   * Supports emotion tags and advanced prompting
   * **Note**: As of 2025-11-14, HF implementation fixed with proper EOS token handling

   For both methods:
   * The model generates SNAC audio tokens from text and voice description
   * SNAC codec decodes tokens into 24 kHz audio waveforms
   * Each chunk is saved as a temporary WAV file
   * Multi-threaded synthesis processes multiple chunks in parallel
   * Supports **emotion tags** like `<laugh>`, `<cry>`, `<angry>` for expressive speech (see [EMOTION_TAGS.md](EMOTION_TAGS.md))

3. **Combine Audio**
   All chunk WAVs are concatenated into a single `book.wav`, with configurable silence gaps between chunks.

4. **Export M4B**
   Audio is encoded to M4B audiobook format with chapters and metadata:

   * AAC encoding for efficient file size
   * Embedded chapter markers for navigation
   * Metadata tags (title, author, genre, etc.)
   * Optional cover art support
   * No video encoding (pure audiobook format)

---

## 🖥️ **User Interfaces**

MayaBook offers two powerful interfaces to suit your workflow:

### Desktop GUI (`app.py`) - **Recommended**
**Unified Tkinter interface combining all features:**

**Core Features:**
* **File Selection:** EPUB, cover image, model, output folder pickers
* **Voice Presets:** 15+ professional voices with instant preview playback
* **Quick Test Mode:** Test TTS without EPUB for rapid iteration
* **Chapter Selection:** Visual dialog to choose specific chapters
* **Real-time Progress:** Progress bar with chunk-level tracking
* **M4B Export:** Chapter-aware audiobook format with metadata
* **Audio Playback:** In-app voice preview with pygame

**Enhanced Features:**
* **GPU Auto-Detection:** Real-time VRAM monitoring with auto-configuration
* **Smart Defaults:** Auto-locate models, EPUBs, and cover images (Ctrl+D)
* **Configuration Profiles:** 6 built-in genre presets + custom profiles
* **Auto-Find Cover:** Automatically locate matching cover images
* **Keyboard Shortcuts:** Ctrl+D (defaults), Ctrl+G (generate), Ctrl+E (extract), Ctrl+O (open folder), Ctrl+S (save), Ctrl+Q (quit)
* **Settings Persistence:** Automatically saves and restores your last settings
* **Menu System:** Profile management, GPU tools, help documentation

All implemented with **Tkinter** for zero-dependency cross-platform compatibility.

### Web UI (`webui.py`) - **NEW! v2.0 Enhanced**
**Browser-based interface with modern design:**
* **Local Network Access:** Use from any device on your network (phone, tablet, laptop)
* **Modern Design:** Warm brown theme with orange accents, inspired by Claude Code
* **Tab-Based Layout:** Files & Model, Voice & TTS, Output & Metadata, Quick Test, Generate
* **GPU Auto-Detection:** Real-time GPU status with VRAM info display
* **Auto-Configuration:** One-click GPU optimization button
* **Smart Defaults:** Auto-populate model/EPUB/cover paths with single click
* **Real-time Updates:** Live progress bars, streaming logs, and status indicators
* **File Upload/Download:** Drag-and-drop EPUB/cover uploads, direct download of outputs
* **Voice Presets & Preview:** All 15+ voice presets with in-browser preview generation
* **Quick Test:** Test TTS without EPUB for rapid iteration
* **Model Auto-Detection:** Dropdown selection of all detected GGUF models
* **Independent Operation:** Runs standalone without interfering with CLI/Tkinter UIs
* **Full Feature Parity:** All core features from desktop GUI available in the browser

**Quick Start:**
```bash
python webui.py                    # Launch on http://localhost:8080
python webui.py --port 8000        # Custom port
python webui.py --host 0.0.0.0     # Local network access (default)
```

Access from any device: `http://YOUR_IP:8080`

See **[webui/README.md](webui/README.md)** for complete web UI documentation.

---

## ⚙️ **Dependencies**

### Core Python Packages (Required)

```bash
ebooklib          # EPUB parsing
beautifulsoup4    # HTML text extraction
llama-cpp-python  # GGUF model inference (GPU-accelerated)
snac              # Maya1 audio codec
soundfile         # WAV file I/O
numpy             # Audio processing
torch             # GPU operations
platformdirs      # Cross-platform config storage
pygame            # Audio preview playback
nicegui           # Web UI framework (for webui.py)
```

### Optional Packages (Enhanced Features)

```bash
librosa           # Advanced audio processing (speech rate, analysis)
transformers      # HuggingFace model support (experimental)
bitsandbytes      # 4-bit quantization (Linux only)
accelerate        # Multi-GPU support
```

### System Requirements

* **Python:** 3.10+ (tested with 3.13)
* **FFmpeg:** Required in PATH for M4B audiobook export
* **GPU:** NVIDIA CUDA-compatible GPU strongly recommended
  - VRAM: 8GB+ for Q5_K_M model
  - CPU-only mode supported but 50x slower
* **Storage:** ~20GB for model + temp files during synthesis
* **OS:** Windows 10/11, Linux, macOS (Intel/Apple Silicon)

### Model Files (Download Separately)

* **Maya1 GGUF Model** (~12-15GB) - **Recommended for most users**
  - Download: [https://huggingface.co/maya-research/maya1](https://huggingface.co/maya-research/maya1)
  - Recommended: `maya1.i1-Q5_K_M.gguf` (best quality/speed balance, ~15GB)
  - Alternative: `maya1.i1-Q4_K_M.gguf` (faster, lower VRAM, slightly lower quality, ~12GB)
  - Higher quants: `maya1.i1-Q8_0.gguf` (maximum quality, ~25GB, slower)

* **Maya1 HuggingFace Model** (~6-8GB) - **Experimental, for advanced users**
  - Download: [https://huggingface.co/maya-research/maya1](https://huggingface.co/maya-research/maya1) (safetensor format)
  - Uses 4-bit quantization via bitsandbytes (Linux only)
  - Requires transformers, accelerate, bitsandbytes packages
  - Select "huggingface" model type in GUI
  - **Known Issue**: Full-book processing may have quality issues; best for testing/experimentation

---

## 🚀 **Installation**

### 1. Clone the Repository

```bash
git clone https://github.com/hebbihebb/MayaBook
cd MayaBook
```

### 2. Set Up Python Environment

```bash
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
# OR
.venv\Scripts\activate       # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Install GPU-Accelerated llama-cpp-python (Recommended)

**For NVIDIA GPUs with CUDA 12.1+:**
```bash
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

**For other CUDA versions:**
- CUDA 11.8: Replace `cu121` with `cu118`
- CPU-only: Skip this step (default CPU version will be used)

### 4. Install Optional Enhanced Features

```bash
pip install pygame      # Voice preview playback (recommended)
pip install librosa     # Advanced audio processing (optional)
```

### 5. Download the Maya1 GGUF Model

**Option A: Manual Download**
1. Visit: https://huggingface.co/maya-research/maya1
2. Download: `maya1.i1-Q5_K_M.gguf` (~15GB)
3. Place in: `assets/models/maya1.i1-Q5_K_M.gguf`

**Option B: Command Line (with huggingface-cli)**
```bash
pip install huggingface-hub
mkdir -p assets/models
cd assets/models
huggingface-cli download maya-research/maya1 maya1.i1-Q5_K_M.gguf --local-dir .
```

### 6. Verify Installation

```bash
# Test model detection
python -c "from core.gpu_utils import get_gpu_info; print(get_gpu_info())"

# Test FFmpeg
ffmpeg -version

# Launch GUI
python app.py
```

---

## ▶️ **Usage**

### Quick Start (Standard Edition)

1. **Launch the Application**
   ```bash
   python app.py
   ```

2. **First-Time Setup**
   - Select your EPUB file
   - Choose a cover image (auto-detected if named similarly to EPUB)
   - Browse to the GGUF model file (or use auto-detected path)
   - Select output folder

3. **Choose a Voice**
   - Use the **Voice Presets** dropdown to select from 15+ professional voices:
     - Professional Female Narrator
     - Authoritative Male (Morgan Freeman-style)
     - Young Adult Female (Energetic)
     - Distinguished British Male
     - Soothing Female (Bedtime Stories)
     - And more...
   - Click **Preview Voice** to hear a sample before generating

4. **Configure Settings** (Optional)
   - **Temperature:** 0.45 (default) - Controls creativity (0.3-0.5 recommended)
   - **Top-p:** 0.92 (default) - Nucleus sampling (0.88-0.95 recommended)
   - **Chunk Size:** 70 words (default) - Prevents token overflow
   - **Gap:** 0.25s (default) - Silence between chunks

5. **Generate Audiobook**
   - Click **Extract EPUB** to preview text
   - Click **Start Generation** to begin synthesis
   - Monitor progress bar and log output
   - Use **Cancel** to stop if needed

6. **Output Files**
   - **M4B:** Audiobook format with chapters and metadata (optional cover art)
   - **WAV:** Lossless audio file
   - Click **Open Output Folder** to access files

### Power User Tips

1. **Use Keyboard Shortcuts**
   - **Ctrl+D** - Load smart defaults (auto-detects all files)
   - **Ctrl+E** - Extract EPUB
   - **Ctrl+G** - Start generation
   - **Ctrl+O** - Open output folder
   - **Ctrl+S** - Save settings
   - **Ctrl+Q** - Quit

2. **Auto-Configure GPU**
   - Click **Auto-Configure GPU** in GPU Status banner
   - Or click **Refresh** to update VRAM info

3. **Use Configuration Profiles**
   - Profiles → Load built-in profiles (Fiction, Non-Fiction, Poetry, etc.)
   - Profiles → Save Current as Profile for custom presets
   - Quick-switch via dropdown in menu

### Advanced Features

**Emotion Tags** - Add expressiveness to narration:
```
The crowd erupted. <laugh>This was incredible!</laugh>
She looked away. <cry>I can't believe it's over.</cry>
He slammed his fist down. <angry>Enough!</angry>
```
See [EMOTION_TAGS.md](EMOTION_TAGS.md) for full list.

**Pronunciation Dictionary** - Fix difficult words:
```python
from core.audio_advanced import PronunciationDictionary
pron_dict = PronunciationDictionary()
pron_dict.add("Hermione", "Her-my-oh-nee")
```

**Configuration Profiles** - Save/load complete settings:
- Menu → Profiles → Save Current as Profile
- Quick-switch via dropdown

---

## 🧩 **Project Structure**

```
MayaBook/
│
├─ app.py                          # Main GUI entry point (standard edition)
├─ test_cli.py                     # CLI testing tool
├─ diagnose_audio.py               # Audio quality analysis tool
├─ requirements.txt                # Python dependencies
│
├─ core/                           # Core processing modules
│   ├─ maya1_constants.py          # SNAC token constants
│   ├─ tts_maya1_local.py          # GPU-accelerated GGUF synthesis
│   ├─ epub_extract.py             # EPUB → text extraction
│   ├─ chunking.py                 # Text → word-based chunks
│   ├─ audio_combine.py            # WAV concatenation
│   ├─ m4b_export.py               # M4B audiobook export with chapters
│   ├─ video_export.py             # DEPRECATED: MP4 video export (legacy)
│   ├─ pipeline.py                 # End-to-end orchestration
│   │
│   ├─ voice_presets.py            # Voice preset library (15+ voices)
│   ├─ voice_preview.py            # Voice sample generation & caching
│   │
│   ├─ gpu_utils.py                # GPU detection & VRAM management
│   ├─ config_manager.py           # Configuration profiles & smart defaults
│   ├─ progress_tracker.py         # ETA calculation & progress metrics
│   ├─ batch_processor.py          # Multi-book queue processing
│   └─ audio_advanced.py           # Advanced audio tools (normalization, etc.)
│
├─ ui/                             # GUI implementations
│   ├─ main_window.py              # Unified Tkinter GUI (all features)
│   └─ chapter_selection_dialog.py # Chapter selection dialog
│
├─ webui/                          # Web UI (NiceGUI-based)
│   ├─ __init__.py                 # Module initialization
│   ├─ theme.py                    # Claude Code-inspired theme/CSS
│   ├─ app.py                      # Main web application
│   └─ README.md                   # Web UI documentation
│
├─ webui.py                        # Web UI entry point
│
├─ assets/
│   ├─ models/                     # GGUF model files (gitignored, ~15GB)
│   └─ test/                       # Sample EPUB/images for testing
│
├─ README.md                       # This file (main documentation)
├─ CLAUDE.md                       # Developer documentation & internal notes
└─ EMOTION_TAGS.md                 # Emotion tag reference guide
```

---

## 🧱 **Design Principles**

* **Fully local processing** - No external servers or API calls
* **GPU acceleration** - Leverages CUDA for fast synthesis
* **Modular architecture** - Each stage (EPUB, TTS, audio, video) is independently testable
* **Thread safety** - Multi-threaded synthesis with proper locking
* **Cross-platform** - Works on Windows/macOS/Linux
* **Minimal dependencies** - Clean, focused codebase
* **Easy to extend** - Add features like chapter markers or multi-voice support

---

## ✅ **What's New in v2.0 Enhanced Edition**

**Major Features Added:**
- ✅ M4B/M4A audiobook export with automatic chapter detection
- ✅ Intelligent GPU configuration with VRAM monitoring
- ✅ Smart default file selection and auto-detection
- ✅ Voice preset library (15+ professional voices)
- ✅ Voice preview with caching
- ✅ Batch processing for multiple EPUBs
- ✅ Configuration profiles (6 built-in genre presets)
- ✅ Enhanced progress tracking with ETA
- ✅ Keyboard shortcuts (Ctrl+D, Ctrl+G, Ctrl+E, etc.)
- ✅ Advanced audio tools (normalization, silence detection, speech rate)
- ✅ Pronunciation dictionary
- ✅ Real-time VRAM usage monitoring

**Bug Fixes:**
- ✅ Fixed EPUB paragraph extraction (non-breaking space handling)
- ✅ Fixed KV cache state bleeding between chunks (GGUF)
- ✅ Fixed token limit overflow (optimized chunk size to 70 words)
- ✅ Fixed HuggingFace EOS token handling (CODE_END_TOKEN_ID, repetition_penalty)
- ✅ Enhanced diagnostic logging

**Experimental Features:**
- ✅ HuggingFace transformers support with 4-bit quantization
- ✅ Safetensor model loading (GPU-accelerated with bitsandbytes)
- ⚠️ HF model quality testing in progress

---

## ❌ **Current Limitations**

* **Multi-voice narration:** Single narrator per book (dialogue uses same voice)
* **Forced alignment:** No word-level timestamps or sync data
* **Cloud integration:** Fully local only (no API support)
* **Streaming:** Must complete full synthesis before playback
* **Platform limitations:**
  - bitsandbytes (4-bit quantization) only on Linux
  - HuggingFace safetensor path experimental (GGUF strongly recommended for production)
* **HuggingFace model notes:**
  - Best for short-form content and testing
  - Full-book processing may produce lower quality audio
  - Legacy mode (non-chapter-aware) uses truncated preview text - **always use chapter-aware mode**

---

## 🚀 **Planned Improvements**

Based on analysis of the **VLLM streaming inference implementation** and the **official Maya1 HuggingFace quick start guide**, the following improvements could enhance MayaBook's audio quality and reliability:

### Analysis Summary

**Sources Analyzed:**
1. [VLLM Streaming Inference Reference](https://github.com/maya-research/maya1) - Advanced streaming TTS with sliding window approach
2. [Official Maya1 Quick Start Guide](https://huggingface.co/maya-research/maya1) - Reference implementation from Maya Research team

**Key Findings:**
- ✅ **Our implementation is validated**: SNAC unpacking, warmup trimming, and repetition_penalty all match official recommendations
- ⭐ **Missing parameters**: `min_new_tokens=28`, `do_sample=True`, `eos_token_id`, `pad_token_id` should be added to HF path
- 📊 **Debug logging**: Official guide includes extensive token diagnostics - we should adopt this
- 🎨 **Prompt building**: HF path should use string-based approach (official method) instead of manual token IDs
- 🎵 **Audio quality**: Crossfade concatenation (from VLLM) could eliminate chunk boundary artifacts

**Validation:**
- Our GGUF implementation is **production-ready** and matches best practices
- Our HF implementation needs minor updates to match official guide
- All improvements are incremental enhancements, not critical fixes

---

### Priority 1: Crossfade Audio Concatenation ⭐

**Goal:** Eliminate pops/clicks at chunk boundaries by using overlapping crossfade instead of simple silence gaps.

**Current Implementation:** [audio_combine.py](core/audio_combine.py) uses fixed-duration silence gaps (default 250ms).

**Proposed Implementation:**
```python
def concat_wavs_with_crossfade(
    wav_paths: list[str],
    out_path: str,
    crossfade_ms: int = 100,
    sr: int = 24000
) -> str:
    """
    Concatenate WAV files with linear crossfade overlap.

    Steps:
    1. Read each chunk WAV file as float32 array
    2. For chunks N and N+1:
       - Extract last 100ms of chunk N
       - Extract first 100ms of chunk N+1
       - Create crossfade: fade_out(chunk_N_end) + fade_in(chunk_N+1_start)
    3. Combine all chunks with crossfade regions
    4. Write final concatenated audio

    Benefits:
    - Smooth transitions eliminate click artifacts
    - Natural audio flow without artificial silence
    - Better quality for expressive/emotional speech
    """
```

**Implementation Details:**
- Add new function in [core/audio_combine.py](core/audio_combine.py)
- Use linear fade (can be upgraded to cosine fade for even smoother transitions)
- Make crossfade duration configurable (default 100ms, range 50-200ms)
- Add UI checkbox: "Use Crossfade" with duration slider
- Fallback to gap-based concat if crossfade fails
- Formula: `crossfade[i] = chunk_A[i] * (1 - fade) + chunk_B[i] * fade`
  where `fade` ranges from 0 to 1 linearly

**Files to Modify:**
- `core/audio_combine.py` - Add `concat_wavs_with_crossfade()` function
- `core/pipeline.py` - Add `use_crossfade` parameter, call new function if enabled
- `ui/main_window.py` - Add crossfade checkbox and duration slider
- `webui/app.py` - Add crossfade toggle in Output & Metadata tab

**Testing:**
```bash
# Compare gap-based vs crossfade concatenation
python test_cli.py --crossfade --crossfade-duration 100
python diagnose_audio.py output/test_gap.wav output/test_crossfade.wav
```

---

### Priority 2: Enhanced Documentation

**Goal:** Match VLLM reference code's documentation quality with detailed docstrings and visual diagrams.

**Current State:** Basic docstrings with limited technical detail.

**Proposed Improvements:**

**File: [core/tts_maya1_local.py](core/tts_maya1_local.py)**
```python
def _unpack_snac_from_7(snac_ids: list[int]):
    """
    Unpack 7-token SNAC frames into 3-level hierarchical codes.

    This is the EXACT INVERSE of Maya1's training preprocessing.

    SNAC Frame Structure (7 tokens per frame):
    ┌───────────────────────────────────────────────────────┐
    │ [slot0, slot1, slot2, slot3, slot4, slot5, slot6]    │
    └───────────────────────────────────────────────────────┘
         │      │      │      │      │      │      │
         ▼      ▼      ▼      ▼      ▼      ▼      ▼
        L1    L2[0]  L3[0]  L3[1]  L2[1]  L3[2]  L3[3]

    Hierarchical Unpacking to [L1, L2, L3]:
    - slot0 → L1[i]       (coarse: 1x rate,  n frames)
    - slot1 → L2[2*i]     (medium: 2x rate, 2n codes, even indices)
    - slot2 → L3[4*i+0]   (fine:   4x rate, 4n codes)
    - slot3 → L3[4*i+1]   (fine:   4x rate, 4n codes)
    - slot4 → L2[2*i+1]   (medium: 2x rate, 2n codes, odd indices)
    - slot5 → L3[4*i+2]   (fine:   4x rate, 4n codes)
    - slot6 → L3[4*i+3]   (fine:   4x rate, 4n codes)

    Token Range:
    - Input:  128266-156937 (vocab IDs from model)
    - Output: 0-4095 (SNAC codes, 4096 per level)
    - Formula: snac_code = (vocab_id - 128266) % 4096

    Args:
        snac_ids: List of SNAC token IDs (vocab space), length divisible by 7

    Returns:
        [L1, L2, L3] where len(L1)=n, len(L2)=2n, len(L3)=4n
    """
```

**File: [core/maya1_constants.py](core/maya1_constants.py)**
```python
"""
Maya1 Model Token Constants

These constants define the special tokens used by the Maya1 TTS model
for structuring prompts and controlling audio generation.

Token Layout:
    SOH_ID (128259)         - Start of Header
    EOH_ID (128260)         - End of Header
    SOA_ID (128261)         - Start of Audio
    CODE_START_TOKEN_ID     - Start of SNAC codes (128257)
    CODE_END_TOKEN_ID       - End of SNAC codes (128258, stops generation)
    TEXT_EOT_ID (128009)    - End of text content

SNAC Token Range:
    CODE_TOKEN_OFFSET (128266) - First SNAC token ID
    SNAC_MIN_ID (128266)       - Minimum valid SNAC token
    SNAC_MAX_ID (156937)       - Maximum valid SNAC token
                                 Calculated as: 128266 + (7 * 4096) - 1

SNAC Frame Structure:
    SNAC_TOKENS_PER_FRAME (7)  - Each audio frame = 7 tokens
                                 Tokens are hierarchical: [L1, L2a, L3a, L3b, L2b, L3c, L3d]
"""
```

**Implementation Steps:**
1. Update all docstrings in [core/tts_maya1_local.py](core/tts_maya1_local.py)
2. Add visual ASCII diagrams for complex logic
3. Document token ID ranges and formulas
4. Add "See Also" references between related functions
5. Include example inputs/outputs in docstrings

---

### Priority 3: Token Validation with Diagnostic Logging ⭐

**Goal:** Detect and log when model generates invalid tokens (helps debug model issues).

**Validation:** The [official Maya1 quick start guide](https://huggingface.co/maya-research/maya1) includes extensive debug logging - this approach is **officially recommended**.

**Current Implementation:** Silent filtering in `_extract_snac_ids()` ([tts_maya1_local.py:62-67](core/tts_maya1_local.py#L62-L67))

**Proposed Implementation:**
```python
def _extract_snac_ids(token_ids: list[int]) -> list[int]:
    """
    Extract valid SNAC tokens from generation output.

    Filters tokens to only include valid SNAC range (128266-156937).
    Logs warnings if invalid tokens are encountered (helps debug model issues).
    """
    # Find EOS or use full sequence
    try:
        end = token_ids.index(CODE_END_TOKEN_ID)
    except ValueError:
        end = len(token_ids)

    # Separate valid and invalid tokens
    valid_snac = []
    invalid_tokens = []

    for token_id in token_ids[:end]:
        if SNAC_MIN_ID <= token_id <= SNAC_MAX_ID:
            valid_snac.append(token_id)
        elif token_id != CODE_END_TOKEN_ID:
            invalid_tokens.append(token_id)

    # Log diagnostics
    if invalid_tokens:
        logger.warning(
            f"Found {len(invalid_tokens)} non-SNAC tokens in generation "
            f"(total tokens: {len(token_ids[:end])}). "
            f"Sample invalid tokens: {invalid_tokens[:10]}"
        )
        logger.debug(f"Valid SNAC tokens extracted: {len(valid_snac)}")

    return valid_snac
```

**Implementation Steps:**
1. Modify `_extract_snac_ids()` in [core/tts_maya1_local.py](core/tts_maya1_local.py)
2. Add warning logs for invalid tokens
3. Include token distribution stats in debug logs
4. Help users identify model configuration issues

**Benefits:**
- Early detection of prompt formatting issues
- Identify when model "hallucinates" text tokens instead of audio
- Better debugging for custom voice descriptions

---

### Priority 4: Add `min_tokens` Parameter ⭐

**Goal:** Ensure minimum generation length to prevent truncated audio.

**Validation:** The [official Maya1 quick start guide](https://huggingface.co/maya-research/maya1) uses `min_new_tokens=28` - this is **officially recommended**.

**Current Implementation:** Only RMS quality check prevents bad audio.

**Proposed Implementation:**
```python
def synthesize_chunk_local(
    model_path: str,
    text: str,
    voice_description: str,
    temperature: float = 0.4,
    top_p: float = 0.9,
    max_tokens: int = 2048,
    min_tokens: int = 28,  # NEW: At least 4 SNAC frames (4 * 7 = 28)
    n_ctx: int = 4096,
    n_gpu_layers: int | None = None,
) -> str:
    """
    Synthesize speech chunk with GGUF model.

    Args:
        min_tokens: Minimum tokens to generate (prevents early EOS).
                    Default 28 = 4 SNAC frames, ~0.17s of audio.
    """
    # ... existing code ...

    out = llm(
        prompt=prompt_tokens,
        max_tokens=max_tokens,
        min_tokens=min_tokens,  # NEW: Force minimum generation
        temperature=temperature,
        top_p=top_p,
        repeat_penalty=1.1,
        echo=False,
        seed=seed,
    )
```

**Implementation Steps:**
1. Add `min_tokens` parameter to `synthesize_chunk_local()` in [core/tts_maya1_local.py](core/tts_maya1_local.py)
2. Pass to `llm()` call (check if llama-cpp-python supports `min_tokens` parameter)
3. Add `min_new_tokens` to HF generation in [core/tts_maya1_hf.py](core/tts_maya1_hf.py) (definitely supported)
4. Add UI slider in Advanced Settings (range: 14-56, default 28)
5. Document relationship: 7 tokens = 1 frame ≈ 0.042s audio @ 24kHz

**Benefits:**
- Prevents model from stopping too early
- Backup safety net to RMS quality check
- Useful for very short chunks or edge cases
- **Officially recommended by Maya Research team**

---

### Priority 5: HuggingFace Generation Parameters

**Goal:** Add missing generation parameters to match official Maya1 quick start guide.

**Validation:** The [official Maya1 quick start guide](https://huggingface.co/maya-research/maya1) explicitly sets these parameters.

**Current Implementation:** [core/tts_maya1_hf.py](core/tts_maya1_hf.py) is missing several recommended parameters.

**Proposed Implementation:**
```python
# In core/tts_maya1_hf.py - synthesize_chunk_hf() function
outputs = model.generate(
    input_ids,
    max_new_tokens=max_tokens,
    min_new_tokens=28,  # NEW: At least 4 SNAC frames (from Priority 4)
    temperature=temperature,
    top_p=top_p,
    repetition_penalty=1.1,
    do_sample=True,  # NEW: Explicitly enable sampling
    eos_token_id=CODE_END_TOKEN_ID,  # NEW: Explicit EOS token (128258)
    pad_token_id=tokenizer.pad_token_id,  # NEW: Prevent padding warnings
)
```

**Implementation Details:**
- `do_sample=True` - Explicitly enables sampling (currently relies on default)
- `eos_token_id=CODE_END_TOKEN_ID` - Forces model to stop at audio end token
- `pad_token_id=tokenizer.pad_token_id` - Prevents "pad_token_id not set" warnings

**Files to Modify:**
- `core/tts_maya1_hf.py` - Update `synthesize_chunk_hf()` function
- `core/maya1_constants.py` - Already has CODE_END_TOKEN_ID defined

**Implementation Steps:**
1. Import CODE_END_TOKEN_ID in [core/tts_maya1_hf.py](core/tts_maya1_hf.py)
2. Add three new parameters to `model.generate()` call
3. Test with sample text to verify no warnings
4. Confirm EOS token properly terminates generation

**Benefits:**
- Matches official reference implementation
- Eliminates warning messages
- More predictable generation behavior
- Explicit parameters improve code clarity

**Testing:**
```bash
# Test HF generation with new parameters
python test_cli.py --model-type huggingface --text "Test sentence." --output output/test_hf
# Check logs for warnings - should be none
# Verify EOS token in generated tokens
```

---

### Priority 6: Alternative Prompt Building Approach

**Goal:** Adopt the official string-based prompt building method for HuggingFace path.

**Validation:** The [official Maya1 quick start guide](https://huggingface.co/maya-research/maya1) uses tokenizer.decode() approach.

**Current Implementation:**
- **GGUF path** ([tts_maya1_local.py](core/tts_maya1_local.py)): Builds prompt as token ID list directly (efficient, keep as-is)
- **HF path** ([tts_maya1_hf.py](core/tts_maya1_hf.py)): Uses similar token ID approach

**Proposed Implementation (HF path only):**
```python
# In core/tts_maya1_hf.py - Add new helper function

def _build_prompt_string(tokenizer, description: str, text: str) -> str:
    """
    Build formatted prompt for Maya1 using official string-based approach.

    This matches the reference implementation from Maya Research.
    Decodes special tokens to strings, builds prompt, then tokenizes.

    Official format:
    <SOH><BOS><description="voice"> text<EOT><EOH><SOA><SOS>

    Args:
        tokenizer: HuggingFace tokenizer
        description: Voice description (e.g., "Realistic male voice...")
        text: Text to synthesize

    Returns:
        Formatted prompt string ready for tokenization

    Reference:
        https://huggingface.co/maya-research/maya1 (Quick Start Guide)
    """
    # Decode special tokens to their string representations
    soh_token = tokenizer.decode([SOH_ID])      # Start of Header
    eoh_token = tokenizer.decode([EOH_ID])      # End of Header
    soa_token = tokenizer.decode([SOA_ID])      # Start of Audio
    sos_token = tokenizer.decode([CODE_START_TOKEN_ID])  # Start of Speech
    eot_token = tokenizer.decode([TEXT_EOT_ID]) # End of Text
    bos_token = tokenizer.bos_token             # Beginning of Sequence

    # Format text with description tag
    formatted_text = f'<description="{description.strip()}"> {text.strip()}'

    # Build full prompt string
    prompt = (
        soh_token + bos_token + formatted_text + eot_token +
        eoh_token + soa_token + sos_token
    )

    return prompt


# Update synthesize_chunk_hf() to use this approach:
def synthesize_chunk_hf(
    model_path: str,
    text: str,
    voice_description: str,
    ...
) -> str:
    # ... existing model loading ...

    # NEW: Build prompt using official string-based method
    prompt_string = _build_prompt_string(tokenizer, voice_description, text)

    logger.debug(f"Prompt preview (first 200 chars): {repr(prompt_string[:200])}")
    logger.debug(f"Prompt length: {len(prompt_string)} characters")

    # Tokenize the prompt string
    inputs = tokenizer(prompt_string, return_tensors="pt")

    logger.debug(f"Input token count: {inputs['input_ids'].shape[1]} tokens")

    # ... rest of generation code ...
```

**Comparison:**

| Approach | GGUF (llama-cpp-python) | HF (transformers) Current | HF (transformers) Proposed |
|----------|-------------------------|---------------------------|----------------------------|
| Method | Direct token ID list | Token ID construction | String-based (official) |
| Efficiency | ✅ High (no decode/encode) | ✅ High | ⚠️ Medium (decode + encode) |
| Clarity | ⚠️ Manual token handling | ⚠️ Manual token handling | ✅ Matches official guide |
| Maintainability | ⚠️ Harder to debug | ⚠️ Harder to debug | ✅ Easy to understand |
| Recommendation | Keep as-is (efficient) | Upgrade to string-based | **Use this approach** |

**Why Keep GGUF Token-Based?**
- llama-cpp-python expects token IDs, not strings
- No decode/re-encode overhead
- Already working correctly
- More efficient for GGUF use case

**Why Upgrade HF to String-Based?**
- Matches official Maya Research reference implementation
- Easier to read and maintain
- Better documentation (can show actual prompt string)
- Same approach used by model creators
- Slight performance cost is negligible for audiobook generation

**Files to Modify:**
- `core/tts_maya1_hf.py` - Add `_build_prompt_string()`, update `synthesize_chunk_hf()`

**Implementation Steps:**
1. Add `_build_prompt_string()` helper function to [core/tts_maya1_hf.py](core/tts_maya1_hf.py)
2. Import SOH_ID, EOH_ID, SOA_ID, CODE_START_TOKEN_ID, TEXT_EOT_ID from maya1_constants
3. Replace existing prompt building with new function call
4. Add debug logging to show prompt string preview
5. Test with sample text to verify identical token output
6. Update docstrings to reference official guide

**Benefits:**
- Code matches official reference implementation
- Easier for new developers to understand
- Better documentation and examples
- Future-proof (follows Maya Research's recommended approach)
- Simpler debugging (can print actual prompt string)

**Testing:**
```bash
# Test HF generation with new prompt building
python test_cli.py --model-type huggingface --text "Hello world!" --output output/test_prompt

# Compare token outputs (should be identical)
# Old approach: [tokens built manually]
# New approach: [tokens from tokenizer(prompt_string)]
```

---

### Lower Priority Ideas

**7. Sliding Window Streaming** (Not Applicable)
- VLLM's streaming approach is for real-time playback
- MayaBook does batch processing (different use case)
- Crossfade already provides smooth transitions

**8. Custom Logits Processor** (Not Feasible)
- llama-cpp-python doesn't support custom logits processors
- Current token filtering approach works well
- Would require switching to VLLM (major architecture change)

**9. VLLM Migration** (Future Consideration)
- Would enable real-time streaming TTS
- Requires full bfloat16 model (~50GB vs 15GB GGUF)
- Higher VRAM requirements (16GB+ vs 8GB)
- Better for server/API use cases vs desktop audiobook conversion

---

### Implementation Timeline

**Phase 1 (Quick Wins - Based on Official Guide):**
1. Priority 5: HuggingFace generation parameters (15 minutes)
2. Priority 4: Add `min_tokens`/`min_new_tokens` (15 minutes)
3. Priority 3: Enhanced token validation logging (30 minutes)

**Phase 2 (Code Quality):**
4. Priority 2: Enhanced documentation with diagrams (1-2 hours)
5. Priority 6: Alternative prompt building for HF (45 minutes)

**Phase 3 (Audio Quality):**
6. Priority 1: Crossfade concatenation implementation (2-3 hours)
7. Priority 1: UI controls for crossfade (1 hour)
8. Testing and validation (2 hours)

**Total Estimated Time:** 8-10 hours of development work

**Recommended Order:**
- Start with Phase 1 (validates against official guide, quick wins)
- Phase 2 improves maintainability
- Phase 3 provides user-facing quality improvements

---

### Testing Plan

After implementing each improvement:
1. **Unit Tests:** Test functions in isolation
2. **Integration Tests:** Full pipeline with sample EPUB
3. **Quality Comparison:** A/B test current vs improved audio
4. **Performance Benchmarks:** Ensure no slowdown
5. **User Testing:** Gather feedback on audio quality improvements

---

## 🐛 **Troubleshooting**

### Installation Issues

**"No module named 'llama_cpp'"**
- Install: `pip install llama-cpp-python`
- For GPU: `pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121`
- Verify: `python -c "import llama_cpp; print(llama_cpp.__version__)"`

**"pygame not found" or "Audio playback not available"**
- Install: `pip install pygame`
- Alternative: `pip install simpleaudio` (may require compilation on Windows)

**"platformdirs module not found"**
- Install: `pip install platformdirs`
- Required for configuration profiles and smart defaults

### Runtime Issues

**"CUDA out of memory"**
1. Use Enhanced Edition and click **Auto-Configure GPU**
2. Manually reduce `n_gpu_layers` (try 20-30 instead of -1)
3. Reduce `n_ctx` to 2048 or lower
4. Close other GPU-intensive applications (browsers, games)
5. Use Q4 model instead of Q5 (lower VRAM usage)

**"Model file not found"**
- Verify path in GUI matches actual file location
- Check file size: ~15GB for Q5_K_M, ~12GB for Q4_K_M
- Re-download if file is corrupted (partial download)
- Use **Load Smart Defaults (Ctrl+D)** for auto-detection

**Synthesis is very slow (CPU-only mode)**
- Verify GPU is detected: Check GPU Status banner
- Install CUDA toolkit: https://developer.nvidia.com/cuda-downloads
- Reinstall llama-cpp-python with GPU support (see Installation)
- Expected speed: ~2-3 chunks/minute (GPU) vs ~0.05 chunks/minute (CPU)

**"Only last paragraph audible" or "Audio cuts off"**
- Fixed in v2.0 - update to latest version
- If persisting: Reduce chunk size to 60 words
- Check logs for "Generated 2500 total tokens" warnings

**"FFmpeg error during M4B export"**
- Install FFmpeg: https://ffmpeg.org/download.html
- Add to PATH (Windows: Edit Environment Variables)
- Verify: `ffmpeg -version` in terminal
- Restart terminal/GUI after installation
- M4B format requires FFmpeg with AAC codec support

### Audio Quality Issues

**"Silent or garbled audio"**
- Check RMS values in logs (should be > 0.001)
- Retry logic automatically triggers (up to 3 attempts)
- Try different temperature (0.40-0.50 range)
- Verify GGUF model file integrity

**"Audio has long pauses between chunks"**
- Reduce gap_seconds in settings (try 0.1-0.2)
- Use Advanced Audio → Trim Silence feature

**"Voice preview not playing"**
- Install pygame: `pip install pygame`
- Check output folder for generated preview file
- Manually open WAV file to verify it works

### Enhanced Features Issues

**"Smart Defaults not finding files"**
- Place files in standard locations:
  - Models: `assets/models/*.gguf`
  - EPUBs: `assets/test/*.epub`
- Use absolute paths if files are elsewhere
- Check file extensions match exactly (.epub, .gguf, .jpg/.png)

**"GPU not detected"**
1. Verify CUDA installation: `nvidia-smi`
2. Check torch GPU: `python -c "import torch; print(torch.cuda.is_available())"`
3. Reinstall torch: `pip install torch --index-url https://download.pytorch.org/whl/cu121`

**"Configuration profile not loading"**
- Check config file exists: `~/.config/MayaBook/config.json` (Linux/Mac) or `C:\Users\<user>\AppData\Local\MayaBook\config.json` (Windows)
- Delete config file to reset: App will recreate with defaults
- Save profile again (may have been corrupted)

**"Batch processing hangs between books"**
- Verify all EPUBs are valid (try extracting individually first)
- Check disk space (temp WAV files can be large)
- Review logs for specific error messages
- Reduce batch size and process fewer books at once

---

## 📜 **License**

MIT License - See [LICENSE](LICENSE) file for details.

You are free to:
- ✅ Use commercially
- ✅ Modify and distribute
- ✅ Use privately
- ✅ Use for any purpose

---

## ❤️ **Credits & Acknowledgments**

### Core Technologies
* **[Maya1 TTS Model](https://huggingface.co/maya-research/maya1)** - Maya Research Team
  - Revolutionary text-to-speech model with emotion support
  - SNAC audio codec for high-quality waveform generation
* **[llama.cpp](https://github.com/ggerganov/llama.cpp)** - Georgi Gerganov (ggerganov)
  - Efficient LLM inference in C/C++
  - GGUF quantization format
* **[llama-cpp-python](https://github.com/abetlen/llama-cpp-python)** - Andrei Betlen (abetlen)
  - Python bindings for llama.cpp
  - GPU acceleration support
* **[SNAC Audio Codec](https://github.com/hubertsiuzdak/snac)** - Hubert Siuzdak
  - Neural audio compression and decompression
  - 24kHz high-quality audio reconstruction

### Python Libraries
* **[ebooklib](https://github.com/aerkalov/ebooklib)** - EPUB parsing and metadata extraction
* **[BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)** - HTML text extraction
* **[PyTorch](https://pytorch.org/)** - GPU tensor operations
* **[NumPy](https://numpy.org/)** - Audio array processing
* **[SoundFile](https://github.com/bastibe/python-soundfile)** - WAV file I/O
* **[Pygame](https://www.pygame.org/)** - Audio playback for voice previews
* **[Librosa](https://librosa.org/)** - Advanced audio analysis and processing
* **[FFmpeg](https://ffmpeg.org/)** - Video/audio encoding and muxing
* **[Transformers](https://github.com/huggingface/transformers)** - HuggingFace model support
* **[bitsandbytes](https://github.com/TimDettmers/bitsandbytes)** - 4-bit quantization (Linux)

### Inspiration & Reference Projects
* **[Abogen](https://github.com/denizsafak/abogen)** by Deniz Safak
  - Audiobook generation tool that inspired MayaBook's M4B chapter support
  - Reference implementation for chapter-aware audiobook creation
  - Custom chapter marker syntax (`<<CHAPTER_MARKER:Name>>`)
  - MIT License - Thank you for pioneering local audiobook generation!

### Community
* Special thanks to the open-source community for making this project possible
* The Maya1 community for sharing knowledge and testing results
* Contributors to the HuggingFace model hub for model hosting and distribution

---

## 🤝 **Contributing**

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📞 **Support & Community**

- **Issues:** [GitHub Issues](https://github.com/hebbihebb/MayaBook/issues)
- **Discussions:** [GitHub Discussions](https://github.com/hebbihebb/MayaBook/discussions)
- **Documentation:** See [CLAUDE.md](CLAUDE.md) for developer guide
- **Emotion Tags:** See [EMOTION_TAGS.md](EMOTION_TAGS.md) for expressive narration guide
- **Web UI:** See [webui/README.md](webui/README.md) for web interface documentation

---

## 🌟 **Star History**

If you find MayaBook useful, please consider starring the repository!

[![Star History Chart](https://api.star-history.com/svg?repos=hebbihebb/MayaBook&type=Date)](https://star-history.com/#hebbihebb/MayaBook&Date)

---

**Built with ❤️ using Python, Maya1, and open-source magic**

**Version:** 2.1 Audiobook Focus | **Last Updated:** 2025-11-16
