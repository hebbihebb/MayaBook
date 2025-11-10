# **MayaBook**

**EPUB → TTS → MP4 Narration Tool**

MayaBook is a lightweight desktop app that turns EPUB books into narrated MP4 videos.
It uses the **[Maya1](https://huggingface.co/maya-research/maya1)** voice model via the **Maya1 FastAPI** server to generate expressive human-like speech.

---

## ✨ **Overview**

**Input:** an EPUB file
**Process:** extract text → send to Maya1 FastAPI → receive WAV audio → merge → make MP4
**Output:** a narrated video with a static or optional waveform cover

This project keeps things simple:

* No alignment, subtitles, or M4B audio.
* No online dependencies beyond the local Maya1 server.
* Minimal Python packages and a single clean GUI.

---

## 🧠 **How It Works**

1. **Extract Text**
   The app reads an EPUB, cleans it to plain text, and splits it into small chunks (~400–600 characters).

2. **Generate Audio**
   Each chunk is sent to a locally running **Maya1 FastAPI** server:

   ```json
   POST /v1/tts/generate
   {
     "description": "Female, 30s, calm narrator with British accent",
     "text": "Once upon a time...",
     "temperature": 0.4,
     "top_p": 0.9
   }
   ```

   The server returns a 24 kHz mono WAV file.

3. **Combine Audio**
   All chunks are concatenated into a single `book.wav`, inserting short silence gaps for pacing.

4. **Export MP4**
   A cover image is combined with the audio using FFmpeg:

   ```bash
   ffmpeg -loop 1 -framerate 2 -i cover.jpg -i book.wav \
          -c:v libx264 -preset fast -crf 18 -c:a aac -b:a 160k -shortest output.mp4
   ```

---

## 🖥️ **GUI Features**

* **EPUB file picker**
* **Cover image selector**
* **Output folder selector**
* **Voice description** (multi-line text)
* **Temperature / Top-p sliders**
* **Chunk length / silence gap sliders**
* **Buttons:** Preview 10 s · Generate MP4 · Open Output Folder
* **Progress bar and log area**

All implemented with **Tkinter** for zero-dependency simplicity.

---

## ⚙️ **Dependencies**

**Python packages**

```
ebooklib
beautifulsoup4
requests
tqdm
```

**System requirements**

* Python 3.10 +
* FFmpeg in PATH
* Running **Maya1 FastAPI** server
  (from [https://github.com/MayaResearch/maya1-fastapi](https://github.com/MayaResearch/maya1-fastapi))

---

## 🚀 **Installation**

```bash
git clone https://github.com/<yourname>/MayaBook
cd MayaBook
python -m venv .venv
source .venv/bin/activate    # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

---

## ▶️ **Usage**

1. **Start Maya1 FastAPI**

   ```bash
   git clone https://github.com/MayaResearch/maya1-fastapi
   cd maya1-fastapi
   pip install -r requirements.txt
   python server.py
   ```

   It will run at `http://localhost:8000`.

2. **Run MayaBook**

   ```bash
   python app.py
   ```

3. In the GUI:

   * Pick your EPUB and cover image
   * Describe the voice and emotions
   * Click **Preview 10 s** or **Generate MP4**

4. Wait until the MP4 appears in your output folder.

---

## 🧩 **Project Structure**

```
project_root/
│
├─ app.py                  # main entry point
│
├─ core/
│   ├─ epub_extract.py     # EPUB → text chunks
│   ├─ tts_maya1.py        # calls Maya1 FastAPI
│   ├─ audio_combine.py    # merges WAV chunks
│   └─ video_export.py     # ffmpeg MP4 assembly
│
└─ ui/
    └─ main_window.py      # Tkinter GUI
```

---

## 🧱 **Design Principles**

* Minimal, readable, dependency-light.
* Modular: each stage (EPUB, TTS, audio, video) can be tested independently.
* Works cross-platform (Windows/macOS/Linux).
* Easy to extend later for features like waveform overlays or chapter selection.

---

## ❌ **Out of Scope**

* No multi-voice support.
* No forced alignment or word timings.
* No streaming or cloud integration.
* No subtitle generation.

---

## 📜 **License**

MIT License — you are free to use, modify, and distribute this project.

---

## ❤️ **Credits**

* **Maya1 Model & SNAC Codec:** [Maya Research](https://huggingface.co/maya-research/maya1)
* **Maya1 FastAPI Server:** [Maya Research GitHub](https://github.com/MayaResearch/maya1-fastapi)
* **App Concept & Integration Design:** Project MayaBook contributors

---
