# core/tts_maya1_local.py
import tempfile, torch, soundfile as sf
import logging
from llama_cpp import Llama
from snac import SNAC
from .maya1_constants import (
SOH_ID, EOH_ID, SOA_ID, TEXT_EOT_ID,
CODE_START_TOKEN_ID, CODE_END_TOKEN_ID, CODE_TOKEN_OFFSET,
SNAC_MIN_ID, SNAC_MAX_ID, SNAC_TOKENS_PER_FRAME,
)

logger = logging.getLogger(__name__)

_llm = None
_snac = None

def _ensure_models(model_path: str, n_ctx: int = 4096, n_gpu_layers: int | None = None):
    global _llm, _snac
    if _llm is None:
        _llm = Llama(
        model_path=model_path,
        n_ctx=n_ctx,
        seed=0,
        logits_all=False,
        n_gpu_layers=-1 if n_gpu_layers is None else n_gpu_layers,
    )
    if _snac is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _snac = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval().to(device)
    return _llm, _snac

def _build_prompt_tokens(llm, description: str, text: str) -> list[int]:
    # Use the recommended format: <description="voice_desc"> text
    # This format is proven to work better for Maya1 TTS
    payload = f'<description="{description.strip()}"> {text.strip()}'
    logger.debug(f"Prompt payload: {payload[:200]}...")
    payload_tokens = llm.tokenize(payload.encode("utf-8"), add_bos=False)
    logger.debug(f"Payload tokenized to {len(payload_tokens)} tokens")
    full_tokens = [SOH_ID, llm.token_bos(), *payload_tokens, TEXT_EOT_ID, EOH_ID, SOA_ID, CODE_START_TOKEN_ID]
    logger.debug(f"Full prompt: {len(full_tokens)} tokens total")
    return full_tokens

def _extract_snac_ids(token_ids: list[int]) -> list[int]:
    try:
        end = token_ids.index(CODE_END_TOKEN_ID)
    except ValueError:
        end = len(token_ids)
    return [t for t in token_ids[:end] if SNAC_MIN_ID <= t <= SNAC_MAX_ID]

def _unpack_snac_from_7(snac_ids: list[int]):
    """
    Unpack 7-token SNAC frames into 3-level hierarchical codes.
    CRITICAL: Order must match Maya1's expected format!
    Frame structure: [L1, L2a, L3a, L3b, L2b, L3c, L3d]
    """
    if snac_ids and snac_ids[-1] == CODE_END_TOKEN_ID:
        snac_ids = snac_ids[:-1]

    frames = len(snac_ids) // SNAC_TOKENS_PER_FRAME
    # Trim to exact frame boundary
    snac_ids = snac_ids[:frames * SNAC_TOKENS_PER_FRAME]

    if frames == 0:
        return [[], [], []]

    l1, l2, l3 = [], [], []
    for i in range(frames):
        s = snac_ids[i*7:(i+1)*7]
        # Correct unpacking order (verified from maya-research reference implementation):
        # slots: [0]   [1]   [2]   [3]   [4]   [5]   [6]
        #        L1    L2a   L3a   L3b   L2b   L3c   L3d
        l1.append((s[0] - CODE_TOKEN_OFFSET) % 4096)
        l2.extend([
            (s[1] - CODE_TOKEN_OFFSET) % 4096,  # L2a
            (s[4] - CODE_TOKEN_OFFSET) % 4096,  # L2b (NOT s[2]!)
        ])
        l3.extend([
            (s[2] - CODE_TOKEN_OFFSET) % 4096,  # L3a
            (s[3] - CODE_TOKEN_OFFSET) % 4096,  # L3b
            (s[5] - CODE_TOKEN_OFFSET) % 4096,  # L3c
            (s[6] - CODE_TOKEN_OFFSET) % 4096,  # L3d
        ])
    return [l1, l2, l3]

def synthesize_chunk_local(
    model_path: str,
    text: str,
    voice_description: str,
    temperature: float = 0.4,
    top_p: float = 0.9,
    max_tokens: int = 2048,
    n_ctx: int = 4096,
    n_gpu_layers: int | None = None,
) -> str:
    llm, snac_model = _ensure_models(model_path, n_ctx=n_ctx, n_gpu_layers=n_gpu_layers)
    prompt_tokens = _build_prompt_tokens(llm, voice_description, text)

    out = llm(
        prompt=prompt_tokens,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        repeat_penalty=1.1,
        echo=False,
    )

    # Debug: log the output structure to understand what keys are available
    logger.debug(f"LLM output keys: {out.keys() if hasattr(out, 'keys') else type(out)}")
    if "choices" in out:
        logger.debug(f"Choices[0] keys: {out['choices'][0].keys()}")

    # Try different possible key names for the generated tokens
    try:
        gen_ids = out["choices"][0]["completion_tokens"]
    except KeyError:
        # Alternative key names used by llama-cpp-python
        if "tokens" in out["choices"][0]:
            gen_ids = out["choices"][0]["tokens"]
            logger.debug("Using 'tokens' key")
        elif "text" in out["choices"][0]:
            # If we only have text, we need to tokenize it back
            text_output = out["choices"][0]["text"]
            gen_ids = llm.tokenize(text_output.encode("utf-8"), add_bos=False)
            logger.debug("Using 'text' key (re-tokenized)")
        else:
            logger.error(f"Available keys in choices[0]: {list(out['choices'][0].keys())}")
            raise KeyError("Could not find tokens in LLM output. Check available keys in log.")

    logger.debug(f"Generated {len(gen_ids)} total tokens")
    snac_ids = _extract_snac_ids(gen_ids)
    logger.debug(f"Extracted {len(snac_ids)} SNAC audio tokens")

    L1, L2, L3 = _unpack_snac_from_7(snac_ids)
    logger.debug(f"Unpacked SNAC: L1={len(L1)}, L2={len(L2)}, L3={len(L3)} codes")

    if not L1 or not L2 or not L3:
        logger.error(f"No audio frames produced. Gen_ids sample: {gen_ids[:20]}")
        raise RuntimeError("No audio frames produced (check description/prompt shape).")

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

    # Flatten/squeeze the audio to 1D array for soundfile
    # Expected shape from SNAC decoder might be (1, 1, samples) or (1, samples)
    audio = audio.squeeze()  # Remove all dimensions of size 1

    logger.debug(f"Audio shape after squeeze: {audio.shape}")

    if audio.ndim > 1:
        # If still multi-dimensional, take the first channel
        logger.warning(f"Audio still has {audio.ndim} dimensions after squeeze, taking first channel")
        audio = audio[0]

    if len(audio) > 2048:
        audio = audio[2048:]

    logger.debug(f"Final audio shape: {audio.shape}, duration: {len(audio)/24000:.2f}s")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(tmp.name, audio, 24000)
    tmp.flush(); tmp.close()
    return tmp.name
