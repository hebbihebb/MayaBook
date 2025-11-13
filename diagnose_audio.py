#!/usr/bin/env python3
"""
Diagnostic script to analyze audio files for silence issues
"""
import soundfile as sf
import numpy as np
import sys

def analyze_audio(filepath):
    """Analyze an audio file for silence and provide detailed RMS statistics"""
    try:
        audio, sr = sf.read(filepath)

        # Handle stereo vs mono
        if audio.ndim > 1:
            audio = audio.mean(axis=1)  # Convert to mono

        duration = len(audio) / sr
        total_rms = float(np.sqrt(np.mean(np.square(audio))))

        print(f"\n{'='*60}")
        print(f"File: {filepath}")
        print(f"{'='*60}")
        print(f"Sample rate: {sr} Hz")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Total samples: {len(audio)}")
        print(f"Total RMS: {total_rms:.6f}")
        print(f"Min value: {audio.min():.6f}")
        print(f"Max value: {audio.max():.6f}")

        # Analyze by 1-second segments
        print(f"\nPer-second RMS analysis:")
        print(f"{'Second':<10} {'RMS':<12} {'Status'}")
        print("-" * 35)

        segment_duration = 1.0  # 1 second
        num_segments = int(duration / segment_duration) + 1

        silent_threshold = 1e-3
        silent_segments = 0

        for i in range(num_segments):
            start_sample = int(i * segment_duration * sr)
            end_sample = min(int((i + 1) * segment_duration * sr), len(audio))
            segment = audio[start_sample:end_sample]

            if len(segment) > 0:
                segment_rms = float(np.sqrt(np.mean(np.square(segment))))
                status = "SILENT" if segment_rms < silent_threshold else "OK"
                if segment_rms < silent_threshold:
                    silent_segments += 1
                print(f"{i:<10} {segment_rms:<12.6f} {status}")

        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"{'='*60}")
        print(f"Total segments: {num_segments}")
        print(f"Silent segments (RMS < {silent_threshold}): {silent_segments}")
        print(f"Audible segments: {num_segments - silent_segments}")

        if silent_segments > 0:
            print(f"\n[WARNING] {silent_segments} silent segments detected!")
            print(f"This audio file may have silence issues.")
        else:
            print(f"\n[OK] All segments are audible (RMS >= {silent_threshold})")

        print(f"{'='*60}\n")

        return total_rms >= silent_threshold

    except Exception as e:
        print(f"ERROR analyzing {filepath}: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_audio.py <audio_file.wav> [audio_file2.wav ...]")
        print("\nExample: python diagnose_audio.py output/test.wav")
        sys.exit(1)

    all_good = True
    for filepath in sys.argv[1:]:
        is_good = analyze_audio(filepath)
        all_good = all_good and is_good

    sys.exit(0 if all_good else 1)
