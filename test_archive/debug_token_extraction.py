#!/usr/bin/env python3
"""
Debug script to analyze token generation and SNAC extraction
for the 4 test chunks to understand why audio is missing/corrupted.
"""
import sys
sys.path.insert(0, '/mnt/Games/MayaBook')

from core.epub_extract import extract_text
from core.chunking import chunk_text
from core.tts_maya1_hf import synthesize_chunk_hf, _extract_snac_ids, _unpack_snac_from_7
from core.maya1_constants import CODE_END_TOKEN_ID, SNAC_MIN_ID, SNAC_MAX_ID
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from snac import SNAC
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print("="*100)
print("DEBUG: TOKEN GENERATION AND SNAC EXTRACTION ANALYSIS")
print("="*100)

# Extract and chunk
epub_path = "assets/test/Zero Combat, Max Crafting_ The - GordanWizard.epub"
text = extract_text(epub_path)
chunks = chunk_text(text, max_words=70)

# Load model once
print("\nLoading HuggingFace model...")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)
model = AutoModelForCausalLM.from_pretrained(
    "assets/models/maya1_4bit_safetensor",
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)
model.eval()
tokenizer = AutoTokenizer.from_pretrained("assets/models/maya1_4bit_safetensor", trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

device = next(model.parameters()).device
print(f"✓ Model loaded on {device}")

# Test chunks
test_chunks = [1, 100, 485, 486]

for chunk_num in test_chunks:
    print(f"\n{'='*100}")
    print(f"CHUNK {chunk_num} TOKEN ANALYSIS")
    print(f"{'='*100}")

    idx = chunk_num - 1
    chunk_text = chunks[idx]

    print(f"\nText ({len(chunk_text.split())} words): {chunk_text[:80]}...")

    # Build prompt (same as tts_maya1_hf.py)
    from core.maya1_constants import SOH_ID, EOH_ID, SOA_ID, TEXT_EOT_ID, CODE_START_TOKEN_ID

    prompt = f'<description="A mature female voice, clear and expressive, with good pacing"> {chunk_text}'
    prompt_tokens = tokenizer.encode(prompt, add_special_tokens=False)
    full_tokens = [SOH_ID, tokenizer.bos_token_id, *prompt_tokens, TEXT_EOT_ID, EOH_ID, SOA_ID, CODE_START_TOKEN_ID]

    print(f"  Input tokens: {len(full_tokens)} (prompt: {len(prompt_tokens)})")

    # Generate
    torch.cuda.empty_cache()  # Apply the fix

    input_ids = torch.tensor([full_tokens], dtype=torch.long, device=device)

    with torch.inference_mode():
        output = model.generate(
            input_ids,
            max_new_tokens=2500,
            min_new_tokens=28,
            temperature=0.45,
            top_p=0.92,
            do_sample=True,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=CODE_END_TOKEN_ID,
        )

    # Extract tokens
    gen_ids = output[0][len(full_tokens):].tolist()
    print(f"  Generated tokens: {len(gen_ids)}")
    print(f"    First 10: {gen_ids[:10]}")
    print(f"    Last 10:  {gen_ids[-10:]}")

    # Check for CODE_END
    has_end_token = CODE_END_TOKEN_ID in gen_ids
    print(f"  Has CODE_END_TOKEN ({CODE_END_TOKEN_ID}): {has_end_token}")

    if has_end_token:
        end_pos = gen_ids.index(CODE_END_TOKEN_ID)
        print(f"    Position: {end_pos}/{len(gen_ids)}")

    # Extract SNAC tokens
    snac_ids = _extract_snac_ids(gen_ids)
    print(f"  SNAC tokens: {len(snac_ids)}")
    print(f"    Range: {SNAC_MIN_ID} to {SNAC_MAX_ID}")

    if snac_ids:
        print(f"    Min ID: {min(snac_ids)}, Max ID: {max(snac_ids)}")
        print(f"    First 10: {snac_ids[:10]}")
        print(f"    Last 10:  {snac_ids[-10:]}")

    # Unpack SNAC
    L1, L2, L3 = _unpack_snac_from_7(snac_ids)
    print(f"  Unpacked SNAC: L1={len(L1)}, L2={len(L2)}, L3={len(L3)}")
    print(f"    Expected frames: ~{len(snac_ids) // 7}")
    print(f"    Actual frames: {len(L1)} (L1 layers)")

    # Estimate duration
    duration_sec = len(L1) / 24000 * 1024  # Rough approximation
    print(f"  Estimated duration: ~{duration_sec/24:.1f}s (based on L1 codes)")

print("\n" + "="*100)
print("TOKEN ANALYSIS COMPLETE")
print("="*100)
