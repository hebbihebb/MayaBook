#!/usr/bin/env python3
"""
GGUF VRAM Optimization Diagnostic Tool

This script implements the performance report's "Sweet Spot Algorithm":
1. Test different n_gpu_layers values
2. Monitor VRAM usage and generation speed
3. Find the optimal balance between GPU offloading and KV cache headroom

Key insight: Setting n_gpu_layers too high leaves no room for KV cache,
forcing it into slow system RAM and killing performance.
"""
import sys
import logging
import time
import psutil
import torch
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.tts_maya1_local import synthesize_chunk_local

def get_gpu_memory_usage():
    """Get current GPU memory usage in GB"""
    if not torch.cuda.is_available():
        return None, None

    allocated = torch.cuda.memory_allocated() / 1024**3
    reserved = torch.cuda.memory_reserved() / 1024**3
    return allocated, reserved

def get_total_gpu_memory():
    """Get total GPU memory in GB"""
    if not torch.cuda.is_available():
        return None
    return torch.cuda.get_device_properties(0).total_memory / 1024**3

def benchmark_n_gpu_layers(model_path: str, n_gpu_layers_values: list):
    """Test different n_gpu_layers values and measure performance"""

    # Test text and parameters
    test_text = "The forest was eerily quiet."
    voice_desc = "A calm, soothing female voice."

    logger.info("=" * 70)
    logger.info("GGUF VRAM Optimization Benchmark")
    logger.info("=" * 70)

    total_vram = get_total_gpu_memory()
    logger.info(f"Total GPU Memory: {total_vram:.2f} GB")
    logger.info(f"Test text: '{test_text}' ({len(test_text)} chars)")
    logger.info("")

    results = []

    for n_gpu_layers in n_gpu_layers_values:
        logger.info(f"Testing n_gpu_layers={n_gpu_layers}...")

        # Clear VRAM before test
        torch.cuda.empty_cache()

        try:
            start_time = time.time()

            output_path = synthesize_chunk_local(
                model_path=model_path,
                text=test_text,
                voice_description=voice_desc,
                temperature=0.45,
                top_p=0.92,
                max_tokens=2500,
                n_ctx=4096,
                n_gpu_layers=n_gpu_layers,
            )

            elapsed = time.time() - start_time
            allocated, reserved = get_gpu_memory_usage()

            logger.info(f"  ✅ SUCCESS")
            logger.info(f"     Generation time: {elapsed:.2f}s")
            logger.info(f"     VRAM allocated: {allocated:.2f} GB")
            logger.info(f"     VRAM reserved: {reserved:.2f} GB")
            logger.info(f"     VRAM headroom: {total_vram - reserved:.2f} GB")
            logger.info(f"     Output: {output_path}")

            results.append({
                'n_gpu_layers': n_gpu_layers,
                'time_seconds': elapsed,
                'vram_allocated_gb': allocated,
                'vram_reserved_gb': reserved,
                'vram_headroom_gb': total_vram - reserved,
                'status': 'success',
            })

        except Exception as e:
            logger.error(f"  ❌ FAILED: {str(e)}")
            results.append({
                'n_gpu_layers': n_gpu_layers,
                'status': 'failed',
                'error': str(e),
            })

        logger.info("")

    # Analysis
    logger.info("=" * 70)
    logger.info("ANALYSIS & RECOMMENDATIONS")
    logger.info("=" * 70)

    successful = [r for r in results if r['status'] == 'success']

    if not successful:
        logger.warning("No successful tests. Check model path and VRAM.")
        return results

    # Find fastest
    fastest = min(successful, key=lambda r: r['time_seconds'])
    logger.info(f"\nFastest: n_gpu_layers={fastest['n_gpu_layers']} ({fastest['time_seconds']:.2f}s)")

    # Find best headroom (1-1.5GB recommended)
    target_min = 1.0
    target_max = 1.5
    good_headroom = [
        r for r in successful
        if target_min <= r['vram_headroom_gb'] <= target_max
    ]

    if good_headroom:
        best = good_headroom[0]
        logger.info(f"\nOptimal (good KV cache headroom): n_gpu_layers={best['n_gpu_layers']}")
        logger.info(f"  Generation time: {best['time_seconds']:.2f}s")
        logger.info(f"  VRAM headroom: {best['vram_headroom_gb']:.2f} GB (target: 1.0-1.5 GB)")
    else:
        logger.warning(f"\nNo configuration found with ideal headroom (1.0-1.5 GB)")
        logger.warning("Closest match:")
        by_headroom = sorted(successful,
                            key=lambda r: abs(r['vram_headroom_gb'] - 1.25))
        best = by_headroom[0]
        logger.info(f"  n_gpu_layers={best['n_gpu_layers']}")
        logger.info(f"  VRAM headroom: {best['vram_headroom_gb']:.2f} GB")

    # Performance summary table
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY TABLE")
    logger.info("=" * 70)
    logger.info(f"{'n_gpu_layers':<15} {'Time (s)':<12} {'Headroom (GB)':<15} {'Status':<10}")
    logger.info("-" * 70)

    for r in sorted(results, key=lambda x: x.get('n_gpu_layers', 999)):
        if r['status'] == 'success':
            logger.info(
                f"{r['n_gpu_layers']:<15} "
                f"{r['time_seconds']:<12.2f} "
                f"{r['vram_headroom_gb']:<15.2f} "
                f"{'✅':<10}"
            )
        else:
            logger.info(
                f"{r['n_gpu_layers']:<15} "
                f"{'N/A':<12} "
                f"{'N/A':<15} "
                f"{'❌':<10}"
            )

    return results

def main():
    model_path = "assets/models/maya1.i1-Q4_K_M.gguf"

    # Test range: Q4_K_M for 13B model has ~43 layers
    # Start low and incrementally increase
    n_gpu_layers_values = [0, 10, 15, 20, 25, 30, 35, 40, -1]

    logger.info("Testing GGUF model n_gpu_layers optimization...")
    logger.info(f"Model: {model_path}")
    logger.info(f"Testing layers: {n_gpu_layers_values}")
    logger.info("")

    results = benchmark_n_gpu_layers(model_path, n_gpu_layers_values)

    logger.info("\n" + "=" * 70)
    logger.info("NEXT STEPS")
    logger.info("=" * 70)
    logger.info("1. Review the summary table above")
    logger.info("2. Look for the sweet spot with:")
    logger.info("   - Good generation speed (close to fastest)")
    logger.info("   - Adequate VRAM headroom (1.0-1.5 GB)")
    logger.info("3. Update tts_maya1_local.py default from n_gpu_layers=-1")
    logger.info("4. Update UI default in main_window.py")

    return 0

if __name__ == "__main__":
    sys.exit(main())
