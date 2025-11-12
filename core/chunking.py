# core/chunking.py
import re

def chunk_text(s: str, max_chars: int = 1200, max_words: int = None) -> list[str]:
    """
    Splits a string into a list of strings, each with a maximum length.
    The splitting is sentence-aware and preserves emotion tags.

    Args:
        s: Text to chunk
        max_chars: Maximum characters per chunk (fallback, default 1200)
        max_words: Maximum words per chunk (recommended: 80-100 for TTS)

    Returns:
        List of text chunks

    Note:
        For TTS/audiobook applications, word-based chunking (80-100 words)
        produces more natural speech than character-based chunking.
        Emotion tags like <laugh>, <cry>, <angry> are preserved within chunks.
    """
    if not s:
        return []

    # Use word-based chunking if specified (recommended for TTS)
    if max_words is not None:
        return _chunk_by_words(s, max_words)

    # Fallback to character-based chunking
    return _chunk_by_chars(s, max_chars)


def _chunk_by_words(s: str, max_words: int) -> list[str]:
    """
    Chunk text by word count, sentence-aware, preserving emotion tags.
    Recommended: 80-100 words per chunk for optimal TTS quality.
    """
    # Split by sentences, but preserve emotion tags
    # Emotion tags: <laugh>, <cry>, <angry>, <excited>, etc.
    sentences = re.split(r'(?<=[.!?]) +', s.strip())

    chunks = []
    current_chunk = ""
    current_word_count = 0

    for sentence in sentences:
        if not sentence:
            continue

        # Count words (excluding emotion tags from word count)
        sentence_text = re.sub(r'<[^>]+>', '', sentence)
        sentence_words = len(sentence_text.split())

        # If a single sentence exceeds max_words, split it
        if sentence_words > max_words:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
                current_word_count = 0

            # Split long sentence at commas or natural breaks
            chunks.extend(_split_long_sentence(sentence, max_words))
            continue

        # Check if adding this sentence would exceed word limit
        if current_word_count + sentence_words > max_words and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
            current_word_count = sentence_words
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
            current_word_count += sentence_words

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def _split_long_sentence(sentence: str, max_words: int) -> list[str]:
    """Split a very long sentence at commas or other natural breaks."""
    # Try splitting at commas, semicolons, or dashes
    parts = re.split(r'([,;—-]\s+)', sentence)

    chunks = []
    current = ""
    current_words = 0

    for part in parts:
        if not part:
            continue

        part_text = re.sub(r'<[^>]+>', '', part)
        part_words = len(part_text.split())

        if current_words + part_words > max_words and current:
            chunks.append(current.strip())
            current = part
            current_words = part_words
        else:
            current += part
            current_words += part_words

    if current:
        chunks.append(current.strip())

    return chunks if chunks else [sentence]


def _chunk_by_chars(s: str, max_chars: int) -> list[str]:
    """
    Original character-based chunking (fallback method).
    """
    sentences = re.split(r'(?<=[.!?]) +', s.strip())

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if not sentence:
            continue

        # If a sentence is longer than max_chars, it's hard-wrapped.
        if len(sentence) > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            for i in range(0, len(sentence), max_chars):
                chunks.append(sentence[i:i+max_chars])
            continue

        # If adding the new sentence exceeds the limit, push the current chunk.
        if len(current_chunk) + len(sentence) + 1 > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks
