"""
Utility functions for MayaBook.

Provides cross-platform file handling, sanitization, and cache management.
"""

import os
import re
import platform
from pathlib import Path


def sanitize_name_for_os(name: str, is_folder: bool = True) -> str:
    """
    Sanitize a filename or folder name based on the operating system.

    Adapted from abogen project for cross-platform compatibility.

    Args:
        name: The name to sanitize
        is_folder: Whether this is a folder name (default: True)

    Returns:
        Sanitized name safe for the current OS
    """
    if not name:
        return "audiobook"

    system = platform.system()

    if system == "Windows":
        # Windows illegal characters: < > : " / \ | ? *
        # Also can't end with space or dot
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
        # Remove control characters (0-31)
        sanitized = re.sub(r"[\x00-\x1f]", "_", sanitized)
        # Remove trailing spaces and dots
        sanitized = sanitized.rstrip(". ")
        # Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
        reserved = (
            ["CON", "PRN", "AUX", "NUL"]
            + [f"COM{i}" for i in range(1, 10)]
            + [f"LPT{i}" for i in range(1, 10)]
        )
        if sanitized.upper() in reserved or sanitized.upper().split(".")[0] in reserved:
            sanitized = f"_{sanitized}"
    elif system == "Darwin":  # macOS
        # macOS illegal characters: : (colon is converted to / by the system)
        # Also can't start with dot (hidden file) for folders typically
        sanitized = re.sub(r"[:]", "_", name)
        # Remove control characters
        sanitized = re.sub(r"[\x00-\x1f]", "_", sanitized)
        # Avoid leading dot for folders (creates hidden folders)
        if is_folder and sanitized.startswith("."):
            sanitized = "_" + sanitized[1:]
    else:  # Linux and others
        # Linux illegal characters: / and null character
        # Though / is illegal, most other chars are technically allowed
        sanitized = re.sub(r"[/\x00]", "_", name)
        # Remove other control characters for safety
        sanitized = re.sub(r"[\x01-\x1f]", "_", sanitized)
        # Avoid leading dot for folders (creates hidden folders)
        if is_folder and sanitized.startswith("."):
            sanitized = "_" + sanitized[1:]

    # Ensure the name is not empty after sanitization
    if not sanitized or sanitized.strip() == "":
        sanitized = "audiobook"

    # Limit length to 255 characters (common limit across filesystems)
    if len(sanitized) > 255:
        sanitized = sanitized[:255].rstrip(". ")

    return sanitized


def sanitize_chapter_name(chapter_name: str, max_length: int = 80) -> str:
    """
    Sanitize a chapter name for use in filenames.

    More aggressive than sanitize_name_for_os - only keeps alphanumeric,
    spaces, hyphens, and underscores. Suitable for chapter file naming.

    Args:
        chapter_name: The chapter name to sanitize
        max_length: Maximum length of the resulting name (default: 80)

    Returns:
        Sanitized chapter name safe for filenames
    """
    # First pass: keep alphanumeric, spaces, hyphens, and underscores
    sanitized = re.sub(r"[^\w\s\-]", "", chapter_name)
    # Replace multiple spaces/hyphens with single underscore
    sanitized = re.sub(r"[\s\-]+", "_", sanitized).strip("_")
    # Apply OS-specific sanitization
    sanitized = sanitize_name_for_os(sanitized, is_folder=False)

    # Limit length (leaving room for chapter number prefix)
    if len(sanitized) > max_length:
        # Try to break at underscore for readability
        pos = sanitized[:max_length].rfind("_")
        sanitized = sanitized[:pos if pos > 0 else max_length].rstrip("_")

    # Fallback if empty
    if not sanitized:
        sanitized = "chapter"

    return sanitized


def get_cache_path(subdir: str = "") -> Path:
    """
    Get platform-appropriate cache directory for MayaBook.

    Args:
        subdir: Optional subdirectory within cache (e.g., "voice_previews")

    Returns:
        Path to cache directory
    """
    try:
        from platformdirs import user_cache_path
        cache_dir = user_cache_path("mayabook")
    except ImportError:
        # Fallback if platformdirs not available
        if platform.system() == "Windows":
            cache_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "mayabook" / "cache"
        elif platform.system() == "Darwin":
            cache_dir = Path.home() / "Library" / "Caches" / "mayabook"
        else:  # Linux
            cache_dir = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "mayabook"

    if subdir:
        cache_dir = cache_dir / subdir

    # Create directory if it doesn't exist
    cache_dir.mkdir(parents=True, exist_ok=True)

    return cache_dir


def find_unique_path(base_path: str, extension: str = "", avoid_extensions: list = None) -> tuple[str, str]:
    """
    Find a unique file/folder path by adding numeric suffix if needed.

    Args:
        base_path: Base path without extension
        extension: File extension (include dot, e.g., ".m4b")
        avoid_extensions: List of extensions to check for conflicts (e.g., [".m4b", ".mp4", ".wav"])

    Returns:
        Tuple of (unique_path_with_extension, suffix_used)

    Example:
        find_unique_path("/output/book", ".m4b", [".m4b", ".mp4"])
        -> ("/output/book.m4b", "") or ("/output/book_2.m4b", "_2")
    """
    if avoid_extensions is None:
        avoid_extensions = [extension]

    parent_dir = os.path.dirname(base_path)
    base_name = os.path.basename(base_path)

    counter = 1
    while True:
        suffix = f"_{counter}" if counter > 1 else ""
        candidate_base = os.path.join(parent_dir, f"{base_name}{suffix}")

        # Check if path with target extension exists
        if extension:
            candidate_path = f"{candidate_base}{extension}"
            if not os.path.exists(candidate_path):
                # Also check for conflicts with other extensions
                has_conflict = False
                if os.path.exists(parent_dir):
                    for fname in os.listdir(parent_dir):
                        fname_base, fname_ext = os.path.splitext(fname)
                        if fname_base == f"{base_name}{suffix}" and fname_ext.lower() in [ext.lower() for ext in avoid_extensions]:
                            has_conflict = True
                            break

                if not has_conflict:
                    return candidate_path, suffix
        else:
            # For folders or no extension
            if not os.path.exists(candidate_base):
                return candidate_base, suffix

        counter += 1

        # Safety limit
        if counter > 1000:
            raise ValueError(f"Could not find unique path after 1000 attempts: {base_path}")


def format_time_hms(seconds: float) -> str:
    """
    Format seconds as HH:MM:SS string.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted time string (e.g., "01:23:45")
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_time_ms(seconds: float) -> str:
    """
    Format seconds as milliseconds (for FFMETADATA).

    Args:
        seconds: Time in seconds

    Returns:
        Milliseconds as integer string
    """
    return str(int(seconds * 1000))
