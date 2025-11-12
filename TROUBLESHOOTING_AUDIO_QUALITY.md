# Troubleshooting Audio Quality Issues

## Problem: Garbled or Poor Quality Audio

If you're experiencing garbled, unclear, or poor quality audio output, here are the known issues and solutions:

---

## Issue 1: Emotion Tags Being Vocalized

**Symptom**: When using emotion tags like `<laugh>`, `<cry>`, you hear the tags spoken literally ("less than laugh greater than") instead of emotional inflection.

**Cause**: The GGUF quantized version of Maya1 treats emotion tags as regular text, unlike the full HuggingFace Transformers version.

**Solution**:
- **Don't use emotion tags with GGUF models**
- Instead, describe the emotion in the voice description:
  ```
  Voice: "Female voice, cheerful and laughing"
  Text: "That's hilarious!"
  ```

---

## Issue 2: Incorrect Prompt Format

**Symptom**: Audio sounds robotic, unnatural, or doesn't match the voice description well.

**Possible Cause**: The prompt format may need adjustment for your specific GGUF model.

**Current Format**:
```
<description="voice_desc"> text_to_synthesize
```

**Alternative Formats to Try**:

### Option A: Original format (revert)
```python
# In tts_maya1_local.py:
payload = f'<|user|>\n{description.strip()}\n<|user|>\n{text.strip()}'
```

### Option B: Simpler format
```python
payload = f'{description.strip()}\n{text.strip()}'
```

### Option C: No description wrapper
```python
payload = text.strip()
# And put voice description as a system message or separate
```

---

## Issue 3: Too Many or Too Few Generated Tokens

**Symptom**: Audio cuts off mid-sentence OR has long silence/garbled noise at the end.

**Solution**: Adjust `max_tokens` parameter:
- **Too short (cuts off)**: Increase to 3000-4000
- **Too long (garbled ending)**: Decrease to 1500-2000
- **Current default**: 3000

```bash
python test_cli.py --max-tokens 2000
```

---

## Issue 4: Model Quantization Quality

**Symptom**: Overall poor audio quality, robotic voice, artifacts.

**Cause**: Q5_K_M quantization may lose quality compared to higher quantizations or full model.

**Solutions**:
1. Try a less quantized model:
   - Q6_K (better quality, more VRAM)
   - Q8_0 (even better, more VRAM)
   - Full F16 model (best quality, ~6GB VRAM)

2. Download from: https://huggingface.co/mradermacher/maya1-i1-GGUF

---

## Issue 5: Voice Description Not Effective

**Symptom**: Generated voice doesn't match your description.

**Solutions**:

###Human: can you list the files we've changed this session in itemized list with descriptions