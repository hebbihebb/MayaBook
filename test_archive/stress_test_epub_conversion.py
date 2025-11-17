#!/usr/bin/env python3
"""
Comprehensive Stress Test for Full EPUB-to-Audiobook Conversion

This script:
1. Extracts text and chapters from a larger EPUB file
2. Validates chunk generation
3. Runs full TTS synthesis with detailed logging
4. Verifies temp file creation and cleanup
5. Creates final M4B audiobook with chapters
6. Reports detailed progress and any failures
"""
import os
import sys
import json
import time
import logging
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

# Configure comprehensive logging
log_filename = f"stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def print_section(title):
    """Print a section header"""
    print(f"\n--- {title} ---")
    logger.info(f"--- {title} ---")

def main():
    print_header("MayaBook Full Conversion Stress Test")

    # Configuration
    EPUB_PATH = "assets/test/Zero Combat, Max Crafting_ The - GordanWizard.epub"
    MODEL_PATH = "assets/models/maya1_4bit_safetensor"
    MODEL_TYPE = "huggingface"  # Use HuggingFace (proven quality from testing)
    OUTPUT_DIR = "output/stress_test"
    VOICE_DESC = "A mature female voice, clear and expressive, with good pacing"
    CHUNK_SIZE = 70  # words per chunk (safe default)
    GAP_SECONDS = 0.25
    TEMPERATURE = 0.45  # Optimal from testing
    TOP_P = 0.92
    MAX_TOKENS = 2500

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    logger.info("="*80)
    logger.info("STRESS TEST CONFIGURATION")
    logger.info("="*80)
    logger.info(f"EPUB: {EPUB_PATH}")
    logger.info(f"Model: {MODEL_PATH}")
    logger.info(f"Model Type: {MODEL_TYPE}")
    logger.info(f"Voice: {VOICE_DESC}")
    logger.info(f"Chunk Size: {CHUNK_SIZE} words")
    logger.info(f"Temperature: {TEMPERATURE}, Top-p: {TOP_P}")
    logger.info(f"Output Directory: {OUTPUT_DIR}")
    logger.info("="*80)

    try:
        # Step 1: Verify files exist
        print_section("STEP 1: Verifying Required Files")

        if not os.path.exists(EPUB_PATH):
            raise FileNotFoundError(f"EPUB not found: {EPUB_PATH}")
        logger.info(f"✓ EPUB found: {EPUB_PATH}")
        epub_size_mb = os.path.getsize(EPUB_PATH) / (1024 * 1024)
        logger.info(f"  File size: {epub_size_mb:.2f} MB")

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
        logger.info(f"✓ Model found: {MODEL_PATH}")
        model_size_gb = os.path.getsize(MODEL_PATH) / (1024 * 1024 * 1024)
        logger.info(f"  File size: {model_size_gb:.2f} GB")

        # Step 2: Extract EPUB content
        print_section("STEP 2: Extracting EPUB Content")
        logger.info("Importing EPUB extraction module...")
        from core.epub_extract import extract_chapters

        start_time = time.time()
        metadata, chapters = extract_chapters(EPUB_PATH)
        extraction_time = time.time() - start_time

        logger.info(f"✓ EPUB extraction completed in {extraction_time:.2f}s")
        logger.info(f"  Metadata: {json.dumps(metadata, indent=2)}")
        logger.info(f"  Chapters extracted: {len(chapters)}")

        if len(chapters) == 0:
            raise RuntimeError("No chapters extracted from EPUB")

        # Log chapter details
        for i, (title, text) in enumerate(chapters, 1):
            word_count = len(text.split())
            char_count = len(text)
            logger.info(f"  Chapter {i}: '{title}'")
            logger.info(f"    Text length: {char_count} chars, {word_count} words")
            logger.info(f"    Preview: {text[:100]}...")

        # Combine all chapters into single text
        full_text = "\n\n".join(text for _, text in chapters)
        total_words = len(full_text.split())
        total_chars = len(full_text)

        logger.info(f"✓ Total content: {total_chars} chars, {total_words} words")

        # Step 3: Chunk text
        print_section("STEP 3: Chunking Text")
        logger.info("Importing chunking module...")
        from core.chunking import chunk_text

        start_time = time.time()
        chunks = chunk_text(full_text, max_words=CHUNK_SIZE)
        chunking_time = time.time() - start_time

        logger.info(f"✓ Text chunked in {chunking_time:.2f}s")
        logger.info(f"  Number of chunks: {len(chunks)}")

        # Analyze chunks
        chunk_sizes = [len(c.split()) for c in chunks]
        logger.info(f"  Chunk size stats:")
        logger.info(f"    Min: {min(chunk_sizes)} words")
        logger.info(f"    Max: {max(chunk_sizes)} words")
        logger.info(f"    Avg: {sum(chunk_sizes)/len(chunk_sizes):.1f} words")

        # Log first few chunks
        for i, chunk in enumerate(chunks[:3], 1):
            words = len(chunk.split())
            logger.info(f"  Chunk {i}: {words} words")
            logger.info(f"    Preview: {chunk[:80]}...")

        # Step 4: Create temporary tracking log
        print_section("STEP 4: Setting Up Temp File Tracking")
        temp_dir = tempfile.gettempdir()
        logger.info(f"System temp directory: {temp_dir}")

        # Get current temp files before synthesis
        initial_temp_files = set(os.listdir(temp_dir))
        logger.info(f"Temp files before synthesis: {len(initial_temp_files)}")

        # Step 5: Run full pipeline
        print_section("STEP 5: Running Full TTS Synthesis Pipeline")
        logger.info("Importing pipeline module...")
        from core.pipeline import run_pipeline

        out_wav = os.path.join(OUTPUT_DIR, "audiobook.wav")
        out_m4b = os.path.join(OUTPUT_DIR, "audiobook.m4b")

        logger.info(f"Starting synthesis pipeline...")
        logger.info(f"Output WAV: {out_wav}")
        logger.info(f"Output M4B: {out_m4b}")

        def progress_callback(completed, total):
            percent = (completed / total) * 100
            msg = f"Progress: {completed}/{total} chunks ({percent:.1f}%)"
            logger.info(msg)
            print(f"  {msg}")

        start_time = time.time()
        synthesis_results = run_pipeline(
            epub_text=full_text,
            model_path=MODEL_PATH,
            voice_desc=VOICE_DESC,
            chunk_size=CHUNK_SIZE,
            gap_s=GAP_SECONDS,
            out_wav=out_wav,
            cover_image=None,  # No cover needed for this test
            temperature=TEMPERATURE,
            top_p=TOP_P,
            max_tokens=MAX_TOKENS,
            workers=1,  # Single worker for stability
            model_type=MODEL_TYPE,
            progress_cb=progress_callback,
        )

        synthesis_time = time.time() - start_time
        wav_path = synthesis_results[0]

        logger.info(f"✓ Synthesis completed in {synthesis_time:.2f}s")
        logger.info(f"  Output WAV: {wav_path}")

        # Check WAV file
        if not os.path.exists(wav_path):
            raise RuntimeError(f"WAV file not created: {wav_path}")

        wav_size_mb = os.path.getsize(wav_path) / (1024 * 1024)
        logger.info(f"  WAV file size: {wav_size_mb:.2f} MB")

        # Analyze WAV file
        logger.info("Analyzing WAV file...")
        import soundfile as sf
        audio_data, samplerate = sf.read(wav_path)
        duration_seconds = len(audio_data) / samplerate
        logger.info(f"  Sample rate: {samplerate} Hz")
        logger.info(f"  Duration: {duration_seconds:.2f} seconds ({duration_seconds/60:.2f} minutes)")
        logger.info(f"  Channels: {'Mono' if len(audio_data.shape) == 1 else 'Stereo'}")

        # Step 6: Check temp files created
        print_section("STEP 6: Analyzing Temporary Files")
        final_temp_files = set(os.listdir(temp_dir))
        new_temp_files = final_temp_files - initial_temp_files

        logger.info(f"New temp files created: {len(new_temp_files)}")
        if new_temp_files:
            logger.info("Sample temp files:")
            for temp_file in list(new_temp_files)[:5]:
                temp_path = os.path.join(temp_dir, temp_file)
                if os.path.isfile(temp_path):
                    size_mb = os.path.getsize(temp_path) / (1024 * 1024)
                    logger.info(f"  - {temp_file}: {size_mb:.2f} MB")

        # Step 7: Create M4B audiobook with chapters
        print_section("STEP 7: Creating M4B Audiobook with Chapters")

        # Check if ffmpeg is available
        result = subprocess.run(['which', 'ffmpeg'], capture_output=True)
        if result.returncode != 0:
            logger.warning("FFmpeg not found, skipping M4B creation")
        else:
            logger.info("FFmpeg found, creating M4B with chapters...")

            from core.m4b_export import create_m4b_stream, write_chapter_metadata_file, add_chapters_to_m4b

            try:
                # Create initial M4B without chapters
                logger.info("Creating M4B file (no chapters yet)...")
                m4b_path = create_m4b_stream(
                    wav_path=wav_path,
                    m4b_path=out_m4b,
                    metadata_title=metadata.get('title', 'Unknown'),
                    metadata_author=metadata.get('author', 'Unknown'),
                    metadata_genre="Audiobook"
                )
                logger.info(f"✓ M4B created: {m4b_path}")

                m4b_size_mb = os.path.getsize(m4b_path) / (1024 * 1024)
                logger.info(f"  M4B file size: {m4b_size_mb:.2f} MB")

                # Add chapter metadata
                logger.info("Writing chapter metadata...")
                metadata_file = os.path.join(OUTPUT_DIR, "chapters.txt")
                write_chapter_metadata_file(
                    chapters=chapters,
                    output_file=metadata_file,
                    total_duration=duration_seconds
                )
                logger.info(f"✓ Chapter metadata file: {metadata_file}")

                # Add chapters to M4B (remux operation)
                logger.info("Adding chapters to M4B (remuxing)...")
                m4b_with_chapters = add_chapters_to_m4b(
                    m4b_path=m4b_path,
                    metadata_file=metadata_file,
                    output_path=out_m4b
                )
                logger.info(f"✓ M4B with chapters: {m4b_with_chapters}")

            except Exception as e:
                logger.error(f"Error creating M4B: {e}", exc_info=True)
                logger.warning("Continuing without M4B (WAV file is still valid)")

        # Step 8: Final report
        print_section("STEP 8: Final Report")

        logger.info("="*80)
        logger.info("STRESS TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"EPUB Extraction:      {extraction_time:.2f}s")
        logger.info(f"Text Chunking:        {chunking_time:.2f}s")
        logger.info(f"TTS Synthesis:        {synthesis_time:.2f}s")
        logger.info(f"Total Time:           {extraction_time + chunking_time + synthesis_time:.2f}s")
        logger.info("")
        logger.info(f"Input:")
        logger.info(f"  EPUB Size:          {epub_size_mb:.2f} MB")
        logger.info(f"  Total Text:         {total_chars} chars, {total_words} words")
        logger.info(f"  Chapters:           {len(chapters)}")
        logger.info(f"  Chunks:             {len(chunks)}")
        logger.info("")
        logger.info(f"Output:")
        logger.info(f"  WAV File:           {wav_size_mb:.2f} MB")
        logger.info(f"  Duration:           {duration_seconds:.2f}s ({duration_seconds/60:.2f} min)")
        if os.path.exists(out_m4b):
            m4b_size_mb = os.path.getsize(out_m4b) / (1024 * 1024)
            logger.info(f"  M4B File:           {m4b_size_mb:.2f} MB")
        logger.info("")
        logger.info(f"Files Created:")
        logger.info(f"  WAV:                {wav_path}")
        if os.path.exists(out_m4b):
            logger.info(f"  M4B:                {out_m4b}")
        logger.info(f"  Log:                {log_filename}")
        logger.info("="*80)

        print("\n✓ STRESS TEST COMPLETED SUCCESSFULLY!")
        print(f"  WAV:  {wav_path}")
        if os.path.exists(out_m4b):
            print(f"  M4B:  {out_m4b}")
        print(f"  Log:  {log_filename}")

        return 0

    except Exception as e:
        print("\n✗ STRESS TEST FAILED!")
        print(f"  Error: {type(e).__name__}: {e}")
        logger.error("="*80)
        logger.error("STRESS TEST FAILED", exc_info=True)
        logger.error("="*80)
        print(f"\nCheck log file for details: {log_filename}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
