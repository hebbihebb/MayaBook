"""
Claude Code-inspired theme for MayaBook Web UI

Dark theme with purple/blue accents, optimized for readability and modern aesthetics.
"""

# Color Palette (inspired by Claude Code)
COLORS = {
    # Backgrounds
    'bg_primary': '#1a1a1a',      # Main background (near-black)
    'bg_secondary': '#242424',    # Card/panel background
    'bg_tertiary': '#2d2d2d',     # Elevated elements
    'bg_hover': '#333333',        # Hover states

    # Accents
    'accent_purple': '#a855f7',   # Primary purple accent
    'accent_purple_hover': '#9333ea',
    'accent_blue': '#3b82f6',     # Secondary blue accent
    'accent_blue_hover': '#2563eb',

    # Text
    'text_primary': '#e5e5e5',    # Main text
    'text_secondary': '#a3a3a3',  # Secondary text
    'text_muted': '#737373',      # Muted text

    # Status Colors
    'success': '#22c55e',
    'warning': '#f59e0b',
    'error': '#ef4444',
    'info': '#3b82f6',

    # Borders
    'border': '#404040',
    'border_focus': '#a855f7',
}

# Global CSS styling
GLOBAL_CSS = f"""
/* Base theme */
:root {{
    --primary-bg: {COLORS['bg_primary']};
    --secondary-bg: {COLORS['bg_secondary']};
    --accent-purple: {COLORS['accent_purple']};
    --accent-blue: {COLORS['accent_blue']};
    --text-primary: {COLORS['text_primary']};
    --text-secondary: {COLORS['text_secondary']};
}}

body {{
    background-color: {COLORS['bg_primary']} !important;
    color: {COLORS['text_primary']} !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}}

/* Card styling */
.maya-card {{
    background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}}

/* Section headers */
.maya-section-header {{
    color: {COLORS['accent_purple']};
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 1rem;
    border-bottom: 2px solid {COLORS['accent_purple']};
    padding-bottom: 0.5rem;
}}

/* Primary button */
.maya-btn-primary {{
    background: linear-gradient(135deg, {COLORS['accent_purple']}, {COLORS['accent_purple_hover']});
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.75rem 1.5rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: 0 2px 4px rgba(168, 85, 247, 0.3);
}}

.maya-btn-primary:hover {{
    background: linear-gradient(135deg, {COLORS['accent_purple_hover']}, {COLORS['accent_purple']});
    box-shadow: 0 4px 8px rgba(168, 85, 247, 0.4);
    transform: translateY(-1px);
}}

/* Secondary button */
.maya-btn-secondary {{
    background-color: {COLORS['bg_tertiary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 0.75rem 1.5rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
}}

.maya-btn-secondary:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {COLORS['accent_blue']};
}}

/* Input fields */
.maya-input {{
    background-color: {COLORS['bg_tertiary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 0.625rem;
    transition: all 0.2s;
}}

.maya-input:focus {{
    border-color: {COLORS['border_focus']};
    outline: none;
    box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.1);
}}

/* Upload area */
.maya-upload {{
    background-color: {COLORS['bg_tertiary']};
    border: 2px dashed {COLORS['border']};
    border-radius: 8px;
    padding: 2rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
}}

.maya-upload:hover {{
    border-color: {COLORS['accent_purple']};
    background-color: {COLORS['bg_hover']};
}}

/* Progress bar */
.maya-progress {{
    background-color: {COLORS['bg_tertiary']};
    border-radius: 8px;
    overflow: hidden;
    height: 8px;
}}

.maya-progress-bar {{
    background: linear-gradient(90deg, {COLORS['accent_purple']}, {COLORS['accent_blue']});
    height: 100%;
    transition: width 0.3s;
}}

/* Log container */
.maya-log {{
    background-color: {COLORS['bg_primary']};
    color: {COLORS['text_secondary']};
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 1rem;
    height: 300px;
    overflow-y: auto;
    white-space: pre-wrap;
}}

/* Slider styling */
.maya-slider {{
    accent-color: {COLORS['accent_purple']};
}}

/* Select/dropdown */
.maya-select {{
    background-color: {COLORS['bg_tertiary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 0.625rem;
}}

/* Badge/chip */
.maya-badge {{
    background-color: {COLORS['accent_purple']};
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.875rem;
    font-weight: 500;
}}

/* Status indicators */
.status-idle {{
    color: {COLORS['text_muted']};
}}

.status-running {{
    color: {COLORS['info']};
}}

.status-success {{
    color: {COLORS['success']};
}}

.status-error {{
    color: {COLORS['error']};
}}

/* Scrollbar styling */
::-webkit-scrollbar {{
    width: 10px;
    height: 10px;
}}

::-webkit-scrollbar-track {{
    background: {COLORS['bg_primary']};
}}

::-webkit-scrollbar-thumb {{
    background: {COLORS['bg_hover']};
    border-radius: 5px;
}}

::-webkit-scrollbar-thumb:hover {{
    background: {COLORS['border']};
}}

/* NiceGUI specific overrides */
.nicegui-content {{
    background-color: {COLORS['bg_primary']} !important;
}}

.q-card {{
    background-color: {COLORS['bg_secondary']} !important;
    color: {COLORS['text_primary']} !important;
}}

.q-field__control {{
    background-color: {COLORS['bg_tertiary']} !important;
    color: {COLORS['text_primary']} !important;
}}

.q-tab {{
    color: {COLORS['text_secondary']} !important;
}}

.q-tab--active {{
    color: {COLORS['accent_purple']} !important;
}}

.q-linear-progress__track {{
    background-color: {COLORS['bg_tertiary']} !important;
}}

.q-linear-progress__model {{
    background: linear-gradient(90deg, {COLORS['accent_purple']}, {COLORS['accent_blue']}) !important;
}}
"""


def apply_theme():
    """
    Apply the Claude Code-inspired theme to the NiceGUI app.
    Call this function during app initialization.
    """
    from nicegui import ui

    # Add global CSS
    ui.add_head_html(f'<style>{GLOBAL_CSS}</style>')

    # Set Quasar dark mode
    ui.dark_mode().enable()


def get_color(color_key: str) -> str:
    """Get a color value from the theme palette."""
    return COLORS.get(color_key, COLORS['text_primary'])
