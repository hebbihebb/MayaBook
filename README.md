# **MayaBook**

**EPUB → TTS → MP4 Narration Tool**

MayaBook is a lightweight desktop app that turns EPUB books into narrated MP4 audio files.
It uses the **[Maya1](https://huggingface.co/maya-research/maya1)** voice model running locally via **GGUF quantized models** and `llama-cpp-python` to generate expressive human-like speech.

![MayaBook GUI](screenshot.jpg)

---

## ✨ **Overview**

**Input:** an EPUB file
**Process:** extract text → synthesize with local Maya1 GGUF → generate WAV audio → merge → make MP4
**Output:** a narrated audio file with a static cover image

This project keeps things simple:

* Fully local processing with no external servers
* GPU acceleration support via `llama-cpp-python`
* Minimal Python packages and a single clean GUI
* Expressive speech synthesis with emotion tag support

---

## 🧠 **How It Works**

1. **Extract Text**
   The app reads an EPUB, cleans it to plain text, and splits it into small chunks (recommended: 70-80 words per chunk for optimal TTS quality and to avoid token limit issues).

2. **Generate Audio Locally**
   Each chunk is synthesized using the **Maya1 GGUF model** via `llama-cpp-python`:

   * The model generates SNAC audio tokens from text and voice description
   * SNAC codec decodes tokens into 24 kHz audio waveforms
   * Each chunk is saved as a temporary WAV file
   * Multi-threaded synthesis processes multiple chunks in parallel
   * Supports **emotion tags** like `<laugh>`, `<cry>`, `<angry>` for expressive speech (see [EMOTION_TAGS.md](EMOTION_TAGS.md))

3. **Combine Audio**
   All chunk WAVs are concatenated into a single `book.wav`, with configurable silence gaps between chunks.

4. **Export MP4**
   A cover image is combined with the audio using FFmpeg:

   ```bash
   ffmpeg -loop 1 -i cover.jpg -i book.wav \
          -c:v libx264 -tune stillimage -c:a aac -b:a 192k \
          -shortest output.mp4
   ```

---

## 🖥️ **GUI Features**

* **EPUB file picker**
* **Cover image selector**
* **Model path selector** (GGUF file)
* **Output folder selector**
* **GGUF configuration:** n_ctx, n_gpu_layers
* **Voice description** (multi-line text for voice characteristics)
* **Temperature / Top-p controls**
* **Chunk size / silence gap controls**
* **Buttons:** Extract EPUB · Start Generation · Cancel · Open Output Folder
* **Real-time progress bar and log area**
* **Threaded execution** (non-blocking UI)

All implemented with **Tkinter** for cross-platform simplicity.

---

## ⚙️ **Dependencies**

**Python packages**

```
ebooklib
beautifulsoup4
llama-cpp-python
snac
soundfile
numpy
torch
```

**System requirements**

* Python 3.10+
* FFmpeg in PATH (for MP4 export)
* CUDA-compatible GPU recommended (CPU inference is supported but slow)
* **Maya1 GGUF model file** (download separately, ~15GB)
  - Download from: [https://huggingface.co/maya-research/maya1](https://huggingface.co/maya-research/maya1)
  - Recommended: `maya1.i1-Q5_K_M.gguf` (quantized for efficiency)

---

## 🚀 **Installation**

### 1. Clone the repository

```bash
git clone https://github.com/<yourname>/MayaBook
cd MayaBook
```

### 2. Set up Python environment

```bash
python -m venv .venv
source .venv/bin/activate    # or .venv\Scripts\activate on Windows
pip install --upgrade pip
pip install -r requirements.txt
```

**Note:** For GPU acceleration, ensure you have CUDA installed and use:
```bash
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

### 3. Download the Maya1 GGUF model

Download the quantized GGUF model from Hugging Face:
- Visit: https://huggingface.co/maya-research/maya1
- Download: `maya1.i1-Q5_K_M.gguf` (~15GB)
- Place it in: `assets/models/maya1.i1-Q5_K_M.gguf`

Or use the command line:
```bash
mkdir -p assets/models
cd assets/models
# Use huggingface-cli or wget to download the model
# huggingface-cli download maya-research/maya1 maya1.i1-Q5_K_M.gguf
```

### 4. Create placeholder files for testing (optional)

```bash
python create_placeholders.py
```

This creates dummy files for initial testing without real assets.

---

## ▶️ **Usage**

1. **Run MayaBook**

   ```bash
   python app.py
   ```

2. **In the GUI:**

   * **Select EPUB file** - Browse to your .epub file
   * **Select cover image** - Choose a .jpg or .png for the video
   * **Select model path** - Browse to your downloaded `maya1.i1-Q5_K_M.gguf`
   * **Configure GGUF settings:**
     - `n_ctx`: Context window size (default: 4096)
     - `n_gpu_layers`: Number of layers to offload to GPU (default: -1 for all)
   * **Describe the voice** - E.g., "Female voice in her 30s, warm and expressive, natural American accent"
   * **Adjust synthesis parameters:**
     - Temperature (0.4-0.5 recommended, default: 0.45)
     - Top-p (0.9-0.95 recommended, default: 0.92)
     - Chunk size (70-80 words recommended, default: 70)
     - Gap between chunks (0.2-0.5 seconds, default: 0.25)
   * **Add emotion tags** (optional) - See [EMOTION_TAGS.md](EMOTION_TAGS.md) for supported tags like `<laugh>`, `<cry>`, etc.
   * Click **Extract EPUB** to preview the text
   * Click **Start Generation** to begin synthesis

3. **Monitor progress:**

   * Progress bar shows chunk completion
   * Log area displays real-time status
   * Use **Cancel** to stop generation early

4. **Output files:**

   The final MP4 and WAV files will be saved to your output folder.
   Click **Open Output Folder** to view them.

---

## 🧩 **Project Structure**

```
project_root/
│
├─ app.py                      # Main entry point
├─ create_placeholders.py      # Generate test files
│
├─ core/
│   ├─ maya1_constants.py      # SNAC token constants
│   ├─ tts_maya1_local.py      # Local GGUF synthesis
│   ├─ epub_extract.py         # EPUB → plain text
│   ├─ chunking.py             # Text → sentence chunks
│   ├─ audio_combine.py        # Merge WAV chunks
│   ├─ video_export.py         # FFmpeg MP4 assembly
│   └─ pipeline.py             # End-to-end orchestration
│
├─ ui/
│   └─ main_window.py          # Tkinter GUI
│
└─ assets/
    ├─ models/                 # GGUF model files (ignored by git)
    └─ test/                   # Sample EPUB and cover for testing
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

## ❌ **Current Limitations**

* Multi-voice support (single narrator only)
* Forced alignment or word-level timings
* Cloud/API integration (fully local)
* Subtitle/caption generation

---

## 🚀 **Future Enhancements**

The following features are planned for future releases:

### High Priority

1. **M4B/M4A Audiobook Format with Chapters**
   - Export to proper audiobook formats (M4B/M4A)
   - Automatically detect and preserve chapter structure from EPUB metadata
   - Add chapter markers for easy navigation in audiobook players
   - Support for chapter artwork and metadata embedding

2. **Intelligent GPU Configuration**
   - Automatic VRAM detection and optimal settings recommendation
   - Smart `n_gpu_layers` calculation based on available VRAM
   - Model size analysis (GGUF quantization level, tensor model size)
   - Real-time VRAM monitoring during synthesis
   - Warning system for potential OOM errors before generation starts

3. **Smart Default File Selection**
   - Auto-detect and pre-fill model path if found in `assets/models/`
   - Auto-detect EPUB files in `assets/test/` or designated input folder
   - Auto-detect cover images matching EPUB filename
   - Display default folder locations in GUI with tooltips
   - "Use Defaults" button to quickly populate all fields
   - Configurable default paths via settings file

### Medium Priority

4. **Voice Preset Library**
   - Curated collection of high-quality voice descriptions
   - Categories: Male/Female, Age ranges, Accents, Styles (narrative, dramatic, conversational)
   - Dropdown selection with preview examples
   - User-created preset saving and sharing
   - Example presets:
     - "Morgan Freeman-style: Deep male voice, 60s, authoritative yet warm, clear American accent"
     - "Audiobook narrator: Professional female voice, 40s, clear enunciation, neutral accent"
     - "Young adult: Energetic female voice, 20s, expressive with natural pauses"

5. **Large EPUB Stress Testing**
   - Test with full-length novels (100k+ words)
   - Benchmark synthesis times for various hardware configurations
   - Memory optimization for long-form content
   - Resume capability for interrupted synthesis
   - Chapter-by-chapter processing option for very large files

6. **HuggingFace Tensor Implementation (Linux)**
   - Complete and test the 4-bit safetensor GPU path on Linux systems
   - Compare performance with GGUF approach
   - Unified interface supporting both GGUF and tensor backends
   - Automatic backend selection based on platform and available libraries

### Low Priority / Nice to Have

7. **Enhanced UI/UX**
   - Dark mode support
   - Drag-and-drop file selection
   - Batch processing for multiple EPUB files
   - Audio preview before full generation
   - Visual waveform display of generated audio
   - Estimated time remaining during synthesis

8. **Quality of Life Improvements**
   - Configuration profiles (save/load all settings)
   - Recent files history
   - Keyboard shortcuts
   - CLI progress bars with rich formatting
   - Desktop notifications on completion

9. **Advanced Features**
   - Custom silence detection between sentences/paragraphs
   - Variable speech rate control
   - Pronunciation dictionary for proper nouns
   - Automatic retry with adjusted parameters on generation failures
   - Export logs with audio analysis metrics

---

## 🐛 **Troubleshooting**

**"No module named 'llama_cpp'"**
- Ensure you installed `llama-cpp-python`: `pip install llama-cpp-python`
- For GPU support, reinstall with CUDA wheels (see Installation section)

**"CUDA out of memory"**
- Reduce `n_gpu_layers` in the GUI (try 20-30 instead of -1)
- Reduce `n_ctx` to 2048 or lower
- Close other GPU-intensive applications

**"Model file not found"**
- Verify the GGUF file path is correct
- Ensure the file is named exactly `maya1.i1-Q5_K_M.gguf`
- Check file size (~15GB) - partial downloads will fail

**Synthesis is very slow**
- Enable GPU layers (`n_gpu_layers = -1` for all layers)
- Ensure CUDA is properly installed
- Try a more quantized model (Q4 instead of Q5)

**FFmpeg error during MP4 export**
- Install FFmpeg and add to PATH
- Verify: `ffmpeg -version` in terminal

---

## 📜 **License**

MIT License — you are free to use, modify, and distribute this project.

---

## ❤️ **Credits**

* **Maya1 Model & SNAC Codec:** [Maya Research](https://huggingface.co/maya-research/maya1)
* **llama.cpp & llama-cpp-python:** [ggerganov](https://github.com/ggerganov/llama.cpp) & [abetlen](https://github.com/abetlen/llama-cpp-python)
* **SNAC Audio Codec:** [hubertsiuzdak](https://github.com/hubertsiuzdak/snac)
* **App Design & Integration:** MayaBook contributors

---
