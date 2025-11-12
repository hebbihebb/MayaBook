#!/usr/bin/env python3
"""
CLI test script for MayaBook - Quick testing without GUI
"""
import os
import sys
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Test MayaBook TTS pipeline from CLI')
    parser.add_argument('--text', type=str, default="Hello, this is a test of the Maya1 text to speech system.",
                        help='Text to synthesize')
    parser.add_argument('--model', type=str, default='assets/maya1.gguf',
                        help='Path to Maya1 GGUF model')
    parser.add_argument('--voice', type=str, default='Female voice in her 30s, calm and friendly, natural American accent',
                        help='Voice description (natural language)')
    parser.add_argument('--chunk-size', type=int, default=100,
                        help='Words per chunk (recommended: 80-100) or characters if >500')
    parser.add_argument('--gap', type=float, default=0.3,
                        help='Gap between chunks in seconds')
    parser.add_argument('--workers', type=int, default=1,
                        help='Number of worker threads (default: 1 for easier debugging)')
    parser.add_argument('--output', type=str, default='output/test',
                        help='Output file prefix (without extension)')
    parser.add_argument('--cover', type=str, default='assets/cover.jpg',
                        help='Cover image for video')
    parser.add_argument('--temp', type=float, default=0.4,
                        help='Temperature for generation (0.3-0.5 recommended)')
    parser.add_argument('--top-p', type=float, default=0.9,
                        help='Top-p for generation (0.9 recommended)')
    parser.add_argument('--max-tokens', type=int, default=3000,
                        help='Max tokens to generate per chunk (2000-4000 recommended)')
    parser.add_argument('--ctx', type=int, default=4096,
                        help='Context size')
    parser.add_argument('--gpu-layers', type=int, default=-1,
                        help='GPU layers (-1 for all)')

    args = parser.parse_args()

    # Import here to catch import errors early
    print("Importing pipeline modules...")
    try:
        from core.pipeline import run_pipeline
    except Exception as e:
        print(f"ERROR: Failed to import pipeline: {e}")
        sys.exit(1)

    # Check if model exists
    if not os.path.exists(args.model):
        print(f"ERROR: Model not found at {args.model}")
        print("Please download the Maya1 GGUF model or specify correct path with --model")
        sys.exit(1)

    # Create output directory
    output_dir = os.path.dirname(args.output) or 'output'
    os.makedirs(output_dir, exist_ok=True)

    out_wav = f"{args.output}.wav"
    out_mp4 = f"{args.output}.mp4"

    print("\n" + "="*60)
    print("MayaBook CLI Test")
    print("="*60)
    print(f"Text: {args.text[:50]}...")
    print(f"Model: {args.model}")
    print(f"Voice: {args.voice}")
    print(f"Workers: {args.workers}")
    print(f"Output: {out_wav}, {out_mp4}")
    print("="*60 + "\n")

    def progress_callback(completed, total):
        percent = (completed / total) * 100
        print(f"Progress: {completed}/{total} chunks ({percent:.1f}%)")

    try:
        print("Starting pipeline...")
        wav_path, mp4_path = run_pipeline(
            epub_text=args.text,
            model_path=args.model,
            voice_desc=args.voice,
            chunk_size=args.chunk_size,
            gap_s=args.gap,
            out_wav=out_wav,
            out_mp4=out_mp4,
            cover_image=args.cover,
            temperature=args.temp,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            n_ctx=args.ctx,
            n_gpu_layers=args.gpu_layers,
            workers=args.workers,
            progress_cb=progress_callback,
        )

        print("\n" + "="*60)
        print("SUCCESS!")
        print("="*60)
        print(f"Audio: {wav_path}")
        print(f"Video: {mp4_path}")
        print("="*60)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print("\n" + "="*60)
        print("ERROR!")
        print("="*60)
        print(f"Exception: {type(e).__name__}: {e}")
        print("="*60)
        print("\nCheck the log file for detailed error information.")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
