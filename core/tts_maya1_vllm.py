# core/tts_maya1_vllm.py
"""
vLLM implementation for Maya1 TTS
Supports both GGUF (experimental) and HuggingFace safetensor models
Key advantages: thread-safe, better batching, efficient memory usage via PagedAttention
"""
import tempfile
import torch
import soundfile as sf
import logging
import numpy as np
import zlib
from typing import Optional

# Make vLLM optional
try:
    from vllm import LLM, SamplingParams
    VLLM_AVAILABLE = True
except ImportError:
    VLLM_AVAILABLE = False
    LLM = None
    SamplingParams = None

from snac import SNAC
from .maya1_constants import (
    SOH_ID, EOH_ID, SOA_ID, TEXT_EOT_ID,
    CODE_START_TOKEN_ID, CODE_END_TOKEN_ID, CODE_TOKEN_OFFSET,
    SNAC_MIN_ID, SNAC_MAX_ID, SNAC_TOKENS_PER_FRAME,
)

logger = logging.getLogger(__name__)

_llm = None
_snac = None

MAX_GEN_ATTEMPTS = 3
MIN_AUDIO_RMS = 1e-3

def _ensure_models(
    model_path: str,
    tokenizer_path: Optional[str] = None,
    gpu_memory_utilization: float = 0.9,
    tensor_parallel_size: int = 1,
):
    """
    Load vLLM model and SNAC codec

    Args:
        model_path: Path to model (GGUF file or HuggingFace directory)
        tokenizer_path: Path to tokenizer (required for GGUF models, optional for HF)
        gpu_memory_utilization: GPU memory fraction to use (0.0-1.0)
        tensor_parallel_size: Number of GPUs for tensor parallelism
    """
    global _llm, _snac

    if _llm is None:
        if not VLLM_AVAILABLE:
            raise RuntimeError(
                "vLLM is not installed. "
                "Please install it with: pip install vllm"
            )

        logger.info(f"Loading vLLM model from {model_path}...")

        # Detect if GGUF or HuggingFace model
        is_gguf = model_path.endswith('.gguf')

        if is_gguf:
            if not tokenizer_path:
                raise ValueError(
                    "GGUF models require a separate tokenizer. "
                    "Please specify tokenizer_path (e.g., 'TinyLlama/TinyLlama-1.1B-Chat-v1.0')"
                )
            logger.info(f"Loading GGUF model with tokenizer from {tokenizer_path}")
            logger.warning("vLLM GGUF support is experimental and may have limitations")

            _llm = LLM(
                model=model_path,
                tokenizer=tokenizer_path,
                gpu_memory_utilization=gpu_memory_utilization,
                tensor_parallel_size=tensor_parallel_size,
                trust_remote_code=True,
                max_model_len=4096,  # Default context size
            )
        else:
            # HuggingFace model
            logger.info("Loading HuggingFace model with vLLM")

            llm_kwargs = {
                "model": model_path,
                "gpu_memory_utilization": gpu_memory_utilization,
                "tensor_parallel_size": tensor_parallel_size,
                "trust_remote_code": True,
                "max_model_len": 4096,
            }

            if tokenizer_path:
                llm_kwargs["tokenizer"] = tokenizer_path

            _llm = LLM(**llm_kwargs)

        logger.info("vLLM model loaded successfully")
        logger.info(f"Model supports {_llm.llm_engine.tokenizer.vocab_size} tokens")

    if _snac is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading SNAC codec on {device}...")
        _snac = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval().to(device)
        logger.info("SNAC codec loaded")

    return _llm, _snac

def _prompt_seed(text: str, voice_description: str) -> int:
    """Generate deterministic seed from text and voice description"""
    data = f"{voice_description}\n{text}".encode("utf-8")
    return zlib.crc32(data) & 0x7FFFFFFF

def _build_prompt_tokens(llm, description: str, text: str) -> list[int]:
    """
    Build prompt tokens for Maya1 TTS
    Format: <SOH> <BOS> <description="voice_desc"> text <TEXT_EOT> <EOH> <SOA> <CODE_START>
    """
    payload = f'<description="{description.strip()}"> {text.strip()}'
    logger.debug(f"Prompt payload: {payload[:200]}...")

    # Get tokenizer from vLLM
    tokenizer = llm.llm_engine.tokenizer.tokenizer
    payload_tokens = tokenizer.encode(payload, add_special_tokens=False)
    logger.debug(f"Payload tokenized to {len(payload_tokens)} tokens")

    # Get BOS token ID
    bos_token_id = tokenizer.bos_token_id if hasattr(tokenizer, 'bos_token_id') else 1

    full_tokens = [
        SOH_ID,
        bos_token_id,
        *payload_tokens,
        TEXT_EOT_ID,
        EOH_ID,
        SOA_ID,
        CODE_START_TOKEN_ID
    ]
    logger.debug(f"Full prompt: {len(full_tokens)} tokens total")
    return full_tokens

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

def synthesize_chunk_vllm(
    model_path: str,
    text: str,
    voice_description: str,
    temperature: float = 0.4,
    top_p: float = 0.9,
    max_tokens: int = 2500,
    tokenizer_path: Optional[str] = None,
    gpu_memory_utilization: float = 0.9,
    tensor_parallel_size: int = 1,
) -> str:
    """
    Synthesize audio using vLLM engine

    Args:
        model_path: Path to model (GGUF file or HuggingFace directory)
        text: Text to synthesize
        voice_description: Natural language voice description
        temperature: Sampling temperature (0.3-0.5 recommended)
        top_p: Top-p sampling (0.9 recommended)
        max_tokens: Maximum tokens to generate
        tokenizer_path: Path to tokenizer (required for GGUF, optional for HF)
        gpu_memory_utilization: GPU memory fraction to use
        tensor_parallel_size: Number of GPUs for tensor parallelism

    Returns:
        Path to generated WAV file
    """
    if not VLLM_AVAILABLE:
        raise RuntimeError(
            "vLLM is not installed. "
            "Please install it with: pip install vllm"
        )

    logger.info(f"Synthesizing text (length={len(text)} chars): {text[:100]}...")

    llm, snac_model = _ensure_models(
        model_path=model_path,
        tokenizer_path=tokenizer_path,
        gpu_memory_utilization=gpu_memory_utilization,
        tensor_parallel_size=tensor_parallel_size,
    )

    # Build prompt tokens
    prompt_tokens = _build_prompt_tokens(llm, voice_description, text)
    base_seed = _prompt_seed(text, voice_description)

    def _generate_audio(seed: int):
        """Generate audio with specified seed"""
        logger.debug(f"Starting vLLM generation (seed={seed})...")

        # vLLM sampling parameters
        sampling_params = SamplingParams(
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            repetition_penalty=1.1,
            seed=seed,
            stop_token_ids=[CODE_END_TOKEN_ID],  # Stop at end of speech
        )

        # Generate using vLLM (thread-safe, no lock needed!)
        outputs = llm.generate(
            prompt_token_ids=[prompt_tokens],
            sampling_params=sampling_params,
            use_tqdm=False,
        )

        # Extract generated tokens
        gen_ids = outputs[0].outputs[0].token_ids
        logger.debug(f"Generated {len(gen_ids)} total tokens")

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

        # Process audio
        audio = audio.squeeze()
        if audio.ndim > 1:
            logger.warning(f"Audio still has {audio.ndim} dimensions, taking first channel")
            audio = audio[0]

        # Trim initial noise
        if len(audio) > 2048:
            audio = audio[2048:]

        logger.debug(f"Final audio shape: {audio.shape}, duration: {len(audio)/24000:.2f}s")
        return audio

    # RMS quality check with retries
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

    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(tmp.name, audio, 24000)
    tmp.flush()
    tmp.close()

    logger.info(f"Audio synthesized successfully: {tmp.name}")
    return tmp.name
