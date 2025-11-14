# ui/main_window_enhanced.py
"""
Enhanced MayaBook GUI with:
- GPU detection and recommendations
- Smart defaults
- Configuration profiles
- Enhanced progress tracking
- Batch processing
- Advanced audio settings
- Keyboard shortcuts
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import subprocess
import sys
import shutil
from pathlib import Path
import json

# Core modules
from core.epub_extract import extract_text, extract_chapters
from core.pipeline import run_pipeline, run_pipeline_with_chapters
from core.m4b_export import verify_ffmpeg_available

# Enhanced modules
from core.gpu_utils import get_gpu_info, get_recommended_gguf_settings, format_vram_info, get_current_vram_usage
from core.config_manager import ConfigManager, get_smart_defaults, BUILTIN_PROFILES, find_matching_cover
from core.progress_tracker import ProgressTracker, format_progress_message
from core.batch_processor import BatchProcessor, BatchItemStatus
from core.audio_advanced import PronunciationDictionary

# Audio playback using pygame
try:
    import pygame.mixer
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except (ImportError, Exception):
    PYGAME_AVAILABLE = False


class EnhancedMainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MayaBook - Enhanced Edition")
        self.geometry("950x1000")

        # Initialize configuration manager
        self.config_mgr = ConfigManager()

        # Initialize pronunciation dictionary
        self.pronunciation_dict = PronunciationDictionary()

        # State variables
        self.stop_generation_flag = None
        self.generation_thread = None
        self.chapters_data = None
        self.extracted_metadata = None
        self.progress_tracker = None
        self.batch_processor = None
        self.gpu_info = None

        # Create menu bar
        self._create_menu()

        # Create main UI
        self._create_widgets()
        self._create_action_buttons()
        self._create_log_widget()

        # Load saved settings
        self._load_saved_settings()

        # Setup keyboard shortcuts
        self._setup_shortcuts()

        # Initial messages
        self.log_message("Welcome to MayaBook Enhanced Edition!")
        self._check_ffmpeg()
        self._detect_gpu()

    def _create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Defaults", command=self._load_smart_defaults, accelerator="Ctrl+D")
        file_menu.add_command(label="Save Settings", command=self._save_current_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Batch Processing...", command=self._open_batch_window)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit, accelerator="Ctrl+Q")

        # Profiles menu
        profiles_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Profiles", menu=profiles_menu)
        profiles_menu.add_command(label="Save Current as Profile...", command=self._save_profile_dialog)
        profiles_menu.add_command(label="Load Profile...", command=self._load_profile_dialog)
        profiles_menu.add_separator()

        # Add builtin profiles
        for profile_name in BUILTIN_PROFILES.keys():
            profiles_menu.add_command(
                label=f"Load: {profile_name}",
                command=lambda p=profile_name: self._load_builtin_profile(p)
            )

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="GPU Information", command=self._show_gpu_info)
        tools_menu.add_command(label="Pronunciation Dictionary...", command=self._open_pronunciation_dict)
        tools_menu.add_command(label="Audio Settings...", command=self._open_audio_settings)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.bind('<Control-d>', lambda e: self._load_smart_defaults())
        self.bind('<Control-g>', lambda e: self._start_generation())
        self.bind('<Control-e>', lambda e: self._extract_epub())
        self.bind('<Control-q>', lambda e: self.quit())
        self.bind('<Control-o>', lambda e: self._open_folder(self.output_folder.get()))
        self.bind('<Control-s>', lambda e: self._save_current_settings())

    def _create_widgets(self):
        # Create canvas with scrollbar
        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        main_frame = ttk.Frame(canvas, padding="10")

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        canvas_frame = canvas.create_window((0, 0), window=main_frame, anchor="nw")

        def on_frame_configure(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfig(canvas_frame, width=event.width)

        main_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        row = 0

        # --- GPU Status Banner ---
        self.gpu_frame = ttk.LabelFrame(main_frame, text="GPU Status")
        self.gpu_frame.grid(row=row, column=0, padx=5, pady=5, sticky="ew")
        row += 1

        self.gpu_status_label = ttk.Label(self.gpu_frame, text="Detecting GPU...", foreground="gray")
        self.gpu_status_label.pack(side=tk.LEFT, padx=10, pady=5)

        ttk.Button(self.gpu_frame, text="Auto-Configure GPU", command=self._auto_configure_gpu).pack(side=tk.RIGHT, padx=5, pady=5)
        ttk.Button(self.gpu_frame, text="Refresh", command=self._detect_gpu).pack(side=tk.RIGHT, padx=5, pady=5)

        # --- Quick Actions ---
        quick_frame = ttk.LabelFrame(main_frame, text="Quick Actions")
        quick_frame.grid(row=row, column=0, padx=5, pady=5, sticky="ew")
        row += 1

        ttk.Button(quick_frame, text="Load Smart Defaults (Ctrl+D)", command=self._load_smart_defaults).pack(side=tk.LEFT, padx=5, pady=5)

        # Profile dropdown
        ttk.Label(quick_frame, text="Profile:").pack(side=tk.LEFT, padx=(15, 5), pady=5)
        self.profile_var = tk.StringVar(value="Custom")
        profile_names = ["Custom"] + list(BUILTIN_PROFILES.keys()) + self.config_mgr.get_profile_names()
        self.profile_combo = ttk.Combobox(quick_frame, textvariable=self.profile_var, values=profile_names, state="readonly", width=25)
        self.profile_combo.pack(side=tk.LEFT, padx=5, pady=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)

        # --- File Paths (with drag-drop indicators) ---
        file_frame = ttk.LabelFrame(main_frame, text="I/O Paths")
        file_frame.grid(row=row, column=0, padx=5, pady=5, sticky="ew")
        file_frame.grid_columnconfigure(1, weight=1)
        row += 1

        ttk.Label(file_frame, text="EPUB File:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.epub_path = tk.StringVar()
        epub_entry = ttk.Entry(file_frame, textvariable=self.epub_path, width=60)
        epub_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(file_frame, text="Browse...", command=self._select_epub).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(file_frame, text="Cover Image:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.cover_path = tk.StringVar()
        cover_entry = ttk.Entry(file_frame, textvariable=self.cover_path, width=60)
        cover_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(file_frame, text="Browse...", command=self._select_cover).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(file_frame, text="Auto-Find", command=self._auto_find_cover).grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(file_frame, text="Output Folder:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.output_folder = tk.StringVar(value=str(Path.home() / "MayaBook_Output"))
        ttk.Entry(file_frame, textvariable=self.output_folder, width=60).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(file_frame, text="Browse...", command=self._select_output).grid(row=2, column=2, padx=5, pady=5)

        # --- Model Settings ---
        model_frame = ttk.LabelFrame(main_frame, text="Model Settings")
        model_frame.grid(row=row, column=0, padx=5, pady=5, sticky="ew")
        model_frame.grid_columnconfigure(1, weight=1)
        row += 1

        ttk.Label(model_frame, text="Model Type:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.model_type = tk.StringVar(value="gguf")
        model_type_combo = ttk.Combobox(model_frame, textvariable=self.model_type, values=["gguf", "huggingface"], state="readonly", width=15)
        model_type_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        model_type_combo.bind("<<ComboboxSelected>>", self._on_model_type_change)

        ttk.Label(model_frame, text="Model Path:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.model_path = tk.StringVar(value="assets/models/maya1.i1-Q5_K_M.gguf")
        ttk.Entry(model_frame, textvariable=self.model_path, width=60).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(model_frame, text="Browse...", command=self._select_model).grid(row=1, column=2, padx=5, pady=5)

        # GGUF settings
        self.gguf_settings_frame = ttk.Frame(model_frame)
        self.gguf_settings_frame.grid(row=2, column=0, columnspan=3, sticky="ew")

        ttk.Label(self.gguf_settings_frame, text="n_ctx:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.n_ctx = tk.IntVar(value=4096)
        ttk.Entry(self.gguf_settings_frame, textvariable=self.n_ctx, width=10).grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(self.gguf_settings_frame, text="n_gpu_layers:").grid(row=0, column=2, padx=15, pady=5, sticky="w")
        self.n_gpu_layers = tk.IntVar(value=-1)
        ttk.Entry(self.gguf_settings_frame, textvariable=self.n_gpu_layers, width=10).grid(row=0, column=3, padx=5, pady=5, sticky="w")

        self.gpu_recommend_label = ttk.Label(self.gguf_settings_frame, text="", foreground="blue")
        self.gpu_recommend_label.grid(row=0, column=4, padx=10, pady=5, sticky="w")

        # --- TTS Settings ---
        tts_frame = ttk.LabelFrame(main_frame, text="TTS Synthesis Settings")
        tts_frame.grid(row=row, column=0, padx=5, pady=5, sticky="ew")
        tts_frame.grid_columnconfigure(1, weight=1)
        row += 1

        ttk.Label(tts_frame, text="Voice Description:").grid(row=0, column=0, padx=5, pady=5, sticky="nw")
        self.voice_description = tk.Text(tts_frame, height=3, width=60)
        self.voice_description.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        self.voice_description.insert(tk.END, "A female speaker with a warm, calm, and clear voice, delivering the narration in a standard American English accent.")

        ttk.Label(tts_frame, text="Temperature:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.temperature = tk.DoubleVar(value=0.45)
        ttk.Entry(tts_frame, textvariable=self.temperature, width=10).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(tts_frame, text="Top-p:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.top_p = tk.DoubleVar(value=0.92)
        ttk.Entry(tts_frame, textvariable=self.top_p, width=10).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(tts_frame, text="Chunk Size (words):").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.chunk_size = tk.IntVar(value=70)
        ttk.Entry(tts_frame, textvariable=self.chunk_size, width=10).grid(row=3, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(tts_frame, text="Gap (seconds):").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.gap_size = tk.DoubleVar(value=0.25)
        ttk.Entry(tts_frame, textvariable=self.gap_size, width=10).grid(row=4, column=1, padx=5, pady=5, sticky="w")

        # --- Output Format ---
        format_frame = ttk.LabelFrame(main_frame, text="Output Format")
        format_frame.grid(row=row, column=0, padx=5, pady=5, sticky="ew")
        row += 1

        ttk.Label(format_frame, text="Format:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.output_format = tk.StringVar(value="m4b")
        self.format_combo = ttk.Combobox(format_frame, textvariable=self.output_format,
                                         values=["m4b", "wav", "mp4"], state="readonly", width=15)
        self.format_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # --- Chapter Options ---
        chapter_frame = ttk.LabelFrame(main_frame, text="Chapter Options")
        chapter_frame.grid(row=row, column=0, padx=5, pady=5, sticky="ew")
        row += 1

        self.use_chapters = tk.BooleanVar(value=True)
        ttk.Checkbutton(chapter_frame, text="Enable chapter-aware processing",
                       variable=self.use_chapters, command=self._toggle_chapter_options).grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.save_separately = tk.BooleanVar(value=False)
        ttk.Checkbutton(chapter_frame, text="Save chapters separately",
                       variable=self.save_separately).grid(row=1, column=0, padx=25, pady=2, sticky="w")

        self.merge_chapters = tk.BooleanVar(value=True)
        ttk.Checkbutton(chapter_frame, text="Create merged file",
                       variable=self.merge_chapters).grid(row=2, column=0, padx=25, pady=2, sticky="w")

        ttk.Label(chapter_frame, text="Chapter silence (seconds):").grid(row=3, column=0, padx=25, pady=5, sticky="w")
        self.chapter_silence = tk.DoubleVar(value=2.0)
        ttk.Spinbox(chapter_frame, from_=0.5, to=5.0, increment=0.5,
                   textvariable=self.chapter_silence, width=8).grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # --- Metadata ---
        metadata_frame = ttk.LabelFrame(main_frame, text="Metadata")
        metadata_frame.grid(row=row, column=0, padx=5, pady=5, sticky="ew")
        metadata_frame.grid_columnconfigure(1, weight=1)
        row += 1

        ttk.Label(metadata_frame, text="Title:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.metadata_title = tk.StringVar()
        ttk.Entry(metadata_frame, textvariable=self.metadata_title, width=50).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(metadata_frame, text="Author:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.metadata_author = tk.StringVar()
        ttk.Entry(metadata_frame, textvariable=self.metadata_author, width=50).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(metadata_frame, text="Year:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.metadata_year = tk.StringVar()
        ttk.Entry(metadata_frame, textvariable=self.metadata_year, width=15).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(metadata_frame, text="Genre:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.metadata_genre = tk.StringVar(value="Audiobook")
        ttk.Entry(metadata_frame, textvariable=self.metadata_genre, width=30).grid(row=3, column=1, padx=5, pady=5, sticky="w")

        self.metadata_status_label = ttk.Label(metadata_frame, text="", foreground="gray")
        self.metadata_status_label.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        # --- EPUB Preview ---
        preview_frame = ttk.LabelFrame(main_frame, text="EPUB Preview")
        preview_frame.grid(row=row, column=0, padx=5, pady=5, sticky="nsew")
        main_frame.grid_rowconfigure(row, weight=1)
        row += 1

        self.text_preview = tk.Text(preview_frame, wrap=tk.WORD, height=10)
        preview_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.text_preview.yview)
        self.text_preview.config(yscrollcommand=preview_scroll.set)
        self.text_preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_action_buttons(self):
        actions_frame = ttk.Frame(self)
        actions_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.extract_button = ttk.Button(actions_frame, text="Extract EPUB (Ctrl+E)", command=self._extract_epub)
        self.extract_button.pack(side=tk.LEFT, padx=5)

        self.generate_button = ttk.Button(actions_frame, text="Start Generation (Ctrl+G)", command=self._start_generation)
        self.generate_button.pack(side=tk.LEFT, padx=5)

        self.cancel_button = ttk.Button(actions_frame, text="Cancel", command=self._cancel_generation, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5)

        self.open_folder_button = ttk.Button(actions_frame, text="Open Output (Ctrl+O)",
                                             command=lambda: self._open_folder(self.output_folder.get()))
        self.open_folder_button.pack(side=tk.LEFT, padx=5)

    def _create_log_widget(self):
        log_frame = ttk.LabelFrame(self, text="Status Log")
        log_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.grid_rowconfigure(2, weight=1)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=10, state=tk.DISABLED)
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Enhanced progress frame
        progress_frame = ttk.Frame(self)
        progress_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        self.progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        self.progress_detail_label = ttk.Label(progress_frame, text="", foreground="gray")
        self.progress_detail_label.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

    # --- Helper Methods (Continued in next part) ---

    def log_message(self, msg):
        """Log message to UI"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.update_idletasks()

    def _detect_gpu(self):
        """Detect GPU and display information"""
        self.gpu_info = get_gpu_info()

        if self.gpu_info['available']:
            vram_text = format_vram_info(self.gpu_info['vram_total_mb'])
            vram_free_text = format_vram_info(self.gpu_info['vram_free_mb'])
            status_text = f"✓ {self.gpu_info['name']} | {vram_text} total | {vram_free_text} free"
            self.gpu_status_label.config(text=status_text, foreground="green")
            self.log_message(f"GPU detected: {self.gpu_info['name']}")
        else:
            self.gpu_status_label.config(text="⚠️ No GPU detected - CPU mode (slow)", foreground="orange")
            self.log_message("No GPU detected. Synthesis will use CPU (very slow).")

    def _auto_configure_gpu(self):
        """Auto-configure GPU settings based on detection"""
        model_path = self.model_path.get()

        settings = get_recommended_gguf_settings(model_path)

        self.n_gpu_layers.set(settings['n_gpu_layers'])
        self.n_ctx.set(settings['n_ctx'])

        self.log_message(f"GPU Auto-Config: {settings['explanation']}")

        if settings['warnings']:
            for warning in settings['warnings']:
                self.log_message(f"⚠️ {warning}")

        self.gpu_recommend_label.config(text=f"✓ Optimized")

    def _load_smart_defaults(self):
        """Load smart default file paths"""
        defaults = get_smart_defaults()

        if defaults['model_path']:
            self.model_path.set(defaults['model_path'])
            self.log_message(f"Auto-loaded model: {Path(defaults['model_path']).name}")

        if defaults['epub_path']:
            self.epub_path.set(defaults['epub_path'])
            self.log_message(f"Auto-loaded EPUB: {Path(defaults['epub_path']).name}")

        if defaults['cover_path']:
            self.cover_path.set(defaults['cover_path'])
            self.log_message(f"Auto-loaded cover: {Path(defaults['cover_path']).name}")

        if defaults['output_folder']:
            self.output_folder.set(defaults['output_folder'])

        self.log_message("✓ Smart defaults loaded")

    def _auto_find_cover(self):
        """Automatically find cover matching EPUB"""
        epub_path = self.epub_path.get()
        if not epub_path:
            messagebox.showwarning("No EPUB", "Please select an EPUB file first.")
            return

        cover = find_matching_cover(epub_path)
        if cover:
            self.cover_path.set(cover)
            self.log_message(f"✓ Found matching cover: {Path(cover).name}")
        else:
            messagebox.showinfo("No Cover Found", "Could not find a matching cover image.")

    def _save_current_settings(self):
        """Save current settings to config"""
        settings = self._get_current_settings()
        self.config_mgr.save_gui_settings(settings)

        # Update recent files
        if self.epub_path.get():
            self.config_mgr.add_recent_file('epubs', self.epub_path.get())
        if self.cover_path.get():
            self.config_mgr.add_recent_file('covers', self.cover_path.get())
        if self.model_path.get():
            self.config_mgr.add_recent_file('models', self.model_path.get())

        self.log_message("✓ Settings saved")

    def _load_saved_settings(self):
        """Load saved settings from config"""
        settings = self.config_mgr.get_gui_settings()
        self._apply_settings(settings)

        # Load last used paths
        last_epub = self.config_mgr.get_last_used('epub_path')
        if last_epub:
            self.epub_path.set(last_epub)

        last_cover = self.config_mgr.get_last_used('cover_path')
        if last_cover:
            self.cover_path.set(last_cover)

        last_model = self.config_mgr.get_last_used('model_path')
        if last_model:
            self.model_path.set(last_model)

        last_output = self.config_mgr.get_last_used('output_folder')
        if last_output:
            self.output_folder.set(last_output)

    def _get_current_settings(self) -> dict:
        """Get current GUI settings as dict"""
        return {
            'model_type': self.model_type.get(),
            'n_ctx': self.n_ctx.get(),
            'n_gpu_layers': self.n_gpu_layers.get(),
            'temperature': self.temperature.get(),
            'top_p': self.top_p.get(),
            'chunk_size': self.chunk_size.get(),
            'gap_size': self.gap_size.get(),
            'output_format': self.output_format.get(),
            'use_chapters': self.use_chapters.get(),
            'save_separately': self.save_separately.get(),
            'merge_chapters': self.merge_chapters.get(),
            'chapter_silence': self.chapter_silence.get(),
            'voice_description': self.voice_description.get("1.0", tk.END).strip(),
        }

    def _apply_settings(self, settings: dict):
        """Apply settings dict to GUI"""
        if 'model_type' in settings:
            self.model_type.set(settings['model_type'])
        if 'n_ctx' in settings:
            self.n_ctx.set(settings['n_ctx'])
        if 'n_gpu_layers' in settings:
            self.n_gpu_layers.set(settings['n_gpu_layers'])
        if 'temperature' in settings:
            self.temperature.set(settings['temperature'])
        if 'top_p' in settings:
            self.top_p.set(settings['top_p'])
        if 'chunk_size' in settings:
            self.chunk_size.set(settings['chunk_size'])
        if 'gap_size' in settings:
            self.gap_size.set(settings['gap_size'])
        if 'output_format' in settings:
            self.output_format.set(settings['output_format'])
        if 'use_chapters' in settings:
            self.use_chapters.set(settings['use_chapters'])
        if 'save_separately' in settings:
            self.save_separately.set(settings['save_separately'])
        if 'merge_chapters' in settings:
            self.merge_chapters.set(settings['merge_chapters'])
        if 'chapter_silence' in settings:
            self.chapter_silence.set(settings['chapter_silence'])
        if 'voice_description' in settings:
            self.voice_description.delete("1.0", tk.END)
            self.voice_description.insert("1.0", settings['voice_description'])

    def _save_profile_dialog(self):
        """Dialog to save current settings as profile"""
        name = tk.simpledialog.askstring("Save Profile", "Enter profile name:")
        if name:
            settings = self._get_current_settings()
            self.config_mgr.save_profile(name, settings)
            self.log_message(f"✓ Profile '{name}' saved")

            # Update profile dropdown
            profile_names = ["Custom"] + list(BUILTIN_PROFILES.keys()) + self.config_mgr.get_profile_names()
            self.profile_combo.config(values=profile_names)

    def _load_profile_dialog(self):
        """Dialog to load a profile"""
        profiles = self.config_mgr.get_profile_names()
        if not profiles:
            messagebox.showinfo("No Profiles", "No saved profiles found.")
            return

        # Create selection dialog
        dialog = tk.Toplevel(self)
        dialog.title("Load Profile")
        dialog.geometry("300x200")

        ttk.Label(dialog, text="Select profile:").pack(padx=10, pady=10)

        listbox = tk.Listbox(dialog)
        for profile in profiles:
            listbox.insert(tk.END, profile)
        listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        def load_selected():
            selection = listbox.curselection()
            if selection:
                profile_name = listbox.get(selection[0])
                profile = self.config_mgr.load_profile(profile_name)
                if profile:
                    self._apply_settings(profile)
                    self.profile_var.set(profile_name)
                    self.log_message(f"✓ Loaded profile: {profile_name}")
                dialog.destroy()

        ttk.Button(dialog, text="Load", command=load_selected).pack(pady=5)

    def _load_builtin_profile(self, profile_name: str):
        """Load a builtin profile"""
        if profile_name in BUILTIN_PROFILES:
            settings = BUILTIN_PROFILES[profile_name]
            self._apply_settings(settings)
            self.profile_var.set(profile_name)
            self.log_message(f"✓ Loaded builtin profile: {profile_name}")

    def _on_profile_selected(self, event=None):
        """Handle profile selection from dropdown"""
        profile_name = self.profile_var.get()

        if profile_name == "Custom":
            return

        # Try builtin profiles first
        if profile_name in BUILTIN_PROFILES:
            self._load_builtin_profile(profile_name)
        else:
            # Try user profiles
            profile = self.config_mgr.load_profile(profile_name)
            if profile:
                self._apply_settings(profile)
                self.log_message(f"✓ Loaded profile: {profile_name}")

    # Continue with remaining methods in part 2...

    def _select_epub(self):
        path = filedialog.askopenfilename(filetypes=[("EPUB files", "*.epub")])
        if path:
            self.epub_path.set(path)
            self.config_mgr.set_last_used('epub_path', path)
            self.log_message(f"Selected EPUB: {Path(path).name}")

    def _select_cover(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp")])
        if path:
            self.cover_path.set(path)
            self.config_mgr.set_last_used('cover_path', path)
            self.log_message(f"Selected cover: {Path(path).name}")

    def _select_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_folder.set(path)
            self.config_mgr.set_last_used('output_folder', path)
            self.log_message(f"Selected output folder: {Path(path).name}")

    def _select_model(self):
        model_type = self.model_type.get()
        if model_type == "gguf":
            path = filedialog.askopenfilename(filetypes=[("GGUF model files", "*.gguf")])
        else:
            path = filedialog.askdirectory(title="Select HuggingFace Model Directory")
        if path:
            self.model_path.set(path)
            self.config_mgr.set_last_used('model_path', path)
            self.log_message(f"Selected model: {Path(path).name}")

    def _on_model_type_change(self, event=None):
        model_type = self.model_type.get()
        if model_type == "gguf":
            self.gguf_settings_frame.grid()
        else:
            self.gguf_settings_frame.grid_remove()
        self.log_message(f"Model type: {model_type}")

    def _extract_epub(self):
        epub_path = self.epub_path.get()
        if not epub_path:
            messagebox.showerror("Error", "Please select an EPUB file.")
            return

        try:
            self.log_message(f"Extracting {Path(epub_path).name}...")
            metadata, chapters = extract_chapters(epub_path)

            self.chapters_data = chapters
            self.extracted_metadata = metadata

            # Populate metadata
            if metadata.get('title'):
                self.metadata_title.set(metadata['title'])
            if metadata.get('author'):
                self.metadata_author.set(metadata['author'])
            if metadata.get('year'):
                self.metadata_year.set(metadata['year'])
            if metadata.get('genre'):
                self.metadata_genre.set(metadata['genre'])

            # Show preview
            self.text_preview.delete("1.0", tk.END)
            if chapters:
                preview = f"Found {len(chapters)} chapter(s):\n\n"
                for i, (title, text) in enumerate(chapters, 1):
                    preview += f"{i}. {title} ({len(text.split())} words)\n"
                self.text_preview.insert(tk.END, preview)
                self.log_message(f"✓ Extracted {len(chapters)} chapters")
            else:
                self.text_preview.insert(tk.END, "No chapters found.")
                self.log_message("⚠️ No chapters found")

        except Exception as e:
            self.log_message(f"❌ Error: {e}")
            messagebox.showerror("EPUB Error", str(e))

    def _start_generation(self):
        """Start audio generation (reuse existing logic with enhancements)"""
        # This will integrate with existing generation logic
        # For now, placeholder
        self.log_message("Generation starting...")
        messagebox.showinfo("WIP", "Generation integration in progress")

    def _cancel_generation(self):
        if self.stop_generation_flag:
            self.stop_generation_flag.set()
            self.log_message("Cancellation requested...")

    def _toggle_chapter_options(self):
        """Toggle chapter options"""
        pass  # Implement based on existing logic

    def _check_ffmpeg(self):
        """Check FFmpeg availability"""
        is_available, message = verify_ffmpeg_available()
        if is_available:
            self.log_message(f"✓ {message}")
        else:
            self.log_message(f"⚠️ {message}")

    def _open_folder(self, path):
        """Open folder in file explorer"""
        if not path or not os.path.isdir(path):
            messagebox.showerror("Error", f"Folder not found: {path}")
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except OSError as e:
            messagebox.showerror("Error", f"Failed to open folder: {e}")

    # === Dialog Windows ===

    def _open_batch_window(self):
        """Open batch processing window"""
        messagebox.showinfo("Batch Processing", "Batch processing window coming soon!")

    def _open_pronunciation_dict(self):
        """Open pronunciation dictionary editor"""
        messagebox.showinfo("Pronunciation Dictionary", "Dictionary editor coming soon!")

    def _open_audio_settings(self):
        """Open advanced audio settings"""
        messagebox.showinfo("Audio Settings", "Advanced audio settings coming soon!")

    def _show_gpu_info(self):
        """Show detailed GPU information"""
        if not self.gpu_info:
            self._detect_gpu()

        info_text = f"""GPU Information:

Name: {self.gpu_info['name']}
Available: {self.gpu_info['available']}
CUDA Available: {self.gpu_info['cuda_available']}
Driver Version: {self.gpu_info['driver_version']}

VRAM:
  Total: {format_vram_info(self.gpu_info['vram_total_mb'])}
  Free: {format_vram_info(self.gpu_info['vram_free_mb'])}
  Used: {format_vram_info(self.gpu_info['vram_used_mb'])}
"""
        messagebox.showinfo("GPU Information", info_text)

    def _show_about(self):
        """Show about dialog"""
        about_text = """MayaBook Enhanced Edition

A local EPUB-to-audiobook converter using Maya1 TTS.

Features:
• GPU acceleration
• Chapter-aware processing
• M4B audiobook export
• Configuration profiles
• Batch processing
• Advanced audio controls

Version: 2.0 Enhanced
"""
        messagebox.showinfo("About MayaBook", about_text)

    def _show_shortcuts(self):
        """Show keyboard shortcuts"""
        shortcuts_text = """Keyboard Shortcuts:

Ctrl+D - Load Smart Defaults
Ctrl+E - Extract EPUB
Ctrl+G - Start Generation
Ctrl+O - Open Output Folder
Ctrl+S - Save Settings
Ctrl+Q - Quit

"""
        messagebox.showinfo("Keyboard Shortcuts", shortcuts_text)


if __name__ == "__main__":
    app = EnhancedMainWindow()
    app.mainloop()
