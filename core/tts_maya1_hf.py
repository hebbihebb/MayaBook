# core/tts_maya1_hf.py
"""
HuggingFace Transformers implementation for Maya1 TTS
Uses 4-bit quantized safetensor model for better quality and emotion tag support
"""
import tempfile
import torch
import soundfile as sf
import logging
from dataclasses import dataclass
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from snac import SNAC
from .maya1_constants import (
    SOH_ID, EOH_ID, SOA_ID, TEXT_EOT_ID,
    CODE_START_TOKEN_ID, CODE_END_TOKEN_ID, CODE_TOKEN_OFFSET,
    SNAC_MIN_ID, SNAC_MAX_ID, SNAC_TOKENS_PER_FRAME,
)

logger = logging.getLogger(__name__)

_model = None
_tokenizer = None
_snac = None

def _ensure_models(model_path: str):
    """Load HuggingFace model, tokenizer, and SNAC codec"""
    global _model, _tokenizer, _snac

    if _model is None:
        logger.info(f"Loading HuggingFace model from {model_path}...")

        if torch.cuda.is_available():
            logger.info("Loading model on CUDA with bitsandbytes 4-bit quantization")

            # Configure 4-bit quantization for GPU
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,  # GTX 2070 (Turing CC 7.5) has native FP16 support, not bfloat16
            )

            # Load model with 4-bit quantization on GPU
            _model = AutoModelForCausalLM.from_pretrained(
                model_path,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
            )
            logger.info("Using bitsandbytes 4-bit GPU kernels")
            logger.info(f"Model device: {next(_model.parameters()).device}")
        else:
            logger.warning("CUDA not available, loading on CPU (this will be slow)")
            _model = AutoModelForCausalLM.from_pretrained(
                model_path,
                device_map="cpu",
                torch_dtype=torch.float32,
                trust_remote_code=True,
            )

        _model.eval()

    if _tokenizer is None:
        logger.info("Loading tokenizer...")
        _tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

        # Set pad token if not set
        if _tokenizer.pad_token is None:
            _tokenizer.pad_token = _tokenizer.eos_token
            logger.info(f"Set pad_token to eos_token: {_tokenizer.eos_token}")

        logger.info("Tokenizer loaded")

    if _snac is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading SNAC codec on {device}...")
        _snac = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval().to(device)
        logger.info("SNAC codec loaded")

    return _model, _tokenizer, _snac

def _build_prompt(description: str, text: str) -> str:
    """
    Build prompt for Maya1 HF model
    Format: <description="voice_desc"> text_with_emotion_tags
    """
    # HF model should handle emotion tags correctly, so we keep them
    return f'<description="{description.strip()}"> {text.strip()}'

def _extract_snac_ids(token_ids: list[int]) -> list[int]:
    """Extract SNAC audio tokens from generated token IDs"""
    return _prepare_snac_frames(token_ids).snac_ids

@dataclass
class SnacFramePreparation:
    snac_ids: list[int]
    code_end_index: int | None
    residual_before_padding: int
    padded_tokens: int
    discarded_tokens: int

def _prepare_snac_frames(gen_ids: list[int]) -> SnacFramePreparation:
    """
    Extract SNAC tokens, detect early CODE_END, and pad partial frames.
    """
    try:
        start_idx = gen_ids.index(CODE_START_TOKEN_ID) + 1
    except ValueError:
        start_idx = 0

    code_end_index = next((i for i, t in enumerate(gen_ids[start_idx:], start=start_idx) if t == CODE_END_TOKEN_ID), None)
    if code_end_index is not None:
        logger.info(
            "CODE_END_TOKEN_ID encountered at generated index %d", code_end_index
        )
    else:
        logger.info("CODE_END_TOKEN_ID not found in generated tokens")

    cutoff = code_end_index if code_end_index is not None else len(gen_ids)
    snac_candidates = [t for t in gen_ids[start_idx:cutoff] if SNAC_MIN_ID <= t <= SNAC_MAX_ID]

    residual = len(snac_candidates) % SNAC_TOKENS_PER_FRAME
    padded_tokens = 0
    discarded_tokens = 0

    if residual:
        logger.warning(
            "Partial SNAC frame detected: %d residual token(s) before padding",
            residual,
        )
        if code_end_index is not None:
            logger.warning(
                "CODE_END_TOKEN_ID arrived before completing a full SNAC frame; padding final frame"
            )
        if snac_candidates:
            padded_tokens = SNAC_TOKENS_PER_FRAME - residual
            snac_candidates.extend([snac_candidates[-1]] * padded_tokens)
            logger.info(
                "Padded final SNAC frame with %d token(s) using last available token",
                padded_tokens,
            )
        else:
            discarded_tokens = residual

    return SnacFramePreparation(
        snac_ids=snac_candidates,
        code_end_index=code_end_index,
        residual_before_padding=residual,
        padded_tokens=padded_tokens,
        discarded_tokens=discarded_tokens,
    )

def _apply_fade_and_trim(audio, trim_samples: int | None = 512, fade_samples: int = 320):
    """
    Soft-trim initial codec warmup and fade edges to avoid clicks when concatenating chunks.
    """
    if trim_samples is not None and len(audio) > trim_samples:
        audio = audio[trim_samples:]

    fade = min(fade_samples, len(audio) // 4)
    if fade > 0:
        ramp = torch.linspace(0.0, 1.0, fade, device="cpu", dtype=torch.float32).numpy()
        audio[:fade] *= ramp
        audio[-fade:] *= ramp[::-1]
    return audio

def _unpack_snac_from_7(snac_ids: list[int]):
    """
    Unpack 7-token SNAC frames into 3-level hierarchical codes.
    Frame structure: [L1, L2a, L3a, L3b, L2b, L3c, L3d]
    """
    frames = len(snac_ids) // SNAC_TOKENS_PER_FRAME

    if frames == 0:
        return [[], [], []]

    l1, l2, l3 = [], [], []
    for i in range(frames):
        s = snac_ids[i*7:(i+1)*7]
        l1.append((s[0] - CODE_TOKEN_OFFSET) % 4096)
        l2.extend([
            (s[1] - CODE_TOKEN_OFFSET) % 4096,  # L2a
            (s[4] - CODE_TOKEN_OFFSET) % 4096,  # L2b
        ])
        l3.extend([
            (s[2] - CODE_TOKEN_OFFSET) % 4096,  # L3a
            (s[3] - CODE_TOKEN_OFFSET) % 4096,  # L3b
            (s[5] - CODE_TOKEN_OFFSET) % 4096,  # L3c
            (s[6] - CODE_TOKEN_OFFSET) % 4096,  # L3d
        ])
    return [l1, l2, l3]

def synthesize_chunk_hf(
    model_path: str,
    text: str,
    voice_description: str,
    temperature: float = 0.5,  # Increased to 0.5 to help break loops
    top_p: float = 0.95,       # Increased to 0.95 for more diversity
    max_tokens: int = 2500,
    trim_samples: int | None = 512,
) -> str:
    """
    Synthesize audio using HuggingFace Transformers model

    Args:
        model_path: Path to HF model directory (with config.json, model.safetensors, etc.)
        text: Text to synthesize (can include emotion tags like <laugh>, <cry>)
        voice_description: Natural language voice description
        temperature: Sampling temperature (0.3-0.5 recommended)
        top_p: Top-p sampling (0.9 recommended)
        max_tokens: Maximum tokens to generate (2500 optimal with smart chunking)
        trim_samples: Number of initial samples to trim from decoded audio (None to disable)

    Returns:
        Path to generated WAV file
    """
    model, tokenizer, snac_model = _ensure_models(model_path)

    # Clear GPU cache to prevent VRAM fragmentation
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        logger.debug("Cleared GPU cache before generation")

    # Build prompt
    prompt = _build_prompt(voice_description, text)
    logger.debug(f"Prompt: {prompt[:200]}...")

    # Tokenize with special tokens
    prompt_tokens = tokenizer.encode(prompt, add_special_tokens=False)
    full_tokens = [SOH_ID, tokenizer.bos_token_id, *prompt_tokens, TEXT_EOT_ID, EOH_ID, SOA_ID, CODE_START_TOKEN_ID]

    logger.debug(f"Full prompt: {len(full_tokens)} tokens")

    # Convert to tensor and move to model device
    device = next(model.parameters()).device
    input_ids = torch.tensor([full_tokens], dtype=torch.long, device=device)

    # Log generation start with device info
    logger.info(f"Generation started on GPU device {device}" if device.type == "cuda" else f"Generation started on {device}")
    logger.debug(f"Input shape: {input_ids.shape}, device: {input_ids.device}")

    # Ensure no KV cache is carried across chunks
    use_cache = True
    if hasattr(model, "flush_kv_cache"):
        logger.debug("Flushing model KV cache via flush_kv_cache()")
        model.flush_kv_cache()
    elif hasattr(model, "generation_cache"):
        cache = getattr(model, "generation_cache")
        if cache is not None:
            if hasattr(cache, "reset"):
                logger.debug("Resetting model generation_cache via reset()")
                cache.reset()
            elif hasattr(cache, "flush"):
                logger.debug("Flushing model generation_cache via flush()")
                cache.flush()
            elif hasattr(cache, "clear"):
                logger.debug("Clearing model generation_cache via clear()")
                cache.clear()
            else:
                logger.debug("Generation cache present but no reset/flush/clear method; disabling use_cache for generation")
                use_cache = False
    else:
        logger.debug("No cache flush available; relying on generate() to create fresh cache")
        # Do NOT disable use_cache - standard HF generate() creates fresh cache anyway
        # Disabling it causes massive slowdown (recomputing context every token)
        use_cache = True

    # Generate - use CODE_END as EOS (as per official implementation)
    with torch.inference_mode():
        output = model.generate(
            input_ids,
            max_new_tokens=max_tokens,
            min_new_tokens=28,  # At least 4 SNAC frames
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
            repetition_penalty=1.2,  # Reduced from 1.3 (too high causes gibberish) but > 1.1 (loops)
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=CODE_END_TOKEN_ID,  # Stop at end of speech token (official way)
            use_cache=use_cache,
        )

    # Extract generated tokens
    gen_ids = output[0][len(full_tokens):].tolist()
    logger.debug(f"Generated {len(gen_ids)} tokens")
    logger.debug(f"First 20 generated token IDs: {gen_ids[:20]}")
    logger.debug(f"Last 20 generated token IDs: {gen_ids[-20:]}")

    # Extract SNAC tokens with instrumentation and padding
    snac_prep = _prepare_snac_frames(gen_ids)
    snac_ids = snac_prep.snac_ids
    logger.info(
        "SNAC extraction complete: %d tokens (residual before padding=%d, padded=%d, discarded=%d)",
        len(snac_ids),
        snac_prep.residual_before_padding,
        snac_prep.padded_tokens,
        snac_prep.discarded_tokens,
    )

    # Unpack SNAC codes
    L1, L2, L3 = _unpack_snac_from_7(snac_ids)
    logger.debug(f"Unpacked SNAC: L1={len(L1)}, L2={len(L2)}, L3={len(L3)} codes")

    if not L1 or not L2 or not L3:
        logger.error(f"No audio frames produced. Gen_ids sample: {gen_ids[:20]}")
        raise RuntimeError("No audio frames produced (check description/prompt shape).")

    # Decode with SNAC
    device = next(snac_model.parameters()).device
    with torch.inference_mode():
        codes_tensor = [
            torch.tensor(L1, dtype=torch.long, device=device).unsqueeze(0),
            torch.tensor(L2, dtype=torch.long, device=device).unsqueeze(0),
            torch.tensor(L3, dtype=torch.long, device=device).unsqueeze(0),
        ]
        z_q = snac_model.quantizer.from_codes(codes_tensor)
        audio = snac_model.decoder(z_q).cpu().numpy()

    logger.debug(f"Audio shape before processing: {audio.shape}")

    # Flatten audio
    audio = audio.squeeze()
    logger.debug(f"Audio shape after squeeze: {audio.shape}")

    if audio.ndim > 1:
        logger.warning(f"Audio still has {audio.ndim} dimensions, taking first channel")
        audio = audio[0]

    # Trim initial noise and apply fades for cleaner chunk joins
    audio = _apply_fade_and_trim(audio, trim_samples=trim_samples)

    logger.debug(f"Final audio shape: {audio.shape}, duration: {len(audio)/24000:.2f}s")

    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(tmp.name, audio, 24000)
    tmp.flush()
    tmp.close()

    return tmp.name
