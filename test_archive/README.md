# Test Archive

This directory contains legacy and diagnostic test scripts from earlier development phases. These scripts have been archived as the project has moved to production-ready status with consolidated testing.

## Archive Organization

### Investigation & Diagnostic Tests

These scripts were used to diagnose and debug issues with audio quality and backend compatibility:

**debug_token_extraction.py**
- Purpose: Debug SNAC token extraction and decoding issues
- Status: Obsolete - issue resolved with Q4_K_M GGUF testing
- Key finding: SNAC decoder behavior was consistent across backends
- Date: 2025-11-17

**phase1_chunk_isolation_test.py**
- Purpose: Test isolated chunk synthesis (chunks 1, 100, 485, 486)
- Status: Superseded by test_q4k_model.py
- Backend: HuggingFace 4-bit
- Key finding: Chunks had audio quality issues (missing sentences, gibberish)
- Date: 2025-11-17

**monitor_stress_test.py**
- Purpose: Monitor long-running stress test progress
- Status: Superseded by better test harnesses
- Date: 2025-11-16

### Full-Scale Testing

These scripts tested complete EPUB-to-audiobook conversion pipelines:

**stress_test_epub_conversion.py**
- Purpose: Full 1,147-chunk audiobook generation with HuggingFace backend
- Status: Archived - too resource-intensive for regular testing
- Result: 67,085 words → ~6.5 hours of audio
- Performance: Abandoned after initial chunks (moved to Q4_K_M GGUF backend)
- Date: 2025-11-16

### Backend Compatibility Tests

These scripts tested different inference engines and models:

**test_hf_15samples.py**
- Purpose: Test HuggingFace backend with 15 different parameter combinations
- Status: Reference data archived
- Backend: bitsandbytes 4-bit quantization
- Sample text: "The forest was eerily quiet. <whisper>Something was watching...</whisper>"
- Result: All 15 samples successful (12.2 minutes total)
- Date: 2025-11-16

**test_hf_model.py**
- Purpose: Simple HuggingFace backend test
- Status: Archived
- Date: 2025-11-14

**test_vllm_15samples.py**
- Purpose: Test vLLM backend with 15 parameter combinations
- Status: Archived - vLLM had quality issues on RTX 2070
- Backend: vLLM with GGUF model
- Result: Failed - audio cuts off and hallucinations
- Date: 2025-11-16

**test_vllm_gguf.py**
- Purpose: Test vLLM GGUF compatibility
- Status: Archived - incompatible with RTX 2070 GPU memory
- Backend: vLLM + GGUF
- Issue: KV cache truncation caused quality degradation
- Date: 2025-11-16

### M4B Format Testing

These scripts tested M4B audiobook creation and concatenation:

**test_m4b_generation.py**
- Purpose: Test M4B file generation from synthesized chunks
- Status: Superseded by test_m4b_combination.py
- Date: 2025-11-17

**test_m4b_simple.py**
- Purpose: Simple M4B creation test
- Status: Superseded
- Date: 2025-11-17

### Configuration & Settings Testing

**test_settings_sweep.py**
- Purpose: Test various generation parameter combinations
- Status: Reference data archived
- Date: 2025-11-16

**test_single_chunk_detailed.py**
- Purpose: Generate and analyze a single chunk in detail
- Status: Archived - replaced by more comprehensive tests
- Date: 2025-11-17

### Setup & Utilities

**create_placeholders.py**
- Purpose: Create placeholder files for missing model assets
- Status: Development utility (no longer needed with real models)
- Date: 2025-11-14

## Active Test Scripts (Root Directory)

The following test scripts are **actively used** and remain in the root folder:

- **test_q4k_model.py** - Q4_K_M GGUF backend verification (3 chunks)
- **test_m4b_combination.py** - M4B creation and distortion testing
- **test_cli.py** - CLI interface testing
- **diagnose_audio.py** - Audio file analysis and diagnostics

## Using Archive Scripts

If you need to refer to or re-run any archived tests:

```bash
# Run an archived test
python test_archive/phase1_chunk_isolation_test.py

# Check logs from previous test runs
less test_archive/*.log
```

## Migration Path

Scripts in this archive document the investigation into:
1. Audio quality issues with HuggingFace backend
2. SNAC token decoding behavior
3. M4B file format creation
4. vLLM compatibility analysis

All findings are summarized in `/docs/CLAUDE.md` under "Backend Testing Results (2025-11-16)".

## Cleanup Status

**Root folder cleaned:** 2025-11-17
- Removed: 13 legacy test scripts
- Archived to: `test_archive/`
- Active scripts remaining: 6
- Documentation consolidated in: `docs/`

---

**Archive Last Updated:** 2025-11-17
**Status:** Complete - Project ready for production audiobook generation

