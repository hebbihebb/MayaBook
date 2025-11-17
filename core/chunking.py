# core/chunking.py
import re

def chunk_text(s: str, max_chars: int = 350, max_words: int = 70) -> list[str]:
    """
    Splits a string into a list of strings using DUAL CONSTRAINTS (words AND chars).
    The splitting is sentence-aware and preserves emotion tags.

    Args:
        s: Text to chunk
        max_words: Maximum words per chunk (default: 70, recommended for token budget with max_tokens=2500)
        max_chars: Maximum characters per chunk (default: 350, prevents dense technical text overflow while maintaining audio continuity)

    Returns:
        List of text chunks

    Note:
        CRITICAL: Dense technical text (avg 8+ chars/word) will hit max_chars limit first.
        Dual constraints ensure both word and character limits are respected, preventing
        token overflow with max_tokens=2500 on HuggingFace backend.

        Character limit of 350 chosen to:
        - Prevent dense technical text from exceeding token budget
        - Minimize chunk fragmentation (fewer cuts = better audio continuity)
        - Balance between safety margin and voice consistency

        Emotion tags like <laugh>, <cry>, <angry> are preserved within chunks.

        Example token budgets with max_chars=350:
        - 70 words × 5 chars/word × 5 tokens/char = ~1,750 tokens (safe margin with 2500 limit)
        - 70 words × 8 chars/word (280 chars, under 350 limit) × 5 tokens/char = ~2,100 tokens (safe)
    """
    if not s:
        return []

    # Use hybrid dual-constraint chunking (word AND character limits)
    return _chunk_by_words_and_chars(s, max_words, max_chars)


def _chunk_by_words_and_chars(s: str, max_words: int, max_chars: int) -> list[str]:
    """
    Chunk text respecting BOTH word count AND character limits (whichever is exceeded first).
    This prevents dense technical text from exceeding token budgets.
    """
    # Split by sentences, preserving emotion tags
    sentences = re.split(r'(?<=[.!?]) +', s.strip())

    chunks = []
    current_chunk = ""
    current_word_count = 0
    current_char_count = 0

    for sentence in sentences:
        if not sentence:
            continue

        # Count words (excluding emotion tags)
        sentence_text = re.sub(r'<[^>]+>', '', sentence)
        sentence_words = len(sentence_text.split())
        sentence_chars = len(sentence_text)

        # If a single sentence exceeds EITHER limit, split it further
        if sentence_words > max_words or sentence_chars > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
                current_word_count = 0
                current_char_count = 0

            # Split long sentence at commas or natural breaks
            chunks.extend(_split_long_sentence(sentence, max_words, max_chars))
            continue

        # Check if adding this sentence would exceed EITHER word or character limit
        if (current_word_count + sentence_words > max_words or
            current_char_count + sentence_chars > max_chars) and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
            current_word_count = sentence_words
            current_char_count = sentence_chars
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
            current_word_count += sentence_words
            current_char_count += sentence_chars

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


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


def _split_long_sentence(sentence: str, max_words: int, max_chars: int) -> list[str]:
    """Split a very long sentence at commas or other natural breaks, respecting BOTH word and char limits."""
    # Try splitting at commas, semicolons, or dashes
    parts = re.split(r'([,;—-]\s+)', sentence)

    chunks = []
    current = ""
    current_words = 0
    current_chars = 0

    for part in parts:
        if not part:
            continue

        part_text = re.sub(r'<[^>]+>', '', part)
        part_words = len(part_text.split())
        part_chars = len(part_text)

        # Check BOTH word and character constraints
        if (current_words + part_words > max_words or
            current_chars + part_chars > max_chars) and current:
            chunks.append(current.strip())
            current = part
            current_words = part_words
            current_chars = part_chars
        else:
            current += part
            current_words += part_words
            current_chars += part_chars

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
