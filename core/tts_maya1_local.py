# core/tts_maya1_local.py
import tempfile, torch, soundfile as sf
from llama_cpp import Llama
from snac import SNAC
from .maya1_constants import (
SOH_ID, EOH_ID, SOA_ID, TEXT_EOT_ID,
CODE_START_TOKEN_ID, CODE_END_TOKEN_ID, CODE_TOKEN_OFFSET,
SNAC_MIN_ID, SNAC_MAX_ID, SNAC_TOKENS_PER_FRAME,
)

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
    payload = f'<|user|>\n{description.strip()}\n<|user|>\n{text.strip()}'
    payload_tokens = llm.tokenize(payload.encode("utf-8"), add_bos=False)
    return [SOH_ID, llm.token_bos(), *payload_tokens, TEXT_EOT_ID, EOH_ID, SOA_ID, CODE_START_TOKEN_ID]

def _extract_snac_ids(token_ids: list[int]) -> list[int]:
    try:
        end = token_ids.index(CODE_END_TOKEN_ID)
    except ValueError:
        end = len(token_ids)
    return [t for t in token_ids[:end] if SNAC_MIN_ID <= t <= SNAC_MAX_ID]

def _unpack_snac_from_7(snac_ids: list[int]):
    if snac_ids and snac_ids[-1] == CODE_END_TOKEN_ID:
        snac_ids = snac_ids[:-1]
    frames = len(snac_ids) // SNAC_TOKENS_PER_FRAME
    if frames == 0:
        return [[], [], []]
    l1, l2, l3 = [], [], []
    for i in range(frames):
        s = snac_ids[i*7:(i+1)*7]
        l1.append((s[0] - CODE_TOKEN_OFFSET) % 4096)
        l2.extend([(s[1] - CODE_TOKEN_OFFSET) % 4096, (s[2] - CODE_TOKEN_OFFSET) % 4096])
        l3.extend([(s[3] - CODE_TOKEN_OFFSET) % 4096, (s[4] - CODE_TOKEN_OFFSET) % 4096,
        (s[5] - CODE_TOKEN_OFFSET) % 4096, (s[6] - CODE_TOKEN_OFFSET) % 4096])
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
    gen_ids = out["choices"][0]["completion_tokens"]

    snac_ids = _extract_snac_ids(gen_ids)
    L1, L2, L3 = _unpack_snac_from_7(snac_ids)
    if not L1 or not L2 or not L3:
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

    if audio.shape[0] > 2048:
        audio = audio[2048:]

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(tmp.name, audio, 24000)
    tmp.flush(); tmp.close()
    return tmp.name
