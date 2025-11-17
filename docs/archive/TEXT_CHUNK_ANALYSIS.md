# Text Chunk Analysis - Stress Test Input/Output Mismatch

## Text Chunks Sent to TTS Model

### Chunk 1: (54 words)
```
Riven Ashmark spent twelve years doing what no other player dared: ignoring every dungeon, skipping every raid, and maxing out all twelve crafting professions in The Empyrean Dawning. No combat. No glory. Just the quiet satisfaction of making things properly.

Then she woke up in her workshop. For real.

Two hundred years have passed.
```

**Model Prompt Format:**
```
<description="A mature female voice, clear and expressive, with good pacing"> [TEXT ABOVE]
```

**Input Tokens:** 92 tokens
**Generated Tokens:** 1,996 tokens (out of 2,500 max)
**Duration:** 24.23 seconds
**Output WAV:** `/tmp/tmpjt4p2_6p.wav` (583 KB)

---

### Chunk 2: (70 words)
```
The world she knew has suffered the Unmaking—a plague that didn't kill people, but erased their knowledge. Master crafters woke up unable to remember their own techniques. Within a generation, centuries of accumulated skill vanished like smoke.

Now civilization limps along on the bones of what it can no longer build. "Legendary" equipment that would've been trash-tier in Riven's era. Repairs that won't hold. Buildings that fight their own foundations.
```

**Input Tokens:** 114 tokens
**Generated Tokens:** 2,500 tokens (MAX - hit token limit)
**Duration:** 30.38 seconds
**Output WAV:** `/tmp/tmp8tmi92at.wav` (731 KB)

---

### Chunk 3: (67 words)
```
A world wealthy in ancient artifacts but bankrupt in understanding.

Riven can make things they've forgotten were possible.

She can forge weapons that make Sword Saints weep. Repair "impossible" enchantments over lunch. Teach techniques that temples preserve as corrupted scripture. And she does it all while insisting she's "just a crafter."

Oh, and she's accidentally immortal. Turns out stacking twelve maxed crafting professions makes you functionally unkillable.
```

**Input Tokens:** 108 tokens (estimated)
**Generated Tokens:** ~1,950 tokens (estimated)
**Duration:** 12.97 seconds
**Output WAV:** `/tmp/tmp02dwuupk.wav` (311 KB)

---

## Audio Quality Analysis

| Metric | Chunk 1 | Chunk 2 | Chunk 3 |
|--------|---------|---------|---------|
| **Duration** | 20.22s | 7.94s | 12.97s |
| **Sample Rate** | 24 kHz | 24 kHz | 24 kHz |
| **RMS Level** | 0.105 | 0.106 | 0.110 |
| **Peak Min** | -0.682 | -0.625 | -0.536 |
| **Peak Max** | 0.758 | 0.849 | 0.702 |
| **Clipping** | ❌ No | ❌ No | ❌ No |
| **File Size** | 948 KB | 372 KB | 608 KB |

**Assessment:** Audio is technically well-formed with proper levels and no clipping. No technical audio defects.

---

## The Core Problem: Model Output Quality

**Issue:** Text content is not reflected in generated audio
- **Text Content:** Coherent English narrative about character Riven Ashmark
- **Generated Audio:** "Mostly gibberish" (per your observation)

**Possible Root Causes:**

1. **Maya1 HuggingFace Model Training Issues**
   - The 4-bit safetensor model may have been poorly quantized
   - Quantization artifacts could corrupt the token generation
   - The model may not have been properly fine-tuned for TTS

2. **SNAC Codec Decoding Issues**
   - Token IDs generated are in ranges like [129057-156912]
   - SNAC codec expecting specific token ranges
   - Mismatch between model token space and SNAC token space

3. **Prompt Format Problem**
   - Voice description tag: `<description="...">` 
   - This tag format may not be compatible with Maya1's training
   - Model might be treating the entire prompt as garbled TTS code

4. **Earlier Testing (HuggingFace 15-sample test) Success**
   - Those tests ran on single test sentence with good results
   - Stress test uses FULL EPUB text chunks
   - Issue may emerge only at scale or with longer sequences

---

## Comparison: HuggingFace Backend Testing History

From CLAUDE.md (backend testing results):

### Working Example (from 15-sample test):
```
Model: maya1_4bit_safetensor (HuggingFace)
Test: "The forest was eerily quiet. <whisper>Something was watching from the shadows.</whisper>"
Result: ✅ 15/15 samples successful with proper audio
Observation: "Quality Findings... Good quality, proper length, stable generation"
```

### Current Problem (Stress Test):
```
Model: Same (maya1_4bit_safetensor)
Input: Full novel chunks (54-70 words each)
Result: ❌ Audio is "gibberish", doesn't reflect text
Observation: Technical audio OK, but content mismatch
```

**Hypothesis:** The issue may be:
- **Scale**: Longer text chunks (54 vs ~20 words) causing problems
- **Context**: Full novel sentences vs test sentence
- **Token Generation**: Both chunks hit token limits (1996, 2500, etc.) - possible truncation of meaningful content

---

## Critical Questions for Investigation

1. **Can we run a quick test?**
   - Take Chunk 1 text
   - Synthesize it in isolation using test script
   - Listen to output
   - Compare against stress test output

2. **Is the concatenation correct?**
   - Individual chunks might sound OK
   - Concatenation might be causing issues
   - But M4B generation works... so concat process is OK

3. **Model state issue?**
   - Is there residual state from previous chunks?
   - Are chunks influenced by earlier generations?
   - (Note: llama.cpp had KV cache issue, but HF shouldn't have this)

4. **Token space mismatch?**
   - Are generated token IDs valid SNAC codes?
   - Is SNAC codec decoding garbage?
   - Check token ID ranges in successful vs failed generations

---

## Next Steps for Diagnosis

1. **Extract and play individual chunk 1 WAV** to confirm it's gibberish
2. **Create single-chunk test** using same text with test script
3. **Check HuggingFace model state** - reload vs reuse
4. **Verify SNAC codec** is receiving valid token IDs
5. **Compare with llama.cpp GGUF** version if available

---

**Generated:** 2025-11-17
**Status:** Diagnostic - Awaiting further investigation
