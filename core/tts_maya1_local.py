# core/tts_maya1_local.py
import tempfile, torch, soundfile as sf
import logging
import threading
import numpy as np
import zlib
from dataclasses import dataclass

# Make llama_cpp optional - only needed for GGUF models
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    Llama = None

from snac import SNAC
from .maya1_constants import (
SOH_ID, EOH_ID, SOA_ID, TEXT_EOT_ID,
CODE_START_TOKEN_ID, CODE_END_TOKEN_ID, CODE_TOKEN_OFFSET,
SNAC_MIN_ID, SNAC_MAX_ID, SNAC_TOKENS_PER_FRAME,
)

logger = logging.getLogger(__name__)

_llm = None
_snac = None
_llm_lock = threading.Lock()  # Protect LLM from concurrent access

MAX_GEN_ATTEMPTS = 3
MIN_AUDIO_RMS = 1e-3

def _ensure_models(model_path: str, n_ctx: int = 4096, n_gpu_layers: int | None = None):
    global _llm, _snac
    if _llm is None:
        _llm = Llama(
        model_path=model_path,
        n_ctx=n_ctx,
        seed=0,
        logits_all=False,
        n_gpu_layers=-1 if n_gpu_layers is None else n_gpu_layers,
        flash_attn=True,  # Enable FlashAttention 1.x for GTX 2070 (Turing CC 7.5) - reduces VRAM pressure and accelerates prompt processing
    )
    if _snac is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _snac = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval().to(device)
    return _llm, _snac

def _prompt_seed(text: str, voice_description: str) -> int:
    data = f"{voice_description}\n{text}".encode("utf-8")
    return zlib.crc32(data) & 0x7FFFFFFF

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
    prep = _prepare_snac_frames(token_ids)
    return prep.snac_ids

@dataclass
class SnacFramePreparation:
    snac_ids: list[int]
    code_end_index: int | None
    residual_before_padding: int
    padded_tokens: int
    discarded_tokens: int

def _prepare_snac_frames(gen_ids: list[int]) -> SnacFramePreparation:
    """
    Extract SNAC tokens between CODE_START and CODE_END, pad partial frames to keep decoder input aligned.
    """
    try:
        start_idx = gen_ids.index(CODE_START_TOKEN_ID) + 1
    except ValueError:
        start_idx = 0

    code_end_index = next((i for i, t in enumerate(gen_ids[start_idx:], start=start_idx) if t == CODE_END_TOKEN_ID), None)
    cutoff = code_end_index if code_end_index is not None else len(gen_ids)
    snac_candidates = [t for t in gen_ids[start_idx:cutoff] if SNAC_MIN_ID <= t <= SNAC_MAX_ID]

    residual = len(snac_candidates) % SNAC_TOKENS_PER_FRAME
    padded_tokens = 0
    discarded_tokens = 0

    if residual:
        if snac_candidates:
            padded_tokens = SNAC_TOKENS_PER_FRAME - residual
            snac_candidates.extend([snac_candidates[-1]] * padded_tokens)
        else:
            discarded_tokens = residual

    return SnacFramePreparation(
        snac_ids=snac_candidates,
        code_end_index=code_end_index,
        residual_before_padding=residual,
        padded_tokens=padded_tokens,
        discarded_tokens=discarded_tokens,
    )

def _apply_fade_and_trim(audio: np.ndarray, trim_samples: int = 640, fade_samples: int = 320) -> np.ndarray:
    """
    Remove initial codec warm-up and apply a short fade to avoid clicks between stitched chunks.
    """
    if trim_samples and len(audio) > trim_samples:
        audio = audio[trim_samples:]

    fade = min(fade_samples, len(audio) // 4)
    if fade > 0:
        ramp = np.linspace(0.0, 1.0, fade, dtype=audio.dtype)
        audio[:fade] *= ramp
        audio[-fade:] *= ramp[::-1]
    return audio

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
    if not LLAMA_CPP_AVAILABLE:
        raise RuntimeError(
            "llama-cpp-python is not installed. "
            "GGUF models require llama-cpp-python. "
            "Please use model_type='huggingface' instead, or install llama-cpp-python."
        )
    logger.info(f"Synthesizing text (length={len(text)} chars): {text[:100]}...")
    llm, snac_model = _ensure_models(model_path, n_ctx=n_ctx, n_gpu_layers=n_gpu_layers)
    prompt_tokens = _build_prompt_tokens(llm, voice_description, text)
    base_seed = _prompt_seed(text, voice_description)

    def _generate_audio(seed: int):
        # Use lock to prevent concurrent access to LLM (llama.cpp is not thread-safe)
        with _llm_lock:
            logger.debug(f"Acquired LLM lock, starting generation (seed={seed})...")
            # Reset KV cache to ensure clean state for each generation
            llm.reset()
            out = llm(
                prompt=prompt_tokens,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                repeat_penalty=1.1,
                echo=False,
                seed=seed,
            )
            logger.debug("Generation complete, releasing LLM lock")

        logger.debug(f"LLM output keys: {out.keys() if hasattr(out, 'keys') else type(out)}")
        if "choices" in out:
            logger.debug(f"Choices[0] keys: {out['choices'][0].keys()}")

        choice = out["choices"][0]
        if "completion_tokens" in choice:
            gen_ids = choice["completion_tokens"]
            logger.debug("Using 'completion_tokens' from llama.cpp response")
        elif "tokens" in choice:
            gen_ids = choice["tokens"]
            logger.debug("Using 'tokens' key from llama.cpp response")
        else:
            text_output = choice["text"]
            gen_ids = llm.tokenize(text_output.encode("utf-8"), add_bos=False)
            logger.debug("Using 'text' key (re-tokenized)")

        logger.debug(f"Generated {len(gen_ids)} total tokens")
        snac_prep = _prepare_snac_frames(gen_ids)
        snac_ids = snac_prep.snac_ids
        logger.info(
            "SNAC extraction: %d tokens (residual=%d, padded=%d, discarded=%d, code_end_index=%s)",
            len(snac_ids),
            snac_prep.residual_before_padding,
            snac_prep.padded_tokens,
            snac_prep.discarded_tokens,
            snac_prep.code_end_index if snac_prep.code_end_index is not None else "none",
        )

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

        audio = audio.squeeze()
        if audio.ndim > 1:
            logger.warning(f"Audio still has {audio.ndim} dimensions after squeeze, taking first channel")
            audio = audio[0]

        audio = _apply_fade_and_trim(audio)

        logger.debug(f"Final audio shape: {audio.shape}, duration: {len(audio)/24000:.2f}s")
        return audio

    audio = None
    for attempt in range(MAX_GEN_ATTEMPTS):
        seed = (base_seed + attempt) & 0x7FFFFFFF
        audio = _generate_audio(seed)
        rms = float(np.sqrt(np.mean(np.square(audio))))
        logger.debug(f"Audio RMS for attempt {attempt+1}: {rms:.6f}")
        if rms >= MIN_AUDIO_RMS:
            break
        logger.warning(
            f"Audio RMS {rms:.6f} below threshold ({MIN_AUDIO_RMS}); retrying with new seed"
        )
        audio = None

    if audio is None:
        raise RuntimeError("Unable to synthesize non-silent audio after multiple attempts.")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(tmp.name, audio, 24000)
    tmp.flush(); tmp.close()
    return tmp.name
