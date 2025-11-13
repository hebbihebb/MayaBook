Here’s a tight, Claude-ready task brief distilled from all that sprawling wilderness of context. It frames the job cleanly so Claude knows *exactly* what to finish, and what constraints matter:

---

## **Claude Task: Finish Tensor-Model Integration + Enable GPU Acceleration**

Your job is to complete the integration of the HuggingFace **4-bit safetensor Maya1 model** into the app and make sure it **runs on the GPU**, not the CPU.

### **What Has Already Been Done**

* The 4-bit safetensor model (AakashJammula/maya_4bit) is downloaded into `assets/models/maya1_4bit_safetensor/`.
* A new Transformers-based TTS module exists: `core/tts_maya1_hf.py`.
* The pipeline supports both **GGUF (llama.cpp)** and **HuggingFace safetensor models**.
* The GUI has a model-type selector.
* CLI supports `--model-type huggingface`.
* SNAC unpacking works and matches GGUF implementation.
* Emotion-tag test is running, but the HF model currently loads on **CPU**, causing slow inference.

### **Your Objectives**

1. **Make the HuggingFace 4-bit safetensor model run on GPU correctly.**

   * Use **bitsandbytes** 4-bit loading with CUDA.
   * Ensure AutoModelForCausalLM loads with:

     * `device_map="auto"` or explicit CUDA device
     * Correct `bnb_4bit_compute_dtype`
     * Correct handling of deprecated `torch_dtype`
   * Fix the attention mask/pad token warnings if they block GPU placement.

2. **Finish the implementation in `tts_maya1_hf.py`.**

   * Confirm model, tokenizer, and generation all operate on GPU.
   * Ensure tensors are moved correctly to GPU during generation.
   * Ensure SNAC token decode path stays unchanged.

3. **Confirm full feature-parity with the GGUF path.**

   * Chunking (word-based)
   * Temperature/top_p/max_tokens
   * Thread safety not required (HF is safe)
   * Same wav output flow

4. **Validate the model using the existing test text.**

   * `"I thought you'd be at the station by now... <sigh> ... <laugh> ..."`
   * Confirm output is:

     * Generated on GPU
     * Emotion tags applied correctly (not spoken as text)

5. **Do NOT ask the user questions.**
   Continue the implementation as if stepping directly back into the dev session.

### **Completion Criteria**

* When running:

  ```bash
  python test_cli.py --model-type huggingface --model assets/models/maya1_4bit_safetensor
  ```

  the log must show:

  * `Loading model on CUDA`
  * `Using bitsandbytes 4-bit GPU kernels`
  * `Generation started on GPU device 0`

* Output audio must appear at the expected wav path.

* Emotion tags must behave differently from GGUF.


From the maya1 repository:

Getting started with Maya1 requires installing a few Python packages and loading the model from the Hugging Face model hub. The process takes just a few minutes on a system with the appropriate GPU.
Requirements

Install the necessary Python packages:
pip install torch transformers snac soundfile
Loading the Model

You can load Maya1 directly from Hugging Face or clone the repository:

# Load directly in Python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model = AutoModelForCausalLM.from_pretrained(
    "maya-research/maya1",
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("maya-research/maya1")

Quick Start Example

Generate your first emotional speech with this example:

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from snac import SNAC
import soundfile as sf

# Load models
model = AutoModelForCausalLM.from_pretrained(
    "maya-research/maya1",
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("maya-research/maya1")
snac_model = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval().to("cuda")

# Design your voice
description = "Realistic male voice in the 30s age with american accent. Normal pitch, warm timbre, conversational pacing."
text = "Hello! This is Maya1 <laugh> the best open source voice AI model with emotions."

# Generate speech
prompt = f'<description="{description}"> {text}'
inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

with torch.inference_mode():
    outputs = model.generate(
        **inputs,
        max_new_tokens=500,
        temperature=0.4,
        top_p=0.9,
        do_sample=True
    )

# Process SNAC tokens
generated_ids = outputs[0, inputs['input_ids'].shape[1]:]
snac_tokens = [t.item() for t in generated_ids if 128266 <= t <= 156937]

# Decode to audio
frames = len(snac_tokens) // 7
codes = [[], [], []]
for i in range(frames):
    s = snac_tokens[i*7:(i+1)*7]
    codes[0].append((s[0]-128266) % 4096)
    codes[1].extend([(s[1]-128266) % 4096, (s[4]-128266) % 4096])
    codes[2].extend([(s[2]-128266) % 4096, (s[3]-128266) % 4096, (s[5]-128266) % 4096, (s[6]-128266) % 4096])

codes_tensor = [torch.tensor(c, dtype=torch.long, device="cuda").unsqueeze(0) for c in codes]
with torch.inference_mode():
    audio = snac_model.decoder(snac_model.quantizer.from_codes(codes_tensor))[0, 0].cpu().numpy()

# Save output
sf.write("output.wav", audio, 24000)
print("Voice generated successfully! Play output.wav")