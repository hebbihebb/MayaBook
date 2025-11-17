#!/usr/bin/env python3
"""
Test a single text chunk in isolation to debug quality issues
"""
import sys
import os
sys.path.insert(0, '/mnt/Games/MayaBook')

from core.epub_extract import extract_text
from core.chunking import chunk_text
from core.tts_maya1_hf import synthesize_chunk_hf
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_single_chunk.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Extract and chunk the EPUB
epub_path = "assets/test/Zero Combat, Max Crafting_ The - GordanWizard.epub"
text = extract_text(epub_path)
chunks = chunk_text(text, max_words=70)

print("=" * 100)
print("SINGLE CHUNK TEST - CHUNK 1")
print("=" * 100)

# Test chunk 1
chunk_text_1 = chunks[0]
print(f"\nChunk 1 Text ({len(chunk_text_1.split())} words):")
print(f"{chunk_text_1}")
print()

# Synthesize
logger.info("=" * 100)
logger.info(f"Synthesizing Chunk 1: {len(chunk_text_1.split())} words")
logger.info("=" * 100)

output_wav = synthesize_chunk_hf(
    model_path="assets/models/maya1_4bit_safetensor",
    text=chunk_text_1,
    voice_description="A mature female voice, clear and expressive, with good pacing",
    temperature=0.45,
    top_p=0.92,
    max_tokens=2500,
)

print(f"\n✓ Generated WAV: {output_wav}")
print(f"  Size: {os.path.getsize(output_wav) / 1024:.1f} KB")

# Analyze the audio
import soundfile as sf
import numpy as np

audio, sr = sf.read(output_wav)
duration = len(audio) / sr
rms = np.sqrt(np.mean(audio**2))

print(f"  Duration: {duration:.2f}s")
print(f"  Sample rate: {sr} Hz")
print(f"  RMS: {rms:.6f}")
print(f"  Shape: {audio.shape}")

print("\n" + "=" * 100)
print("SINGLE CHUNK TEST COMPLETE")
print("=" * 100)
print("\nCheck the output WAV file to hear if it matches the text above.")
print("Output: " + output_wav)
print("Log: test_single_chunk.log")
