# MayaBook Web UI

A standalone NiceGUI-based web interface for the MayaBook TTS audiobook generation pipeline. Access all MayaBook features through a modern, browser-based UI from anywhere on your local network.

## Features

### 🎨 Modern Interface
- **Claude Code-inspired theme** - Dark theme with purple/blue accents
- **Responsive design** - Works on desktop, tablet, and mobile
- **Tab-based organization** - Clean, organized workflow

### 📚 Full Pipeline Access
- **EPUB upload & processing** - Drag-and-drop EPUB files
- **Chapter-aware generation** - Automatic chapter detection and metadata
- **Voice presets** - 15 pre-configured voice options with preview
- **Custom voice descriptions** - Full control over voice characteristics
- **Real-time progress tracking** - Live progress bars and log streaming
- **Multiple output formats** - WAV, MP4, M4B audiobook formats

### 🚀 Advanced Features
- **Quick Test mode** - Test TTS without uploading full EPUBs
- **Voice previews** - Generate and play voice samples before full generation
- **Metadata editing** - Title, author, album, year, genre
- **Chapter controls** - Save chapters separately or merged
- **File downloads** - Direct download of generated audiobooks
- **Cancellation support** - Stop generation mid-process

### 🔧 Technical
- **Independent operation** - Doesn't interfere with CLI or Tkinter UI
- **Local network access** - Access from any device on your network
- **Thread-safe processing** - Background generation with live updates
- **Comprehensive logging** - Real-time log display with 500-message buffer

---

## Installation

### Prerequisites

MayaBook must already be installed. If not, install core dependencies first:

```bash
pip install -r requirements.txt
```

### Web UI Dependencies

The web UI uses NiceGUI, which is already included in `requirements.txt`:

```bash
# If not already installed
pip install nicegui
```

That's it! No additional setup required.

---

## Quick Start

### Launch the Web UI

```bash
# From the MayaBook project root
python webui.py
```

The server will start on `http://0.0.0.0:8080` by default.

Access it via:
- **Local machine**: http://localhost:8080
- **Local network**: http://YOUR_IP:8080 (check your local IP address)

### Command-Line Options

```bash
# Custom port
python webui.py --port 8000

# Localhost only (not accessible from other devices)
python webui.py --host 127.0.0.1

# Development mode (auto-reload on code changes)
python webui.py --dev

# Combine options
python webui.py --host 0.0.0.0 --port 9000
```

---

## Usage Guide

### 1. Upload Files

**Files & Model Tab:**
1. Upload your EPUB file (drag-and-drop or click to browse)
2. Optionally upload a cover image (for MP4/M4B output)
3. Configure model settings:
   - Model type: GGUF (recommended) or HuggingFace
   - Model path: Path to your Maya1 model file
   - Context size: Default 4096
   - GPU layers: -1 for all layers on GPU

### 2. Configure Voice

**Voice & TTS Tab:**
1. Select a voice preset from the dropdown (15 options available)
   - Young Adult Female (Energetic)
   - Middle-Aged Male (Authoritative)
   - Child (Curious)
   - And more...
2. Or write a custom voice description
3. Click "Preview Voice" to hear a sample
4. Adjust TTS parameters:
   - **Temperature** (0.0-1.0): Controls randomness (default: 0.45)
   - **Top-p** (0.0-1.0): Nucleus sampling (default: 0.92)
   - **Chunk size**: Words per chunk (default: 70)
   - **Gap**: Silence between chunks in seconds (default: 0.25)

### 3. Configure Output

**Output & Metadata Tab:**
1. Select output format:
   - **M4B** (recommended for audiobooks with chapters)
   - **WAV** (uncompressed audio)
   - **MP4** (audio + static cover image)
2. Enable/disable chapter-aware processing
3. Choose chapter options:
   - Save chapters separately
   - Create merged file
   - Set silence between chapters
4. Fill in metadata (optional but recommended):
   - Title, Author, Album/Series, Year, Genre

### 4. Quick Test (Optional)

**Quick Test Tab:**
- Test TTS generation without uploading an EPUB
- Enter sample text (default preview text provided)
- Click "Generate Test Audio"
- Download and play the result to verify settings

### 5. Generate Audiobook

**Generate Tab:**
1. Click "Start Generation"
2. Monitor real-time progress:
   - Progress bar shows completion percentage
   - Log displays detailed processing steps
   - Current chunk count updates live
3. Cancel anytime with the "Cancel" button
4. When complete, download files from the "Output Files" section

---

## Architecture

### Module Structure

```
webui/
├── __init__.py          # Module initialization
├── theme.py             # Claude Code-inspired theme and CSS
├── app.py               # Main NiceGUI application
└── README.md            # This file

webui.py                 # Standalone entry point (project root)
```

### Integration Points

The web UI integrates seamlessly with MayaBook's core pipeline:

```python
# Core pipeline imports
from core import pipeline
from core.epub_extract import extract_chapters
from core.voice_presets import get_preset_names, get_preset_by_name
from core.voice_preview import generate_voice_preview
```

**Pipeline Functions Used:**
- `pipeline.run_pipeline()` - Simple text-to-audio generation
- `pipeline.run_pipeline_with_chapters()` - Chapter-aware processing
- `extract_chapters()` - EPUB chapter extraction
- `generate_voice_preview()` - Voice preview generation

### Thread Safety

- Generation runs in background threads
- Progress callbacks update UI in real-time
- Stop flags allow clean cancellation
- No interference with CLI or Tkinter UI

---

## Configuration

### Default Settings

The web UI uses these recommended defaults (matching the Tkinter UI):

```python
# TTS Parameters
chunk_size = 70          # words per chunk
temperature = 0.45       # slight randomness for naturalness
top_p = 0.92            # nucleus sampling
gap_seconds = 0.25      # silence between chunks
chapter_silence = 2.0   # silence between chapters

# Model Parameters (GGUF)
n_ctx = 4096            # context window
n_gpu_layers = -1       # all layers to GPU
max_tokens = 2500       # per-chunk limit

# Output
output_format = "m4b"   # M4B audiobook format
enable_chapters = True  # chapter-aware processing
merge_chapters = True   # create merged file
```

### File Locations

**Uploads:**
- Temporary uploads stored in: `~/tmp/mayabook_uploads/`

**Outputs:**
- Generated audiobooks saved to: `~/MayaBook_Output/`
- Quick tests saved to: `~/tmp/mayabook_quick_test/`

**Downloads:**
- Files downloaded via browser's default download location

---

## Customization

### Theme Customization

Edit `webui/theme.py` to customize colors:

```python
COLORS = {
    'bg_primary': '#1a1a1a',      # Main background
    'accent_purple': '#a855f7',   # Primary accent
    'accent_blue': '#3b82f6',     # Secondary accent
    # ... modify as desired
}
```

### Layout Customization

Edit `webui/app.py` to modify the UI layout:

- Add new tabs
- Rearrange sections
- Add custom controls
- Modify progress display

---

## Troubleshooting

### Web UI Won't Start

**Error: `ModuleNotFoundError: No module named 'nicegui'`**
```bash
pip install nicegui
```

**Error: Port already in use**
```bash
# Use a different port
python webui.py --port 8001
```

### Can't Access from Other Devices

1. Check firewall settings (allow port 8080)
2. Verify you're using `--host 0.0.0.0` (default)
3. Find your local IP: `ifconfig` (macOS/Linux) or `ipconfig` (Windows)
4. Access via `http://YOUR_IP:8080`

### Generation Fails

**Model path issues:**
- Verify model path is correct
- Use absolute paths, not relative paths
- Check file permissions

**Out of memory:**
- Reduce `n_gpu_layers` (try 20-30 instead of -1)
- Reduce `chunk_size` to 50-60 words
- Close other GPU applications

**Silent audio:**
- Check RMS values in logs
- Retry logic should trigger automatically
- Try different temperature/top_p values

### Upload Issues

**EPUB not extracting:**
- Verify file is valid EPUB format
- Check logs for extraction errors
- Try re-uploading

**Cover image not working:**
- Supported formats: JPG, PNG, WebP
- Max file size: ~10MB (NiceGUI default)

---

## Development

### Enable Auto-Reload

```bash
python webui.py --dev
```

Changes to `webui/*.py` files will trigger automatic reload.

### Add New Features

1. **New UI components**: Edit `webui/app.py`
2. **Theme changes**: Edit `webui/theme.py`
3. **New pipeline features**: Add to `core/` modules (see `CLAUDE.md`)

### Debug Mode

Enable verbose logging:

```python
# In webui/app.py, modify setup_logging()
logger.setLevel(logging.DEBUG)
```

---

## Comparison with Other UIs

| Feature | Web UI | Tkinter UI | CLI |
|---------|--------|------------|-----|
| Local network access | ✅ | ❌ | ❌ |
| Modern design | ✅ | ⚠️ | ❌ |
| Real-time logs | ✅ | ✅ | ✅ |
| Quick Test | ✅ | ✅ | ✅ |
| Voice preview | ✅ | ⚠️ | ❌ |
| File downloads | ✅ | ❌ | ❌ |
| Chapter-aware | ✅ | ✅ | ⚠️ |
| Mobile friendly | ✅ | ❌ | ❌ |
| No GUI required | ✅ | ❌ | ✅ |

**Legend:**
- ✅ Full support
- ⚠️ Partial support
- ❌ Not supported

---

## Technical Details

### Dependencies

- **NiceGUI** (^1.4.0): Modern web UI framework based on FastAPI and Vue
- **FastAPI**: Backend API framework (NiceGUI dependency)
- **Uvicorn**: ASGI server (NiceGUI dependency)

### Browser Compatibility

Tested on:
- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Security Considerations

⚠️ **Important Security Notes:**

1. **Local network only**: Web UI is designed for trusted local networks
2. **No authentication**: No password protection by default
3. **File access**: Web UI can access any files the Python process can read
4. **No HTTPS**: Communication is unencrypted (HTTP only)

**For production use:**
- Use `--host 127.0.0.1` to restrict to localhost
- Run behind reverse proxy (nginx) with authentication
- Add HTTPS via reverse proxy or NiceGUI SSL configuration

---

## Performance

### Resource Usage

- **Memory**: ~200MB base + model size (~6-8GB for Q5_K_M GGUF)
- **CPU**: Minimal (UI thread only)
- **GPU**: Same as CLI/Tkinter (CUDA inference)

### Concurrent Users

- Multiple users can access the UI simultaneously
- Only one generation can run at a time (llama-cpp-python thread safety)
- Multiple users will queue their requests

---

## Roadmap

Potential future enhancements:

- [ ] User authentication/login system
- [ ] Multi-user job queue
- [ ] WebSocket-based real-time updates (smoother progress)
- [ ] Audio player preview in browser
- [ ] Waveform visualization
- [ ] Batch processing (multiple EPUBs)
- [ ] Cloud storage integration (S3, Google Drive)
- [ ] Mobile app wrapper (PWA)

---

## Support

For issues, questions, or contributions:

1. Check the main project documentation: `CLAUDE.md`
2. Review troubleshooting section above
3. Check NiceGUI documentation: https://nicegui.io
4. Open an issue on GitHub

---

## License

Same as the main MayaBook project.

---

**Last Updated**: 2025-11-16
**Version**: 1.0.0
**Author**: hebbihebb
**Contributors**: Claude (Anthropic)
