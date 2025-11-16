# core/video_export.py
"""
DEPRECATED: MP4 video export functionality

This module is deprecated as of 2025-11-16. MayaBook now focuses on
audiobook formats (M4B and WAV) instead of video files.

MP4 export has been removed from all user-facing interfaces.
This file is kept for backward compatibility but should not be used.

For audiobook output, use:
- M4B format for chapter-aware audiobooks (with optional cover art)
- WAV format for lossless audio or preview generation
"""
import subprocess
from pathlib import Path

def export_mp4(cover_image_path, audio_wav_path, out_mp4_path,
               width=1920, height=1080, crf=20, preset="medium"):
    """
    DEPRECATED: Create MP4 video file from cover image and audio.

    This function is deprecated. Use M4B format for audiobook output instead.
    """
    Path(out_mp4_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", cover_image_path,
        "-i", audio_wav_path,
        "-c:v", "libx264", "-tune", "stillimage",
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
               f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-shortest", "-movflags", "+faststart",
        "-preset", preset, "-crf", str(crf),
        out_mp4_path,
    ]
    subprocess.run(cmd, check=True)
    return out_mp4_path
