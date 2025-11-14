"""
Chapter Selection Dialog for MayaBook
Inspired by abogen's chapter selection interface
"""
import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Optional


class ChapterSelectionDialog(tk.Toplevel):
    """Dialog for selecting which chapters to process from an EPUB."""

    def __init__(self, parent, chapters: List[Tuple[str, str]], metadata: dict = None):
        """
        Initialize chapter selection dialog.

        Args:
            parent: Parent window
            chapters: List of (chapter_title, chapter_text) tuples
            metadata: Optional metadata dict with title, author, etc.
        """
        super().__init__(parent)

        self.chapters = chapters
        self.metadata = metadata or {}
        self.selected_chapters = []  # Will store indices of selected chapters
        self.result = None  # "ok" or "cancel"

        # Dialog settings
        self.title("Select Chapters to Process")
        self.geometry("900x700")
        self.resizable(True, True)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self._populate_chapter_list()

        # Center dialog on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create dialog widgets."""
        # Header with book info
        header_frame = ttk.Frame(self, padding="10")
        header_frame.pack(fill=tk.X)

        title = self.metadata.get('title', 'Unknown Book')
        author = self.metadata.get('author', 'Unknown Author')

        ttk.Label(header_frame, text=f"Book: {title}", font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(header_frame, text=f"Author: {author}", foreground="gray").pack(anchor=tk.W)
        ttk.Label(header_frame, text=f"Total Chapters: {len(self.chapters)}", foreground="gray").pack(anchor=tk.W)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # Instructions
        instructions = ttk.Label(self, text="Select chapters to include in the audiobook. Click a chapter to preview its content.",
                                padding="10")
        instructions.pack(fill=tk.X)

        # Main content area with paned window
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left pane: Chapter list with checkboxes
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)

        # Action buttons above list
        action_frame = ttk.Frame(left_frame)
        action_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(action_frame, text="Select All", command=self._select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Deselect All", command=self._deselect_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Invert Selection", command=self._invert_selection).pack(side=tk.LEFT, padx=2)

        # Chapter list with scrollbar
        list_label = ttk.Label(left_frame, text="Chapters:", font=("TkDefaultFont", 9, "bold"))
        list_label.pack(anchor=tk.W, pady=(0, 2))

        # Create treeview for chapter list
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=("words", "chars"),
                                 show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Chapter Title")
        self.tree.heading("words", text="Words")
        self.tree.heading("chars", text="Chars")

        self.tree.column("#0", width=300, minwidth=200)
        self.tree.column("words", width=80, minwidth=60, anchor=tk.E)
        self.tree.column("chars", width=80, minwidth=60, anchor=tk.E)

        tree_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind selection and toggle events
        self.tree.bind("<<TreeviewSelect>>", self._on_chapter_select)
        self.tree.bind("<space>", self._toggle_selected_item)
        self.tree.bind("<Double-Button-1>", self._on_double_click)

        # Right pane: Chapter preview
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)

        preview_label = ttk.Label(right_frame, text="Chapter Preview:", font=("TkDefaultFont", 9, "bold"))
        preview_label.pack(anchor=tk.W, pady=(0, 2))

        preview_frame = ttk.Frame(right_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.preview_text = tk.Text(preview_frame, wrap=tk.WORD, width=50, height=20)
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=preview_scrollbar.set)

        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Make preview read-only
        self.preview_text.configure(state=tk.DISABLED)

        # Stats label
        self.stats_label = ttk.Label(right_frame, text="", foreground="gray")
        self.stats_label.pack(anchor=tk.W, pady=(5, 0))

        # Bottom button frame
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        button_frame = ttk.Frame(self, padding="10")
        button_frame.pack(fill=tk.X)

        # Selection summary
        self.summary_label = ttk.Label(button_frame, text="No chapters selected")
        self.summary_label.pack(side=tk.LEFT, padx=10)

        # OK/Cancel buttons
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Process Selected Chapters", command=self._on_ok).pack(side=tk.RIGHT, padx=5)

    def _populate_chapter_list(self):
        """Populate the chapter list treeview."""
        # Store chapter check state
        self.chapter_checked = {}

        for idx, (title, text) in enumerate(self.chapters):
            word_count = len(text.split())
            char_count = len(text)

            # Insert item
            item_id = self.tree.insert("", tk.END, text=f"☐ {title}",
                                      values=(f"{word_count:,}", f"{char_count:,}"),
                                      tags=(f"chapter_{idx}",))

            self.chapter_checked[item_id] = False

        # Select all by default
        self._select_all()

    def _toggle_item(self, item_id):
        """Toggle checkbox for a specific item."""
        if item_id not in self.chapter_checked:
            return

        # Toggle state
        current_state = self.chapter_checked[item_id]
        new_state = not current_state
        self.chapter_checked[item_id] = new_state

        # Update display
        current_text = self.tree.item(item_id, "text")
        if new_state:
            # Check it
            new_text = "☑ " + current_text[2:]
            self.tree.item(item_id, text=new_text)
        else:
            # Uncheck it
            new_text = "☐ " + current_text[2:]
            self.tree.item(item_id, text=new_text)

        self._update_summary()

    def _toggle_selected_item(self, event=None):
        """Toggle checkbox for currently selected item."""
        selection = self.tree.selection()
        if selection:
            self._toggle_item(selection[0])

    def _select_all(self):
        """Select all chapters."""
        for item_id in self.chapter_checked.keys():
            if not self.chapter_checked[item_id]:
                self._toggle_item(item_id)

    def _deselect_all(self):
        """Deselect all chapters."""
        for item_id in self.chapter_checked.keys():
            if self.chapter_checked[item_id]:
                self._toggle_item(item_id)

    def _invert_selection(self):
        """Invert selection."""
        for item_id in self.chapter_checked.keys():
            self._toggle_item(item_id)

    def _update_summary(self):
        """Update selection summary label."""
        selected_count = sum(1 for checked in self.chapter_checked.values() if checked)
        total_count = len(self.chapter_checked)

        if selected_count == 0:
            self.summary_label.config(text="No chapters selected")
        elif selected_count == total_count:
            self.summary_label.config(text=f"All {total_count} chapters selected")
        else:
            self.summary_label.config(text=f"{selected_count} of {total_count} chapters selected")

    def _on_chapter_select(self, event=None):
        """Handle chapter selection in treeview."""
        selection = self.tree.selection()
        if not selection:
            return

        # Get chapter index from tags
        item_id = selection[0]
        tags = self.tree.item(item_id, "tags")
        if not tags:
            return

        # Extract chapter index
        chapter_tag = tags[0]
        chapter_idx = int(chapter_tag.split("_")[1])

        # Show preview
        self._show_chapter_preview(chapter_idx)

    def _on_double_click(self, event=None):
        """Handle double-click to toggle checkbox."""
        # Get item under cursor
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self._toggle_item(item_id)
            # Keep the item selected
            self.tree.selection_set(item_id)

    def _show_chapter_preview(self, chapter_idx: int):
        """Show preview of selected chapter."""
        if chapter_idx < 0 or chapter_idx >= len(self.chapters):
            return

        title, text = self.chapters[chapter_idx]

        # Update preview text
        self.preview_text.configure(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", f"=== {title} ===\n\n{text}")
        self.preview_text.configure(state=tk.DISABLED)

        # Update stats
        word_count = len(text.split())
        char_count = len(text)
        paragraph_count = len([p for p in text.split("\n\n") if p.strip()])

        self.stats_label.config(
            text=f"Words: {word_count:,} | Characters: {char_count:,} | Paragraphs: {paragraph_count}"
        )

    def _on_ok(self):
        """Handle OK button."""
        # Get selected chapter indices
        self.selected_chapters = []

        for item_id, checked in self.chapter_checked.items():
            if checked:
                tags = self.tree.item(item_id, "tags")
                if tags:
                    chapter_tag = tags[0]
                    chapter_idx = int(chapter_tag.split("_")[1])
                    self.selected_chapters.append(chapter_idx)

        if not self.selected_chapters:
            tk.messagebox.showwarning("No Selection",
                                     "Please select at least one chapter to process.",
                                     parent=self)
            return

        self.result = "ok"
        self.destroy()

    def _on_cancel(self):
        """Handle Cancel button."""
        self.result = "cancel"
        self.destroy()

    def get_selected_chapters(self) -> Optional[List[Tuple[str, str]]]:
        """
        Get the selected chapters.

        Returns:
            List of (title, text) tuples for selected chapters, or None if cancelled
        """
        if self.result == "ok":
            return [self.chapters[idx] for idx in sorted(self.selected_chapters)]
        return None


def show_chapter_selection_dialog(parent, chapters: List[Tuple[str, str]],
                                  metadata: dict = None) -> Optional[List[Tuple[str, str]]]:
    """
    Show chapter selection dialog and return selected chapters.

    Args:
        parent: Parent window
        chapters: List of (chapter_title, chapter_text) tuples
        metadata: Optional metadata dict

    Returns:
        List of selected (title, text) tuples, or None if cancelled
    """
    dialog = ChapterSelectionDialog(parent, chapters, metadata)
    parent.wait_window(dialog)
    return dialog.get_selected_chapters()
