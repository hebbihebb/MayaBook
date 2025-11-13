# core/gpu_utils.py
"""
GPU detection and VRAM management utilities
"""
import logging
import subprocess
import re
from pathlib import Path
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

def get_gpu_info() -> Dict[str, any]:
    """
    Detect GPU information including VRAM availability

    Returns:
        dict: {
            'available': bool,
            'name': str,
            'vram_total_mb': int,
            'vram_free_mb': int,
            'vram_used_mb': int,
            'driver_version': str,
            'cuda_available': bool,
        }
    """
    gpu_info = {
        'available': False,
        'name': 'N/A',
        'vram_total_mb': 0,
        'vram_free_mb': 0,
        'vram_used_mb': 0,
        'driver_version': 'N/A',
        'cuda_available': False,
    }

    # Try torch first if available
    try:
        import torch
        if torch.cuda.is_available():
            gpu_info['cuda_available'] = True
            gpu_info['available'] = True

            # Get GPU properties
            props = torch.cuda.get_device_properties(0)
            gpu_info['name'] = props.name
            gpu_info['vram_total_mb'] = props.total_memory // (1024 * 1024)

            # Get current memory usage
            mem_allocated = torch.cuda.memory_allocated(0) // (1024 * 1024)
            mem_reserved = torch.cuda.memory_reserved(0) // (1024 * 1024)
            gpu_info['vram_used_mb'] = mem_reserved
            gpu_info['vram_free_mb'] = gpu_info['vram_total_mb'] - mem_reserved

            logger.info(f"GPU detected via torch: {gpu_info['name']}")
            logger.info(f"VRAM: {gpu_info['vram_total_mb']} MB total, {gpu_info['vram_free_mb']} MB free")
            return gpu_info
    except ImportError:
        logger.debug("torch not available, trying nvidia-smi")
    except Exception as e:
        logger.warning(f"Error detecting GPU via torch: {e}")

    # Fallback to nvidia-smi
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.total,memory.free,memory.used,driver_version',
             '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            line = result.stdout.strip().split('\n')[0]  # Get first GPU
            parts = [p.strip() for p in line.split(',')]

            if len(parts) >= 4:
                gpu_info['available'] = True
                gpu_info['name'] = parts[0]
                gpu_info['vram_total_mb'] = int(float(parts[1]))
                gpu_info['vram_free_mb'] = int(float(parts[2]))
                gpu_info['vram_used_mb'] = int(float(parts[3]))
                if len(parts) >= 5:
                    gpu_info['driver_version'] = parts[4]

                logger.info(f"GPU detected via nvidia-smi: {gpu_info['name']}")
                logger.info(f"VRAM: {gpu_info['vram_total_mb']} MB total, {gpu_info['vram_free_mb']} MB free")
                return gpu_info
    except FileNotFoundError:
        logger.debug("nvidia-smi not found")
    except Exception as e:
        logger.warning(f"Error running nvidia-smi: {e}")

    logger.info("No GPU detected")
    return gpu_info


def get_model_size_mb(model_path: str) -> int:
    """
    Get approximate size of GGUF model file in MB

    Args:
        model_path: Path to model file

    Returns:
        Size in MB, or 0 if file not found
    """
    try:
        path = Path(model_path)
        if path.exists() and path.is_file():
            size_mb = path.stat().st_size // (1024 * 1024)
            logger.debug(f"Model size: {size_mb} MB")
            return size_mb
    except Exception as e:
        logger.warning(f"Error getting model size: {e}")
    return 0


def calculate_optimal_gpu_layers(vram_free_mb: int, model_size_mb: int, safety_margin_mb: int = 2048) -> Tuple[int, str]:
    """
    Calculate optimal n_gpu_layers based on available VRAM and model size

    Args:
        vram_free_mb: Free VRAM in MB
        model_size_mb: Model file size in MB
        safety_margin_mb: Safety margin to leave free (default 2GB)

    Returns:
        Tuple of (recommended_layers, explanation_text)
    """
    # Heuristic: GGUF models typically have 32-40 layers
    # Each layer uses roughly model_size / 32 MB of VRAM
    # Add overhead for context buffer (~1-2GB depending on n_ctx)

    # Account for overhead
    overhead_mb = 1024  # Base overhead for inference
    available_for_model = vram_free_mb - safety_margin_mb - overhead_mb

    if available_for_model <= 0:
        return (0, f"Insufficient VRAM. Only {vram_free_mb} MB free. Recommend CPU mode.")

    if model_size_mb == 0:
        # Can't determine model size, use conservative estimate
        if vram_free_mb < 4096:
            return (10, "Model size unknown. Conservative estimate: 10 layers (low VRAM)")
        elif vram_free_mb < 8192:
            return (20, "Model size unknown. Conservative estimate: 20 layers")
        else:
            return (-1, "Model size unknown. Sufficient VRAM for all layers")

    # If we have room for full model + overhead + margin, use all layers
    if available_for_model >= model_size_mb:
        return (-1, f"Sufficient VRAM ({vram_free_mb} MB free) for all layers. Using GPU fully.")

    # Otherwise, calculate partial offload
    # Assume 32 layers total (typical for llama-style models)
    estimated_layers = 32
    layer_size_mb = model_size_mb / estimated_layers
    layers_that_fit = int(available_for_model / layer_size_mb)

    # Clamp to reasonable range
    layers_that_fit = max(0, min(layers_that_fit, estimated_layers))

    explanation = (
        f"Partial GPU offload: {layers_that_fit} layers "
        f"({vram_free_mb} MB free, {model_size_mb} MB model, {safety_margin_mb} MB margin)"
    )

    return (layers_that_fit, explanation)


def get_current_vram_usage() -> Dict[str, int]:
    """
    Get current VRAM usage (useful for monitoring during synthesis)

    Returns:
        dict: {'used_mb': int, 'free_mb': int, 'total_mb': int}
    """
    try:
        import torch
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated(0) // (1024 * 1024)
            reserved = torch.cuda.memory_reserved(0) // (1024 * 1024)
            props = torch.cuda.get_device_properties(0)
            total = props.total_memory // (1024 * 1024)
            return {
                'used_mb': reserved,
                'free_mb': total - reserved,
                'total_mb': total,
            }
    except Exception as e:
        logger.debug(f"Could not get VRAM usage via torch: {e}")

    # Fallback to nvidia-smi
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.used,memory.free,memory.total',
             '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=2
        )

        if result.returncode == 0:
            line = result.stdout.strip().split('\n')[0]
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 3:
                return {
                    'used_mb': int(float(parts[0])),
                    'free_mb': int(float(parts[1])),
                    'total_mb': int(float(parts[2])),
                }
    except Exception as e:
        logger.debug(f"Could not get VRAM usage via nvidia-smi: {e}")

    return {'used_mb': 0, 'free_mb': 0, 'total_mb': 0}


def get_recommended_gguf_settings(model_path: str) -> Dict[str, any]:
    """
    Get recommended GGUF settings based on GPU and model

    Args:
        model_path: Path to GGUF model file

    Returns:
        dict: {
            'n_gpu_layers': int,
            'n_ctx': int,
            'explanation': str,
            'warnings': list[str],
        }
    """
    gpu_info = get_gpu_info()
    model_size_mb = get_model_size_mb(model_path)

    warnings = []

    if not gpu_info['available']:
        warnings.append("No GPU detected. CPU inference will be very slow.")
        return {
            'n_gpu_layers': 0,
            'n_ctx': 2048,  # Lower context for CPU
            'explanation': "CPU mode (no GPU detected)",
            'warnings': warnings,
        }

    # Calculate optimal layers
    layers, explanation = calculate_optimal_gpu_layers(
        gpu_info['vram_free_mb'],
        model_size_mb,
        safety_margin_mb=2048
    )

    # Determine context size based on VRAM
    if gpu_info['vram_free_mb'] < 6144:  # Less than 6GB
        n_ctx = 2048
        warnings.append("Limited VRAM. Reduced context size to 2048.")
    elif gpu_info['vram_free_mb'] < 10240:  # Less than 10GB
        n_ctx = 4096
    else:
        n_ctx = 8192

    # Warn if VRAM is very low
    if gpu_info['vram_free_mb'] < 4096:
        warnings.append(
            f"Very low VRAM ({gpu_info['vram_free_mb']} MB free). "
            "Consider closing other GPU applications or using CPU mode."
        )

    return {
        'n_gpu_layers': layers,
        'n_ctx': n_ctx,
        'explanation': explanation,
        'warnings': warnings,
    }


def format_vram_info(vram_mb: int) -> str:
    """Format VRAM amount as human-readable string"""
    if vram_mb >= 1024:
        return f"{vram_mb / 1024:.1f} GB"
    return f"{vram_mb} MB"
