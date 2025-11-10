import tkinter as tk
from tkinter import filedialog, ttk
from core.epub_extract import extract_text

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MayaBook")
        self.geometry("800x600")

        self._create_widgets()

    def _create_widgets(self):
        # Frame for file paths
        file_frame = ttk.LabelFrame(self, text="Files")
        file_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # EPUB file picker
        ttk.Label(file_frame, text="EPUB File:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.epub_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.epub_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="Browse...", command=self._select_epub).grid(row=0, column=2, padx=5, pady=5)

        # Cover image picker
        ttk.Label(file_frame, text="Cover Image:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.cover_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.cover_path, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="Browse...", command=self._select_cover).grid(row=1, column=2, padx=5, pady=5)

        # Output folder
        ttk.Label(file_frame, text="Output Folder:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.output_folder = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.output_folder, width=50).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="Browse...", command=self._select_output).grid(row=2, column=2, padx=5, pady=5)

        # Frame for settings
        settings_frame = ttk.LabelFrame(self, text="Settings")
        settings_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        # Maya1 server URL
        ttk.Label(settings_frame, text="Maya1 Server URL:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.server_url = tk.StringVar(value="http://localhost:8000")
        ttk.Entry(settings_frame, textvariable=self.server_url, width=50).grid(row=0, column=1, padx=5, pady=5)

        # Voice description
        ttk.Label(settings_frame, text="Voice Description:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.voice_description = tk.Text(settings_frame, height=3, width=50)
        self.voice_description.grid(row=1, column=1, padx=5, pady=5)
        self.voice_description.insert(tk.END, "Female, 30s, warm and calm tone")

        # Temperature
        ttk.Label(settings_frame, text="Temperature:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.temperature = tk.DoubleVar(value=0.4)
        ttk.Entry(settings_frame, textvariable=self.temperature, width=10).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Top-p
        ttk.Label(settings_frame, text="Top-p:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.top_p = tk.DoubleVar(value=0.9)
        ttk.Entry(settings_frame, textvariable=self.top_p, width=10).grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # Chunk size
        ttk.Label(settings_frame, text="Chunk Size:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.chunk_size = tk.IntVar(value=500)
        ttk.Scale(settings_frame, from_=200, to=1000, orient=tk.HORIZONTAL, variable=self.chunk_size, length=200).grid(row=4, column=1, padx=5, pady=5, sticky="w")

        # Gap size
        ttk.Label(settings_frame, text="Gap (ms):").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.gap_size = tk.IntVar(value=200)
        ttk.Scale(settings_frame, from_=0, to=1000, orient=tk.HORIZONTAL, variable=self.gap_size, length=200).grid(row=5, column=1, padx=5, pady=5, sticky="w")

        # Frame for actions
        actions_frame = ttk.Frame(self)
        actions_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        # Buttons
        ttk.Button(actions_frame, text="Extract EPUB", command=self._extract_epub).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Preview 10s", command=self._preview).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Start Generation", command=self._start_generation).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Open Output Folder", command=self._open_output_folder).pack(side=tk.LEFT, padx=5)

        # Frame for EPUB text preview
        preview_frame = ttk.LabelFrame(self, text="EPUB Text Preview")
        preview_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
        self.grid_rowconfigure(3, weight=1)

        self.text_preview = tk.Text(preview_frame, wrap=tk.WORD, height=15)
        self.text_preview_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.text_preview.yview)
        self.text_preview.config(yscrollcommand=self.text_preview_scrollbar.set)

        self.text_preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Progress bar
        self.progress = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.grid(row=4, column=0, padx=10, pady=10, sticky="ew")

        # Status log
        self.log = tk.Text(self, height=10)
        self.log.grid(row=5, column=0, padx=10, pady=10, sticky="nsew")
        self.grid_rowconfigure(5, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def _select_epub(self):
        path = filedialog.askopenfilename(filetypes=[("EPUB files", "*.epub")])
        if path:
            self.epub_path.set(path)
            print(f"Selected EPUB: {path}")

    def _select_cover(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if path:
            self.cover_path.set(path)
            print(f"Selected cover: {path}")

    def _select_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_folder.set(path)
            print(f"Selected output folder: {path}")

    def _preview(self):
        print("Preview button clicked")

    def _start_generation(self):
        print("Start Generation button clicked")

    def _open_output_folder(self):
        print("Open Output Folder button clicked")

    def _extract_epub(self):
        epub_path = filedialog.askopenfilename(
            title="Select an EPUB file",
            filetypes=[("EPUB files", "*.epub")]
        )
        if not epub_path:
            return

        self.epub_path.set(epub_path)
        extracted_text = extract_text(epub_path)

        self.text_preview.delete("1.0", tk.END)
        self.text_preview.insert(tk.END, extracted_text[:2000])


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
