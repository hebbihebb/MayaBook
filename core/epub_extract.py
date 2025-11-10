from pathlib import Path
from typing import List

def extract_text(epub_path: Path) -> List[str]:
    """
    Extracts readable text from EPUB chapters, cleans it, and splits it into chunks.

    Args:
        epub_path: The path to the EPUB file.

    Returns:
        A list of text chunks.
    """
    # TODO: Implement EPUB text extraction and chunking logic.
    print(f"Extracting text from {epub_path}...")
    return []
