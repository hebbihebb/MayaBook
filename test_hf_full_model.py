#!/usr/bin/env python3
"""
Quick smoke test for the full-precision Maya1 HuggingFace model.
Defaults target the freshly downloaded safetensor split in assets/models/maya1_full.
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

# Ensure imports work when invoked from repo root
sys.path.insert(0, str(Path(__file__).parent))

from core.tts_maya1_hf import synthesize_chunk_hf


def diagnose_audio(audio_path: Path) -> dict:
    """Lightweight audio health check."""
    try:
        audio, sr = sf.read(audio_path)
        if audio.ndim > 1:
            audio = audio[:, 0]

        rms = float(np.sqrt(np.mean(audio ** 2)))
        duration = len(audio) / sr
        peak = float(np.max(np.abs(audio)))

        return {
            "success": True,
            "sample_rate": sr,
            "samples": len(audio),
            "duration_seconds": duration,
            "rms": rms,
            "peak": peak,
            "is_silent": rms < 1e-3,
            "is_clipping": peak >= 0.99,
        }
    except Exception as exc:  # pragma: no cover - diagnostic helper
        return {"success": False, "error": str(exc)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke test for the full Maya1 safetensor model (HF backend)."
    )
    parser.add_argument(
        "--model",
        default="assets/models/maya1_full",
        help="Path to the full Maya1 HF model directory (config.json, model-*.safetensors).",
    )
    parser.add_argument(
        "--text",
        default=(
            "<curious> Maya is a multilingual voice model built for natural, expressive narration. "
            "<excited> This is a quick test of the full-precision weights, making sure the sentence completes."
        ),
        help="Text to synthesize.",
    )
    parser.add_argument(
        "--voice",
        default="A warm, balanced narrator with clear diction.",
        help="Natural language voice description.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.4,
        help="Sampling temperature.",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=0.9,
        help="Top-p sampling.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=800,
        help="Maximum tokens to generate. If --chunk-size is provided, it overrides this value.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=0,
        help="Optional alias for max tokens to match other test scripts.",
    )
    parser.add_argument(
        "--trim-samples",
        type=int,
        default=512,
        help="Samples to trim from the start of the decoded audio (set to 0 to disable).",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to place the synthesized WAV.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("test_hf_full_model")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target_path = output_dir / "maya1_full_test.wav"

    max_tokens = args.chunk_size or args.max_tokens

    logger.info("=" * 70)
    logger.info("Maya1 full-precision HF smoke test")
    logger.info("=" * 70)
    logger.info("Model directory: %s", args.model)
    logger.info("Output file: %s", target_path)
    logger.info(
        "Params: temp=%.2f top_p=%.2f max_tokens=%d trim_samples=%d",
        args.temperature,
        args.top_p,
        max_tokens,
        args.trim_samples,
    )

    try:
        tmp_path = synthesize_chunk_hf(
            model_path=args.model,
            text=args.text,
            voice_description=args.voice,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=max_tokens,
            trim_samples=args.trim_samples if args.trim_samples > 0 else None,
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(tmp_path, target_path)
    except Exception as exc:  # pragma: no cover - manual test harness
        logger.error("Synthesis failed: %s", exc)
        return 1

    diag = diagnose_audio(target_path)
    if not diag.get("success"):
        logger.error("Audio diagnostics failed: %s", diag.get("error", "unknown"))
        return 1

    logger.info("✅ Synthesis OK")
    logger.info(
        "Duration: %.2fs | RMS: %.6f | Peak: %.6f | Silent: %s | Clipping: %s",
        diag["duration_seconds"],
        diag["rms"],
        diag["peak"],
        diag["is_silent"],
        diag["is_clipping"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
