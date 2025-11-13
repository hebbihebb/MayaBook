# MayaBook Bug Fixes - Final Summary

## Problem Statement
When using the GUI to generate audio from a 2-paragraph EPUB file with GPU acceleration enabled, only the second paragraph was being rendered in the output audio file. The first paragraph was either missing or replaced with incorrect content.

## Root Causes Identified

### Bug #1: EPUB Paragraph Extraction
**Issue:** Non-breaking spaces (`\xa0`) between paragraphs prevented proper text splitting.

**Symptoms:**
- EPUB extraction returned single block of text instead of separate paragraphs
- Text chunking couldn't identify paragraph boundaries

**Solution:** Modified `core/epub_extract.py` to:
- Extract each `<p>` tag separately
- Replace non-breaking spaces with regular spaces
- Preserve paragraph breaks with `\n\n` separators

**Files Modified:**
- `core/epub_extract.py` (lines 28-44)

---

### Bug #2: KV Cache State Bleeding
**Issue:** The llama.cpp model maintained KV cache state between chunk generations, causing the first chunk to generate audio based on stale context instead of the actual input text.

**Symptoms:**
- First chunk generated completely different speech than requested
- User heard "Dante cleared his throat..." instead of "I thought you'd be..."
- Model was predicting content rather than following input

**Solution:** Added `llm.reset()` before each generation to clear KV cache.

**Files Modified:**
- `core/tts_maya1_local.py` (line 116)

---

### Bug #3: Token Limit Overflow
**Issue:** Chunk size of 90 words created chunks requiring ~2500 tokens to synthesize, exactly hitting the `max_tokens` limit and truncating audio mid-chunk.

**Symptoms:**
- Missing text at the end of chunks
- Specifically: "closer, his breath fogging in the air. 'I wasn't sure I would,' he admitted, his tone carrying the weight of unspoken things."

**Evidence:**
- Log showed chunk 0 generated exactly 2500 tokens (hit limit!)
- 501 chars input × 5 tokens/char = 2505 tokens needed

**Solution:** Reduced default chunk size from 90 words to 70 words.

**Files Modified:**
- `ui/main_window.py` (line 111)

---

## Additional Improvements

### Diagnostic Enhancements
1. **Enhanced Logging in `core/audio_combine.py`:**
   - Shows shape, duration, and RMS of each chunk
   - Displays combined audio statistics
   - Helps verify correct concatenation

2. **Text Synthesis Logging in `core/tts_maya1_local.py`:**
   - Logs first 100 characters of text being synthesized
   - Shows text length for debugging

3. **Created `diagnose_audio.py`:**
   - Analyzes audio files second-by-second
   - Detects silent segments
   - Provides detailed RMS statistics

---

## Files Changed Summary

| File | Purpose | Key Changes |
|------|---------|-------------|
| `core/epub_extract.py` | EPUB parsing | Extract paragraphs individually, normalize whitespace |
| `core/tts_maya1_local.py` | TTS generation | Added `llm.reset()`, text logging |
| `ui/main_window.py` | GUI settings | Reduced default chunk_size to 70 |
| `core/audio_combine.py` | Audio processing | Added diagnostic logging |
| `diagnose_audio.py` | New tool | Audio analysis utility |

---

## Testing Results

**Before Fixes:**
- ❌ Only second paragraph audible
- ❌ First paragraph missing or incorrect
- ❌ Truncated audio at chunk boundaries

**After Fixes:**
- ✅ All paragraphs present and in correct order
- ✅ Complete text synthesized
- ✅ No audio truncation
- ✅ CLI and GUI both working correctly

---

## Recommended Settings

For optimal results with GPU-accelerated GGUF path:

- **Chunk Size:** 70 words (default)
- **Max Tokens:** 2500 (current limit works with 70-word chunks)
- **Temperature:** 0.45
- **Top-p:** 0.92
- **GPU Layers:** -1 (offload all to GPU)

**Note:** If processing longer texts, consider staying at 70 words per chunk or increasing `max_tokens` to 3000+ to accommodate larger chunks.

---

## Technical Details

### Token Budget Calculation
For GPU-accelerated Maya1 TTS:
- Approximately **5 audio tokens per character** of input text
- 70 words ≈ 350 chars ≈ 1750 tokens needed
- Safe margin below 2500 token limit

### Chunk Distribution Example (Test EPUB)
With 70-word chunks:
- Chunk 0: 277 chars → ~1385 tokens → ~11s audio
- Chunk 1: 369 chars → ~1845 tokens → ~15s audio
- Chunk 2: 126 chars → ~630 tokens → ~5s audio
- **Total:** 3 chunks, ~31s audio (all text included)

---

## Lessons Learned

1. **GPU acceleration can introduce state management issues** - Always reset model state between generations
2. **EPUB parsing requires careful whitespace handling** - Don't assume standard newlines
3. **Token limits are hard constraints** - Monitor generation lengths and adjust chunk sizes accordingly
4. **User testing is invaluable** - The user's detective work (manually shuffling paragraphs, removing tags) was crucial in isolating the EPUB extraction bug

---

## Future Improvements

1. **Dynamic token limit detection:** Automatically adjust chunk size based on available token budget
2. **Better EPUB handling:** Support more complex EPUB structures (nested divs, multiple chapters)
3. **RMS retry logic for HuggingFace path:** Apply the same quality checks to safetensor model
4. **Chunk preview in GUI:** Show what chunks will be created before generation starts

---

## Date
2025-11-13

## Status
✅ **ALL ISSUES RESOLVED**
