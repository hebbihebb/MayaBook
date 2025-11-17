#!/usr/bin/env python3
"""
vLLM GGUF Test
Tests vLLM with GGUF model (Q5_K_M) using external tokenizer
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.tts_maya1_vllm import synthesize_chunk_vllm
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Test text with emotion tag - corrected format (single tag)
TEST_TEXT = "The forest was eerily quiet. <whisper> Something was watching from the shadows."

# Voice description
VOICE_DESC = "A mature female voice, clear and expressive, with good pacing"

# Model paths
GGUF_MODEL_PATH = "assets/models/maya1.i1-Q5_K_M.gguf"
TOKENIZER_PATH = "assets/models/maya1_4bit_safetensor"  # Use HF tokenizer

# Output directory
OUTPUT_DIR = Path("output/vllm_gguf_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Test with just a few samples to avoid OOM
PARAM_SETS = [
    {"temp": 0.40, "top_p": 0.89, "gpu_mem": 0.6},  # Conservative memory
    {"temp": 0.45, "top_p": 0.92, "gpu_mem": 0.6},
    {"temp": 0.50, "top_p": 0.91, "gpu_mem": 0.6},
]

def main():
    print("=" * 80)
    print("vLLM GGUF TEST (RTX 2070)")
    print("=" * 80)
    print(f"\nTest text: {TEST_TEXT}")
    print(f"Voice: {VOICE_DESC}")
    print(f"GGUF Model: {GGUF_MODEL_PATH}")
    print(f"Tokenizer: {TOKENIZER_PATH}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"\nTesting {len(PARAM_SETS)} samples with conservative memory settings...\n")
    print("NOTE: Using gpu_memory_utilization=0.6 to avoid OOM on 7.6GB GPU")
    print("=" * 80)
    print()

    if not os.path.exists(GGUF_MODEL_PATH):
        print(f"ERROR: GGUF model not found at {GGUF_MODEL_PATH}")
        return

    if not os.path.exists(TOKENIZER_PATH):
        print(f"ERROR: Tokenizer directory not found at {TOKENIZER_PATH}")
        return

    results = []
    total_start = time.time()

    for i, params in enumerate(PARAM_SETS, 1):
        temp = params["temp"]
        top_p = params["top_p"]
        gpu_mem = params["gpu_mem"]

        # Generate filename based on settings
        filename = f"vllm_gguf_temp{temp:.2f}_topp{top_p:.2f}.wav"
        output_path = OUTPUT_DIR / filename

        print(f"[{i}/{len(PARAM_SETS)}] Generating: {filename}")
        print(f"    Settings: temp={temp}, top_p={top_p}, gpu_mem={gpu_mem}")

        start_time = time.time()

        try:
            # Generate audio using vLLM with GGUF
            wav_path = synthesize_chunk_vllm(
                text=TEST_TEXT,
                voice_description=VOICE_DESC,
                model_path=GGUF_MODEL_PATH,
                tokenizer_path=TOKENIZER_PATH,  # External tokenizer for GGUF
                temperature=temp,
                top_p=top_p,
                max_tokens=2500,
                gpu_memory_utilization=gpu_mem  # Conservative setting
            )

            elapsed = time.time() - start_time

            # Move to output directory with descriptive name
            if wav_path and os.path.exists(wav_path):
                import shutil
                shutil.move(wav_path, str(output_path))

                # Get file size
                size_kb = os.path.getsize(output_path) / 1024

                print(f"    [OK] Success! ({elapsed:.2f}s, {size_kb:.1f} KB)")
                results.append({
                    "filename": filename,
                    "params": params,
                    "success": True,
                    "size_kb": size_kb,
                    "time": elapsed
                })
            else:
                elapsed = time.time() - start_time
                print(f"    [FAIL] Failed - no output generated ({elapsed:.2f}s)")
                results.append({
                    "filename": filename,
                    "params": params,
                    "success": False,
                    "time": elapsed
                })

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"    [ERROR] {e} ({elapsed:.2f}s)")
            import traceback
            traceback.print_exc()
            results.append({
                "filename": filename,
                "params": params,
                "success": False,
                "error": str(e),
                "time": elapsed
            })

        print()

    total_elapsed = time.time() - total_start

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"\nTotal: {len(results)} generations")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Total time: {total_elapsed:.2f}s")

    if successful:
        avg_time = sum(r["time"] for r in successful) / len(successful)
        avg_size = sum(r["size_kb"] for r in successful) / len(successful)
        print(f"Average time per sample: {avg_time:.2f}s")
        print(f"Average file size: {avg_size:.1f} KB")
        print(f"\n[OK] Generated files saved to: {OUTPUT_DIR.absolute()}")
        print("\nSuccessful generations:")
        for r in successful:
            p = r["params"]
            print(f"  - {r['filename']} ({r['size_kb']:.1f} KB, {r['time']:.2f}s)")
            print(f"    temp={p['temp']}, top_p={p['top_p']}, gpu_mem={p['gpu_mem']}")

    if failed:
        print("\n[FAIL] Failed generations:")
        for r in failed:
            print(f"  - {r['filename']}")
            if "error" in r:
                print(f"    Error: {r['error'][:200]}...")  # Truncate long errors

    print("\n" + "=" * 80)
    if successful:
        print("✅ vLLM GGUF test completed successfully!")
        print("The GGUF model works with vLLM on RTX 2070 (with reduced gpu_memory_utilization)")
    else:
        print("❌ vLLM GGUF test failed on RTX 2070")
        print("The 7.6GB VRAM may be insufficient even with GGUF model")
    print("=" * 80)

if __name__ == "__main__":
    main()
