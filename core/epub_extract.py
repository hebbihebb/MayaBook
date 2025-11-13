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

            # Extract text from each paragraph separately to preserve paragraph breaks
            paragraphs = soup.find_all('p')
            if paragraphs:
                for p in paragraphs:
                    p_text = p.get_text().strip()
                    if p_text:  # Only add non-empty paragraphs
                        text_content += p_text + "\n\n"
            else:
                # Fallback to whole text if no <p> tags found
                text = soup.get_text()
                text_content += text + "\n\n"

        logging.info("Text extraction successful.")
        # Normalize whitespace: replace non-breaking spaces and multiple newlines
        text_content = text_content.replace('\xa0', ' ')  # Replace non-breaking space with regular space
        text_content = text_content.strip()
        return text_content

    except Exception as e:
        logging.error(f"Error extracting text from EPUB: {e}")
        return f"Error: Could not extract text from {epub_path}. The file might be corrupted or not a valid EPUB."
