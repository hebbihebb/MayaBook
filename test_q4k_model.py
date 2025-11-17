#!/usr/bin/env python3
"""
Test script for Maya1 Q4_K_M GGUF model
Tests chunks 1, 100, and 486 to compare quality with HuggingFace backend
"""
import sys
sys.path.insert(0, '/mnt/Games/MayaBook')

from core.epub_extract import extract_text
from core.chunking import chunk_text
from core.tts_maya1_local import synthesize_chunk_local
import shutil
import logging
from datetime import datetime

# Configure logging
log_filename = f"test_q4k_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    print("\n" + "="*100)
    print("TESTING MAYA1 Q4_K_M GGUF MODEL")
    print("="*100)
    print("\nComparing Q4_K_M GGUF vs HuggingFace 4-bit backend\n")

    # Load EPUB and chunks
    print("Loading EPUB and creating chunks...")
    epub_path = "assets/test/Zero Combat, Max Crafting_ The - GordanWizard.epub"
    text = extract_text(epub_path)
    chunks = chunk_text(text, max_words=70)
    print(f"✓ EPUB loaded: {len(chunks)} total chunks\n")

    # Test chunks
    test_chunks = [1, 100, 486]
    model_path = "assets/models/maya1.i1-Q4_K_M.gguf"
    output_dir = "output/q4k_test"

    logger.info("="*100)
    logger.info("Q4_K_M GGUF MODEL TEST")
    logger.info("="*100)
    logger.info(f"Model: {model_path}")
    logger.info(f"Test chunks: {test_chunks}\n")

    results = {}

    for chunk_num in test_chunks:
        print("="*100)
        print(f"TEST CHUNK {chunk_num}")
        print("="*100)

        chunk_content = chunks[chunk_num - 1]
        words = len(chunk_content.split())

        print(f"Text ({words} words):")
        print(f"  {chunk_content[:100]}...\n")

        logger.info(f"\n{'='*100}")
        logger.info(f"CHUNK {chunk_num}: {words} words")
        logger.info(f"Text: {chunk_content[:150]}...")

        try:
            print("Synthesizing with Q4_K_M GGUF model...")
            logger.info("Starting synthesis with GGUF model...")

            output_wav = synthesize_chunk_local(
                model_path=model_path,
                text=chunk_content,
                voice_description="A mature female voice, clear and expressive, with good pacing",
                temperature=0.45,
                top_p=0.92,
                max_tokens=2500,
            )

            # Copy to output folder
            output_filename = f"q4k_chunk_{chunk_num:03d}.wav"
            output_path = f"{output_dir}/{output_filename}"
            shutil.copy(output_wav, output_path)

            print(f"✓ Synthesis successful")
            print(f"  Output: {output_path}\n")

            logger.info(f"✓ Chunk {chunk_num} synthesized successfully")
            logger.info(f"  Output file: {output_path}")

            results[chunk_num] = {'success': True, 'output': output_path}

        except Exception as e:
            print(f"✗ Synthesis failed: {e}\n")
            logger.error(f"✗ Chunk {chunk_num} synthesis failed: {e}", exc_info=True)
            results[chunk_num] = {'success': False, 'error': str(e)}

    # Summary
    print("="*100)
    print("TEST SUMMARY")
    print("="*100)

    success_count = sum(1 for r in results.values() if r['success'])

    for chunk_num in test_chunks:
        result = results[chunk_num]
        status = "✓ PASS" if result['success'] else "✗ FAIL"
        print(f"Chunk {chunk_num:3d}: {status}")
        if result['success']:
            print(f"           Output: {result['output']}")
        else:
            print(f"           Error: {result['error']}")

    print()
    print(f"Results: {success_count}/{len(test_chunks)} tests passed")
    print("="*100)

    logger.info(f"\n{'='*100}")
    logger.info("Q4_K_M TEST COMPLETE")
    logger.info(f"Results: {success_count}/{len(test_chunks)} tests passed")
    logger.info(f"Log file: {log_filename}")
    logger.info("="*100)

    return 0 if success_count == len(test_chunks) else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
