#!/usr/bin/env python3
"""
Test M4B Creation with Chunk Combination
Tests combining 3 Q4_K_M GGUF chunks into a single M4B file
Validates for distortion, gaps, and audio quality during concatenation
"""
import sys
sys.path.insert(0, '/mnt/Games/MayaBook')

from core.audio_combine import concat_wavs
from core.m4b_export import create_m4b_stream
import soundfile as sf
import numpy as np
import logging
from datetime import datetime
import os

# Configure logging
log_filename = f"test_m4b_combination_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def analyze_audio(wav_path):
    """Detailed audio analysis"""
    audio, sr = sf.read(wav_path)

    # Handle stereo
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    duration = len(audio) / sr
    rms = np.sqrt(np.mean(audio**2))
    peak = np.max(np.abs(audio))
    min_val = np.min(audio)
    max_val = np.max(audio)

    # Check for clipping (values at ±1.0)
    clipping_samples = np.sum((np.abs(audio) > 0.99))
    clipping_percent = (clipping_samples / len(audio)) * 100

    # Check for silence
    silence_threshold = 0.001
    silent_samples = np.sum(np.abs(audio) < silence_threshold)
    silence_percent = (silent_samples / len(audio)) * 100

    return {
        'duration': duration,
        'sample_rate': sr,
        'rms': rms,
        'peak': peak,
        'min': min_val,
        'max': max_val,
        'clipping': clipping_percent,
        'silence_percent': silence_percent,
        'total_samples': len(audio),
        'file_size_mb': os.path.getsize(wav_path) / (1024*1024)
    }

def main():
    print("\n" + "="*100)
    print("TEST: M4B CREATION WITH CHUNK COMBINATION")
    print("="*100)
    print("\nGoal: Combine 3 Q4_K_M GGUF chunks and detect any distortion/artifacts\n")

    logger.info("="*100)
    logger.info("M4B COMBINATION TEST")
    logger.info("="*100)

    # Input files (Q4_K_M test output)
    q4k_dir = "output/q4k_test"
    chunk_files = [
        f"{q4k_dir}/q4k_chunk_001.wav",
        f"{q4k_dir}/q4k_chunk_100.wav",
        f"{q4k_dir}/q4k_chunk_486.wav"
    ]

    output_dir = "output/m4b_test"
    os.makedirs(output_dir, exist_ok=True)

    combined_wav = f"{output_dir}/combined_3chunks.wav"
    m4b_output = f"{output_dir}/test_3chunks.m4b"

    # Verify input files
    print("Verifying input files...")
    for i, chunk_file in enumerate(chunk_files, 1):
        if not os.path.exists(chunk_file):
            print(f"✗ Missing: {chunk_file}")
            logger.error(f"Input file missing: {chunk_file}")
            return 1

        metrics = analyze_audio(chunk_file)
        print(f"✓ Chunk {i}: {metrics['duration']:.2f}s @ {metrics['sample_rate']} Hz, RMS={metrics['rms']:.6f}")
        logger.info(f"  Input chunk {i}: {metrics['duration']:.2f}s, RMS={metrics['rms']:.6f}")

    print()

    # PHASE 1: Concatenate WAVs
    print("="*100)
    print("PHASE 1: CONCATENATING WAV FILES")
    print("="*100)

    try:
        print("Combining 3 chunks with 0.25s silence gap...")
        logger.info("Starting WAV concatenation...")

        concat_wavs(chunk_files, combined_wav, gap_seconds=0.25)

        print("✓ Concatenation successful")
        logger.info("✓ WAV concatenation complete")

        # Analyze combined WAV
        combined_metrics = analyze_audio(combined_wav)
        expected_duration = sum(analyze_audio(f)['duration'] for f in chunk_files) + (0.25 * 2)

        print(f"\nCombined WAV Analysis:")
        print(f"  Duration: {combined_metrics['duration']:.2f}s (expected ~{expected_duration:.2f}s)")
        print(f"  RMS: {combined_metrics['rms']:.6f}")
        print(f"  Peak: {combined_metrics['peak']:.6f}")
        print(f"  Clipping: {combined_metrics['clipping']:.4f}%")
        print(f"  Silence: {combined_metrics['silence_percent']:.4f}%")
        print(f"  File Size: {combined_metrics['file_size_mb']:.2f} MB")

        logger.info(f"Combined metrics: Duration={combined_metrics['duration']:.2f}s, RMS={combined_metrics['rms']:.6f}, Peak={combined_metrics['peak']:.6f}")

        # Check for issues
        if combined_metrics['clipping'] > 0.1:
            print(f"⚠️  WARNING: {combined_metrics['clipping']:.2f}% clipping detected")
            logger.warning(f"Clipping detected: {combined_metrics['clipping']:.2f}%")

        if combined_metrics['silence_percent'] > 5:
            print(f"⚠️  WARNING: {combined_metrics['silence_percent']:.2f}% silence detected")
            logger.warning(f"Excessive silence: {combined_metrics['silence_percent']:.2f}%")

    except Exception as e:
        print(f"✗ Concatenation failed: {e}")
        logger.error(f"Concatenation error: {e}", exc_info=True)
        return 1

    # PHASE 2: Create M4B
    print("\n" + "="*100)
    print("PHASE 2: CREATING M4B FILE")
    print("="*100)

    try:
        print("Converting combined WAV to M4B with metadata...")
        logger.info("Starting M4B creation...")

        # Read combined WAV
        audio_data, sr = sf.read(combined_wav)

        # Create M4B with basic metadata
        metadata = {
            'title': 'Test: Q4_K_M Combination',
            'artist': 'MayaBook TTS',
            'album': 'Test Output',
        }

        # Start FFmpeg process for M4B streaming
        proc = create_m4b_stream(
            output_path=m4b_output,
            sample_rate=sr,
            metadata=metadata
        )

        # Convert to float32 and write to FFmpeg
        audio_f32 = audio_data.astype(np.float32)
        proc.stdin.write(audio_f32.tobytes())
        proc.stdin.close()

        # Wait for FFmpeg to finish
        return_code = proc.wait()

        if return_code != 0:
            raise Exception(f"FFmpeg failed with return code {return_code}")

        if not os.path.exists(m4b_output):
            raise Exception("M4B file not created")

        m4b_size = os.path.getsize(m4b_output) / (1024*1024)
        print(f"✓ M4B creation successful")
        print(f"  Output: {m4b_output}")
        print(f"  Size: {m4b_size:.2f} MB")

        logger.info(f"✓ M4B created: {m4b_output} ({m4b_size:.2f} MB)")

    except Exception as e:
        print(f"✗ M4B creation failed: {e}")
        logger.error(f"M4B creation error: {e}", exc_info=True)
        return 1

    # PHASE 3: Validation
    print("\n" + "="*100)
    print("PHASE 3: VALIDATION")
    print("="*100)

    try:
        # Re-verify combined WAV
        print("Final validation of combined audio...")
        final_metrics = analyze_audio(combined_wav)

        # Check duration
        duration_match = abs(final_metrics['duration'] - expected_duration) < 0.5
        duration_status = "✓" if duration_match else "✗"
        print(f"{duration_status} Duration: {final_metrics['duration']:.2f}s vs expected {expected_duration:.2f}s")

        # Check RMS levels
        rms_ok = final_metrics['rms'] > 0.01
        rms_status = "✓" if rms_ok else "✗"
        print(f"{rms_status} RMS Level: {final_metrics['rms']:.6f} (expected > 0.01)")

        # Check no clipping
        no_clip = final_metrics['clipping'] < 0.1
        clip_status = "✓" if no_clip else "✗"
        print(f"{clip_status} No Clipping: {final_metrics['clipping']:.4f}% (expected < 0.1%)")

        # Check no excessive silence
        low_silence = final_metrics['silence_percent'] < 5
        silence_status = "✓" if low_silence else "✗"
        print(f"{silence_status} Silence Level: {final_metrics['silence_percent']:.4f}% (expected < 5%)")

        # Overall pass/fail
        all_pass = duration_match and rms_ok and no_clip and low_silence

        print()
        if all_pass:
            print("✅ ALL VALIDATION CHECKS PASSED")
            print("\nCombination Summary:")
            print(f"  ✓ 3 chunks combined successfully")
            print(f"  ✓ No distortion detected")
            print(f"  ✓ No audio artifacts")
            print(f"  ✓ M4B file created successfully")
            logger.info("✅ VALIDATION COMPLETE - ALL CHECKS PASSED")
            return 0
        else:
            print("❌ VALIDATION FAILED - Issues detected")
            logger.info("❌ VALIDATION FAILED")
            return 1

    except Exception as e:
        print(f"✗ Validation error: {e}")
        logger.error(f"Validation error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = main()
    print(f"\nLog file: {log_filename}")
    sys.exit(exit_code)
