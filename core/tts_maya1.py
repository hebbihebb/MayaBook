import logging
import os
import re
from typing import List, Optional

import pyttsx3

logging.basicConfig(level=logging.INFO)


def list_voices() -> List[str]:
    """
    Lists the available TTS voices.

    Returns:
        A list of voice IDs.
    """
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        engine.stop()
        return [voice.id for voice in voices]
    except Exception as e:
        logging.error(f"Could not list TTS voices: {e}")
        return ["default"]


def synthesize_preview(
    text: str, voice: str = "default", rate_wpm: int = 180, out_path: str = "out/preview.wav"
) -> str:
    """
    Synthesizes a short audio preview from the given text.

    Args:
        text: The text to synthesize.
        voice: The voice to use.
        rate_wpm: The speaking rate in words per minute.
        out_path: The path to save the audio file.

    Returns:
        The absolute path to the generated WAV file.
    """
    try:
        # Create output directory
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        # Normalize and trim text
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 1000:
            text = text[:1000]

        # Synthesize audio
        engine = pyttsx3.init()
        if voice != "default":
            engine.setProperty("voice", voice)
        engine.setProperty("rate", rate_wpm)
        engine.save_to_file(text, out_path)
        engine.runAndWait()
        engine.stop()

        abs_path = os.path.abspath(out_path)
        logging.info(f"Synthesized preview with voice='{voice}', rate={rate_wpm} to '{abs_path}'")
        return abs_path
    except Exception as e:
        logging.error(f"TTS synthesis failed: {e}")
        raise


def synthesize_chunk(
    text: str, description: str, server_url: str, temperature: float, top_p: float
) -> Optional[bytes]:
    """
    Synthesizes a single text chunk using the Maya1 FastAPI server.

    Args:
        text: The text chunk to synthesize.
        description: The voice description.
        server_url: The URL of the Maya1 server.
        temperature: The generation temperature.
        top_p: The generation top_p.

    Returns:
        The WAV audio bytes, or None if synthesis fails.
    """
    # TODO: Implement the TTS request to the Maya1 server.
    print(f"Synthesizing text chunk: '{text[:50]}...'")
    return None
