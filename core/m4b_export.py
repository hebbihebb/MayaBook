"""
M4B/M4A audiobook export with chapter support.

Provides incremental FFmpeg streaming for memory-efficient audiobook generation
with embedded chapter markers and metadata.
"""

import os
import subprocess
import logging
from typing import List, Dict, Optional
from pathlib import Path


def create_m4b_stream(
    output_path: str,
    sample_rate: int = 24000,
    metadata: Optional[Dict[str, str]] = None,
) -> subprocess.Popen:
    """
    Create FFmpeg process for incremental M4B writing via stdin pipe.

    Args:
        output_path: Path to output M4B file
        sample_rate: Audio sample rate (default: 24000 Hz)
        metadata: Optional metadata dict (title, artist, album, year, genre, composer)

    Returns:
        FFmpeg subprocess.Popen object with stdin available for writing

    Example:
        proc = create_m4b_stream("output.m4b", metadata={"title": "My Book"})
        proc.stdin.write(audio_chunk.astype("float32").tobytes())
        proc.stdin.close()
        proc.wait()
    """
    # Build FFmpeg command
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output file
        "-thread_queue_size", "32768",  # Large buffer for smooth streaming
        "-f", "f32le",  # Input format: 32-bit float little-endian
        "-ar", str(sample_rate),  # Sample rate
        "-ac", "1",  # Mono audio
        "-i", "pipe:0",  # Read from stdin
        "-c:a", "aac",  # AAC codec
        "-q:a", "2",  # Quality level (2 = high quality, ~192 kbps)
        "-movflags", "+faststart+use_metadata_tags",  # Optimize for streaming playback
    ]

    # Add metadata if provided
    if metadata:
        cmd.extend(_build_metadata_options(metadata, output_path))

    cmd.append(output_path)

    # Log the command (sanitized)
    logging.info(f"Starting M4B stream: {output_path}")
    logging.debug(f"FFmpeg command: {' '.join(cmd[:10])}...")

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,  # Binary mode for audio data
        )
        return proc
    except FileNotFoundError:
        raise RuntimeError(
            "FFmpeg not found. Please install FFmpeg and ensure it's in your PATH.\n"
            "Download from: https://ffmpeg.org/download.html"
        )
    except Exception as e:
        raise RuntimeError(f"Failed to start FFmpeg process: {e}")


def write_chapter_metadata_file(
    chapters: List[Dict[str, any]],
    metadata_path: str,
) -> None:
    """
    Write FFMETADATA1 chapter file for embedding in M4B.

    Args:
        chapters: List of chapter dicts with 'chapter', 'start', 'end' keys
                  Times should be in seconds (float)
        metadata_path: Path to write metadata file

    Format:
        ;FFMETADATA1
        [CHAPTER]
        TIMEBASE=1/1000
        START=0
        END=120500
        title=Chapter 1: Introduction
    """
    logging.info(f"Writing chapter metadata to {metadata_path}")

    with open(metadata_path, "w", encoding="utf-8") as f:
        f.write(";FFMETADATA1\n")

        for chapter in chapters:
            chapter_name = chapter["chapter"]
            start_ms = int(chapter["start"] * 1000)
            end_ms = int(chapter["end"] * 1000)

            # Escape special characters in chapter title
            safe_title = chapter_name.replace("=", "\\=")

            f.write(f"\n[CHAPTER]\n")
            f.write(f"TIMEBASE=1/1000\n")
            f.write(f"START={start_ms}\n")
            f.write(f"END={end_ms}\n")
            f.write(f"title={safe_title}\n")

    logging.info(f"Wrote {len(chapters)} chapters to metadata file")


def add_chapters_to_m4b(
    m4b_path: str,
    chapters_metadata_path: str,
    metadata: Optional[Dict[str, str]] = None,
) -> None:
    """
    Remux M4B file with chapter metadata (no re-encoding, very fast).

    Args:
        m4b_path: Path to existing M4B file
        chapters_metadata_path: Path to FFMETADATA1 chapter file
        metadata: Optional metadata dict to preserve/update
    """
    logging.info(f"Adding chapters to M4B: {m4b_path}")

    # Create temporary output path
    root, ext = os.path.splitext(m4b_path)
    tmp_path = root + ".tmp" + ext

    # Build FFmpeg remux command
    cmd = [
        "ffmpeg",
        "-y",
        "-i", m4b_path,  # Input M4B
        "-i", chapters_metadata_path,  # Chapter metadata
        "-map", "0:a",  # Copy audio from input 0
        "-map_metadata", "1",  # Copy metadata from input 1
        "-map_chapters", "1",  # Copy chapters from input 1
        "-c:a", "copy",  # Don't re-encode (fast!)
    ]

    # Add metadata again to ensure preservation
    if metadata:
        cmd.extend(_build_metadata_options(metadata, None))

    cmd.append(tmp_path)

    logging.debug(f"Chapter remux command: {' '.join(cmd[:15])}...")

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg chapter remux failed:\n{result.stderr}")

        # Replace original with chapter-enhanced version
        os.replace(tmp_path, m4b_path)
        logging.info("Successfully added chapters to M4B")

    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg chapter remux timed out after 5 minutes")
    except Exception as e:
        # Clean up temp file if it exists
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass
        raise RuntimeError(f"Failed to add chapters to M4B: {e}")


def _build_metadata_options(metadata: Dict[str, str], output_path: Optional[str]) -> List[str]:
    """
    Build FFmpeg metadata options from metadata dict.

    Args:
        metadata: Dict with keys like title, artist, album, year, genre, composer
        output_path: Optional output path for fallback title (filename)

    Returns:
        List of FFmpeg arguments for metadata
    """
    options = []

    # Title
    title = metadata.get("title")
    if not title and output_path:
        title = Path(output_path).stem
    if title:
        options.extend(["-metadata", f"title={title}"])

    # Artist (narrator/author)
    artist = metadata.get("artist") or metadata.get("author") or "Unknown"
    options.extend(["-metadata", f"artist={artist}"])

    # Album (book title or series)
    album = metadata.get("album") or metadata.get("title") or "Unknown"
    options.extend(["-metadata", f"album={album}"])

    # Year/Date
    year = metadata.get("year")
    if not year:
        # Use current year as fallback
        import datetime
        year = str(datetime.datetime.now().year)
    options.extend(["-metadata", f"date={year}"])

    # Album Artist
    album_artist = metadata.get("album_artist") or artist
    options.extend(["-metadata", f"album_artist={album_artist}"])

    # Composer (typically narrator for audiobooks)
    composer = metadata.get("composer") or "Narrator"
    options.extend(["-metadata", f"composer={composer}"])

    # Genre
    genre = metadata.get("genre") or "Audiobook"
    options.extend(["-metadata", f"genre={genre}"])

    # Publisher (if available)
    if "publisher" in metadata:
        options.extend(["-metadata", f"publisher={metadata['publisher']}"])

    # Comment/Description (if available)
    if "description" in metadata:
        # Truncate long descriptions
        desc = metadata["description"][:500]
        options.extend(["-metadata", f"comment={desc}"])

    return options


def create_opus_stream(
    output_path: str,
    sample_rate: int = 24000,
    bitrate: str = "24000",
) -> subprocess.Popen:
    """
    Create FFmpeg process for Opus audio streaming (alternative format).

    Opus is more efficient than AAC but less compatible with audiobook players.

    Args:
        output_path: Path to output Opus file
        sample_rate: Audio sample rate (default: 24000 Hz)
        bitrate: Bitrate in bps (default: "24000" = 24 kbps)

    Returns:
        FFmpeg subprocess.Popen object
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-thread_queue_size", "32768",
        "-f", "f32le",
        "-ar", str(sample_rate),
        "-ac", "1",
        "-i", "pipe:0",
        "-c:a", "libopus",
        "-b:a", bitrate,
        output_path,
    ]

    logging.info(f"Starting Opus stream: {output_path}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )
        return proc
    except FileNotFoundError:
        raise RuntimeError("FFmpeg not found or Opus codec not available")
    except Exception as e:
        raise RuntimeError(f"Failed to start Opus stream: {e}")


def verify_ffmpeg_available() -> tuple[bool, str]:
    """
    Verify FFmpeg is installed and has AAC codec support.

    Returns:
        Tuple of (is_available, message)
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return False, "FFmpeg command failed"

        # Check for AAC codec
        codec_result = subprocess.run(
            ["ffmpeg", "-codecs"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )

        if "aac" not in codec_result.stdout.lower():
            return False, "FFmpeg found but AAC codec not available"

        return True, "FFmpeg with AAC codec is available"

    except FileNotFoundError:
        return False, "FFmpeg not found in PATH"
    except subprocess.TimeoutExpired:
        return False, "FFmpeg verification timed out"
    except Exception as e:
        return False, f"FFmpeg verification error: {e}"
