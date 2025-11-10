import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import logging

def extract_text(epub_path: str) -> str:
    """
    Extracts readable text from an EPUB file.

    Args:
        epub_path: The path to the EPUB file.

    Returns:
        The extracted and cleaned text from the EPUB.
    """
    try:
        logging.info(f"Extracting text from {epub_path}...")
        book = epub.read_epub(epub_path)
        chapters = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                chapters.append(item.get_content())

        text_content = ""
        for chapter in chapters:
            soup = BeautifulSoup(chapter, 'html.parser')
            text = soup.get_text()
            text_content += text + "\n\n"

        logging.info("Text extraction successful.")
        return text_content.strip()

    except Exception as e:
        logging.error(f"Error extracting text from EPUB: {e}")
        return f"Error: Could not extract text from {epub_path}. The file might be corrupted or not a valid EPUB."
