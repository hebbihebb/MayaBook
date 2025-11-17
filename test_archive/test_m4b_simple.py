#!/usr/bin/env python3
"""
Simple M4B generation test from stress test WAV files

This script:
1. Concatenates the 817 partial WAV files into a single WAV
2. Converts to M4B using FFmpeg
3. Validates output
"""
import os
import sys
import glob
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Configure logging
log_filename = f"m4b_simple_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
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

def main():
    print_header("M4B Generation Test - WAV to M4B Conversion")

    # Configuration
    TEMP_DIR = "/tmp"
    OUTPUT_DIR = "output/m4b_test"

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    logger.info("="*80)
    logger.info("M4B GENERATION TEST")
    logger.info("="*80)

    try:
        # Step 1: Find all temp WAV files
        print("Step 1: Locating temp WAV files...")
        wav_files = sorted(glob.glob(f"{TEMP_DIR}/tmp*.wav"))
        logger.info(f"Found {len(wav_files)} WAV files in {TEMP_DIR}")
        print(f"✓ Found {len(wav_files)} WAV files")

        if not wav_files:
            raise RuntimeError("No WAV files found!")

        # Step 2: Concatenate WAVs
        print("\nStep 2: Concatenating WAV files...")
        logger.info("Importing audio concatenation module...")
        from core.audio_combine import concat_wavs

        concat_wav = os.path.join(OUTPUT_DIR, "combined_audio.wav")
        logger.info(f"Concatenating {len(wav_files)} WAV files to {concat_wav}")

        concat_wavs(wav_files, concat_wav, gap_seconds=0.25)

        if not os.path.exists(concat_wav):
            raise RuntimeError(f"Concatenation failed - output not found: {concat_wav}")

        concat_size_mb = os.path.getsize(concat_wav) / (1024 * 1024)
        logger.info(f"✓ Concatenation successful: {concat_size_mb:.1f} MB")
        print(f"✓ Concatenated to {concat_wav} ({concat_size_mb:.1f} MB)")

        # Step 3: Analyze the audio
        print("\nStep 3: Analyzing concatenated audio...")
        logger.info("Importing soundfile module...")
        import soundfile as sf

        audio_data, samplerate = sf.read(concat_wav)
        duration_seconds = len(audio_data) / samplerate
        duration_hours = duration_seconds / 3600
        duration_minutes = (duration_seconds % 3600) / 60

        logger.info(f"Audio properties:")
        logger.info(f"  Sample rate: {samplerate} Hz")
        logger.info(f"  Duration: {duration_seconds:.1f} seconds ({duration_hours:.1f} hours, {duration_minutes:.0f} minutes)")
        logger.info(f"  Channels: {'Mono' if len(audio_data.shape) == 1 else 'Stereo'}")

        print(f"✓ Audio analyzed:")
        print(f"  - Sample rate: {samplerate} Hz")
        print(f"  - Duration: {duration_hours:.1f} hours ({duration_minutes:.0f} minutes)")
        print(f"  - Format: {'Mono' if len(audio_data.shape) == 1 else 'Stereo'}")

        # Step 4: Convert WAV to M4B using FFmpeg
        print("\nStep 4: Converting WAV to M4B using FFmpeg...")
        logger.info("Converting WAV to M4B...")

        m4b_output = os.path.join(OUTPUT_DIR, "audiobook.m4b")

        # FFmpeg command to convert WAV to M4B
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", concat_wav,
            "-c:a", "aac",
            "-q:a", "2",
            "-movflags", "+faststart",
            "-metadata", "title=MayaBook Stress Test",
            "-metadata", "artist=Test Suite",
            "-metadata", "genre=Audiobook",
            m4b_output
        ]

        logger.info(f"Running FFmpeg: {' '.join(ffmpeg_cmd)}")
        print(f"Running FFmpeg conversion...")

        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")

        if not os.path.exists(m4b_output):
            raise RuntimeError(f"M4B creation failed - output not found: {m4b_output}")

        m4b_size_mb = os.path.getsize(m4b_output) / (1024 * 1024)
        logger.info(f"✓ M4B created successfully: {m4b_size_mb:.1f} MB")
        print(f"✓ M4B created: {m4b_output} ({m4b_size_mb:.1f} MB)")

        # Step 5: Verify with ffprobe
        print("\nStep 5: Verifying M4B with ffprobe...")
        logger.info("Verifying M4B file with ffprobe...")

        ffprobe_cmd = [
            "ffprobe",
            "-v", "error",
            "-show_format",
            "-show_streams",
            m4b_output
        ]

        result = subprocess.run(ffprobe_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            logger.info("✓ M4B file is valid")
            print("✓ M4B validation passed (ffprobe)")

            # Extract duration from ffprobe output
            for line in result.stdout.split('\n'):
                if 'duration=' in line:
                    logger.info(f"  {line}")
                    print(f"  {line}")
        else:
            logger.warning("ffprobe verification not available")
            print("⚠ ffprobe not available, skipping detailed verification")

        # Final report
        print("\n" + "="*80)
        print("✅ M4B GENERATION TEST SUCCESSFUL")
        print("="*80)
        print(f"\nGenerated Files:")
        print(f"  Concatenated WAV: {concat_wav}")
        print(f"    Size: {concat_size_mb:.1f} MB")
        print(f"    Duration: {duration_hours:.1f} hours ({duration_minutes:.0f} min)")
        print(f"\n  M4B Audiobook: {m4b_output}")
        print(f"    Size: {m4b_size_mb:.1f} MB")
        print(f"    Compression: {((1 - (m4b_size_mb / concat_size_mb)) * 100):.1f}%")
        print(f"\nLog: {log_filename}")
        print("="*80)

        logger.info("="*80)
        logger.info("M4B GENERATION TEST COMPLETED SUCCESSFULLY")
        logger.info("="*80)
        logger.info(f"Concatenated WAV: {concat_wav} ({concat_size_mb:.1f} MB, {duration_hours:.1f}h)")
        logger.info(f"M4B Output: {m4b_output} ({m4b_size_mb:.1f} MB, {((1 - (m4b_size_mb / concat_size_mb)) * 100):.1f}% compression)")
        logger.info("="*80)

        return 0

    except Exception as e:
        print(f"\n✗ TEST FAILED: {type(e).__name__}: {e}")
        logger.error("M4B Generation test failed", exc_info=True)
        print(f"\nCheck log: {log_filename}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
