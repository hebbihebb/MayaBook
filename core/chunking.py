# core/chunking.py
import re

def chunk_text(s: str, max_chars: int = 1200) -> list[str]:
    """
    Splits a string into a list of strings, each with a maximum length
    of `max_chars`. The splitting is sentence-aware.
    """
    if not s:
        return []

    # A simple way to split by sentences. This can be improved.
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
