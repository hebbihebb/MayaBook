# core/voice_preview.py
"""
Voice preview generation and caching system for MayaBook.

Generates 30-second voice samples from presets and caches them to avoid
regenerating the same voice preview multiple times.
"""

import os
import hashlib
import logging
from pathlib import Path
from .tts_maya1_local import synthesize_chunk_local
from .voice_presets import PREVIEW_TEXT

logger = logging.getLogger(__name__)

# Cache directory for voice previews
CACHE_DIR = Path.home() / ".mayabook" / "voice_previews"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_cache_key(voice_description: str, model_path: str, temperature: float, top_p: float) -> str:
    """
    Generate a unique cache key based on voice description and synthesis parameters.

    Args:
        voice_description: The voice description text
        model_path: Path to the TTS model file
        temperature: Synthesis temperature parameter
        top_p: Synthesis top_p parameter

    Returns:
        MD5 hash string to use as cache key
    """
    # Include model filename (not full path) to handle model updates
    model_name = os.path.basename(model_path)

    # Create a unique string from all parameters that affect output
    cache_string = f"{voice_description}|{model_name}|{temperature:.3f}|{top_p:.3f}"

    # Generate MD5 hash
    return hashlib.md5(cache_string.encode('utf-8')).hexdigest()


def _get_cache_path(cache_key: str) -> Path:
    """Get the filesystem path for a cached preview file."""
    return CACHE_DIR / f"preview_{cache_key}.wav"


def is_preview_cached(voice_description: str, model_path: str, temperature: float = 0.45, top_p: float = 0.92) -> bool:
    """
    Check if a voice preview is already cached.

    Args:
        voice_description: The voice description text
        model_path: Path to the TTS model file
        temperature: Synthesis temperature parameter (default: 0.45)
        top_p: Synthesis top_p parameter (default: 0.92)

    Returns:
        True if cached preview exists, False otherwise
    """
    cache_key = _get_cache_key(voice_description, model_path, temperature, top_p)
    cache_path = _get_cache_path(cache_key)
    return cache_path.exists() and cache_path.stat().st_size > 0


def get_cached_preview_path(voice_description: str, model_path: str, temperature: float = 0.45, top_p: float = 0.92) -> str | None:
    """
    Get the path to a cached preview if it exists.

    Args:
        voice_description: The voice description text
        model_path: Path to the TTS model file
        temperature: Synthesis temperature parameter (default: 0.45)
        top_p: Synthesis top_p parameter (default: 0.92)

    Returns:
        Path to cached preview WAV file, or None if not cached
    """
    if is_preview_cached(voice_description, model_path, temperature, top_p):
        cache_key = _get_cache_key(voice_description, model_path, temperature, top_p)
        return str(_get_cache_path(cache_key))
    return None


def generate_voice_preview(
    voice_description: str,
    model_path: str,
    temperature: float = 0.45,
    top_p: float = 0.92,
    n_ctx: int = 4096,
    n_gpu_layers: int = -1,
    force_regenerate: bool = False,
) -> str:
    """
    Generate a voice preview sample (or retrieve from cache).

    Args:
        voice_description: The voice description text to synthesize
        model_path: Path to the TTS model file
        temperature: Synthesis temperature parameter (default: 0.45)
        top_p: Synthesis top_p parameter (default: 0.92)
        n_ctx: Model context window size (default: 4096)
        n_gpu_layers: Number of GPU layers to offload (default: -1 = all)
        force_regenerate: If True, bypass cache and regenerate (default: False)

    Returns:
        Path to the generated (or cached) preview WAV file

    Raises:
        RuntimeError: If synthesis fails
        FileNotFoundError: If model file doesn't exist
    """
    # Validate model exists
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    # Check cache first (unless force regenerate)
    cache_key = _get_cache_key(voice_description, model_path, temperature, top_p)
    cache_path = _get_cache_path(cache_key)

    if not force_regenerate and cache_path.exists():
        logger.info(f"Using cached voice preview: {cache_path}")
        return str(cache_path)

    # Generate new preview
    logger.info(f"Generating voice preview for: {voice_description[:60]}...")
    logger.debug(f"Preview text: {PREVIEW_TEXT[:100]}...")

    try:
        # Synthesize preview using the same TTS engine as main pipeline
        temp_wav = synthesize_chunk_local(
            model_path=model_path,
            text=PREVIEW_TEXT,
            voice_description=voice_description,
            temperature=temperature,
            top_p=top_p,
            max_tokens=2500,  # Preview text is ~70 words, should fit comfortably
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
        )

        # Move temp file to cache location
        import shutil
        shutil.move(temp_wav, cache_path)

        logger.info(f"Voice preview generated and cached: {cache_path}")
        return str(cache_path)

    except Exception as e:
        logger.error(f"Failed to generate voice preview: {e}")
        raise RuntimeError(f"Voice preview generation failed: {e}")


def clear_preview_cache():
    """
    Clear all cached voice previews.
    Useful for troubleshooting or freeing disk space.
    """
    if not CACHE_DIR.exists():
        logger.info("No preview cache directory to clear")
        return

    count = 0
    for preview_file in CACHE_DIR.glob("preview_*.wav"):
        try:
            preview_file.unlink()
            count += 1
        except Exception as e:
            logger.warning(f"Failed to delete {preview_file}: {e}")

    logger.info(f"Cleared {count} cached voice preview(s)")
    return count


def get_cache_size() -> tuple[int, int]:
    """
    Get information about the preview cache.

    Returns:
        Tuple of (file_count, total_size_bytes)
    """
    if not CACHE_DIR.exists():
        return 0, 0

    files = list(CACHE_DIR.glob("preview_*.wav"))
    total_size = sum(f.stat().st_size for f in files)

    return len(files), total_size
