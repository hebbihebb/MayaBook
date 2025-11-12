# Maya1 Emotion Tags Guide

⚠️ **CRITICAL LIMITATION**: Emotion tags **DO NOT WORK** with GGUF quantized models. The GGUF version **will vocalize tags as literal text** (e.g., "less than laugh greater than") instead of processing them as emotions.

**Current Status**: Confirmed through testing that emotion tags like `<laugh>`, `<cry>`, `<whisper>`, `<sigh>`, etc. are spoken out loud in the GGUF version.

**Why?** The quantization process that creates GGUF models can lose specialized behaviors like emotion tag processing that were present in the full HuggingFace Transformers model.

## ✅ Solution: Use Voice Descriptions Instead

Instead of embedding emotion tags in text, describe the desired emotion and tone in your **voice description**:

```python
# ❌ DON'T: Use emotion tags (they'll be read out loud)
text = "Hello there! <laugh> That's funny!"

# ✅ DO: Describe emotion in voice description
voice_desc = "Female voice, cheerful and laughing while speaking"
text = "Hello there! That's funny!"
```

### Example Voice Descriptions

**For laughter/joy:**
- "Female voice, cheerful and laughing, warm and friendly tone"
- "Male voice with occasional chuckles, jovial and upbeat"

**For sadness/crying:**
- "Female voice, sad and emotional, verge of tears, gentle and soft"
- "Male voice, melancholic and subdued, slightly shaky"

**For anger:**
- "Female voice, stern and firm, slightly raised volume, tense"
- "Male voice, irritated and sharp, clipped speech"

**For whispers:**
- "Female voice, whispering softly, intimate and hushed"
- "Male voice, speaking in a low whisper, secretive"

---

## About Emotion Tags (for reference)

The original Maya1 model supports inline emotion tags to add expressiveness. These tags can be embedded directly in text.

## Available Emotion Tags

### Basic Emotions
- `<laugh>` - Light laughter
- `<laugh_harder>` - Stronger laughter
- `<cry>` - Crying/sad emotion
- `<angry>` - Angry tone
- `<excited>` - Excited/enthusiastic
- `<curious>` - Questioning/inquisitive
- `<mischievous>` - Playful/teasing

### Vocal Effects
- `<snort>` - Snorting sound
- `<scream>` - Screaming/intense emotion
- `<whisper>` - Whispered speech (if supported)
- `<sigh>` - Sighing sound

## Usage Examples

### In Your Text
```
"I can't believe it!" she said. <laugh> "That's hilarious!"

"What are you doing?" <curious> he asked.

<angry> "Get out of here right now!"

"I miss you so much," <cry> she whispered.
```

### Natural Integration
Tags work best when placed naturally in the flow of speech:

```
He looked at the mess on the floor. <sigh> "I guess I'll clean this up."

"Oh really?" <mischievous> "Tell me more about that."

<excited> "We won! We actually won!"
```

## Best Practices

### 1. **Don't Overuse**
- Use emotion tags sparingly for emphasis
- Too many tags can make speech sound unnatural
- Let the voice description set the base tone

### 2. **Place Naturally**
- Put tags at the beginning of sentences or after dialogue tags
- Avoid interrupting mid-word or mid-phrase

### 3. **Combine with Voice Description**
For best results, combine emotion tags with appropriate voice descriptions:

```python
voice_description = "Female voice in her 30s, warm and expressive, natural American accent"
text = "I can't wait to see you! <excited> It's been so long!"
```

### 4. **Context Matters**
- Use `<laugh>` for lighthearted moments
- Use `<cry>` for emotional scenes
- Use `<angry>` for confrontational dialogue
- Use `<curious>` for questions or uncertainty

## Examples for Audiobooks

### Chapter Opening
```
<sigh> It had been a long day. Sarah walked through the door, exhausted.
```

### Dialogue Scene
```
"You did what?" <angry> Mark's voice rose. "I told you not to!"

"I'm sorry," <cry> she replied. "I didn't know."

<curious> "Wait, what happened here?" John asked as he entered the room.
```

### Narrative with Emotion
```
The treasure was real! <excited> After all these years of searching,
they had finally found it. <laugh> The crew erupted in celebration.
```

## Technical Notes

- Tags are preserved during text chunking
- Tags don't count toward word limits for chunk size
- Multiple tags in sequence are supported
- Tags are case-sensitive (use lowercase)
- Unknown tags may be ignored by the model

## Testing

To test emotion tags, try the CLI:

```bash
python test_cli.py --text "Hello there! <laugh> This is a test. <excited> It works!"
```

## Troubleshooting

**Problem**: Tags appear in the output as text
- **Solution**: Check that tags are properly formatted with `<` and `>`

**Problem**: No emotional effect
- **Solution**: Try placing the tag at a different position, or adjust voice description

**Problem**: Speech sounds unnatural
- **Solution**: Reduce the number of tags, use them more sparingly

---

For more information, see the [Maya1 model documentation](https://huggingface.co/maya-research/maya1).
