import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import subprocess
import sys
import shutil
from pathlib import Path

# Assuming these modules exist and are correct
from core.epub_extract import extract_text, extract_chapters
from core.pipeline import run_pipeline, run_pipeline_with_chapters
from core.m4b_export import verify_ffmpeg_available
from core.voice_presets import get_preset_names, get_preset_by_name
from core.voice_preview import generate_voice_preview, is_preview_cached, get_cached_preview_path
from ui.chapter_selection_dialog import show_chapter_selection_dialog

# Audio playback using pygame
try:
    import pygame.mixer
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except (ImportError, Exception):
    PYGAME_AVAILABLE = False

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MayaBook Local GGUF")
        self.geometry("850x900")  # Increased height for new sections

        self.stop_generation_flag = None
        self.generation_thread = None
        self.chapters_data = None  # Store extracted chapters (all chapters from EPUB)
        self.selected_chapters = None  # Store user-selected chapters for processing
        self.extracted_metadata = None  # Store extracted metadata

        self._create_widgets()
        self._create_action_buttons()

        # Add a logger text box
        self._create_log_widget()
        self.log_message("Welcome to MayaBook!")

        # Check FFmpeg availability on startup
        self._check_ffmpeg()

    def _create_widgets(self):
        # Create canvas with scrollbar for main content
        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)

        main_frame = ttk.Frame(canvas, padding="10")

        # Configure canvas
        canvas.configure(yscrollcommand=scrollbar.set)

        # Grid layout
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create window in canvas
        canvas_frame = canvas.create_window((0, 0), window=main_frame, anchor="nw")

        # Configure scrolling
        def on_frame_configure(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            # Update the window width to match canvas width
            canvas.itemconfig(canvas_frame, width=event.width)

        main_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        # Enable mousewheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # --- File Paths ---
        file_frame = ttk.LabelFrame(main_frame, text="I/O Paths")
        file_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        file_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(file_frame, text="EPUB File:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.epub_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.epub_path, width=60).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(file_frame, text="Browse...", command=self._select_epub).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(file_frame, text="Cover Image:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.cover_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.cover_path, width=60).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(file_frame, text="Browse...", command=self._select_cover).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(file_frame, text="Output Folder:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.output_folder = tk.StringVar(value=str(Path.home() / "MayaBook_Output"))
        ttk.Entry(file_frame, textvariable=self.output_folder, width=60).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(file_frame, text="Browse...", command=self._select_output).grid(row=2, column=2, padx=5, pady=5)

        # --- Model Settings ---
        model_frame = ttk.LabelFrame(main_frame, text="Model Settings")
        model_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        model_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(model_frame, text="Model Type:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.model_type = tk.StringVar(value="gguf")
        model_type_combo = ttk.Combobox(model_frame, textvariable=self.model_type, values=["gguf", "huggingface"], state="readonly", width=15)
        model_type_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        model_type_combo.bind("<<ComboboxSelected>>", self._on_model_type_change)

        ttk.Label(model_frame, text="Model Path:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.model_path = tk.StringVar(value="assets/models/maya1.i1-Q5_K_M.gguf")
        model_entry = ttk.Entry(model_frame, textvariable=self.model_path, width=60)
        model_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(model_frame, text="Browse...", command=self._select_model).grid(row=1, column=2, padx=5, pady=5)

        # GGUF-specific settings (shown/hidden based on model type)
        self.gguf_settings_frame = ttk.Frame(model_frame)
        self.gguf_settings_frame.grid(row=2, column=0, columnspan=3, sticky="ew")

        ttk.Label(self.gguf_settings_frame, text="n_ctx:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.n_ctx = tk.IntVar(value=4096)
        ttk.Entry(self.gguf_settings_frame, textvariable=self.n_ctx, width=10).grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(self.gguf_settings_frame, text="n_gpu_layers:").grid(row=0, column=2, padx=15, pady=5, sticky="w")
        self.n_gpu_layers = tk.IntVar(value=-1)
        ttk.Entry(self.gguf_settings_frame, textvariable=self.n_gpu_layers, width=10).grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # --- TTS Synthesis Settings ---
        tts_frame = ttk.LabelFrame(main_frame, text="TTS Synthesis Settings")
        tts_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        tts_frame.grid_columnconfigure(1, weight=1)

        # Voice Preset Selection
        ttk.Label(tts_frame, text="Voice Preset:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.voice_preset = tk.StringVar(value="Young Adult Female (Energetic)")
        voice_preset_combo = ttk.Combobox(tts_frame, textvariable=self.voice_preset,
                                         values=get_preset_names(), state="readonly", width=40)
        voice_preset_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        voice_preset_combo.bind("<<ComboboxSelected>>", self._on_voice_preset_change)

        # Preview Voice button
        self.preview_button = ttk.Button(tts_frame, text="Preview Voice", command=self._preview_voice)
        self.preview_button.grid(row=0, column=2, padx=5, pady=5)

        # Custom voice description
        ttk.Label(tts_frame, text="Voice Description:").grid(row=1, column=0, padx=5, pady=5, sticky="nw")
        self.voice_description = tk.Text(tts_frame, height=3, width=60)
        self.voice_description.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        # Set default voice description from preset
        default_preset = get_preset_by_name("Young Adult Female (Energetic)")
        if default_preset:
            self.voice_description.insert(tk.END, default_preset["description"])
        else:
            # Fallback if preset not found
            self.voice_description.insert(tk.END, "A bright, energetic female voice in her early 20s with excellent articulation. Her delivery is expressive and dynamic, with a contemporary American accent that's perfect for young adult fiction and romance novels.")

        ttk.Label(tts_frame, text="Temperature:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.temperature = tk.DoubleVar(value=0.45)
        ttk.Entry(tts_frame, textvariable=self.temperature, width=10).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(tts_frame, text="Top-p:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.top_p = tk.DoubleVar(value=0.92)
        ttk.Entry(tts_frame, textvariable=self.top_p, width=10).grid(row=3, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(tts_frame, text="Chunk Size (words):").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.chunk_size = tk.IntVar(value=70)
        ttk.Entry(tts_frame, textvariable=self.chunk_size, width=10).grid(row=4, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(tts_frame, text="Gap (seconds):").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.gap_size = tk.DoubleVar(value=0.25)
        ttk.Entry(tts_frame, textvariable=self.gap_size, width=10).grid(row=5, column=1, padx=5, pady=5, sticky="w")

        # --- Quick Test ---
        quick_test_frame = ttk.LabelFrame(main_frame, text="Quick Test (No EPUB Required)")
        quick_test_frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        quick_test_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(quick_test_frame, text="Enter text to quickly test TTS with current settings:",
                 foreground="gray").grid(row=0, column=0, columnspan=2, padx=5, pady=(5, 0), sticky="w")

        self.quick_test_text = tk.Text(quick_test_frame, height=4, width=60, wrap=tk.WORD)
        self.quick_test_text.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.quick_test_text.insert(tk.END, "Hello! This is a quick test of the Maya1 text to speech system. The voice should sound natural and expressive.")

        quick_test_scrollbar = ttk.Scrollbar(quick_test_frame, orient=tk.VERTICAL, command=self.quick_test_text.yview)
        quick_test_scrollbar.grid(row=1, column=1, pady=5, sticky="ns")
        self.quick_test_text.config(yscrollcommand=quick_test_scrollbar.set)

        self.quick_test_button = ttk.Button(quick_test_frame, text="Generate Quick Test Audio", command=self._quick_test_generation)
        self.quick_test_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

        # --- Output Format ---
        format_frame = ttk.LabelFrame(main_frame, text="Output Format")
        format_frame.grid(row=4, column=0, padx=5, pady=5, sticky="ew")
        format_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(format_frame, text="Format:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.output_format = tk.StringVar(value="m4b")
        self.format_combo = ttk.Combobox(format_frame, textvariable=self.output_format,
                                         values=["m4b", "wav", "mp4"], state="readonly", width=15)
        self.format_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        format_help = ttk.Label(format_frame, text="M4B: Audiobook with chapters | WAV: Lossless audio | MP4: Video with cover",
                               foreground="gray")
        format_help.grid(row=1, column=0, columnspan=3, padx=5, pady=(0, 5), sticky="w")

        # --- Chapter Options ---
        self.chapter_frame = ttk.LabelFrame(main_frame, text="Chapter Options")
        self.chapter_frame.grid(row=5, column=0, padx=5, pady=5, sticky="ew")
        self.chapter_frame.grid_columnconfigure(1, weight=1)

        self.use_chapters = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.chapter_frame, text="Enable chapter-aware processing",
                       variable=self.use_chapters, command=self._toggle_chapter_options).grid(
                           row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        self.save_separately = tk.BooleanVar(value=False)
        self.save_sep_check = ttk.Checkbutton(self.chapter_frame, text="Save chapters separately",
                                             variable=self.save_separately)
        self.save_sep_check.grid(row=1, column=0, columnspan=2, padx=25, pady=2, sticky="w")

        self.merge_chapters = tk.BooleanVar(value=True)
        self.merge_check = ttk.Checkbutton(self.chapter_frame, text="Create merged file",
                                          variable=self.merge_chapters)
        self.merge_check.grid(row=2, column=0, columnspan=2, padx=25, pady=2, sticky="w")

        ttk.Label(self.chapter_frame, text="Chapter silence (seconds):").grid(row=3, column=0, padx=25, pady=5, sticky="w")
        self.chapter_silence = tk.DoubleVar(value=2.0)
        silence_spin = ttk.Spinbox(self.chapter_frame, from_=0.5, to=5.0, increment=0.5,
                                   textvariable=self.chapter_silence, width=8)
        silence_spin.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # --- Metadata ---
        self.metadata_frame = ttk.LabelFrame(main_frame, text="Metadata (Optional)")
        self.metadata_frame.grid(row=6, column=0, padx=5, pady=5, sticky="ew")
        self.metadata_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(self.metadata_frame, text="Title:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.metadata_title = tk.StringVar()
        ttk.Entry(self.metadata_frame, textvariable=self.metadata_title, width=50).grid(
            row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(self.metadata_frame, text="Author:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.metadata_author = tk.StringVar()
        ttk.Entry(self.metadata_frame, textvariable=self.metadata_author, width=50).grid(
            row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(self.metadata_frame, text="Album/Series:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.metadata_album = tk.StringVar()
        ttk.Entry(self.metadata_frame, textvariable=self.metadata_album, width=50).grid(
            row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(self.metadata_frame, text="Year:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.metadata_year = tk.StringVar()
        ttk.Entry(self.metadata_frame, textvariable=self.metadata_year, width=15).grid(
            row=3, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(self.metadata_frame, text="Genre:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.metadata_genre = tk.StringVar(value="Audiobook")
        ttk.Entry(self.metadata_frame, textvariable=self.metadata_genre, width=30).grid(
            row=4, column=1, padx=5, pady=5, sticky="w")

        self.metadata_status_label = ttk.Label(self.metadata_frame, text="", foreground="gray")
        self.metadata_status_label.grid(row=5, column=0, columnspan=2, padx=5, pady=(0, 5), sticky="w")

        # --- EPUB Preview ---
        preview_frame = ttk.LabelFrame(main_frame, text="EPUB Text Preview")
        preview_frame.grid(row=7, column=0, padx=5, pady=5, sticky="nsew")
        main_frame.grid_rowconfigure(7, weight=1)

        self.text_preview = tk.Text(preview_frame, wrap=tk.WORD, height=10)
        self.text_preview_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.text_preview.yview)
        self.text_preview.config(yscrollcommand=self.text_preview_scrollbar.set)
        self.text_preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_action_buttons(self):
        actions_frame = ttk.Frame(self)
        actions_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.extract_button = ttk.Button(actions_frame, text="Extract EPUB", command=self._extract_epub)
        self.extract_button.pack(side=tk.LEFT, padx=5)

        self.select_chapters_button = ttk.Button(actions_frame, text="Select Chapters...",
                                                 command=self._select_chapters, state=tk.DISABLED)
        self.select_chapters_button.pack(side=tk.LEFT, padx=5)

        self.generate_button = ttk.Button(actions_frame, text="Start Generation", command=self._start_generation)
        self.generate_button.pack(side=tk.LEFT, padx=5)

        self.cancel_button = ttk.Button(actions_frame, text="Cancel", command=self._cancel_generation, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5)

        self.open_folder_button = ttk.Button(actions_frame, text="Open Output Folder", command=lambda: self._open_folder(self.output_folder.get()))
        self.open_folder_button.pack(side=tk.LEFT, padx=5)

    def _create_log_widget(self):
        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.grid_rowconfigure(2, weight=1)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=10, state=tk.DISABLED)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Progress bar
        self.progress = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

    def log_message(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.update_idletasks() # Force UI update

    def _select_epub(self):
        path = filedialog.askopenfilename(filetypes=[("EPUB files", "*.epub")])
        if path:
            self.epub_path.set(path)
            self.log_message(f"Selected EPUB: {path}")

    def _select_cover(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if path:
            self.cover_path.set(path)
            self.log_message(f"Selected cover: {path}")

    def _select_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_folder.set(path)
            self.log_message(f"Selected output folder: {path}")

    def _select_model(self):
        model_type = self.model_type.get()
        if model_type == "gguf":
            path = filedialog.askopenfilename(filetypes=[("GGUF model files", "*.gguf")])
        else:
            path = filedialog.askdirectory(title="Select HuggingFace Model Directory")
        if path:
            self.model_path.set(path)
            self.log_message(f"Selected model: {path}")

    def _on_model_type_change(self, event=None):
        """Handle model type change - show/hide GGUF settings"""
        model_type = self.model_type.get()
        if model_type == "gguf":
            self.gguf_settings_frame.grid()
            self.model_path.set("assets/models/maya1.i1-Q5_K_M.gguf")
        else:  # huggingface
            self.gguf_settings_frame.grid_remove()
            self.model_path.set("assets/models/maya1_4bit_safetensor")
        self.log_message(f"Model type changed to: {model_type}")

    def _extract_epub(self):
        epub_path = self.epub_path.get()
        if not epub_path:
            messagebox.showerror("Error", "Please select an EPUB file first.")
            return

        try:
            self.log_message(f"Extracting chapters and metadata from {os.path.basename(epub_path)}...")

            # Use extract_chapters to get structured data
            metadata, chapters = extract_chapters(epub_path)

            # Store the chapters for later use
            self.chapters_data = chapters
            self.extracted_metadata = metadata

            # Populate metadata fields in GUI
            if metadata.get('title'):
                self.metadata_title.set(metadata['title'])
            if metadata.get('author'):
                self.metadata_author.set(metadata['author'])
            if metadata.get('year'):
                self.metadata_year.set(metadata['year'])
            if metadata.get('genre'):
                self.metadata_genre.set(metadata['genre'])

            # Show metadata status
            detected_fields = [k for k in ['title', 'author', 'year', 'genre'] if metadata.get(k)]
            if detected_fields:
                self.metadata_status_label.config(
                    text=f"Auto-detected: {', '.join(detected_fields)}"
                )

            # Display chapter preview in text area
            self.text_preview.delete("1.0", tk.END)

            if chapters:
                preview_text = f"Found {len(chapters)} chapter(s):\n\n"
                for i, (title, text) in enumerate(chapters, 1):
                    word_count = len(text.split())
                    preview_text += f"{i}. {title} ({word_count} words)\n"

                preview_text += "\n" + "=" * 60 + "\n\n"

                # Also show full text (first 1000 chars of each chapter)
                for title, text in chapters:
                    preview_text += f"=== {title} ===\n\n"
                    preview_text += text[:1000]
                    if len(text) > 1000:
                        preview_text += "...\n\n"
                    else:
                        preview_text += "\n\n"

                self.text_preview.insert(tk.END, preview_text)
                self.log_message(f"EPUB extracted: {len(chapters)} chapters, {sum(len(t.split()) for _, t in chapters)} total words")

                # Enable chapter selection button
                self.select_chapters_button.config(state=tk.NORMAL)

                # Auto-launch chapter selection dialog
                self._select_chapters()
            else:
                self.text_preview.insert(tk.END, "Error: No chapters extracted from EPUB.")
                self.log_message("Warning: No chapters found in EPUB.")

        except Exception as e:
            self.log_message(f"Error extracting EPUB: {e}")
            messagebox.showerror("EPUB Error", f"Failed to extract text from EPUB:\n{e}")

    def _select_chapters(self):
        """Launch chapter selection dialog."""
        if not self.chapters_data:
            messagebox.showwarning("No Chapters", "Please extract an EPUB first.")
            return

        # Show chapter selection dialog
        selected = show_chapter_selection_dialog(self, self.chapters_data, self.extracted_metadata)

        if selected is not None:
            # User clicked OK
            self.selected_chapters = selected

            # Update preview to show selected chapters
            self.text_preview.delete("1.0", tk.END)

            preview_text = f"Selected {len(selected)} of {len(self.chapters_data)} chapters:\n\n"
            for i, (title, text) in enumerate(selected, 1):
                word_count = len(text.split())
                preview_text += f"{i}. {title} ({word_count} words)\n"

            preview_text += "\n" + "=" * 60 + "\n\n"

            # Show preview of selected chapters (first 1000 chars)
            for title, text in selected:
                preview_text += f"=== {title} ===\n\n"
                preview_text += text[:1000]
                if len(text) > 1000:
                    preview_text += "...\n\n"
                else:
                    preview_text += "\n\n"

            self.text_preview.insert(tk.END, preview_text)

            total_words = sum(len(t.split()) for _, t in selected)
            self.log_message(f"Selected {len(selected)} chapters ({total_words:,} words total)")
        else:
            # User cancelled - keep previous selection or use all chapters
            if self.selected_chapters is None:
                self.selected_chapters = self.chapters_data
                self.log_message("No selection made - will process all chapters")

    def _start_generation(self):
        # --- Validate inputs ---
        model_path = self.model_path.get()
        if not model_path:
            messagebox.showerror("Error", "Please select a model file.")
            return

        if not os.path.exists(model_path):
            messagebox.showerror("Model Not Found",
                f"Model file not found:\n{model_path}\n\n"
                "Please download maya1.i1-Q5_K_M.gguf from:\n"
                "https://huggingface.co/maya-research/maya1\n\n"
                "Or run: python create_placeholders.py")
            return

        # Check if model file is too small (likely a placeholder)
        model_size = os.path.getsize(model_path)
        if model_size < 1_000_000:  # Less than 1MB is suspicious
            response = messagebox.askyesno("Warning: Small Model File",
                f"The model file is only {model_size:,} bytes.\n"
                "This appears to be a placeholder, not a real model.\n\n"
                "Synthesis will likely fail. Continue anyway?")
            if not response:
                return

        cover_path = self.cover_path.get()

        # Check for FFmpeg
        output_format = self.output_format.get()
        if output_format in ["m4b", "mp4"] and not shutil.which("ffmpeg"):
            messagebox.showerror("FFmpeg Not Found",
                f"FFmpeg is required for {output_format.upper()} export but was not found in PATH.\n\n"
                "Please install FFmpeg:\n"
                "- Windows: Download from ffmpeg.org and add to PATH\n"
                "- macOS: brew install ffmpeg\n"
                "- Linux: sudo apt install ffmpeg")
            return

        # For MP4 output, cover is required
        if output_format == "mp4":
            if not cover_path or not os.path.exists(cover_path):
                messagebox.showerror("Error", "Please select a valid cover image for MP4 output.")
                return

        output_dir = self.output_folder.get()
        if not output_dir:
            messagebox.showerror("Error", "Please select an output folder.")
            return
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Check if chapter-aware processing is enabled
        use_chapters = self.use_chapters.get()

        if use_chapters:
            # Validate chapter data
            if not self.chapters_data:
                messagebox.showerror("Error", "Please extract EPUB first to use chapter-aware processing.")
                return

            # Use selected chapters if available, otherwise use all chapters
            chapters_to_process = self.selected_chapters if self.selected_chapters else self.chapters_data

            # --- Prepare for chapter-aware pipeline ---
            self.log_message(f"Starting chapter-aware generation ({len(chapters_to_process)} chapters)...")
            self.progress['value'] = 0
            self.generate_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.NORMAL)

            self.stop_generation_flag = threading.Event()

            base_name = Path(self.epub_path.get()).stem
            output_base = str(Path(output_dir) / base_name)  # No extension

            # Prepare metadata
            metadata = {
                'title': self.metadata_title.get() or base_name,
                'author': self.metadata_author.get() or 'Unknown',
                'album': self.metadata_album.get() or self.metadata_title.get() or base_name,
                'year': self.metadata_year.get(),
                'genre': self.metadata_genre.get() or 'Audiobook',
            }

            # Run chapter-aware pipeline in thread
            self.generation_thread = threading.Thread(
                target=self._run_chapter_pipeline_thread,
                args=(
                    chapters_to_process, metadata, model_path,
                    self.voice_description.get("1.0", tk.END).strip(),
                    self.chunk_size.get(), self.gap_size.get(),
                    output_base, cover_path, output_format,
                    self.save_separately.get(), self.merge_chapters.get(),
                    self.chapter_silence.get(), self.temperature.get(),
                    self.top_p.get(), self.n_ctx.get(),
                    self.n_gpu_layers.get(), self.model_type.get(),
                ),
                daemon=True
            )
            self.generation_thread.start()

        else:
            # Legacy mode - FIXED: Use full chapter data instead of truncated preview
            if not self.chapters_data:
                messagebox.showerror("Error", "Please extract EPUB first.")
                return

            # Combine all chapters into single text (full text, not truncated)
            chapters_to_process = self.selected_chapters if self.selected_chapters else self.chapters_data
            epub_text = "\n\n".join(text for _, text in chapters_to_process)

            if not epub_text:
                messagebox.showerror("Error", "EPUB text is empty.")
                return

            if not cover_path or not os.path.exists(cover_path):
                messagebox.showerror("Error", "Please select a valid cover image for legacy MP4 mode.")
                return

            # --- Prepare for legacy pipeline ---
            self.log_message("Starting generation (legacy mode)...")
            self.progress['value'] = 0
            self.generate_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.NORMAL)

            self.stop_generation_flag = threading.Event()

            base_name = Path(self.epub_path.get()).stem
            out_wav = str(Path(output_dir) / f"{base_name}.wav")
            out_mp4 = str(Path(output_dir) / f"{base_name}.mp4")

            # --- Run legacy pipeline in a thread ---
            self.generation_thread = threading.Thread(
                target=self._run_pipeline_thread,
                args=(
                    epub_text, model_path, self.voice_description.get("1.0", tk.END).strip(),
                    self.chunk_size.get(), self.gap_size.get(), out_wav, out_mp4,
                    cover_path, self.temperature.get(), self.top_p.get(),
                    self.n_ctx.get(), self.n_gpu_layers.get(), self.model_type.get(),
                ),
                daemon=True
            )
            self.generation_thread.start()

    def _quick_test_generation(self):
        """Quick test generation - bypasses EPUB workflow."""
        # --- Validate inputs ---
        model_path = self.model_path.get()
        if not model_path:
            messagebox.showerror("Error", "Please select a model file.")
            return

        if not os.path.exists(model_path):
            messagebox.showerror("Model Not Found",
                f"Model file not found:\n{model_path}\n\n"
                "Please download maya1.i1-Q5_K_M.gguf from:\n"
                "https://huggingface.co/maya-research/maya1")
            return

        # Check if model file is too small (likely a placeholder)
        model_size = os.path.getsize(model_path)
        if model_size < 1_000_000:  # Less than 1MB is suspicious
            response = messagebox.askyesno("Warning: Small Model File",
                f"The model file is only {model_size:,} bytes.\n"
                "This appears to be a placeholder, not a real model.\n\n"
                "Synthesis will likely fail. Continue anyway?")
            if not response:
                return

        # Get test text
        test_text = self.quick_test_text.get("1.0", tk.END).strip()
        if not test_text:
            messagebox.showerror("Error", "Please enter some test text.")
            return

        # Get output directory
        output_dir = self.output_folder.get()
        if not output_dir:
            output_dir = str(Path.home() / "MayaBook_Output")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Create quick test output path with timestamp to avoid file locking issues
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_wav = str(Path(output_dir) / f"quick_test_{timestamp}.wav")

        # Stop any playing audio to prevent file locking issues
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except:
                pass

        # Disable button during generation
        self.quick_test_button.config(state=tk.DISABLED, text="Generating...")
        self.log_message("Starting quick test generation...")

        # Run in background thread
        def quick_test_thread():
            try:
                from core.chunking import chunk_text
                from core.audio_combine import concat_wavs
                import tempfile

                # Get synthesis parameters
                voice_desc = self.voice_description.get("1.0", tk.END).strip()
                chunk_size = self.chunk_size.get()
                gap_s = self.gap_size.get()
                temperature = self.temperature.get()
                top_p = self.top_p.get()
                n_ctx = self.n_ctx.get()
                n_gpu_layers = self.n_gpu_layers.get()
                model_type = self.model_type.get()

                # Import the appropriate TTS module based on model type
                if model_type == "gguf":
                    from core.tts_maya1_local import synthesize_chunk_local as synthesize_fn
                else:
                    from core.tts_maya1_hf import synthesize_chunk_hf as synthesize_fn

                # Chunk the text
                chunks = chunk_text(test_text, max_words=chunk_size)
                self.log_message(f"Text split into {len(chunks)} chunk(s)")

                # Synthesize each chunk
                wav_paths = []
                for i, chunk in enumerate(chunks, 1):
                    self.log_message(f"Synthesizing chunk {i}/{len(chunks)}...")

                    if model_type == "gguf":
                        wav_path = synthesize_fn(
                            model_path=model_path,
                            text=chunk,
                            voice_description=voice_desc,
                            temperature=temperature,
                            top_p=top_p,
                            n_ctx=n_ctx,
                            n_gpu_layers=n_gpu_layers,
                            max_tokens=2500,
                        )
                    else:  # huggingface
                        wav_path = synthesize_fn(
                            text=chunk,
                            voice_description=voice_desc,
                            model_path=model_path,
                            temperature=temperature,
                            top_p=top_p,
                        )

                    wav_paths.append(wav_path)

                # Concatenate chunks
                self.log_message("Combining audio chunks...")
                concat_wavs(wav_paths, out_wav, gap_seconds=gap_s)

                self.after(0, self._quick_test_complete, out_wav)

            except Exception as e:
                self.after(0, self._quick_test_failed, str(e))

        thread = threading.Thread(target=quick_test_thread, daemon=True)
        thread.start()

    def _quick_test_complete(self, wav_path):
        """Handle successful quick test completion."""
        self.quick_test_button.config(state=tk.NORMAL, text="Generate Quick Test Audio")
        self.log_message(f"Quick test complete! Saved to: {wav_path}")

        # Try to play the audio
        self._play_preview_audio(wav_path)

    def _quick_test_failed(self, error_msg):
        """Handle quick test failure."""
        self.quick_test_button.config(state=tk.NORMAL, text="Generate Quick Test Audio")
        self.log_message(f"Quick test failed: {error_msg}")
        messagebox.showerror("Quick Test Error", f"Failed to generate quick test:\n{error_msg}")

    def _run_chapter_pipeline_thread(self, chapters, metadata, model_path, voice_desc,
                                    chunk_size, gap_s, output_base, cover_path, output_format,
                                    save_separately, merge_chapters, chapter_silence,
                                    temperature, top_p, n_ctx, n_gpu_layers, model_type):
        """Thread for running chapter-aware pipeline."""
        try:
            result = run_pipeline_with_chapters(
                chapters=chapters,
                metadata=metadata,
                model_path=model_path,
                voice_desc=voice_desc,
                chunk_size=chunk_size,
                gap_s=gap_s,
                output_base_path=output_base,
                cover_image=cover_path,
                output_format=output_format,
                save_chapters_separately=save_separately,
                merge_chapters=merge_chapters,
                chapter_silence=chapter_silence,
                temperature=temperature,
                top_p=top_p,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                workers=1,
                max_tokens=2500,
                model_type=model_type,
                progress_cb=self._update_progress,
                stop_flag=self.stop_generation_flag,
            )

            if self.stop_generation_flag and self.stop_generation_flag.is_set():
                self.after(0, self._generation_cancelled)
            else:
                self.after(0, self._generation_complete, result)
        except Exception as e:
            self.after(0, self._generation_failed, e)

    def _run_pipeline_thread(self, *args):
        try:
            # Last arg is model_type, extract it for keyword arg
            model_type = args[-1]
            other_args = args[:-1]
            run_pipeline(*other_args, model_type=model_type, progress_cb=self._update_progress, stop_flag=self.stop_generation_flag)

            if self.stop_generation_flag and self.stop_generation_flag.is_set():
                self.after(0, self._generation_cancelled)
            else:
                self.after(0, self._generation_complete)
        except Exception as e:
            self.after(0, self._generation_failed, e)

    def _update_progress(self, current, total, chapter_info=None):
        """Update progress bar and log message."""
        self.progress['maximum'] = total
        self.progress['value'] = current

        if chapter_info:
            self.log_message(f"{chapter_info}: Chunk {current}/{total}")
        else:
            self.log_message(f"Synthesized chunk {current} of {total}...")

    def _generation_complete(self, result=None):
        """Handle successful generation completion."""
        self.log_message("Generation completed successfully!")

        if result and isinstance(result, dict):
            # Chapter-aware pipeline result
            if result.get('merged_path'):
                self.log_message(f"✓ Merged file: {result['merged_path']}")
            if result.get('chapter_paths'):
                self.log_message(f"✓ Created {len(result['chapter_paths'])} separate chapter files")

            messagebox.showinfo("Success",
                f"Audiobook generation complete!\n\n"
                f"Format: {self.output_format.get().upper()}\n"
                f"Chapters: {len(result.get('chapter_times', []))}")
        else:
            # Legacy pipeline result
            messagebox.showinfo("Success", "MP4 generation complete.")

        self._reset_ui_state()

    def _generation_failed(self, error):
        self.log_message(f"Generation failed: {error}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Generation Error", f"An error occurred:\n{error}")
        self._reset_ui_state()

    def _generation_cancelled(self):
        self.log_message("Generation cancelled by user.")
        self._reset_ui_state()

    def _cancel_generation(self):
        if self.stop_generation_flag:
            self.stop_generation_flag.set()
            self.log_message("Cancellation requested...")
            self.cancel_button.config(state=tk.DISABLED) # Prevent multiple clicks

    def _reset_ui_state(self):
        self.generate_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.generation_thread = None
        self.stop_generation_flag = None

    def _check_ffmpeg(self):
        """Check FFmpeg availability on startup."""
        is_available, message = verify_ffmpeg_available()
        if not is_available:
            self.log_message(f"⚠️ {message}")
            self.log_message("M4B format requires FFmpeg. Please install FFmpeg to use M4B export.")
            # Disable M4B option if FFmpeg not available
            self.format_combo.config(values=["wav", "mp4"])
            if self.output_format.get() == "m4b":
                self.output_format.set("wav")
        else:
            self.log_message(f"✓ {message}")

    def _toggle_chapter_options(self):
        """Enable/disable chapter options based on checkbox state."""
        enabled = self.use_chapters.get()
        state = tk.NORMAL if enabled else tk.DISABLED

        self.save_sep_check.config(state=state)
        self.merge_check.config(state=state)

        # Also toggle metadata fields
        for widget in self.metadata_frame.winfo_children():
            if isinstance(widget, ttk.Entry) or isinstance(widget, ttk.Spinbox):
                widget.config(state=state)

    def _open_folder(self, path):
        if not path or not os.path.isdir(path):
            messagebox.showerror("Error", f"Folder not found:\n{path}")
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except OSError as e:
            messagebox.showerror("Error", f"Failed to open folder:\n{e}")

    def _on_voice_preset_change(self, event=None):
        """Handle voice preset selection - update voice description text."""
        preset_name = self.voice_preset.get()
        preset = get_preset_by_name(preset_name)

        if preset:
            # Update the voice description text box
            self.voice_description.delete("1.0", tk.END)
            self.voice_description.insert(tk.END, preset["description"])
            self.log_message(f"Voice preset changed to: {preset_name}")

            # Show preset details
            details = f"{preset.get('age', 'N/A')}, {preset.get('accent', 'N/A')}"
            self.log_message(f"  Details: {details}")
        else:
            self.log_message(f"Warning: Preset '{preset_name}' not found")

    def _preview_voice(self):
        """Generate and play a voice preview sample."""
        model_path = self.model_path.get()
        if not model_path or not os.path.exists(model_path):
            messagebox.showerror("Error", "Please select a valid model file first.")
            return

        # Check if model is too small (placeholder)
        model_size = os.path.getsize(model_path)
        if model_size < 1_000_000:
            messagebox.showerror("Error",
                f"Model file appears to be a placeholder ({model_size:,} bytes).\n"
                "Please download the full model file first.")
            return

        voice_desc = self.voice_description.get("1.0", tk.END).strip()
        if not voice_desc:
            messagebox.showerror("Error", "Voice description is empty.")
            return

        # Get synthesis parameters
        temperature = self.temperature.get()
        top_p = self.top_p.get()
        n_ctx = self.n_ctx.get()
        n_gpu_layers = self.n_gpu_layers.get()

        # Check if already cached
        cached_path = get_cached_preview_path(voice_desc, model_path, temperature, top_p)
        if cached_path:
            self.log_message("Using cached voice preview...")
            self._play_preview_audio(cached_path)
            return

        # Generate preview in background thread
        self.log_message("Generating voice preview (this may take 10-30 seconds)...")
        self.preview_button.config(state=tk.DISABLED, text="Generating...")

        def generate_thread():
            try:
                preview_path = generate_voice_preview(
                    voice_description=voice_desc,
                    model_path=model_path,
                    temperature=temperature,
                    top_p=top_p,
                    n_ctx=n_ctx,
                    n_gpu_layers=n_gpu_layers,
                )
                self.after(0, self._preview_generated_success, preview_path)
            except Exception as e:
                self.after(0, self._preview_generated_error, str(e))

        thread = threading.Thread(target=generate_thread, daemon=True)
        thread.start()

    def _preview_generated_success(self, preview_path):
        """Handle successful preview generation."""
        self.preview_button.config(state=tk.NORMAL, text="Preview Voice")
        self.log_message("Voice preview generated successfully!")
        self._play_preview_audio(preview_path)

    def _preview_generated_error(self, error_msg):
        """Handle preview generation error."""
        self.preview_button.config(state=tk.NORMAL, text="Preview Voice")
        self.log_message(f"Preview generation failed: {error_msg}")
        messagebox.showerror("Preview Error", f"Failed to generate voice preview:\n{error_msg}")

    def _play_preview_audio(self, audio_path):
        """Play a preview audio file using pygame."""
        if not PYGAME_AVAILABLE:
            self.log_message("Audio playback not available (pygame not installed)")
            messagebox.showinfo("Preview Ready",
                f"Voice preview generated:\n{audio_path}\n\n"
                "Install 'pygame' package for in-app playback.")
            return

        try:
            # Load and play the audio file using pygame
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()

            # Get duration for logging
            import soundfile as sf
            audio_data, sample_rate = sf.read(audio_path)
            duration = len(audio_data) / sample_rate

            self.log_message(f"Playing voice preview ({duration:.1f}s)...")
            messagebox.showinfo("Preview Playing",
                f"Voice preview is playing ({duration:.1f}s)\n\n"
                f"Preview file saved at:\n{audio_path}")

        except Exception as e:
            self.log_message(f"Audio playback error: {e}")
            messagebox.showerror("Playback Error",
                f"Failed to play audio:\n{e}\n\n"
                f"Preview file saved at:\n{audio_path}")

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
