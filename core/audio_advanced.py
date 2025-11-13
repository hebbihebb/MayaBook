# core/audio_advanced.py
"""
Advanced audio processing features
- Variable speech rate control
- Silence detection and trimming
- Pronunciation dictionary
- Audio normalization
"""
import logging
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re

logger = logging.getLogger(__name__)


class PronunciationDictionary:
    """Manages pronunciation overrides for specific words"""

    def __init__(self):
        self.dictionary: Dict[str, str] = {}
        self.load_defaults()

    def load_defaults(self):
        """Load default pronunciation overrides for common proper nouns"""
        # Common names and places with tricky pronunciations
        self.dictionary.update({
            # Names
            'Hermione': 'Her-my-oh-nee',
            'Yosemite': 'Yoh-sem-it-ee',
            'Nguyen': 'Win',
            'Tucson': 'Too-sawn',

            # Technical terms
            'SQL': 'sequel',
            'NGINX': 'engine-ex',
            'JPEG': 'jay-peg',
            'GIF': 'jif',

            # Brand names
            'Porsche': 'Por-shuh',
            'Nike': 'Ny-kee',
        })

    def add(self, word: str, pronunciation: str):
        """Add or update pronunciation"""
        self.dictionary[word] = pronunciation
        logger.debug(f"Added pronunciation: {word} -> {pronunciation}")

    def remove(self, word: str):
        """Remove pronunciation override"""
        if word in self.dictionary:
            del self.dictionary[word]
            logger.debug(f"Removed pronunciation: {word}")

    def apply_to_text(self, text: str) -> str:
        """
        Apply pronunciation dictionary to text

        Replaces words with their pronunciation hints
        """
        result = text
        for word, pronunciation in self.dictionary.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(word) + r'\b'
            result = re.sub(pattern, pronunciation, result, flags=re.IGNORECASE)

        return result

    def load_from_file(self, filepath: str):
        """Load dictionary from CSV file (word,pronunciation)"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        self.add(parts[0].strip(), parts[1].strip())
            logger.info(f"Loaded {len(self.dictionary)} pronunciations from {filepath}")
        except Exception as e:
            logger.error(f"Error loading pronunciation dictionary: {e}")

    def save_to_file(self, filepath: str):
        """Save dictionary to CSV file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("# Word,Pronunciation\n")
                for word, pronunciation in sorted(self.dictionary.items()):
                    f.write(f"{word},{pronunciation}\n")
            logger.info(f"Saved {len(self.dictionary)} pronunciations to {filepath}")
        except Exception as e:
            logger.error(f"Error saving pronunciation dictionary: {e}")


def adjust_speech_rate(audio: np.ndarray, sample_rate: int, rate: float) -> np.ndarray:
    """
    Adjust speech rate without changing pitch (time stretching)

    Args:
        audio: Audio data as numpy array
        sample_rate: Sample rate in Hz
        rate: Speed multiplier (0.5 = half speed, 2.0 = double speed)
              Recommended range: 0.8 - 1.5

    Returns:
        Time-stretched audio
    """
    try:
        import librosa

        if rate == 1.0:
            return audio

        # Use librosa's time stretch
        stretched = librosa.effects.time_stretch(audio, rate=rate)
        logger.debug(f"Adjusted speech rate by {rate}x: {len(audio)} -> {len(stretched)} samples")
        return stretched

    except ImportError:
        logger.warning("librosa not installed. Cannot adjust speech rate. Install with: pip install librosa")
        return audio
    except Exception as e:
        logger.error(f"Error adjusting speech rate: {e}")
        return audio


def detect_silence(audio: np.ndarray, sample_rate: int,
                   threshold_db: float = -40.0,
                   min_silence_duration: float = 0.1) -> List[Tuple[int, int]]:
    """
    Detect silence regions in audio

    Args:
        audio: Audio data
        sample_rate: Sample rate in Hz
        threshold_db: Silence threshold in dB (lower = more sensitive)
        min_silence_duration: Minimum silence duration in seconds

    Returns:
        List of (start_sample, end_sample) tuples for silence regions
    """
    # Convert to dB
    audio_abs = np.abs(audio)
    audio_db = 20 * np.log10(audio_abs + 1e-10)  # Add epsilon to avoid log(0)

    # Find samples below threshold
    is_silence = audio_db < threshold_db

    # Find contiguous silence regions
    silence_regions = []
    in_silence = False
    silence_start = 0

    min_samples = int(min_silence_duration * sample_rate)

    for i, silent in enumerate(is_silence):
        if silent and not in_silence:
            # Start of silence
            in_silence = True
            silence_start = i
        elif not silent and in_silence:
            # End of silence
            in_silence = False
            silence_length = i - silence_start
            if silence_length >= min_samples:
                silence_regions.append((silence_start, i))

    # Handle silence at end
    if in_silence:
        silence_length = len(audio) - silence_start
        if silence_length >= min_samples:
            silence_regions.append((silence_start, len(audio)))

    logger.debug(f"Detected {len(silence_regions)} silence regions")
    return silence_regions


def trim_silence(audio: np.ndarray, sample_rate: int,
                 threshold_db: float = -40.0,
                 trim_start: bool = True,
                 trim_end: bool = True,
                 pad_seconds: float = 0.1) -> np.ndarray:
    """
    Trim silence from start and/or end of audio

    Args:
        audio: Audio data
        sample_rate: Sample rate in Hz
        threshold_db: Silence threshold in dB
        trim_start: Whether to trim start
        trim_end: Whether to trim end
        pad_seconds: Padding to keep after trim (seconds)

    Returns:
        Trimmed audio
    """
    # Find silence regions
    silence_regions = detect_silence(audio, sample_rate, threshold_db, min_silence_duration=0.05)

    if not silence_regions:
        return audio

    pad_samples = int(pad_seconds * sample_rate)
    start_trim = 0
    end_trim = len(audio)

    # Trim start
    if trim_start and silence_regions and silence_regions[0][0] == 0:
        start_trim = max(0, silence_regions[0][1] - pad_samples)

    # Trim end
    if trim_end and silence_regions and silence_regions[-1][1] == len(audio):
        end_trim = min(len(audio), silence_regions[-1][0] + pad_samples)

    trimmed = audio[start_trim:end_trim]
    logger.debug(f"Trimmed audio: {len(audio)} -> {len(trimmed)} samples")
    return trimmed


def normalize_audio(audio: np.ndarray, target_db: float = -3.0) -> np.ndarray:
    """
    Normalize audio to target dB level (peak normalization)

    Args:
        audio: Audio data
        target_db: Target peak level in dB (e.g., -3.0 for standard mastering)

    Returns:
        Normalized audio
    """
    # Find current peak
    current_peak = np.max(np.abs(audio))

    if current_peak == 0:
        logger.warning("Audio is silent, cannot normalize")
        return audio

    # Calculate current peak in dB
    current_db = 20 * np.log10(current_peak)

    # Calculate gain needed
    gain_db = target_db - current_db
    gain_linear = 10 ** (gain_db / 20)

    # Apply gain
    normalized = audio * gain_linear

    # Clip to prevent overflow
    normalized = np.clip(normalized, -1.0, 1.0)

    logger.debug(f"Normalized audio: {current_db:.1f} dB -> {target_db:.1f} dB (gain: {gain_db:.1f} dB)")
    return normalized


def apply_fade(audio: np.ndarray, sample_rate: int,
               fade_in_duration: float = 0.0,
               fade_out_duration: float = 0.0) -> np.ndarray:
    """
    Apply fade in/out to audio

    Args:
        audio: Audio data
        sample_rate: Sample rate in Hz
        fade_in_duration: Fade in duration in seconds
        fade_out_duration: Fade out duration in seconds

    Returns:
        Audio with fades applied
    """
    result = audio.copy()

    # Fade in
    if fade_in_duration > 0:
        fade_in_samples = int(fade_in_duration * sample_rate)
        fade_in_samples = min(fade_in_samples, len(audio) // 2)  # Don't exceed half the audio length

        fade_in_curve = np.linspace(0, 1, fade_in_samples)
        result[:fade_in_samples] *= fade_in_curve

    # Fade out
    if fade_out_duration > 0:
        fade_out_samples = int(fade_out_duration * sample_rate)
        fade_out_samples = min(fade_out_samples, len(audio) // 2)

        fade_out_curve = np.linspace(1, 0, fade_out_samples)
        result[-fade_out_samples:] *= fade_out_curve

    return result


def auto_retry_on_failure(synthesis_function, text: str, max_attempts: int = 3,
                          temperature_adjustments: List[float] = [0.0, -0.1, +0.1]) -> Optional[str]:
    """
    Automatically retry synthesis with adjusted parameters on failure

    Args:
        synthesis_function: Function that synthesizes audio
        text: Text to synthesize
        max_attempts: Maximum retry attempts
        temperature_adjustments: Temperature adjustments to try on each retry

    Returns:
        Path to generated audio, or None if all attempts failed
    """
    for attempt in range(max_attempts):
        try:
            # Adjust temperature
            temp_adjustment = temperature_adjustments[min(attempt, len(temperature_adjustments) - 1)]

            logger.info(f"Synthesis attempt {attempt + 1}/{max_attempts} (temp adjustment: {temp_adjustment:+.2f})")

            # Call synthesis function with adjusted temperature
            # Note: This is a simplified version - actual implementation would need to
            # accept temperature as parameter
            result = synthesis_function(text)

            if result:
                logger.info(f"Synthesis succeeded on attempt {attempt + 1}")
                return result

        except Exception as e:
            logger.warning(f"Synthesis attempt {attempt + 1} failed: {e}")

            if attempt == max_attempts - 1:
                logger.error(f"All {max_attempts} synthesis attempts failed")
                raise

    return None


def analyze_audio_quality(audio_path: str) -> Dict[str, any]:
    """
    Analyze audio quality metrics

    Returns dict with:
        - rms: Root mean square
        - peak: Peak amplitude
        - duration: Duration in seconds
        - silence_ratio: Ratio of silence to total duration
        - clipping: Whether audio is clipped
    """
    try:
        audio, sr = sf.read(audio_path)

        # Calculate metrics
        rms = np.sqrt(np.mean(audio ** 2))
        peak = np.max(np.abs(audio))
        duration = len(audio) / sr

        # Detect silence
        silence_regions = detect_silence(audio, sr, threshold_db=-40.0)
        silence_samples = sum(end - start for start, end in silence_regions)
        silence_ratio = silence_samples / len(audio) if len(audio) > 0 else 0

        # Detect clipping
        clipping = np.any(np.abs(audio) > 0.99)

        metrics = {
            'rms': float(rms),
            'peak': float(peak),
            'duration': float(duration),
            'silence_ratio': float(silence_ratio),
            'clipping': bool(clipping),
            'sample_rate': sr,
            'channels': 1 if audio.ndim == 1 else audio.shape[1],
        }

        logger.debug(f"Audio quality: RMS={rms:.4f}, Peak={peak:.4f}, Duration={duration:.1f}s, Silence={silence_ratio:.1%}")
        return metrics

    except Exception as e:
        logger.error(f"Error analyzing audio quality: {e}")
        return {}
