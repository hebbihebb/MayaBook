#!/usr/bin/env python3
"""
GGUF Workflow Test Script
-------------------------
Orchestrates the full audio generation pipeline:
1. Parses EPUB
2. Selects specific text (end of Ch1 + start of Ch2)
3. Chunks text
4. Synthesizes audio using GGUF model
5. Combines audio and creates chaptered M4B
"""
import sys
import os
import logging
import shutil
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.epub_extract import extract_chapters
from core.chunking import chunk_text
from core.tts_maya1_local import synthesize_chunk_local
from core.audio_combine import concat_wavs
from core.m4b_export import create_m4b_stream, add_chapters_to_m4b, write_chapter_metadata_file
import soundfile as sf
import numpy as np

# Configure logging
log_filename = f"test_gguf_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_specific_content(chapters):
    """
    Extracts text from end of Chapter 3 and start of Chapter 4.
    Ensures at least ~150 words per section for rigorous testing.
    """
    if len(chapters) < 5:
        raise ValueError("EPUB must have at least 5 chapters for this test.")

    # Chapter 3: End (target ~150 words)
    ch3_title, ch3_text = chapters[3] # 0-indexed, so 3 is Chapter 4? No, usually Title, Ch1, Ch2, Ch3. Let's verify index.
    # Actually, let's find chapters by title to be safe, or just assume standard ordering if titles are reliable.
    # Based on previous log: Title Page, Chapter 1. So index 3 is likely Chapter 3.
    
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
    print("\n" + "="*100)
    print("GGUF WORKFLOW RIGOROUS TEST (Ch3 -> Ch4)")
    print("="*100)
    
    # Configuration
    epub_path = "assets/test/Zero Combat, Max Crafting_ The - GordanWizard.epub"
    model_path = "assets/models/maya1.i1-Q4_K_M.gguf"
    output_dir = "output/gguf_workflow_test_v2"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Load EPUB
    print(f"\n[1/6] Loading EPUB: {epub_path}")
    metadata, chapters = extract_chapters(epub_path)
    print(f"✓ Found {len(chapters)} chapters")
    
    # 2. Select Content
    print("\n[2/6] Selecting content (End of Ch3 + Start of Ch4)...")
    try:
        selected_content = get_specific_content(chapters)
    except ValueError as e:
        print(f"Error: {e}")
        # Fallback for debugging if chapter count is low
        print("Fallback: Using chapters 1 and 2")
        selected_content = [
            {"title": chapters[1][0], "text": chapters[1][1][:500], "id": "ch1_fallback"},
            {"title": chapters[2][0], "text": chapters[2][1][:500], "id": "ch2_fallback"}
        ]

    for item in selected_content:
        print(f"  - {item['title']}: {len(item['text'].split())} words")
        logger.info(f"Selected content from {item['title']}:\n{item['text'][:100]}...")

    # 3. Process each section
    print("\n[3/6] Processing sections (Chunking & Synthesis)...")
    
    section_audio_files = []
    chapter_metadata = []
    current_time_sec = 0.0
    
    for section in selected_content:
        print(f"\nProcessing {section['title']}...")
        
        # Chunking
        chunks = chunk_text(section['text'], max_words=70, max_chars=350)
        print(f"  - Created {len(chunks)} chunks")
        
        section_wavs = []
        
        # Synthesis
        for i, chunk_text_content in enumerate(chunks):
            print(f"    - Synthesizing chunk {i+1}/{len(chunks)}...")
            try:
                wav_path = synthesize_chunk_local(
                    model_path=model_path,
                    text=chunk_text_content,
                    voice_description="A mature female voice, clear and expressive, with good pacing",
                    temperature=0.45,
                    top_p=0.92,
                    max_tokens=2500
                )
                
                # Move to output dir
                dest_path = f"{output_dir}/{section['id']}_chunk_{i+1:03d}.wav"
                shutil.move(wav_path, dest_path)
                section_wavs.append(dest_path)
                
            except Exception as e:
                print(f"    ✗ Failed: {e}")
                logger.error(f"Synthesis failed for chunk {i}: {e}")
                return 1

        # Combine section chunks (Paragraph breaks)
        print(f"  - Combining {len(section_wavs)} chunks for section...")
        section_output = f"{output_dir}/{section['id']}_combined.wav"
        # 0.5s gap between paragraphs/chunks
        concat_wavs(section_wavs, section_output, gap_seconds=0.5)
        section_audio_files.append(section_output)
        
        # Calculate duration for chapter metadata
        audio_data, sr = sf.read(section_output)
        duration = len(audio_data) / sr
        
        chapter_metadata.append({
            "chapter": section['title'],
            "start": current_time_sec,
            "end": current_time_sec + duration
        })
        
        # Add chapter gap to current time for next chapter start
        # Note: The gap is added AFTER this chapter in the full concatenation
        # So the next chapter starts at: current_end + gap
        current_time_sec += duration + 3.0 # 3.0s gap between chapters
        
        print(f"  ✓ Section complete: {duration:.2f}s")

    # 4. Combine all sections (Chapter breaks)
    print("\n[4/6] Combining all sections...")
    full_wav_path = f"{output_dir}/full_test.wav"
    # 3.0s gap between chapters based on research
    concat_wavs(section_audio_files, full_wav_path, gap_seconds=3.0) 
    print(f"✓ Full WAV created: {full_wav_path}")

    # 5. Create M4B
    print("\n[5/6] Creating M4B...")
    m4b_path = f"{output_dir}/test_chaptered_v2.m4b"
    
    # Read full WAV
    audio_data, sr = sf.read(full_wav_path)
    
    # Create M4B stream
    proc = create_m4b_stream(
        output_path=m4b_path,
        sample_rate=sr,
        metadata={
            "title": "GGUF Workflow Test V2",
            "artist": "MayaBook",
            "album": "Test Output"
        }
    )
    
    # Write audio
    audio_f32 = audio_data.astype(np.float32)
    if audio_f32.ndim > 1:
        audio_f32 = audio_f32.mean(axis=1) # Ensure mono
        
    proc.stdin.write(audio_f32.tobytes())
    proc.stdin.close()
    proc.wait()
    
    if proc.returncode != 0:
        print("✗ M4B creation failed")
        return 1
        
    print(f"✓ M4B created: {m4b_path}")

    # 6. Add Chapters
    print("\n[6/6] Adding Chapter Markers...")
    chapters_file = f"{output_dir}/chapters.txt"
    write_chapter_metadata_file(chapter_metadata, chapters_file)
    add_chapters_to_m4b(m4b_path, chapters_file)
    print("✓ Chapters added")

    print("\n" + "="*100)
    print("TEST COMPLETE")
    print(f"Output: {m4b_path}")
    print("="*100)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
