#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.epub_extract import extract_chapters
from core.chunking import chunk_text

def get_specific_content(chapters):
    """
    Extracts text from end of Chapter 3 and start of Chapter 4.
    Ensures at least ~150 words per section for rigorous testing.
    """
    if len(chapters) < 5:
        raise ValueError("EPUB must have at least 5 chapters for this test.")

    # Chapter 3: End (target ~150 words)
    ch3_title, ch3_text = chapters[3]
    paras = [p for p in ch3_text.split('\n\n') if p.strip()]
    selected_paras = []
    word_count = 0
    for p in reversed(paras):
        selected_paras.insert(0, p)
        word_count += len(p.split())
        if word_count >= 150:
            break
    ch3_selected = "\n\n".join(selected_paras)
    
    # Chapter 4: Start (target ~150 words)
    ch4_title, ch4_text = chapters[4]
    paras = [p for p in ch4_text.split('\n\n') if p.strip()]
    selected_paras = []
    word_count = 0
    for p in paras:
        selected_paras.append(p)
        word_count += len(p.split())
        if word_count >= 150:
            break
    ch4_selected = "\n\n".join(selected_paras)

    return [
        {"title": ch3_title, "text": ch3_selected, "id": "ch3"},
        {"title": ch4_title, "text": ch4_selected, "id": "ch4"}
    ]

def main():
    epub_path = "assets/test/Zero Combat, Max Crafting_ The - GordanWizard.epub"
    metadata, chapters = extract_chapters(epub_path)
    selected_content = get_specific_content(chapters)
    
    print("# Transcript\n")
    for section in selected_content:
        print(f"## {section['title']}\n")
        chunks = chunk_text(section['text'], max_words=70, max_chars=350)
        for i, chunk in enumerate(chunks):
            print(f"**Chunk {i+1}:**")
            print(f"> {chunk}\n")

if __name__ == "__main__":
    main()
