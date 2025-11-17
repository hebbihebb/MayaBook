#!/usr/bin/env python3
"""
Focused test to diagnose Chunk 2 gibberish issue.
Re-runs Test 4 (technical text) with enhanced logging and diagnostics.
"""
import sys
import logging
import numpy as np
import soundfile as sf
from pathlib import Path

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.tts_maya1_hf import synthesize_chunk_hf
from core.chunking import chunk_text

def analyze_audio_detailed(audio_path: str) -> dict:
    """Analyze audio file with detailed metrics."""
    try:
        audio, sr = sf.read(audio_path)
        if audio.ndim > 1:
            audio = audio[:, 0]

        duration = len(audio) / sr
        rms = float(np.sqrt(np.mean(audio ** 2)))
        peak = float(np.max(np.abs(audio)))

        return {
            'success': True,
            'sample_rate': sr,
            'samples': len(audio),
            'duration_seconds': duration,
            'rms': rms,
            'peak': peak,
            'is_silent': rms < 1e-3,
            'is_clipping': peak >= 0.99,
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def main():
    model_path = "assets/models/maya1_4bit_safetensor"

    # Test 4 from extended test
    test_text = 'The quantum computing architecture represents a fundamental shift in computational paradigms, leveraging superposition and entanglement principles to achieve exponential speedups over classical algorithms. Modern quantum processors operate at cryogenic temperatures, requiring sophisticated error correction mechanisms to maintain coherence across multiple qubits. The challenge of scaling beyond current limitations involves addressing decoherence, gate fidelity, and the need for fault-tolerant quantum computation.'
    voice_description = 'A professional, authoritative male voice.'

    logger.info("="*80)
    logger.info("Test 4 Re-run: Chunk 2 Gibberish Investigation")
    logger.info("="*80)
    logger.info(f"Text: {test_text[:100]}...")
    logger.info(f"Voice: {voice_description}")
    logger.info(f"Text length: {len(test_text)} chars, {len(test_text.split())} words")
    logger.info("")

    # Step 1: Chunk the text
    logger.info("Step 1: Chunking text with max_words=70, max_chars=350")
    chunks = chunk_text(test_text, max_chars=350, max_words=70)
    logger.info(f"Text chunked into {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        chunk_words = len(chunk.split())
        chunk_chars = len(chunk)
        logger.info(f"  Chunk {i+1}: {chunk_words} words, {chunk_chars} chars")
        logger.info(f"           {chunk[:70]}...")
    logger.info("")

    # Step 2: Synthesize each chunk with detailed logging
    logger.info("Step 2: Synthesizing each chunk")
    results = []

    for i, chunk in enumerate(chunks, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"Synthesizing Chunk {i}/{len(chunks)}")
        logger.info(f"{'='*80}")
        logger.info(f"Text: {chunk}")
        logger.info(f"Words: {len(chunk.split())}, Chars: {len(chunk)}")

        try:
            output_path = synthesize_chunk_hf(
                model_path=model_path,
                text=chunk,
                voice_description=voice_description,
                temperature=0.43,
                top_p=0.90,
                max_tokens=2000,
            )

            logger.info(f"✅ Synthesis complete: {output_path}")

            # Analyze output
            diag = analyze_audio_detailed(output_path)
            if diag['success']:
                logger.info(f"Audio Analysis:")
                logger.info(f"  Duration: {diag['duration_seconds']:.2f}s")
                logger.info(f"  Sample Rate: {diag['sample_rate']} Hz")
                logger.info(f"  RMS: {diag['rms']:.6f}")
                logger.info(f"  Peak: {diag['peak']:.6f}")
                logger.info(f"  Silent: {diag['is_silent']}")
                logger.info(f"  Clipping: {diag['is_clipping']}")

                results.append({
                    'chunk': i,
                    'path': output_path,
                    'duration': diag['duration_seconds'],
                    'rms': diag['rms'],
                    'analysis': diag,
                })
            else:
                logger.error(f"❌ Audio analysis failed: {diag['error']}")
                results.append({
                    'chunk': i,
                    'path': output_path,
                    'error': diag['error'],
                })

        except Exception as e:
            logger.error(f"❌ Synthesis failed: {str(e)}", exc_info=True)

    # Summary
    logger.info(f"\n{'='*80}")
    logger.info("SYNTHESIS SUMMARY")
    logger.info(f"{'='*80}")
    for r in results:
        if 'error' not in r:
            logger.info(f"Chunk {r['chunk']}: {r['duration']:.2f}s, RMS={r['rms']:.6f}, File: {Path(r['path']).name}")
        else:
            logger.info(f"Chunk {r['chunk']}: ERROR - {r['error']}")

    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Listen to the audio files for each chunk")
    logger.info("2. Run diagnose_chunk_quality.py on the files to check for artifacts")
    logger.info("3. Look for patterns in RMS values and time windows")
    logger.info("")

    for r in results:
        if 'path' in r:
            logger.info(f"Run: python diagnose_chunk_quality.py {r['path']}")

if __name__ == "__main__":
    sys.exit(main() or 0)
