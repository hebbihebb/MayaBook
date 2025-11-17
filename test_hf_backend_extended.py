#!/usr/bin/env python3
"""
Extended HuggingFace backend test with longer sentences.

Tests the float16 fix robustness with:
- Short sentences (baseline)
- Medium paragraphs
- Long technical text
- Emotion-heavy text
"""
import sys
import logging
import numpy as np
import soundfile as sf
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.tts_maya1_hf import synthesize_chunk_hf

def diagnose_audio(audio_path: str) -> dict:
    """Analyze audio file"""
    try:
        audio, sr = sf.read(audio_path)
        if audio.ndim > 1:
            audio = audio[:, 0]  # Take first channel if stereo

        rms = float(np.sqrt(np.mean(audio ** 2)))
        duration = len(audio) / sr
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

    # Extended test cases with longer sentences
    test_cases = [
        {
            'name': 'Short (baseline)',
            'text': 'Hello, this is a test.',
            'voice': 'A friendly male narrator.',
            'word_count': 5,
        },
        {
            'name': 'Medium (single sentence)',
            'text': 'The ancient forest stood silent and still, its towering trees casting long shadows across the moss-covered ground as the evening sun dipped below the distant horizon.',
            'voice': 'A calm, soothing female voice.',
            'word_count': 32,
        },
        {
            'name': 'Paragraph (narrative)',
            'text': 'She walked through the marketplace with purpose, dodging vendors and customers alike. The cobblestone streets were worn smooth by centuries of footsteps. Every corner held a memory, a moment frozen in time. She remembered the last time she was here, years ago, when everything felt possible and the future stretched out before her like an endless road.',
            'voice': 'A reflective, contemplative female voice with slight emotion.',
            'word_count': 66,
        },
        {
            'name': 'Technical (longer)',
            'text': 'The quantum computing architecture represents a fundamental shift in computational paradigms, leveraging superposition and entanglement principles to achieve exponential speedups over classical algorithms. Modern quantum processors operate at cryogenic temperatures, requiring sophisticated error correction mechanisms to maintain coherence across multiple qubits. The challenge of scaling beyond current limitations involves addressing decoherence, gate fidelity, and the need for fault-tolerant quantum computation.',
            'voice': 'A professional, authoritative male voice.',
            'word_count': 62,
        },
        {
            'name': 'Emotion (with tags)',
            'text': 'The news hit her like a thunderbolt. <gasp> She couldn\'t believe what she was hearing. <cry> Years of hope and dreams, shattered in a single moment. Her hands trembled as she read the letter again and again, each word cutting deeper than the last. <whisper> But beneath the pain, a spark of determination flickered.',
            'voice': 'A deeply emotional female voice.',
            'word_count': 52,
        },
    ]

    logger.info("=" * 80)
    logger.info("HuggingFace Backend Extended Test (Optimized with Smart Chunking)")
    logger.info("=" * 80)
    logger.info(f"Model path: {model_path}")
    logger.info(f"Test settings: temp=0.43, top_p=0.90, max_tokens=2000")
    logger.info(f"Chunking: max_words=70, max_chars=350 (dual-constraint)")
    logger.info("")

    results = []
    passed = 0
    failed = 0

    for test_case in test_cases:
        logger.info(f"📝 Test: {test_case['name']} ({test_case['word_count']} words)")
        logger.info(f"   Text: {test_case['text'][:70]}...")
        logger.info(f"   Voice: {test_case['voice']}")

        try:
            output_path = synthesize_chunk_hf(
                model_path=model_path,
                text=test_case['text'],
                voice_description=test_case['voice'],
                temperature=0.43,
                top_p=0.90,
                max_tokens=2000,
            )

            # Diagnose output
            diag = diagnose_audio(output_path)

            if diag['success']:
                # Validate audio quality
                issues = []
                if diag['is_silent']:
                    issues.append("SILENT (RMS < 0.001)")
                if diag['is_clipping']:
                    issues.append("CLIPPING (peak >= 0.99)")
                if diag['rms'] < 0.01:
                    issues.append("LOW RMS (< 0.01)")
                if diag['duration_seconds'] < 1:
                    issues.append("TOO SHORT (< 1s)")

                if issues:
                    logger.warning(f"   ⚠️  ISSUES: {', '.join(issues)}")
                    logger.warning(f"      Duration: {diag['duration_seconds']:.2f}s")
                    logger.warning(f"      RMS: {diag['rms']:.6f}")
                    logger.warning(f"      Peak: {diag['peak']:.6f}")
                    failed += 1
                    result_status = "FAIL"
                else:
                    logger.info(f"   ✅ SUCCESS")
                    logger.info(f"      Duration: {diag['duration_seconds']:.2f}s")
                    logger.info(f"      RMS: {diag['rms']:.6f} (healthy)")
                    logger.info(f"      Peak: {diag['peak']:.6f} (no clip)")
                    logger.info(f"      File: {output_path}")
                    passed += 1
                    result_status = "PASS"
            else:
                logger.error(f"   ❌ DIAGNOSIS FAILED: {diag['error']}")
                failed += 1
                result_status = "FAIL"

        except Exception as e:
            logger.error(f"   ❌ SYNTHESIS FAILED: {str(e)}")
            failed += 1
            result_status = "FAIL"

        results.append({
            'name': test_case['name'],
            'words': test_case['word_count'],
            'status': result_status,
        })
        logger.info("")

    # Summary
    logger.info("=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Passed: {passed}/{len(test_cases)}")
    logger.info(f"Failed: {failed}/{len(test_cases)}")
    logger.info("")

    logger.info("Results by test case:")
    logger.info(f"{'Test Name':<25} {'Words':<8} {'Status':<10}")
    logger.info("-" * 80)
    for r in results:
        status_icon = "✅" if r['status'] == "PASS" else "❌"
        logger.info(f"{r['name']:<25} {r['words']:<8} {status_icon} {r['status']:<8}")

    logger.info("")
    if passed == len(test_cases):
        logger.info("✅ All tests passed! float16 fix is ROBUST across all text lengths.")
        logger.info("   HuggingFace backend ready for production use.")
        return 0
    else:
        logger.warning(f"⚠️  {failed} test(s) failed. Review issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
