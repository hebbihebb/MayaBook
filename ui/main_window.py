import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import subprocess
import sys
import shutil
from pathlib import Path

# Assuming these modules exist and are correct
from core.epub_extract import extract_text
from core.pipeline import run_pipeline

# The old preview system used pyttsx3, which is no longer the focus.
# We'll keep the simpleaudio part for potential playback.
try:
    import simpleaudio as sa
except ImportError:
    sa = None

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MayaBook Local GGUF")
        self.geometry("850x750")

        self.stop_generation_flag = None
        self.generation_thread = None

        self._create_widgets()
        self._create_action_buttons()

        # Add a logger text box
        self._create_log_widget()
        self.log_message("Welcome to MayaBook!")

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

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

        ttk.Label(tts_frame, text="Voice Description:").grid(row=0, column=0, padx=5, pady=5, sticky="nw")
        self.voice_description = tk.Text(tts_frame, height=3, width=60)
        self.voice_description.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        self.voice_description.insert(tk.END, "A female speaker with a warm, calm, and clear voice, delivering the narration in a standard American English accent. Her tone is engaging and pleasant, suitable for long listening sessions.")

        ttk.Label(tts_frame, text="Temperature:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.temperature = tk.DoubleVar(value=0.45)
        ttk.Entry(tts_frame, textvariable=self.temperature, width=10).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(tts_frame, text="Top-p:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.top_p = tk.DoubleVar(value=0.92)
        ttk.Entry(tts_frame, textvariable=self.top_p, width=10).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(tts_frame, text="Chunk Size (words):").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.chunk_size = tk.IntVar(value=90)
        ttk.Entry(tts_frame, textvariable=self.chunk_size, width=10).grid(row=3, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(tts_frame, text="Gap (seconds):").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.gap_size = tk.DoubleVar(value=0.25)
        ttk.Entry(tts_frame, textvariable=self.gap_size, width=10).grid(row=4, column=1, padx=5, pady=5, sticky="w")

        # --- EPUB Preview ---
        preview_frame = ttk.LabelFrame(main_frame, text="EPUB Text Preview")
        preview_frame.grid(row=4, column=0, padx=5, pady=5, sticky="nsew")
        main_frame.grid_rowconfigure(4, weight=1)

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
            self.log_message(f"Extracting text from {os.path.basename(epub_path)}...")
            extracted_text = extract_text(epub_path)
            self.text_preview.delete("1.0", tk.END)
            self.text_preview.insert(tk.END, extracted_text)
            self.log_message("EPUB text extracted successfully.")
        except Exception as e:
            self.log_message(f"Error extracting EPUB: {e}")
            messagebox.showerror("EPUB Error", f"Failed to extract text from EPUB:\n{e}")

    def _start_generation(self):
        # --- Validate inputs ---
        epub_text = self.text_preview.get("1.0", tk.END).strip()
        if not epub_text:
            messagebox.showerror("Error", "EPUB text is empty. Please extract an EPUB first.")
            return

        model_path = self.model_path.get()
        if not model_path:
            messagebox.showerror("Error", "Please select a GGUF model file.")
            return

        if not os.path.exists(model_path):
            messagebox.showerror("Model Not Found",
                f"GGUF model file not found:\n{model_path}\n\n"
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
        if not cover_path or not os.path.exists(cover_path):
            messagebox.showerror("Error", "Please select a valid cover image.")
            return

        # Check for FFmpeg
        if not shutil.which("ffmpeg"):
            messagebox.showerror("FFmpeg Not Found",
                "FFmpeg is required for MP4 export but was not found in PATH.\n\n"
                "Please install FFmpeg:\n"
                "- Windows: Download from ffmpeg.org and add to PATH\n"
                "- macOS: brew install ffmpeg\n"
                "- Linux: sudo apt install ffmpeg")
            return

        output_dir = self.output_folder.get()
        if not output_dir:
            messagebox.showerror("Error", "Please select an output folder.")
            return
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # --- Prepare for pipeline ---
        self.log_message("Starting generation...")
        self.progress['value'] = 0
        self.generate_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)

        self.stop_generation_flag = threading.Event()

        base_name = Path(self.epub_path.get()).stem
        out_wav = str(Path(output_dir) / f"{base_name}.wav")
        out_mp4 = str(Path(output_dir) / f"{base_name}.mp4")

        # --- Run pipeline in a thread ---
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

    def _update_progress(self, current, total):
        self.progress['maximum'] = total
        self.progress['value'] = current
        self.log_message(f"Synthesized chunk {current} of {total}...")

    def _generation_complete(self):
        self.log_message("Generation completed successfully!")
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

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
