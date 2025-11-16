"""Standalone NiceGUI interface for controlling the MayaBook pipeline."""
from __future__ import annotations

import logging
import queue
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from nicegui import events, ui

from core.epub_extract import extract_chapters
from core.pipeline import run_pipeline
from core.utils import sanitize_name_for_os

REPO_ROOT = Path(__file__).resolve().parents[1]
UPLOAD_DIR = REPO_ROOT / "webui" / "uploads"
OUTPUT_DIR = REPO_ROOT / "webui" / "outputs"
DEFAULT_COVER = REPO_ROOT / "assets" / "test" / "cover.jpg"
FALLBACK_COVER = REPO_ROOT / "screenshot.jpg"

for directory in (UPLOAD_DIR, OUTPUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def _cover_fallback() -> Optional[Path]:
    if DEFAULT_COVER.exists():
        return DEFAULT_COVER
    if FALLBACK_COVER.exists():
        return FALLBACK_COVER
    return None


class QueueLogHandler(logging.Handler):
    """Logging handler that forwards messages to a queue for the UI."""

    def __init__(self, log_queue: queue.Queue):
        super().__init__(level=logging.INFO)
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            self.log_queue.put_nowait(message)
        except Exception:  # pragma: no cover - defensive
            pass


class PipelineController:
    """Coordinates background execution of the MayaBook pipeline."""

    def __init__(self) -> None:
        self.epub_path: Optional[Path] = None
        self.cover_path: Optional[Path] = _cover_fallback()
        self.epub_text: Optional[str] = None
        self.metadata: Dict[str, str] = {}
        self.chapter_count: int = 0
        self.is_running = False
        self.status_message = "Waiting for input"
        self.progress_done = 0
        self.progress_total = 0
        self.wav_path: Optional[Path] = None
        self.mp4_path: Optional[Path] = None
        self.error_message: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.log_handler = QueueLogHandler(self.log_queue)
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(self.log_handler)

    # ------------------------------------------------------------------
    # Upload helpers
    # ------------------------------------------------------------------
    def update_epub(self, epub_path: Path) -> None:
        self.epub_path = epub_path
        self.status_message = "EPUB loaded"
        self._extract_epub_text_and_metadata()

    def update_cover(self, cover_path: Path) -> None:
        self.cover_path = cover_path
        self.status_message = "Cover image loaded"

    def _extract_epub_text_and_metadata(self) -> None:
        if not self.epub_path:
            return
        try:
            metadata, chapters = extract_chapters(str(self.epub_path))
            self.metadata = metadata
            self.chapter_count = len(chapters)
            self.epub_text = "\n\n".join(text for _, text in chapters if text.strip())
            if not self.epub_text.strip():
                raise ValueError("No readable text found in EPUB")
            self.status_message = "Text extracted"
        except Exception as exc:
            self.status_message = f"Extraction failed: {exc}"
            self.metadata = {}
            self.epub_text = None
            self.chapter_count = 0
            raise

    # ------------------------------------------------------------------
    # Pipeline execution
    # ------------------------------------------------------------------
    def start_job(self, *, params: Dict) -> None:
        if self.is_running:
            raise RuntimeError("A job is already running")
        if not self.epub_path or not self.epub_text:
            raise RuntimeError("Upload an EPUB before starting the pipeline")
        if not self.cover_path:
            raise RuntimeError("Please upload a cover image or keep the default placeholder")

        self.error_message = None
        self.wav_path = None
        self.mp4_path = None
        self.progress_done = 0
        self.progress_total = 0
        self._stop_event.clear()
        self.is_running = True
        self.status_message = "Starting MayaBook pipeline..."

        def _worker() -> None:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                title = self.metadata.get("title") or self.epub_path.stem
                base_name = sanitize_name_for_os(f"{title}_{timestamp}")
                out_wav = OUTPUT_DIR / f"{base_name}.wav"
                out_mp4 = OUTPUT_DIR / f"{base_name}.mp4"

                wav_path, mp4_path = run_pipeline(
                    epub_text=self.epub_text,
                    model_path=params["model_path"],
                    voice_desc=params["voice_desc"],
                    chunk_size=params["chunk_size"],
                    gap_s=params["gap_s"],
                    out_wav=str(out_wav),
                    out_mp4=str(out_mp4),
                    cover_image=str(self.cover_path),
                    temperature=params["temperature"],
                    top_p=params["top_p"],
                    n_ctx=params["n_ctx"],
                    n_gpu_layers=params["n_gpu_layers"],
                    workers=params["workers"],
                    max_tokens=params["max_tokens"],
                    model_type=params["model_type"],
                    progress_cb=self._update_progress,
                    stop_flag=self._stop_event,
                )
                self.wav_path = Path(wav_path) if wav_path else None
                self.mp4_path = Path(mp4_path) if mp4_path else None
                if self._stop_event.is_set():
                    self.status_message = "Generation canceled"
                else:
                    self.status_message = "Generation finished"
            except Exception as exc:
                logging.exception("Pipeline execution failed")
                self.error_message = str(exc)
                self.status_message = f"Failed: {exc}"
            finally:
                self.is_running = False

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    def _update_progress(self, done: int, total: int) -> None:
        self.progress_done = done
        self.progress_total = total

    def request_stop(self) -> None:
        if self.is_running and not self._stop_event.is_set():
            self._stop_event.set()
            self.status_message = "Stopping..."


controller = PipelineController()


def _save_upload(event: events.UploadEvent, target_dir: Path) -> Path:
    """Persist an uploaded file to disk and return the resulting path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sanitized_name = sanitize_name_for_os(event.name or "upload")
    target_path = target_dir / f"{timestamp}_{sanitized_name}"
    with target_path.open("wb") as outfile:
        outfile.write(event.content.read())
    event.content.seek(0)
    return target_path


# ----------------------------------------------------------------------
# NiceGUI layout helpers
# ----------------------------------------------------------------------

def apply_claude_theme() -> None:
    ui.dark_mode().enable()
    ui.colors(
        primary="#b69bff",
        secondary="#57e6c9",
        accent="#ffc87a",
        positive="#57e6c9",
        warning="#ffb347",
        negative="#ff7a7a",
    )
    ui.add_head_html(
        """
        <style>
        :root {
            --claude-bg: #0c0f17;
            --claude-panel: #151a27;
            --claude-panel-muted: #1b2335;
            --claude-text: #f1f2ff;
            --claude-muted: #9ea7c2;
            --claude-accent: #9c83ff;
        }
        body {
            background: var(--claude-bg) !important;
            color: var(--claude-text);
            font-family: 'Space Grotesk', 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .claude-card {
            background: linear-gradient(135deg, rgba(20,26,40,0.95), rgba(24,16,45,0.95));
            border: 1px solid rgba(156,131,255,0.2);
            box-shadow: 0 30px 60px rgba(0,0,0,0.3);
            border-radius: 22px;
            padding: 24px;
        }
        .claude-header {
            background: linear-gradient(120deg, rgba(17,12,28,0.9), rgba(26,28,46,0.9));
            border-radius: 28px;
            border: 1px solid rgba(87,230,201,0.3);
            padding: 28px;
        }
        .claude-chip {
            border-radius: 9999px;
            padding: 6px 16px;
            background: rgba(87,230,201,0.08);
            border: 1px solid rgba(87,230,201,0.25);
            color: var(--claude-text);
            font-size: 0.85rem;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }
        .claude-mono {
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
        }
        </style>
        """
    )


def build_layout() -> None:
    apply_claude_theme()

    with ui.column().classes("min-h-screen w-full gap-6 p-6 md:p-10"):
        with ui.row().classes("claude-header items-center justify-between flex-wrap gap-4"):
            with ui.column().classes("gap-2"):
                ui.label("MayaBook // Web Control").classes("text-2xl md:text-3xl font-semibold text-white")
                ui.label("Control the MayaBook TTS pipeline anywhere on your LAN")\
                    .classes("text-sm text-[var(--claude-muted)]")
            ui.label(controller.status_message).classes("claude-chip")

        with ui.row().classes("w-full gap-6 flex-wrap"):
            with ui.column().classes("claude-card flex-1 min-w-[320px] gap-4"):
                ui.label("1. Upload Source & Cover").classes("text-lg font-semibold")
                ui.label("Drop your EPUB and an optional cover image. We'll auto-extract metadata.")\
                    .classes("text-sm text-[var(--claude-muted)]")

                ui.upload(
                    label="Upload EPUB",
                    multiple=False,
                    auto_upload=True,
                    on_upload=lambda e: handle_epub_upload(e),
                ).classes("w-full")

                ui.upload(
                    label="Upload Cover (jpg/png)",
                    multiple=False,
                    auto_upload=True,
                    on_upload=lambda e: handle_cover_upload(e),
                ).classes("w-full")

                ui.separator()
                ui.label("Extracted Metadata").classes("font-medium")
                metadata_container = ui.column().classes("gap-1")

                def refresh_metadata_panel() -> None:
                    metadata_container.clear()
                    if not controller.metadata:
                        ui.label("Upload an EPUB to view metadata.").classes("text-sm text-[var(--claude-muted)]")
                        return
                    fields = {
                        "Title": controller.metadata.get("title", "Unknown"),
                        "Author": controller.metadata.get("author", "Unknown"),
                        "Chapters": str(controller.chapter_count),
                        "Language": controller.metadata.get("language", "?") or "?",
                    }
                    for label_text, value in fields.items():
                        with ui.row().classes("justify-between text-sm w-full"):
                            ui.label(label_text).classes("text-[var(--claude-muted)]")
                            ui.label(value).classes("font-semibold")

                refresh_metadata_panel()

                ui.separator()
                ui.label("2. Voice & Model").classes("text-lg font-semibold")
                model_path_input = ui.input(label="Model path", value="", placeholder="/path/to/maya1.i1-Q5_K_M.gguf")
                voice_input = ui.textarea(
                    label="Voice description",
                    value="Warm professional narrator with confident pacing and subtle emotion.",
                ).props("rows=2")
                model_type_select = ui.select(
                    {
                        "gguf": "GGUF (llama.cpp)",
                        "huggingface": "Hugging Face Transformers",
                    },
                    value="gguf",
                    label="Backend",
                )

                ui.separator()
                ui.label("3. Generation Controls").classes("text-lg font-semibold")
                chunk_size_input = ui.number(label="Chunk size (words)", value=90, min=40, max=400)
                gap_input = ui.number(label="Silence gap (seconds)", value=0.4, min=0, max=5, step=0.1)
                with ui.row().classes("gap-4 flex-wrap"):
                    temperature_input = ui.number(label="Temperature", value=0.45, min=0.1, max=1.0, step=0.05)
                    top_p_input = ui.number(label="Top-p", value=0.92, min=0.1, max=1.0, step=0.05)
                with ui.row().classes("gap-4 flex-wrap"):
                    max_tokens_input = ui.number(label="Max tokens", value=2500, min=500, max=4000, step=100)
                    workers_input = ui.number(label="Worker threads", value=1, min=1, max=8, step=1)
                with ui.row().classes("gap-4 flex-wrap"):
                    n_ctx_input = ui.number(label="Context (n_ctx)", value=4096, min=1024, max=8192, step=512)
                    n_gpu_layers_input = ui.number(label="GPU layers", value=-1, min=-1, max=1000, step=1)

            with ui.column().classes("claude-card flex-1 min-w-[320px] gap-4"):
                ui.label("Pipeline Status").classes("text-lg font-semibold")
                progress = ui.linear_progress(value=0).classes("w-full h-3 rounded-full")
                progress_label = ui.label("Awaiting job...").classes("text-sm text-[var(--claude-muted)]")

                with ui.row().classes("gap-4 flex-wrap"):
                    start_button = ui.button("Start Generation", icon="play_arrow")
                    cancel_button = ui.button("Cancel", icon="stop", color="warning")

                status_label = ui.label(controller.status_message).classes("text-sm")
                error_label = ui.label(" ").classes("text-sm text-red-400")

                ui.separator()
                ui.label("Live Logs").classes("text-lg font-semibold")
                log_panel = ui.log(max_lines=400)
                log_panel.classes("h-72 overflow-y-auto claude-mono text-xs bg-[var(--claude-panel-muted)]")

                ui.separator()
                ui.label("Downloads").classes("text-lg font-semibold")
                with ui.row().classes("gap-4 flex-wrap"):
                    wav_button = ui.button(
                        "Download WAV", icon="graphic_eq", on_click=lambda: trigger_download(controller.wav_path)
                    )
                    mp4_button = ui.button(
                        "Download MP4", icon="movie", on_click=lambda: trigger_download(controller.mp4_path)
                    )
                wav_button.disable()
                mp4_button.disable()

        # ------------------------------------------------------------------
        # Event handlers scoped within layout
        # ------------------------------------------------------------------
        def trigger_download(path: Optional[Path]) -> None:
            if path and path.exists():
                ui.download(path)
            else:
                ui.notify("File not ready yet", type="warning")

        async def start_job_handler() -> None:
            if controller.is_running:
                ui.notify("A generation is already running", type="warning")
                return
            model_path = model_path_input.value.strip()
            voice_desc = voice_input.value.strip()
            if not model_path:
                ui.notify("Set the model path", type="negative")
                return
            if not voice_desc:
                ui.notify("Enter a voice description", type="negative")
                return
            try:
                params = {
                    "model_path": model_path,
                    "voice_desc": voice_desc,
                    "chunk_size": int(chunk_size_input.value or 90),
                    "gap_s": float(gap_input.value or 0.4),
                    "temperature": float(temperature_input.value or 0.45),
                    "top_p": float(top_p_input.value or 0.92),
                    "max_tokens": int(max_tokens_input.value or 2500),
                    "n_ctx": int(n_ctx_input.value or 4096),
                    "n_gpu_layers": int(n_gpu_layers_input.value or -1),
                    "workers": int(workers_input.value or 1),
                    "model_type": model_type_select.value or "gguf",
                }
            except ValueError:
                ui.notify("One or more parameters are invalid", type="negative")
                return
            try:
                controller.start_job(params=params)
                ui.notify("Pipeline started", type="positive")
            except Exception as exc:
                ui.notify(str(exc), type="negative")

        def cancel_job_handler() -> None:
            controller.request_stop()
            ui.notify("Stop requested", type="warning")

        start_button.on("click", start_job_handler)
        cancel_button.on("click", cancel_job_handler)

        def handle_epub_upload(event: events.UploadEvent) -> None:
            try:
                path = _save_upload(event, UPLOAD_DIR)
                controller.update_epub(path)
                ui.notify(f"EPUB uploaded: {event.name}", type="positive")
                refresh_metadata_panel()
            except Exception as exc:
                ui.notify(f"EPUB upload failed: {exc}", type="negative")

        def handle_cover_upload(event: events.UploadEvent) -> None:
            try:
                path = _save_upload(event, UPLOAD_DIR)
                controller.update_cover(path)
                ui.notify("Cover image ready", type="positive")
            except Exception as exc:
                ui.notify(f"Cover upload failed: {exc}", type="negative")

        def sync_status() -> None:
            status_label.text = controller.status_message
            if controller.progress_total:
                progress.value = controller.progress_done / controller.progress_total
                progress_label.text = f"{controller.progress_done}/{controller.progress_total} chunks finished"
            else:
                progress.value = 0
                progress_label.text = "Waiting for progress..."
            if controller.error_message:
                error_label.text = controller.error_message
            else:
                error_label.text = " "
            if controller.wav_path and controller.wav_path.exists():
                wav_button.enable()
            else:
                wav_button.disable()
            if controller.mp4_path and controller.mp4_path.exists():
                mp4_button.enable()
            else:
                mp4_button.disable()

        def drain_logs() -> None:
            while True:
                try:
                    message = controller.log_queue.get_nowait()
                except queue.Empty:
                    break
                log_panel.push(message)

        ui.timer(0.75, sync_status)
        ui.timer(0.5, drain_logs)


def main() -> None:
    build_layout()
    ui.run(host="0.0.0.0", port=8080, title="MayaBook Web UI", reload=False, show=False)


if __name__ == "__main__":
    main()
