# core/tts_maya1_hf.py
"""
HuggingFace Transformers implementation for Maya1 TTS
Uses 4-bit quantized safetensor model for better quality and emotion tag support
"""
import tempfile
import torch
import soundfile as sf
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer
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
        device = "cuda" if torch.cuda.is_available() else "cpu"

        # Load model with 4-bit quantization
        _model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True,
        )
        _model.eval()
        logger.info(f"Model loaded on device: {device}")

    if _tokenizer is None:
        logger.info("Loading tokenizer...")
        _tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
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
    try:
        end = token_ids.index(CODE_END_TOKEN_ID)
    except ValueError:
        end = len(token_ids)
    return [t for t in token_ids[:end] if SNAC_MIN_ID <= t <= SNAC_MAX_ID]

def _unpack_snac_from_7(snac_ids: list[int]):
    """
    Unpack 7-token SNAC frames into 3-level hierarchical codes.
    Frame structure: [L1, L2a, L3a, L3b, L2b, L3c, L3d]
    """
    if snac_ids and snac_ids[-1] == CODE_END_TOKEN_ID:
        snac_ids = snac_ids[:-1]

    frames = len(snac_ids) // SNAC_TOKENS_PER_FRAME
    snac_ids = snac_ids[:frames * SNAC_TOKENS_PER_FRAME]

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
    temperature: float = 0.4,
    top_p: float = 0.9,
    max_tokens: int = 2500,
) -> str:
    """
    Synthesize audio using HuggingFace Transformers model

    Args:
        model_path: Path to HF model directory (with config.json, model.safetensors, etc.)
        text: Text to synthesize (can include emotion tags like <laugh>, <cry>)
        voice_description: Natural language voice description
        temperature: Sampling temperature (0.3-0.5 recommended)
        top_p: Top-p sampling (0.9 recommended)
        max_tokens: Maximum tokens to generate

    Returns:
        Path to generated WAV file
    """
    model, tokenizer, snac_model = _ensure_models(model_path)

    # Build prompt
    prompt = _build_prompt(voice_description, text)
    logger.debug(f"Prompt: {prompt[:200]}...")

    # Tokenize with special tokens
    prompt_tokens = tokenizer.encode(prompt, add_special_tokens=False)
    full_tokens = [SOH_ID, tokenizer.bos_token_id, *prompt_tokens, TEXT_EOT_ID, EOH_ID, SOA_ID, CODE_START_TOKEN_ID]

    logger.debug(f"Full prompt: {len(full_tokens)} tokens")

    # Convert to tensor
    device = next(model.parameters()).device
    input_ids = torch.tensor([full_tokens], dtype=torch.long, device=device)

    # Generate
    logger.debug("Starting generation...")
    with torch.no_grad():
        output = model.generate(
            input_ids,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    # Extract generated tokens
    gen_ids = output[0][len(full_tokens):].tolist()
    logger.debug(f"Generated {len(gen_ids)} tokens")

    # Extract SNAC tokens
    snac_ids = _extract_snac_ids(gen_ids)
    logger.debug(f"Extracted {len(snac_ids)} SNAC audio tokens")

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

    # Trim initial noise
    if len(audio) > 2048:
        audio = audio[2048:]

    logger.debug(f"Final audio shape: {audio.shape}, duration: {len(audio)/24000:.2f}s")

    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(tmp.name, audio, 24000)
    tmp.flush()
    tmp.close()

    return tmp.name
