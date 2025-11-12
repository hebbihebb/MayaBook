# core/audio_combine.py
import numpy as np
import soundfile as sf
from pathlib import Path

def concat_wavs(wav_paths, out_path, sr=24000, channels=None, gap_seconds=0.25):
    if not wav_paths:
        raise ValueError("No WAVs provided.")

    pieces, target_channels = [], channels
    for i, p in enumerate(wav_paths):
        audio, file_sr = sf.read(p, dtype="float32", always_2d=True)

        if file_sr != sr:
            raise ValueError(f"SR mismatch: {p} has {file_sr}, expected {sr}.")

        if target_channels is None:
            target_channels = audio.shape[1]

        if audio.shape[1] != target_channels:
            if audio.shape[1] == 1 and target_channels == 2:
                audio = np.repeat(audio, 2, axis=1)
            elif audio.shape[1] == 2 and target_channels == 1:
                audio = audio.mean(axis=1, keepdims=True)
            else:
                raise ValueError("Channel mismatch.")

        pieces.append(audio)

        if i < len(wav_paths) - 1 and gap_seconds > 0:
            pieces.append(np.zeros((int(sr * gap_seconds), target_channels), dtype="float32"))

    combined = np.vstack(pieces)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(out_path, combined, sr)

    return out_path
