#!/usr/bin/env python3
"""
Test script for HuggingFace Maya1 TTS implementation
Tests the 4-bit quantized safetensor model with GPU acceleration
"""
import os
import sys
import torch
from core.tts_maya1_hf import synthesize_chunk_hf

def main():
    # Check CUDA availability
    print("=" * 60)
    print("System Information")
    print("=" * 60)
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU device: {torch.cuda.get_device_name(0)}")
        print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    print()

    # Model path
    model_path = "assets/models/maya1_4bit_safetensor"

    if not os.path.exists(model_path):
        print(f"ERROR: Model not found at {model_path}")
        sys.exit(1)

    print("=" * 60)
    print("Model Configuration")
    print("=" * 60)
    print(f"Model path: {model_path}")
    print()

    # Test parameters
    test_text = "Hello, this is a test of the Maya text to speech system."
    voice_description = "A calm, friendly female voice"

    print("=" * 60)
    print("Test Configuration")
    print("=" * 60)
    print(f"Text: {test_text}")
    print(f"Voice: {voice_description}")
    print(f"Temperature: 0.4")
    print(f"Top-p: 0.9")
    print(f"Max tokens: 2500")
    print()

    # Run synthesis
    print("=" * 60)
    print("Starting Synthesis")
    print("=" * 60)

    try:
        wav_path = synthesize_chunk_hf(
            model_path=model_path,
            text=test_text,
            voice_description=voice_description,
            temperature=0.4,
            top_p=0.9,
            max_tokens=2500,
        )

        print()
        print("=" * 60)
        print("Success!")
        print("=" * 60)
        print(f"Audio saved to: {wav_path}")

        # Check file size
        file_size = os.path.getsize(wav_path)
        print(f"File size: {file_size / 1024:.2f} KB")

        # Try to read audio info
        import soundfile as sf
        audio_data, sample_rate = sf.read(wav_path)
        duration = len(audio_data) / sample_rate
        print(f"Sample rate: {sample_rate} Hz")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Audio shape: {audio_data.shape}")

        print()
        print("You can play the audio file with:")
        print(f"  ffplay {wav_path}")
        print()

        return 0

    except Exception as e:
        print()
        print("=" * 60)
        print("ERROR")
        print("=" * 60)
        print(f"Failed to synthesize audio: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
