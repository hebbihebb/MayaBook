from pathlib import Path

def export_mp4(audio_path: Path, cover_path: Path, out_path: Path) -> None:
    """
    Combines an audio file and a cover image into an MP4 video.

    Args:
        audio_path: The path to the audio file.
        cover_path: The path to the cover image.
        out_path: The path to the output MP4 file.
    """
    # TODO: Implement MP4 export using ffmpeg.
    print(f"Exporting MP4 to {out_path}...")
