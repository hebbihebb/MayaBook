import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import logging
import re
from typing import Tuple, List, Dict, Optional


def extract_text(epub_path: str) -> str:
    """
    Extracts readable text from an EPUB file (legacy flat text extraction).

    Args:
        epub_path: The path to the EPUB file.

    Returns:
        The extracted and cleaned text from the EPUB.
    """
    # Use new chapter extraction and combine all text
    metadata, chapters = extract_chapters(epub_path)

    if not chapters:
        return "Error: Could not extract any text from the EPUB."

    # Combine all chapter texts
    return "\n\n".join(text for _, text in chapters)


def extract_metadata(book: epub.EpubBook) -> Dict[str, str]:
    """
    Extract metadata from EPUB book.

    Args:
        book: EpubBook object

    Returns:
        Dictionary of metadata fields
    """
    metadata = {}

    try:
        # Title
        title = book.get_metadata('DC', 'title')
        if title:
            metadata['title'] = title[0][0] if isinstance(title[0], tuple) else title[0]

        # Creator/Author
        creator = book.get_metadata('DC', 'creator')
        if creator:
            metadata['author'] = creator[0][0] if isinstance(creator[0], tuple) else creator[0]

        # Publisher
        publisher = book.get_metadata('DC', 'publisher')
        if publisher:
            metadata['publisher'] = publisher[0][0] if isinstance(publisher[0], tuple) else publisher[0]

        # Language
        language = book.get_metadata('DC', 'language')
        if language:
            metadata['language'] = language[0][0] if isinstance(language[0], tuple) else language[0]

        # Date
        date = book.get_metadata('DC', 'date')
        if date:
            date_str = date[0][0] if isinstance(date[0], tuple) else date[0]
            # Extract year from date string (format varies: YYYY, YYYY-MM-DD, etc.)
            year_match = re.search(r'\d{4}', date_str)
            if year_match:
                metadata['year'] = year_match.group(0)

        # Description
        description = book.get_metadata('DC', 'description')
        if description:
            metadata['description'] = description[0][0] if isinstance(description[0], tuple) else description[0]

        # Subject/Genre
        subject = book.get_metadata('DC', 'subject')
        if subject:
            metadata['genre'] = subject[0][0] if isinstance(subject[0], tuple) else subject[0]

    except Exception as e:
        logging.warning(f"Error extracting some metadata: {e}")

    return metadata


def extract_chapters(epub_path: str) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    """
    Extracts chapters and metadata from an EPUB file.

    Args:
        epub_path: The path to the EPUB file.

    Returns:
        Tuple of (metadata_dict, chapters_list)
        - metadata_dict: Dictionary with title, author, publisher, etc.
        - chapters_list: List of (chapter_title, chapter_text) tuples
    """
    try:
        logging.info(f"Extracting chapters and metadata from {epub_path}...")
        book = epub.read_epub(epub_path)

        # Extract metadata
        metadata = extract_metadata(book)
        logging.info(f"Extracted metadata: {metadata.get('title', 'Unknown')}")

        # Try to extract chapter structure from TOC
        chapters = []
        toc = book.toc

        if toc and isinstance(toc, (list, tuple)) and len(toc) > 0:
            # EPUB has a proper table of contents
            logging.info(f"Found {len(toc)} chapters in TOC")
            chapters = _extract_from_toc(book, toc)

        # Fallback: Extract all documents sequentially if TOC didn't work
        if not chapters:
            logging.info("No TOC found, extracting all documents sequentially")
            chapters = _extract_all_documents(book)

        # Check for custom chapter markers in text
        if chapters:
            chapters = _check_for_chapter_markers(chapters)

        logging.info(f"Text extraction successful. Found {len(chapters)} chapters.")
        return metadata, chapters

    except Exception as e:
        logging.error(f"Error extracting chapters from EPUB: {e}")
        # Return minimal structure with error
        return {}, [("Text", f"Error: Could not extract text from {epub_path}. The file might be corrupted or not a valid EPUB.")]


def _extract_from_toc(book: epub.EpubBook, toc: list) -> List[Tuple[str, str]]:
    """Extract chapters using table of contents structure."""
    chapters = []

    def process_toc_item(item, chapter_num=[1]):
        """Recursively process TOC items (handles nested chapters)."""
        if isinstance(item, tuple):
            # Section with sub-items
            section_title, section_items = item
            if isinstance(section_title, epub.Link):
                # Section has its own content
                text = _extract_item_text(book, section_title.href)
                if text.strip():
                    chapters.append((section_title.title or f"Chapter {chapter_num[0]}", text))
                    chapter_num[0] += 1
            # Process sub-items
            for sub_item in section_items:
                process_toc_item(sub_item, chapter_num)
        elif isinstance(item, epub.Link):
            # Direct chapter link
            text = _extract_item_text(book, item.href)
            if text.strip():
                chapters.append((item.title or f"Chapter {chapter_num[0]}", text))
                chapter_num[0] += 1
        elif isinstance(item, list):
            # List of items
            for sub_item in item:
                process_toc_item(sub_item, chapter_num)

    for item in toc:
        process_toc_item(item)

    return chapters


def _extract_item_text(book: epub.EpubBook, href: str) -> str:
    """Extract text from a specific EPUB item by href."""
    # Remove anchor if present
    item_id = href.split('#')[0]

    try:
        item = book.get_item_with_href(item_id)
        if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_content()
            return _parse_html_content(content)
    except Exception as e:
        logging.warning(f"Could not extract text from {href}: {e}")

    return ""


def _extract_all_documents(book: epub.EpubBook) -> List[Tuple[str, str]]:
    """Extract all document items sequentially (fallback when no TOC)."""
    chapters = []
    chapter_num = 1

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_content()
            text = _parse_html_content(content)

            if text.strip():
                # Try to extract title from HTML
                try:
                    soup = BeautifulSoup(content, 'html.parser')
                    title_tag = soup.find(['h1', 'h2', 'title'])
                    if title_tag:
                        title = title_tag.get_text().strip()
                    else:
                        title = f"Chapter {chapter_num}"
                except:
                    title = f"Chapter {chapter_num}"

                chapters.append((title, text))
                chapter_num += 1

    return chapters


def _parse_html_content(content: bytes) -> str:
    """Parse HTML content and extract clean text."""
    soup = BeautifulSoup(content, 'html.parser')

    # Extract text from each paragraph separately to preserve paragraph breaks
    text_parts = []
    paragraphs = soup.find_all('p')

    if paragraphs:
        for p in paragraphs:
            p_text = p.get_text().strip()
            if p_text:  # Only add non-empty paragraphs
                text_parts.append(p_text)
    else:
        # Fallback to whole text if no <p> tags found
        text = soup.get_text()
        if text.strip():
            text_parts.append(text.strip())

    # Join with double newlines and normalize
    text_content = "\n\n".join(text_parts)
    text_content = text_content.replace('\xa0', ' ')  # Replace non-breaking space

    return text_content


def _check_for_chapter_markers(chapters: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Check for custom chapter markers in text and re-split if found.

    Supports markers like: <<CHAPTER_MARKER:Chapter Name>>
    """
    # Check if any chapter contains markers
    has_markers = False
    for _, text in chapters:
        if '<<CHAPTER_MARKER:' in text:
            has_markers = True
            break

    if not has_markers:
        return chapters

    # Combine all text and re-split by markers
    logging.info("Found custom chapter markers, re-splitting chapters")
    all_text = "\n\n".join(text for _, text in chapters)

    chapter_pattern = r"<<CHAPTER_MARKER:(.*?)>>"
    chapter_splits = list(re.finditer(chapter_pattern, all_text))

    if not chapter_splits:
        return chapters

    new_chapters = []

    # Add introduction if there's content before first marker
    first_start = chapter_splits[0].start()
    if first_start > 0:
        intro_text = all_text[:first_start].strip()
        if intro_text:
            new_chapters.append(("Introduction", intro_text))

    # Extract each marked chapter
    for idx, match in enumerate(chapter_splits):
        start = match.end()
        end = chapter_splits[idx + 1].start() if idx + 1 < len(chapter_splits) else len(all_text)
        chapter_name = match.group(1).strip()
        chapter_text = all_text[start:end].strip()

        # Remove the marker from the text
        chapter_text = re.sub(r"<<CHAPTER_MARKER:.*?>>", "", chapter_text).strip()

        if chapter_text:
            new_chapters.append((chapter_name, chapter_text))

    return new_chapters
