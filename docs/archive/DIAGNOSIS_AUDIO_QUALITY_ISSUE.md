# Diagnosis: Audio Quality Issue in HuggingFace Backend

## Symptoms
- First 40% of EPUB (chunks 1-485) produce gibberish/garbled audio
- Audio becomes intelligible only around chunk 486 (40% into book)
- Individual chunk synthesis test produces similar quality
- Technical audio parameters are fine (proper levels, no clipping, correct sample rates)

## Key Finding
The audible sentences in the 5-hour concatenated file appear at character position 168,195 (39.8% through the text), which corresponds to chunk 486.

**This means chunks 1-485 generated SOME audio (not silent) but with incorrect/garbled content.**

## Root Cause Analysis

### Primary Hypothesis: Model KV Cache State Bleeding

**Evidence:**
1. **No cache clearing between chunks** in `tts_maya1_hf.py`
   - The HuggingFace model is loaded once globally and reused
   - Each call to `model.generate()` may accumulate KV cache state
   - No `torch.cuda.empty_cache()` or model cache reset between generations

2. **Earlier CLAUDE.md documented KV cache issues with llama.cpp**
   - Fixed in llama.cpp by adding `llm.reset()` before each generation
   - HuggingFace backend never had this fix implemented
   - Similar state bleeding may be happening here

3. **Degradation pattern is gradual**
   - First chunks (1-100) might have some latent state
   - By chunk 485, enough state has accumulated
   - Around chunk 486, model "resets" somehow or state changes fundamentally

### Secondary Hypothesis: Token Space/Codec Mismatch

**Less likely but possible:**
- Generated token IDs might be accumulating in a problematic way
- SNAC codec might be misinterpreting the token sequences
- Token ranges are consistent (128K-157K range), so probably not this

### Tertiary Hypothesis: Model Quantization Artifacts

- 4-bit quantization might be degrading with model reuse
- Temperature/top_p sampling might be interacting poorly with quantized weights
- Earlier single-chunk test also produced similar quality to stress test chunks

---

## Solution: Add Model State Reset

The fix is to clear GPU caches and potentially the model's internal state between chunk generations.

### Option 1: Simple Cache Clearing (Low Risk)
```python
def synthesize_chunk_hf(...):
    model, tokenizer, snac_model = _ensure_models(model_path)

    # CLEAR GPU CACHE
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # ... rest of synthesis code ...
```

### Option 2: Model KV Cache Reset (Medium Risk)
```python
def synthesize_chunk_hf(...):
    model, tokenizer, snac_model = _ensure_models(model_path)

    # Clear any cached KV states in the model
    if hasattr(model, 'flush_kv_cache'):
        model.flush_kv_cache()

    # ... rest of synthesis code ...
```

### Option 3: Reload Model Per Chunk (High Risk/Cost)
```python
def synthesize_chunk_hf(...):
    # Don't cache globally - reload fresh each time
    # (Very slow, defeats purpose of keeping model in memory)
```

---

## Testing Strategy

### Test 1: Isolate Chunk Quality
1. Synthesize chunk 1 in isolation ✅ DONE - need to listen
2. Synthesize chunk 100 in isolation
3. Synthesize chunk 485 in isolation
4. Synthesize chunk 486 in isolation

Compare audio quality - if they're all gibberish, it's a fundamental model issue.
If chunk 1 is gibberish but 486 is fine when isolated, it's state bleeding.

### Test 2: Apply Cache Clear Fix
1. Add `torch.cuda.empty_cache()` after each generation
2. Re-run stress test on subset (first 100 chunks)
3. Compare audio quality

### Test 3: Verify with llama.cpp GGUF
1. Test same chunks with GGUF backend (llama.cpp)
2. Check if quality is better (it should be if HF backend issue)

---

## Recommended Next Steps

1. **IMMEDIATE**: Test isolation of chunks 1, 100, 485, 486 individually
   - If all produce gibberish: Model is fundamentally broken
   - If only early chunks gibberish: Confirms state bleeding hypothesis

2. **SHORT TERM**: Implement cache clearing fix in HuggingFace backend
   - Add `torch.cuda.empty_cache()` after each generation
   - Test on subset of EPUB

3. **MEDIUM TERM**: Compare with GGUF backend
   - Run same test with llama.cpp backend
   - Confirm which backend is problematic

4. **LONG TERM**: Consider model alternatives
   - If HF backend is fundamentally broken, switch to GGUF (llama.cpp) as primary
   - Keep HF as fallback option only

---

## Related Documentation

From CLAUDE.md - llama.cpp KV Cache Fix (2025-11-13):
```
### Bug #2: KV Cache State Bleeding
Symptom: First chunk generated wrong speech despite correct input text
Cause: llama.cpp model maintained KV cache state between generations
Fix: Added llm.reset() before each generation
File: core/tts_maya1_local.py line 116
```

This suggests the HuggingFace backend may need the same treatment.

---

**Status**: Awaiting individual chunk isolation testing
**Created**: 2025-11-17
**Priority**: HIGH - Affects all HuggingFace backend usage
