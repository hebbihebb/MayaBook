# Verification Checklist - GPU Cache State Bleeding Fix

**Fix Location:** `core/tts_maya1_hf.py` (lines 151-155)  
**Date Implemented:** 2025-11-17  
**Status:** AWAITING VERIFICATION

---

## Pre-Testing Checklist

- [x] Root cause identified (GPU KV cache state bleeding)
- [x] Fix implemented (GPU cache clearing before each generation)
- [x] Similar fix verified to work in llama.cpp backend
- [x] Code changes reviewed (safe, minimal, uses standard PyTorch API)
- [x] Documentation complete (5 detailed analysis documents)
- [ ] Ready for verification testing

---

## Verification Phase 1: Isolated Chunk Testing

### Purpose
Confirm that individual chunks produce high-quality audio when tested in isolation with the fix applied.

### Test Plan

**Test 1.1: Chunk 1 (Should be coherent)**
```bash
# Expected: "Riven Ashmark spent twelve years doing what no other player dared..."
python3 test_single_chunk_detailed.py
# Listen to output: /tmp/tmpXXXXXXXX.wav
# Quality: Should be GOOD (not gibberish)
```
- [ ] Chunk 1 audio is clear and coherent
- [ ] Text matches audio content
- [ ] Audio quality is professional

**Test 1.2: Chunk 100 (Sanity check)**
```bash
# Take a chunk from middle of first corrupted section
# Should also be clear now (with fix applied)
```
- [ ] Chunk 100 audio is clear and coherent
- [ ] No degradation from chunk 1

**Test 1.3: Chunk 485 (Last chunk before gibberish turned coherent)**
```bash
# This chunk was gibberish in original stress test
# Should be clear with fix applied
```
- [ ] Chunk 485 audio is now clear and coherent
- [ ] Confirms fix prevents early corruption

**Test 1.4: Chunk 486 (Was already coherent)**
```bash
# This chunk was already coherent in original stress test
# Should still be coherent with fix
```
- [ ] Chunk 486 remains coherent
- [ ] Fix doesn't break later chunks

### Success Criteria
✅ **ALL tests PASS** if:
- All 4 chunks are clear, coherent, and match text content
- No gibberish detected
- Audio quality is consistent across all chunks

❌ **Tests FAIL** if:
- Any chunk still produces gibberish
- Audio quality is degraded
- Content doesn't match text

---

## Verification Phase 2: Small-Scale Stress Test

### Purpose
Verify fix works across multiple sequential chunks (not just isolated).

### Test Plan

**Test 2.1: Synthesize first 100 chunks**
```bash
# Create test script to synthesize chunks 1-100
# Expected time: ~2.5 hours (average 90 seconds per chunk)
python3 stress_test_subset_100.py
```
- [ ] All 100 chunks complete without errors
- [ ] No crashes or hangs
- [ ] GPU memory stable (no OOM errors)
- [ ] Log file shows cache clearing happening

**Test 2.2: Concatenate and listen**
```bash
# Combine chunks 1-100 into single WAV
# Listen to quality throughout
python3 concat_subset_100.py
```
- [ ] Audio quality consistent from chunk 1-100
- [ ] No gibberish in early chunks
- [ ] No progressive degradation
- [ ] Smooth transitions between chunks

**Test 2.3: Create M4B from 100-chunk subset**
```bash
# Generate M4B audiobook from subset
ffmpeg -i combined_100.wav -c:a aac -q:a 2 test_100_chunk.m4b
```
- [ ] M4B creates successfully
- [ ] M4B plays without issues
- [ ] Audio quality preserved

### Success Criteria
✅ **Tests PASS** if:
- All 100 chunks synthesize successfully
- Audio quality is consistent throughout
- No gibberish detected in early chunks
- M4B file is playable and correct

❌ **Tests FAIL** if:
- Any chunk fails to synthesize
- Audio quality degrades over chunks
- Gibberish appears in early chunks
- M4B has issues

---

## Verification Phase 3: Full Stress Test

### Purpose
Confirm fix works for complete 1,147-chunk conversion.

### Test Plan

**Test 3.1: Run full stress test with fix**
```bash
# Complete conversion of all 1,147 chunks
python3 stress_test_epub_conversion_fixed.py
# Expected time: ~31 hours
```
- [ ] All 1,147 chunks complete
- [ ] No crashes or errors
- [ ] Progress logging shows all chunks
- [ ] Final WAV file created
- [ ] Temp files created correctly

**Test 3.2: Generate M4B from full audio**
```bash
# Create final M4B audiobook
ffmpeg -i audiobook.wav -c:a aac -q:a 2 audiobook_final.m4b
```
- [ ] M4B created successfully
- [ ] File size reasonable (~800 MB)
- [ ] M4B is playable

**Test 3.3: Quality sampling**
```bash
# Sample audio at key points
# Expected: ALL coherent and consistent
- Chunk 1-10:     Should be GOOD
- Chunk 100-110:  Should be GOOD
- Chunk 500-510:  Should be GOOD
- Chunk 1140+:    Should be GOOD
```
- [ ] Chunk 1-10 audio is clear
- [ ] Chunk 100-110 audio is clear
- [ ] Chunk 500-510 audio is clear
- [ ] Chunk 1140+ audio is clear
- [ ] No gibberish anywhere
- [ ] Consistent quality throughout

### Success Criteria
✅ **Tests PASS** if:
- All 1,147 chunks complete successfully
- Audio quality is consistent from start to finish
- No gibberish detected at any point
- M4B file is complete and playable
- Final audiobook sounds professional

❌ **Tests FAIL** if:
- Any chunk fails
- Gibberish appears anywhere
- Audio quality degrades
- M4B has issues

---

## Comparative Analysis

### Before Fix (Original Stress Test)
```
Chunks 1-485:    ✗ Gibberish/corrupted
Chunks 486+:     ✓ Coherent
5-hour file:     ✗ Mostly gibberish until 40% mark
M4B quality:     ✗ Poor for first 2+ hours
```

### After Fix (Expected)
```
Chunks 1-1147:   ✓ All coherent
Audio quality:   ✓ Consistent throughout
5-hour file:     ✓ Fully intelligible
M4B quality:     ✓ Professional throughout
```

---

## Regression Testing

### Purpose
Ensure fix doesn't break anything else.

- [ ] GUI still works (app.py)
- [ ] NiceGUI web interface still works
- [ ] Other synthesis backends (GGUF, vLLM) unaffected
- [ ] M4B chapter metadata generation still works
- [ ] Temp file cleanup still works
- [ ] All existing unit tests pass

---

## Documentation Updates (After Verification)

Once fix is verified:
- [ ] Update CLAUDE.md with HuggingFace fix details
- [ ] Create bug fix PR with detailed description
- [ ] Add notes about why fix was needed (KV cache explanation)
- [ ] Update best practices for long conversions
- [ ] Document performance characteristics

---

## Final Approval Criteria

Fix is APPROVED for production if:
- ✅ Phase 1 (isolated chunks) ALL PASS
- ✅ Phase 2 (100 chunks) ALL PASS
- ✅ Phase 3 (1,147 chunks) ALL PASS
- ✅ Comparative analysis shows improvement
- ✅ No regressions detected

---

## Timeline

| Phase | Estimated Duration | Status |
|-------|-------------------|--------|
| Phase 1 (Isolated chunks) | 1-2 hours | [ ] Pending |
| Phase 2 (100 chunks) | 3-4 hours | [ ] Pending |
| Phase 3 (1,147 chunks) | 32-35 hours | [ ] Pending |
| Analysis & Approval | 1-2 hours | [ ] Pending |
| **TOTAL** | **36-43 hours** | **AWAITING START** |

---

## Notes

- Phase 1 can run on a sample subset to verify fix concept
- Phase 2 can be done overnight (background)
- Phase 3 requires continuous GPU access (~31 hours)
- Phases can run sequentially or skip Phase 2 if Phase 1 is strong

---

**Prepared by:** Investigation Team  
**Date:** 2025-11-17  
**Status:** Ready for Verification Start  
**Next Action:** Begin Phase 1 Testing
