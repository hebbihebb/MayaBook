#!/usr/bin/env python3
"""
Detailed audio quality diagnostic for chunk analysis.
Samples audio at multiple points to identify quality degradation patterns.
"""
import sys
import numpy as np
import soundfile as sf
from pathlib import Path

def analyze_audio_regions(audio_path: str, sample_rate: int = 24000) -> dict:
    """
    Analyze audio in 1-second windows to identify quality degradation.
    """
    try:
        audio, sr = sf.read(audio_path)
        if audio.ndim > 1:
            audio = audio[:, 0]  # Take first channel if stereo

        duration = len(audio) / sr
        window_size = sr  # 1 second window

        results = {
            'file': Path(audio_path).name,
            'sample_rate': sr,
            'total_samples': len(audio),
            'duration_seconds': duration,
            'windows': []
        }

        # Analyze 1-second windows
        num_windows = int(np.ceil(duration))

        for i in range(num_windows):
            start_sample = i * window_size
            end_sample = min((i + 1) * window_size, len(audio))

            if start_sample >= len(audio):
                break

            window = audio[start_sample:end_sample]

            # Calculate metrics
            rms = float(np.sqrt(np.mean(window ** 2)))
            peak = float(np.max(np.abs(window)))
            zero_crossings = float(np.sum(np.abs(np.diff(np.sign(window))))) / 2

            # Entropy (signal complexity)
            hist, _ = np.histogram(window, bins=256, range=(-1, 1))
            hist = hist / len(window)
            hist = hist[hist > 0]
            entropy = float(-np.sum(hist * np.log2(hist)))

            results['windows'].append({
                'window': i,
                'time_seconds': f"{i}-{i+1}s",
                'rms': rms,
                'peak': peak,
                'zero_crossings': zero_crossings,
                'entropy': entropy,
                'is_silent': rms < 1e-3,
                'is_clipping': peak >= 0.99,
            })

        # Overall stats
        overall_rms = float(np.sqrt(np.mean(audio ** 2)))
        rms_values = [w['rms'] for w in results['windows']]

        results['overall'] = {
            'rms': overall_rms,
            'peak': float(np.max(np.abs(audio))),
            'rms_mean': float(np.mean(rms_values)),
            'rms_std': float(np.std(rms_values)),
            'rms_min': float(np.min(rms_values)),
            'rms_max': float(np.max(rms_values)),
        }

        return results

    except Exception as e:
        return {
            'file': Path(audio_path).name,
            'error': str(e),
            'success': False
        }

def print_analysis(results: dict):
    """Pretty print analysis results."""
    if 'error' in results:
        print(f"❌ Error analyzing {results['file']}: {results['error']}")
        return

    print(f"\n{'='*80}")
    print(f"File: {results['file']}")
    print(f"Duration: {results['duration_seconds']:.2f}s @ {results['sample_rate']}Hz")
    print(f"{'='*80}")

    # Overall stats
    o = results['overall']
    print(f"\nOverall Statistics:")
    print(f"  RMS (mean):    {o['rms_mean']:.6f}")
    print(f"  RMS (std):     {o['rms_std']:.6f}")
    print(f"  RMS (min):     {o['rms_min']:.6f}")
    print(f"  RMS (max):     {o['rms_max']:.6f}")
    print(f"  Peak:          {o['peak']:.6f}")

    # Window-by-window analysis
    print(f"\nWindow-by-Window Analysis (1-second windows):")
    print(f"{'Win':<4} {'Time':<10} {'RMS':<10} {'Peak':<10} {'Zero Cr.':<10} {'Entropy':<10} {'Status':<15}")
    print(f"{'-'*80}")

    for w in results['windows']:
        status = ""
        if w['is_silent']:
            status = "⚠️  SILENT"
        elif w['is_clipping']:
            status = "⚠️  CLIPPING"
        else:
            status = "✅ OK"

        # Entropy check for gibberish (very low or very high entropy = unusual)
        if w['entropy'] < 2.0:
            status = "⚠️  LOW ENT"
        elif w['entropy'] > 7.5:
            status = "⚠️  HIGH ENT"

        print(f"{w['window']:<4} {w['time_seconds']:<10} {w['rms']:<10.6f} {w['peak']:<10.6f} {w['zero_crossings']:<10.1f} {w['entropy']:<10.2f} {status:<15}")

    # Identify problem regions
    print(f"\nProblem Regions:")
    has_issues = False
    for w in results['windows']:
        if w['is_silent']:
            print(f"  ⚠️  Window {w['window']} ({w['time_seconds']}): SILENT (RMS < 0.001)")
            has_issues = True
        elif w['is_clipping']:
            print(f"  ⚠️  Window {w['window']} ({w['time_seconds']}): CLIPPING (peak >= 0.99)")
            has_issues = True
        elif w['rms'] < 0.01:
            print(f"  ⚠️  Window {w['window']} ({w['time_seconds']}): LOW RMS ({w['rms']:.6f})")
            has_issues = True
        elif w['entropy'] < 2.0 or w['entropy'] > 7.5:
            print(f"  ⚠️  Window {w['window']} ({w['time_seconds']}): ABNORMAL ENTROPY ({w['entropy']:.2f})")
            has_issues = True

    if not has_issues:
        print(f"  ✅ No obvious quality issues detected")

def main():
    if len(sys.argv) < 2:
        print("Usage: python diagnose_chunk_quality.py <audio_file> [audio_file2] ...")
        print("\nExample: python diagnose_chunk_quality.py tmp1cg1kqhz.wav tmpvzkgqlej.wav")
        sys.exit(1)

    for audio_file in sys.argv[1:]:
        if not Path(audio_file).exists():
            print(f"❌ File not found: {audio_file}")
            continue

        results = analyze_audio_regions(audio_file)
        print_analysis(results)

if __name__ == "__main__":
    main()
