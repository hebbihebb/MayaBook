# **MayaBook**

**EPUB → TTS → M4B Audiobook Generator**

MayaBook is a local EPUB-to-audiobook converter that transforms your digital books into high-quality narrated audiobooks. Using the **[Maya1](https://huggingface.co/maya-research/maya1)** voice model and GPU-accelerated inference, it produces professional M4B/WAV files with expressive, natural-sounding speech.

![MayaBook GUI](screenshot.jpg)

**Version:** 2.3 Production Ready
**Status:** ✅ Fully Functional

---

## ✨ **Key Features**

* **100% Local Processing** - No cloud services, API keys, or internet required
* **GPU Acceleration** - Fast synthesis with CUDA support for NVIDIA GPUs
* **High-Quality Audio** - Professional narration with zero artifacts
* **Two Interfaces** - Desktop Tkinter GUI and modern web browser interface
* **M4B Audiobook Export** - Chapter-aware format with metadata and optional cover art
* **Voice Presets** - 15+ professional voices with instant preview
* **Batch Processing** - Queue multiple books for unattended conversion
* **Expressive Speech** - Emotion tags for dynamic narration (`<laugh>`, `<cry>`, `<angry>`, etc.)
* **Smart Defaults** - Auto-detection of models, files, and optimal settings
* **Configuration Profiles** - Genre-specific presets (Fiction, Non-Fiction, Poetry, etc.)

---

## 🧠 **How It Works**

1. **Extract Text**
   Your EPUB is parsed and cleaned into plain text, then split into optimal chunks (70 words recommended)

2. **Generate Audio**
   Each chunk is synthesized using the Maya1 model via **llama-cpp-python** with GPU acceleration:
   - **GGUF Models** (Recommended): Q4_K_M, Q5_K_M, or Q8_0 quantized versions
   - **HuggingFace Models** (Experimental): 4-bit quantized safetensor format
   - Each chunk generates SNAC audio tokens that are decoded into 24 kHz waveforms

3. **Combine Audio**
   All chunk WAV files are concatenated with configurable silence gaps between chapters

4. **Export M4B**
   Audio is encoded to M4B audiobook format with:
   - AAC encoding for efficient file size
   - Automatic chapter markers for navigation
   - Metadata tags (title, author, genre)
   - Optional cover art embedding

---

## 🖥️ **User Interfaces**

### Desktop GUI (`app.py`) - **Recommended**

A unified Tkinter application with all features in one window:

**Core Features:**
- File pickers for EPUB, cover image, models, and output folder
- 15+ voice presets with instant preview playback
- Quick test mode for rapid iteration without full EPUB processing
- Chapter selection dialog for selective narration
- Real-time progress bar with chunk-level tracking
- M4B export with automatic chapters and metadata

**Advanced Features:**
- GPU auto-detection with real-time VRAM monitoring
- Smart defaults button (Ctrl+D) to auto-locate all files
- Configuration profiles for different genres
- Keyboard shortcuts (Ctrl+G to generate, Ctrl+E to extract, etc.)
- Settings persistence across sessions
- Audio normalization and silence detection tools

**Quick Start:**
```bash
python app.py
```

### Web UI (`webui.py`) - **Modern & Accessible**

Browser-based interface with responsive design:
- Access from any device on your network (phone, tablet, laptop)
- Modern interface inspired by Claude Code
- Drag-and-drop file uploads
- Real-time progress streaming
- All voice presets with in-browser preview
- Works independently from CLI/Tkinter interfaces

**Quick Start:**
```bash
python webui.py                    # Launch on http://localhost:8080
python webui.py --port 8000        # Custom port
python webui.py --host 0.0.0.0     # Local network access
```

See [webui/README.md](webui/README.md) for complete web UI documentation.

---

## 📋 **System Requirements**

* **Python:** 3.10+ (tested with 3.13)
* **GPU:** NVIDIA CUDA-compatible GPU (8GB+ VRAM recommended)
  - CPU-only mode supported but 50x slower
* **Storage:** ~20GB for model + temporary synthesis files
* **FFmpeg:** Required in PATH for M4B audiobook export
* **OS:** Windows 10/11, Linux, macOS (Intel/Apple Silicon)

### Model Files (Download Separately)

**Maya1 GGUF Model** (~12-15GB) - **Recommended**
- Download: https://huggingface.co/maya-research/maya1
- Recommended: `maya1.i1-Q4_K_M.gguf` (~12GB, excellent quality/speed balance)
- Alternative: `maya1.i1-Q5_K_M.gguf` (~15GB, maximum quality)

**Maya1 HuggingFace Model** (~6-8GB) - Experimental
- Download: https://huggingface.co/maya-research/maya1 (safetensor format)
- Requires additional packages: `transformers`, `bitsandbytes`, `accelerate`
- Linux only for 4-bit quantization support
- **Note:** Lower quality than GGUF, use for testing only

---

## 🚀 **Installation**

### 1. Clone Repository
```bash
git clone https://github.com/hebbihebb/MayaBook
cd MayaBook
```

### 2. Create Python Environment
```bash
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
# OR
.venv\Scripts\activate       # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Install GPU-Accelerated llama-cpp-python

For **NVIDIA GPUs with CUDA 12.1+:**
```bash
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

For **other CUDA versions:**
- CUDA 11.8: Replace `cu121` with `cu118`
- CPU-only: Skip this step (default CPU version will be used)

### 4. Download Maya1 Model

**Option A: Manual Download**
1. Visit: https://huggingface.co/maya-research/maya1
2. Download: `maya1.i1-Q4_K_M.gguf` (~12GB)
3. Place in: `assets/models/maya1.i1-Q4_K_M.gguf`

**Option B: Command Line**
```bash
pip install huggingface-hub
mkdir -p assets/models
huggingface-cli download maya-research/maya1 maya1.i1-Q4_K_M.gguf --local-dir assets/models
```

### 5. Verify Installation
```bash
python app.py    # Launch GUI to verify everything works
```

---

## ▶️ **Quick Start Guide**

### 1. Launch the Application
```bash
python app.py
```

### 2. Select Your Book
- Click **Browse EPUB** and select your ebook file
- Cover image is auto-detected if it shares the EPUB filename
- Click **Browse Model** to select your GGUF model file

### 3. Choose Settings
- **Voice Preset:** Select from 15+ professional voices
  - Click **Preview Voice** to hear a sample
- **Temperature:** 0.45 (default) - Controls expression
- **Top-p:** 0.92 (default) - Controls coherence
- **Chunk Size:** 70 words (don't change unless you understand the implications)

### 4. Optional: Preview
- Click **Extract EPUB** to see the extracted text
- Use **Quick Test** to generate a short sample without full EPUB processing

### 5. Generate
- Click **Start Generation** to begin synthesis
- Monitor the progress bar and log output
- Final files appear in your selected output folder

---

## 🎯 **Usage Examples**

### Standard Audiobook Generation
```bash
python app.py
# GUI: Select EPUB → Choose voice → Click Generate
# Wait for completion (time varies with book length)
```

### Command-Line Testing
```bash
python test_cli.py --text "Hello, this is a test." --output output/test
```

### Audio Quality Analysis
```bash
python diagnose_audio.py output/mybook.wav
```

---

## 📊 **Performance Expectations**

### Generation Speed (GGUF Q4_K_M Backend)
- **Per Chunk:** ~4-5 minutes for 50-70 words
- **Speed Ratio:** ~60-75x real-time (4 min to generate 20 seconds of audio)
- **Full Book:** ~3-4 days continuous for typical novel (~6.5-7 hours audio)

### Audio Quality
- **Clarity:** Excellent, natural speech
- **Artifacts:** None detected in testing
- **Consistency:** Reliable across all chunks
- **Volume:** Properly normalized, no clipping

### Storage
- **Model File:** 12-15 GB (GGUF)
- **Temporary Files:** ~500 GB during synthesis (cleaned up automatically)
- **Final Output:** 150-200 MB (M4B, compressed)

---

## 🛠️ **Troubleshooting**

### "GPU not detected" or "CUDA not found"
- Ensure NVIDIA GPU drivers are installed
- Verify CUDA 11.8+ is installed
- Re-run: `pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121`
- Fallback: CPU mode (very slow) works without GPU

### "Model file not found"
- Verify model path in GUI points to actual file
- Use **Smart Defaults** button (Ctrl+D) to auto-locate
- Check file size is ~12-15 GB (not corrupted download)

### "Audio cuts off mid-sentence"
- This shouldn't happen with current settings
- If it does, report with log file from output folder

### "Generation is very slow"
- Normal for GGUF models (~4-5 min per chunk)
- Slower than expected? Check GPU is being used (see log)
- GPU not selected? Use **Auto-Configure GPU** button

### "Cover art not embedding"
- Cover art is optional - M4B works without it
- Ensure image file is JPG/PNG
- Try different image format or skip cover art

---

## 📁 **Project Structure**

```
MayaBook/
├── app.py                    # Main GUI launcher
├── webui.py                  # Web UI launcher
├── test_cli.py              # Command-line testing
├── diagnose_audio.py        # Audio analysis tool
├── README.md                # This file
├── CLAUDE.md                # Developer documentation
├── requirements.txt         # Python dependencies
│
├── core/                    # Core processing modules
│   ├── tts_maya1_local.py  # GGUF synthesis
│   ├── epub_extract.py     # EPUB parsing
│   ├── chunking.py         # Text splitting
│   ├── audio_combine.py    # WAV concatenation
│   ├── m4b_export.py       # M4B creation
│   ├── pipeline.py         # End-to-end orchestration
│   ├── gpu_utils.py        # GPU detection
│   ├── voice_presets.py    # Voice library
│   └── ...more modules
│
├── ui/                      # GUI implementations
│   ├── main_window.py      # Tkinter interface
│   └── chapter_selection_dialog.py
│
├── webui/                   # Web UI code
│   ├── app.py              # Web application
│   └── theme.py            # Styling
│
├── assets/
│   ├── models/             # Model files (gitignored)
│   └── test/               # Sample EPUBs for testing
│
└── docs/                    # Documentation
    ├── test_logs/          # Test output logs
    └── archive/            # Historical documentation
```

---

## ❓ **Frequently Asked Questions**

**Q: How long does it take to convert a book?**
A: ~3-4 days continuous for a typical novel (6-7 hours of audio). Generation happens in the background; you can leave it running overnight.

**Q: Does it require internet?**
A: No, everything runs locally on your computer.

**Q: Can I use a different voice?**
A: Yes, 15+ professional voices are included. Select from the dropdown and preview before generating.

**Q: What if the GPU isn't fast enough?**
A: The software automatically uses available GPU. Slower GPUs will take longer per chunk, but quality remains high.

**Q: Can I pause and resume generation?**
A: The GUI has a Cancel button to stop. To resume, you'll need to restart from the beginning.

**Q: What formats are supported for output?**
A: M4B (recommended for audiobooks) and WAV (lossless audio).

---

## 🤝 **Contributing**

This is a personal project. For bug reports, feature requests, or questions, please refer to the GitHub repository.

---

## 📜 **License**

This project uses the [Maya1 model](https://huggingface.co/maya-research/maya1) from Maya Research. Refer to their license terms for redistribution and usage guidelines.

---

**For detailed development documentation and testing results, see [CLAUDE.md](CLAUDE.md).**

Last Updated: 2025-11-17
