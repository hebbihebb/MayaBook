#!/usr/bin/env python3
"""
Phase 1 Verification: Isolated Chunk Testing
Tests chunks 1, 100, 485, 486 to verify GPU cache fix

Chunk Selection:
  - Chunk 1:   First chunk (was gibberish in original stress test)
  - Chunk 100: Middle of corrupted section (should also be fixed)
  - Chunk 485: Last chunk before coherent audio started (should now be fixed)
  - Chunk 486: First coherent chunk in original (should remain good)
"""
import sys
import os
sys.path.insert(0, '/mnt/Games/MayaBook')

from core.epub_extract import extract_text
from core.chunking import chunk_text
from core.tts_maya1_hf import synthesize_chunk_hf
import soundfile as sf
import numpy as np
import logging
from datetime import datetime

# Configure detailed logging
log_filename = f"phase1_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def analyze_audio(wav_path, chunk_num):
    """Analyze generated audio file"""
    audio, sr = sf.read(wav_path)
    duration = len(audio) / sr
    rms = np.sqrt(np.mean(audio**2))

    return {
        'duration': duration,
        'sample_rate': sr,
        'rms': rms,
        'shape': audio.shape,
        'min': audio.min(),
        'max': audio.max(),
        'file_size_kb': os.path.getsize(wav_path) / 1024
    }

def main():
    print("\n" + "="*100)
    print("PHASE 1 VERIFICATION: ISOLATED CHUNK TESTING")
    print("="*100)
    print("\nGoal: Verify that individual chunks produce high-quality audio with GPU cache fix\n")

    logger.info("="*100)
    logger.info("PHASE 1: ISOLATED CHUNK TESTING")
    logger.info("="*100)

    # Extract and chunk EPUB
    print("Loading EPUB and creating chunks...")
    epub_path = "assets/test/Zero Combat, Max Crafting_ The - GordanWizard.epub"
    text = extract_text(epub_path)
    chunks = chunk_text(text, max_words=70)

    print(f"✓ EPUB loaded: {len(chunks)} total chunks")
    logger.info(f"EPUB loaded with {len(chunks)} chunks")

    # Test chunks
    test_chunks = [1, 100, 485, 486]
    results = {}

    for chunk_idx in test_chunks:
        chunk_num = chunk_idx  # 1-indexed for display
        python_idx = chunk_idx - 1  # 0-indexed for array access

        print("\n" + "="*100)
        print(f"TEST {chunk_num}: CHUNK {chunk_num} of {len(chunks)}")
        print("="*100)

        # Get text
        chunk_content = chunks[python_idx]
        words = len(chunk_content.split())

        print(f"Text ({words} words):")
        print(f"  {chunk_content[:100]}...")
        print()

        logger.info(f"\n{'='*100}")
        logger.info(f"TEST {chunk_num}: Synthesizing chunk {chunk_num}")
        logger.info(f"{'='*100}")
        logger.info(f"Chunk {chunk_num}: {words} words")
        logger.info(f"Text preview: {chunk_content[:150]}...")

        try:
            # Synthesize
            print("Synthesizing...")
            logger.info("Starting synthesis...")

            output_wav = synthesize_chunk_hf(
                model_path="assets/models/maya1_4bit_safetensor",
                text=chunk_content,
                voice_description="A mature female voice, clear and expressive, with good pacing",
                temperature=0.45,
                top_p=0.92,
                max_tokens=2500,
            )

            # Analyze
            logger.info(f"Synthesis complete. Analyzing audio...")
            metrics = analyze_audio(output_wav, chunk_num)
            results[chunk_num] = {
                'success': True,
                'wav_path': output_wav,
                'metrics': metrics
            }

            print(f"✓ Synthesis successful")
            print(f"  Output: {output_wav}")
            print(f"  Duration: {metrics['duration']:.2f}s")
            print(f"  Sample rate: {metrics['sample_rate']} Hz")
            print(f"  RMS: {metrics['rms']:.6f}")
            print(f"  File size: {metrics['file_size_kb']:.1f} KB")

            logger.info(f"✓ Chunk {chunk_num} synthesis successful")
            logger.info(f"  Duration: {metrics['duration']:.2f}s")
            logger.info(f"  RMS: {metrics['rms']:.6f}")
            logger.info(f"  File: {output_wav}")

        except Exception as e:
            print(f"✗ Synthesis failed: {e}")
            logger.error(f"✗ Chunk {chunk_num} synthesis failed: {e}", exc_info=True)
            results[chunk_num] = {
                'success': False,
                'error': str(e)
            }

    # Summary
    print("\n" + "="*100)
    print("PHASE 1 TEST SUMMARY")
    print("="*100)
    print()

    logger.info("\n" + "="*100)
    logger.info("PHASE 1 SUMMARY")
    logger.info("="*100)

    success_count = sum(1 for r in results.values() if r['success'])

    for chunk_num in test_chunks:
        result = results[chunk_num]
        status = "✓ PASS" if result['success'] else "✗ FAIL"
        print(f"Chunk {chunk_num:3d}: {status}")

        if result['success']:
            metrics = result['metrics']
            print(f"        Duration: {metrics['duration']:6.2f}s  RMS: {metrics['rms']:.6f}  Size: {metrics['file_size_kb']:7.1f} KB")
            logger.info(f"Chunk {chunk_num}: PASS - Duration {metrics['duration']:.2f}s, RMS {metrics['rms']:.6f}")
        else:
            print(f"        Error: {result['error']}")
            logger.info(f"Chunk {chunk_num}: FAIL - {result['error']}")

    print()
    print("="*100)
    print(f"RESULTS: {success_count}/{len(test_chunks)} tests passed")
    print("="*100)

    logger.info(f"\nFinal Result: {success_count}/{len(test_chunks)} tests PASSED")

    if success_count == len(test_chunks):
        print("\n✅ PHASE 1 VERIFICATION SUCCESSFUL")
        print("\nAll chunks produced audio successfully!")
        print("Next step: Phase 2 (small-scale 100-chunk stress test)")
        logger.info("✅ PHASE 1 COMPLETE - ALL TESTS PASSED")
        return 0
    else:
        print(f"\n❌ PHASE 1 VERIFICATION FAILED")
        print(f"\n{len(test_chunks) - success_count} test(s) failed. Check log for details.")
        logger.info("❌ PHASE 1 FAILED - Some tests did not pass")
        return 1

if __name__ == "__main__":
    exit_code = main()
    print(f"\nLog file: {log_filename}")
    sys.exit(exit_code)
