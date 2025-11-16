"""
Test script to compare different TTS settings
Generates 15 variations of the same 2-sentence text with different parameters
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.tts_maya1_local import synthesize_chunk_local
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Test text with emotion tag
TEST_TEXT = "The forest was eerily quiet. <whisper>Something was watching from the shadows.</whisper>"

# Voice description
VOICE_DESC = "A mature female voice, clear and expressive, with good pacing"

# Model path - adjust if needed
MODEL_PATH = r"assets\models\maya1.i1-Q5_K_M.gguf"

# Output directory
OUTPUT_DIR = Path("output/settings_sweep")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Define 15 parameter combinations
# Varying temperature and top_p
PARAM_SETS = [
    # Low temperature variations
    {"temp": 0.30, "top_p": 0.85},
    {"temp": 0.35, "top_p": 0.87},
    {"temp": 0.40, "top_p": 0.89},

    # Medium-low temperature
    {"temp": 0.45, "top_p": 0.90},
    {"temp": 0.45, "top_p": 0.92},
    {"temp": 0.50, "top_p": 0.91},

    # Medium temperature
    {"temp": 0.55, "top_p": 0.92},
    {"temp": 0.60, "top_p": 0.93},
    {"temp": 0.65, "top_p": 0.94},

    # Medium-high temperature
    {"temp": 0.70, "top_p": 0.94},
    {"temp": 0.75, "top_p": 0.95},
    {"temp": 0.80, "top_p": 0.95},

    # High temperature variations
    {"temp": 0.85, "top_p": 0.96},
    {"temp": 0.90, "top_p": 0.96},
    {"temp": 0.95, "top_p": 0.97},
]

def main():
    print("=" * 80)
    print("TTS SETTINGS SWEEP TEST")
    print("=" * 80)
    print(f"\nTest text: {TEST_TEXT}")
    print(f"Voice: {VOICE_DESC}")
    print(f"Model: {MODEL_PATH}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"\nGenerating {len(PARAM_SETS)} variations...\n")

    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model file not found at {MODEL_PATH}")
        print("Please update MODEL_PATH in the script to point to your GGUF model")
        return

    results = []

    for i, params in enumerate(PARAM_SETS, 1):
        temp = params["temp"]
        top_p = params["top_p"]

        # Generate filename based on settings
        filename = f"test_temp{temp:.2f}_topp{top_p:.2f}.wav"
        output_path = OUTPUT_DIR / filename

        print(f"[{i}/{len(PARAM_SETS)}] Generating: {filename}")
        print(f"    Settings: temp={temp}, top_p={top_p}")

        try:
            # Generate audio
            wav_path = synthesize_chunk_local(
                model_path=MODEL_PATH,
                text=TEST_TEXT,
                voice_description=VOICE_DESC,
                temperature=temp,
                top_p=top_p,
                max_tokens=2500,
                n_gpu_layers=-1  # Use GPU if available
            )

            # Move to output directory with descriptive name
            if wav_path and os.path.exists(wav_path):
                import shutil
                shutil.move(wav_path, str(output_path))

                # Get file size
                size_kb = os.path.getsize(output_path) / 1024

                print(f"    [OK] Success! Size: {size_kb:.1f} KB")
                results.append({
                    "filename": filename,
                    "params": params,
                    "success": True,
                    "size_kb": size_kb
                })
            else:
                print(f"    [FAIL] Failed - no output generated")
                results.append({
                    "filename": filename,
                    "params": params,
                    "success": False
                })

        except Exception as e:
            print(f"    [ERROR] {e}")
            results.append({
                "filename": filename,
                "params": params,
                "success": False,
                "error": str(e)
            })

        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"\nTotal: {len(results)} generations")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    if successful:
        print(f"\n[OK] Generated files saved to: {OUTPUT_DIR.absolute()}")
        print("\nSuccessful generations:")
        for r in successful:
            p = r["params"]
            print(f"  - {r['filename']} ({r['size_kb']:.1f} KB)")
            print(f"    temp={p['temp']}, top_p={p['top_p']}")

    if failed:
        print("\n[FAIL] Failed generations:")
        for r in failed:
            print(f"  - {r['filename']}")
            if "error" in r:
                print(f"    Error: {r['error']}")

    print("\n" + "=" * 80)
    print("Test complete! Listen to the files to compare settings.")
    print("=" * 80)

if __name__ == "__main__":
    main()
