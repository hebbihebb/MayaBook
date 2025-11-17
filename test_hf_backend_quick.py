#!/usr/bin/env python3
"""
Quick test for HuggingFace backend with fixed compute dtype
Tests the fix for bfloat16 -> float16 issue on GTX 2070
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

    # Test parameters (optimal: no repetition, clean breathing)
    test_cases = [
        {
            'text': 'The forest was eerily quiet. <whisper> Something was watching from the shadows.',
            'voice': 'A calm, soothing female voice with a slight British accent.',
            'temp': 0.43,
            'top_p': 0.90,
            'max_tokens': 2500,
        },
        {
            'text': 'Hello, this is a simple test.',
            'voice': 'A friendly male narrator voice.',
            'temp': 0.43,
            'top_p': 0.90,
            'max_tokens': 2500,
        },
    ]

    logger.info("=" * 70)
    logger.info("HuggingFace Backend Quick Test (with float16 fix)")
    logger.info("=" * 70)
    logger.info(f"Model path: {model_path}")
    logger.info("")

    results = []

    for i, test in enumerate(test_cases, 1):
        logger.info(f"Test {i}/2: {test['text'][:50]}...")
        logger.info(f"  Voice: {test['voice'][:50]}...")
        logger.info(f"  Params: temp={test['temp']}, top_p={test['top_p']}, max_tokens={test.get('max_tokens', 2500)}")

        try:
            output_path = synthesize_chunk_hf(
                model_path=model_path,
                text=test['text'],
                voice_description=test['voice'],
                temperature=test['temp'],
                top_p=test['top_p'],
                max_tokens=test.get('max_tokens', 2500),
            )

            # Diagnose output
            diag = diagnose_audio(output_path)

            if diag['success']:
                logger.info(f"  ✅ SUCCESS")
                logger.info(f"     Duration: {diag['duration_seconds']:.2f}s")
                logger.info(f"     RMS: {diag['rms']:.6f}")
                logger.info(f"     Peak: {diag['peak']:.6f}")
                logger.info(f"     Silent: {diag['is_silent']}")
                logger.info(f"     Clipping: {diag['is_clipping']}")
                logger.info(f"     File: {output_path}")
                results.append({
                    'test': i,
                    'status': 'PASS',
                    'duration': diag['duration_seconds'],
                    'rms': diag['rms'],
                })
            else:
                logger.error(f"  ❌ DIAGNOSIS FAILED: {diag['error']}")
                results.append({'test': i, 'status': 'FAIL', 'error': diag['error']})

        except Exception as e:
            logger.error(f"  ❌ SYNTHESIS FAILED: {str(e)}")
            results.append({'test': i, 'status': 'FAIL', 'error': str(e)})

        logger.info("")

    # Summary
    logger.info("=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)
    passed = sum(1 for r in results if r['status'] == 'PASS')
    logger.info(f"Passed: {passed}/{len(results)}")

    if passed == len(results):
        logger.info("✅ All tests passed! HuggingFace backend working correctly.")
        return 0
    else:
        logger.warning(f"⚠️  {len(results) - passed} test(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
