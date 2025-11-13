# core/audio_combine.py
import numpy as np
import soundfile as sf
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def concat_wavs(wav_paths, out_path, sr=24000, channels=None, gap_seconds=0.25):
    if not wav_paths:
        raise ValueError("No WAVs provided.")

    pieces, target_channels = [], channels
    logger.info(f"Concatenating {len(wav_paths)} audio files with {gap_seconds}s gaps")

    for i, p in enumerate(wav_paths):
        audio, file_sr = sf.read(p, dtype="float32", always_2d=True)

        # Calculate RMS for diagnostics
        rms = float(np.sqrt(np.mean(np.square(audio))))
        duration = len(audio) / file_sr
        logger.info(f"Chunk {i}: shape={audio.shape}, duration={duration:.2f}s, RMS={rms:.6f}, path={p}")

        if file_sr != sr:
            raise ValueError(f"SR mismatch: {p} has {file_sr}, expected {sr}.")

        if target_channels is None:
            target_channels = audio.shape[1]
            logger.debug(f"Target channels set to {target_channels} from first file")

        if audio.shape[1] != target_channels:
            if audio.shape[1] == 1 and target_channels == 2:
                audio = np.repeat(audio, 2, axis=1)
            elif audio.shape[1] == 2 and target_channels == 1:
                audio = audio.mean(axis=1, keepdims=True)
            else:
                raise ValueError("Channel mismatch.")

        pieces.append(audio)

        if i < len(wav_paths) - 1 and gap_seconds > 0:
            gap_samples = int(sr * gap_seconds)
            gap = np.zeros((gap_samples, target_channels), dtype="float32")
            logger.debug(f"Adding gap: {gap.shape} ({gap_seconds}s)")
            pieces.append(gap)

    combined = np.vstack(pieces)
    combined_rms = float(np.sqrt(np.mean(np.square(combined))))
    combined_duration = len(combined) / sr
    logger.info(f"Combined audio: shape={combined.shape}, duration={combined_duration:.2f}s, RMS={combined_rms:.6f}")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(out_path, combined, sr)

    return out_path
