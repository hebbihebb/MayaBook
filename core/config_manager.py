# core/config_manager.py
"""
Configuration management and smart defaults
"""
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from platformdirs import user_config_dir, user_data_dir

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    'last_used': {
        'epub_path': '',
        'cover_path': '',
        'model_path': 'assets/models/maya1.i1-Q5_K_M.gguf',
        'output_folder': str(Path.home() / 'MayaBook_Output'),
    },
    'recent_files': {
        'epubs': [],
        'covers': [],
        'models': [],
    },
    'gui_settings': {
        'model_type': 'gguf',
        'n_ctx': 4096,
        'n_gpu_layers': -1,
        'temperature': 0.45,
        'top_p': 0.92,
        'chunk_size': 70,
        'gap_size': 0.25,
        'output_format': 'm4b',
        'use_chapters': True,
        'save_separately': False,
        'merge_chapters': True,
        'chapter_silence': 2.0,
        'voice_description': 'A female speaker with a warm, calm, and clear voice, delivering the narration in a standard American English accent. Her tone is engaging and pleasant, suitable for long listening sessions.',
    },
    'profiles': {}
}


class ConfigManager:
    """Manages application configuration and user preferences"""

    def __init__(self, app_name: str = "MayaBook"):
        self.app_name = app_name
        self.config_dir = Path(user_config_dir(app_name))
        self.config_file = self.config_dir / "config.json"
        self.config = DEFAULT_CONFIG.copy()

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load existing config
        self.load()

    def load(self) -> Dict:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle new keys
                    self._merge_configs(self.config, loaded)
                logger.info(f"Configuration loaded from {self.config_file}")
        except Exception as e:
            logger.warning(f"Could not load config: {e}. Using defaults.")

        return self.config

    def save(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Could not save config: {e}")

    def _merge_configs(self, base: Dict, update: Dict):
        """Recursively merge update dict into base dict"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value

    def get_last_used(self, key: str) -> str:
        """Get last used path for a specific key"""
        return self.config.get('last_used', {}).get(key, '')

    def set_last_used(self, key: str, value: str):
        """Set last used path"""
        if 'last_used' not in self.config:
            self.config['last_used'] = {}
        self.config['last_used'][key] = value
        self.save()

    def add_recent_file(self, category: str, file_path: str, max_recent: int = 10):
        """Add file to recent files list"""
        if 'recent_files' not in self.config:
            self.config['recent_files'] = {}
        if category not in self.config['recent_files']:
            self.config['recent_files'][category] = []

        recent = self.config['recent_files'][category]

        # Remove if already exists
        if file_path in recent:
            recent.remove(file_path)

        # Add to front
        recent.insert(0, file_path)

        # Trim to max
        self.config['recent_files'][category] = recent[:max_recent]
        self.save()

    def get_recent_files(self, category: str) -> List[str]:
        """Get recent files for a category"""
        return self.config.get('recent_files', {}).get(category, [])

    def save_gui_settings(self, settings: Dict):
        """Save current GUI settings"""
        self.config['gui_settings'].update(settings)
        self.save()

    def get_gui_settings(self) -> Dict:
        """Get saved GUI settings"""
        return self.config.get('gui_settings', DEFAULT_CONFIG['gui_settings'].copy())

    def save_profile(self, profile_name: str, settings: Dict):
        """Save a named configuration profile"""
        if 'profiles' not in self.config:
            self.config['profiles'] = {}
        self.config['profiles'][profile_name] = settings
        self.save()
        logger.info(f"Saved profile: {profile_name}")

    def load_profile(self, profile_name: str) -> Optional[Dict]:
        """Load a named configuration profile"""
        profile = self.config.get('profiles', {}).get(profile_name)
        if profile:
            logger.info(f"Loaded profile: {profile_name}")
        return profile

    def get_profile_names(self) -> List[str]:
        """Get list of saved profile names"""
        return list(self.config.get('profiles', {}).keys())

    def delete_profile(self, profile_name: str):
        """Delete a configuration profile"""
        if 'profiles' in self.config and profile_name in self.config['profiles']:
            del self.config['profiles'][profile_name]
            self.save()
            logger.info(f"Deleted profile: {profile_name}")


def find_default_model() -> Optional[str]:
    """
    Search for GGUF model in standard locations

    Returns:
        Path to first found model, or None
    """
    search_paths = [
        Path('assets/models'),
        Path.home() / 'MayaBook' / 'assets' / 'models',
        Path.cwd() / 'models',
    ]

    for base_path in search_paths:
        if not base_path.exists():
            continue

        # Look for any .gguf file
        gguf_files = list(base_path.glob('*.gguf'))
        if gguf_files:
            logger.info(f"Found default model: {gguf_files[0]}")
            return str(gguf_files[0])

    return None


def find_default_epub() -> Optional[str]:
    """
    Search for EPUB file in standard test locations

    Returns:
        Path to first found EPUB, or None
    """
    search_paths = [
        Path('assets/test'),
        Path.home() / 'MayaBook' / 'assets' / 'test',
        Path.cwd() / 'test',
        Path.home() / 'Documents',
    ]

    for base_path in search_paths:
        if not base_path.exists():
            continue

        epub_files = list(base_path.glob('*.epub'))
        if epub_files:
            logger.info(f"Found default EPUB: {epub_files[0]}")
            return str(epub_files[0])

    return None


def find_matching_cover(epub_path: str) -> Optional[str]:
    """
    Find cover image matching EPUB filename

    Args:
        epub_path: Path to EPUB file

    Returns:
        Path to matching cover image, or None
    """
    if not epub_path:
        return None

    epub_path = Path(epub_path)
    if not epub_path.exists():
        return None

    # Look for images with same base name
    base_name = epub_path.stem
    epub_dir = epub_path.parent

    for ext in ['.jpg', '.jpeg', '.png', '.webp']:
        cover_path = epub_dir / f"{base_name}{ext}"
        if cover_path.exists():
            logger.info(f"Found matching cover: {cover_path}")
            return str(cover_path)

    # Look for generic cover names
    for name in ['cover', 'Cover', 'COVER']:
        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
            cover_path = epub_dir / f"{name}{ext}"
            if cover_path.exists():
                logger.info(f"Found generic cover: {cover_path}")
                return str(cover_path)

    return None


def get_smart_defaults() -> Dict[str, str]:
    """
    Get smart default values for all file inputs

    Returns:
        dict: {
            'model_path': str,
            'epub_path': str,
            'cover_path': str,
            'output_folder': str,
        }
    """
    defaults = {
        'model_path': find_default_model() or 'assets/models/maya1.i1-Q5_K_M.gguf',
        'epub_path': find_default_epub() or '',
        'cover_path': '',
        'output_folder': str(Path.home() / 'MayaBook_Output'),
    }

    # If we found an EPUB, try to find matching cover
    if defaults['epub_path']:
        cover = find_matching_cover(defaults['epub_path'])
        if cover:
            defaults['cover_path'] = cover

    return defaults


# Built-in profiles for common use cases
BUILTIN_PROFILES = {
    'Fiction - Narrative': {
        'temperature': 0.45,
        'top_p': 0.92,
        'chunk_size': 70,
        'gap_size': 0.25,
        'chapter_silence': 2.0,
        'voice_description': 'A female speaker with a warm, calm, and clear voice, delivering the narration in a standard American English accent. Her tone is engaging and pleasant, suitable for long listening sessions.',
    },
    'Non-Fiction - Informative': {
        'temperature': 0.35,
        'top_p': 0.88,
        'chunk_size': 80,
        'gap_size': 0.3,
        'chapter_silence': 2.5,
        'voice_description': 'A clear, professional male voice with precise enunciation and measured pacing. American accent with authoritative yet approachable tone, suitable for educational content.',
    },
    'Poetry - Expressive': {
        'temperature': 0.5,
        'top_p': 0.95,
        'chunk_size': 50,
        'gap_size': 0.5,
        'chapter_silence': 3.0,
        'voice_description': 'An expressive female voice with dramatic pauses and emotional depth. Warm British accent, suitable for poetic and literary works with rich language.',
    },
    'Children - Playful': {
        'temperature': 0.48,
        'top_p': 0.93,
        'chunk_size': 60,
        'gap_size': 0.4,
        'chapter_silence': 2.0,
        'voice_description': 'A bright, energetic female voice with playful inflection and clear diction. Young and cheerful tone, perfect for children\'s stories and young adult fiction.',
    },
    'Academic - Professional': {
        'temperature': 0.3,
        'top_p': 0.85,
        'chunk_size': 90,
        'gap_size': 0.35,
        'chapter_silence': 2.0,
        'voice_description': 'A mature, authoritative male voice with formal diction and steady pacing. Deep, clear tone suitable for academic texts, research papers, and technical documentation.',
    },
    'Mystery - Suspenseful': {
        'temperature': 0.42,
        'top_p': 0.90,
        'chunk_size': 65,
        'gap_size': 0.3,
        'chapter_silence': 2.5,
        'voice_description': 'A low, mysterious female voice with subtle tension and dramatic pacing. Hushed and intense tone, perfect for suspense, thrillers, and mystery novels.',
    },
}
