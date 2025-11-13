# core/voice_presets.py
"""
Voice preset library for MayaBook TTS synthesis.

Each preset contains:
- name: Display name for the UI
- description: The actual voice prompt sent to Maya1 TTS
- category: Grouping for organization (male/female/neutral, age range, style)
"""

# Voice presets organized by category
VOICE_PRESETS = [
    {
        "name": "Professional Female Narrator",
        "description": "A female speaker with a warm, calm, and clear voice, delivering the narration in a standard American English accent. Her tone is engaging and pleasant, suitable for long listening sessions.",
        "category": "female_professional",
        "age": "40s",
        "accent": "American",
    },
    {
        "name": "Authoritative Male (Morgan Freeman-style)",
        "description": "A deep, resonant male voice in his 60s with a commanding yet warm presence. He speaks with a refined American accent, delivering each word with gravitas and authority, perfect for dramatic narration and non-fiction.",
        "category": "male_professional",
        "age": "60s",
        "accent": "American",
    },
    {
        "name": "Young Adult Female (Energetic)",
        "description": "A bright, energetic female voice in her early 20s with excellent articulation. Her delivery is expressive and dynamic, with a contemporary American accent that's perfect for young adult fiction and romance novels.",
        "category": "female_young",
        "age": "20s",
        "accent": "American",
    },
    {
        "name": "Distinguished British Male",
        "description": "A mature male speaker with a distinguished Received Pronunciation British accent. His voice is cultured and articulate, ideal for classical literature, historical fiction, and mystery novels.",
        "category": "male_professional",
        "age": "50s",
        "accent": "British",
    },
    {
        "name": "Soothing Female (Bedtime Stories)",
        "description": "A gentle, soothing female voice with a soft, melodic quality. She speaks slowly and calmly with a warm American accent, creating a peaceful atmosphere perfect for bedtime stories and relaxation content.",
        "category": "female_soothing",
        "age": "30s",
        "accent": "American",
    },
    {
        "name": "Conversational Male (Podcast-style)",
        "description": "A casual, friendly male voice in his 30s with a natural conversational tone. His American accent is neutral and approachable, making him ideal for non-fiction, memoirs, and contemporary fiction.",
        "category": "male_casual",
        "age": "30s",
        "accent": "American",
    },
    {
        "name": "Elegant Female (Literary Fiction)",
        "description": "A refined female voice with impeccable diction and a sophisticated American accent. She delivers prose with artistic sensibility and emotional depth, perfect for literary fiction and poetry.",
        "category": "female_professional",
        "age": "40s",
        "accent": "American",
    },
    {
        "name": "Dramatic Male (Fantasy/Sci-Fi)",
        "description": "A powerful, expressive male voice capable of rich dramatic range. His deep timbre and theatrical delivery bring epic fantasy and science fiction narratives to life with intensity and passion.",
        "category": "male_dramatic",
        "age": "40s",
        "accent": "American",
    },
    {
        "name": "Cheerful Female (Children's Books)",
        "description": "An upbeat, animated female voice that's warm and inviting. She brings characters to life with playful energy and clear enunciation, perfect for children's literature and middle-grade fiction.",
        "category": "female_young",
        "age": "30s",
        "accent": "American",
    },
    {
        "name": "Wise Elder Male",
        "description": "A seasoned male voice in his 70s with a gentle, grandfatherly quality. His speech is measured and thoughtful with subtle warmth, ideal for philosophical works, memoirs, and inspirational content.",
        "category": "male_mature",
        "age": "70s",
        "accent": "American",
    },
    {
        "name": "Southern Female (Regional Charm)",
        "description": "A warm female voice with a gentle Southern American accent. Her drawl is authentic yet easy to understand, adding regional flavor perfect for Southern fiction and historical narratives.",
        "category": "female_regional",
        "age": "40s",
        "accent": "Southern US",
    },
    {
        "name": "Academic Male (Non-Fiction)",
        "description": "A clear, articulate male voice with an educated mid-Atlantic accent. His delivery is precise and authoritative without being dry, excellent for academic texts, biographies, and historical non-fiction.",
        "category": "male_professional",
        "age": "50s",
        "accent": "Mid-Atlantic",
    },
    {
        "name": "Intimate Female (Romance)",
        "description": "A sultry, expressive female voice with emotional depth and range. She delivers romantic passages with genuine warmth and sensuality, perfect for romance novels and intimate character-driven stories.",
        "category": "female_expressive",
        "age": "30s",
        "accent": "American",
    },
    {
        "name": "Youthful Male (Adventure)",
        "description": "An energetic male voice in his 20s with an adventurous spirit. His delivery is quick-paced and enthusiastic with clear American pronunciation, ideal for action-adventure and thriller genres.",
        "category": "male_young",
        "age": "20s",
        "accent": "American",
    },
    {
        "name": "Neutral Narrator (Versatile)",
        "description": "A balanced, versatile voice with neutral American pronunciation and moderate pacing. This narrator adapts well to any genre with professional clarity and consistent quality throughout long narrations.",
        "category": "neutral_professional",
        "age": "35-45",
        "accent": "American",
    },
]

# Sample text for voice previews (approximately 30 seconds when spoken)
PREVIEW_TEXT = """The old library stood at the corner of Main Street, its weathered brick facade a testament to a century of stories.
Inside, dust motes danced in shafts of afternoon sunlight, and the familiar scent of aged paper and leather bindings welcomed every visitor.
Eleanor had discovered this sanctuary when she was just a child, and now, decades later, she still found magic between these walls.
Today she climbed the spiral staircase to the fiction section, her fingers trailing along the spines of countless adventures waiting to be discovered."""


def get_preset_by_name(name: str) -> dict | None:
    """Get a voice preset by its name."""
    for preset in VOICE_PRESETS:
        if preset["name"] == name:
            return preset
    return None


def get_preset_names() -> list[str]:
    """Get a list of all voice preset names for UI dropdown."""
    return [preset["name"] for preset in VOICE_PRESETS]


def get_presets_by_category(category: str) -> list[dict]:
    """Get all voice presets in a specific category."""
    return [preset for preset in VOICE_PRESETS if preset["category"] == category]


def get_all_categories() -> list[str]:
    """Get a unique list of all categories."""
    return list(set(preset["category"] for preset in VOICE_PRESETS))
