"""
Claude-inspired theme for MayaBook Web UI

Warm brown backgrounds with orange accents, inspired by Claude's interface.
"""

# Color Palette (inspired by Claude)
COLORS = {
    # Backgrounds - Warm browns
    'bg_primary': '#1a140f',      # Main background (deep warm brown)
    'bg_secondary': '#2d2420',    # Card/panel background (medium brown)
    'bg_tertiary': '#3a2f27',     # Elevated elements (lighter brown)
    'bg_hover': '#4a3d35',        # Hover states (warm tan-brown)

    # Accents - Orange primary, Blue secondary
    'accent_orange': '#ea580c',   # Primary orange accent
    'accent_orange_hover': '#fb923c',  # Lighter orange on hover
    'accent_orange_dark': '#c2410c',   # Darker orange
    'accent_blue': '#3b82f6',     # Secondary blue accent
    'accent_blue_hover': '#60a5fa',

    # Text - White and warm tones
    'text_primary': '#f5f5f5',    # Main text (bright white)
    'text_secondary': '#d4c5b9',  # Secondary text (warm light tan)
    'text_muted': '#9c8b7e',      # Muted text (warm medium tan)

    # Status Colors
    'success': '#22c55e',
    'warning': '#f59e0b',
    'error': '#ef4444',
    'info': '#3b82f6',

    # Borders
    'border': '#4a3d35',
    'border_focus': '#ea580c',
}

# Global CSS styling
GLOBAL_CSS = f"""
/* Base theme */
:root {{
    --primary-bg: {COLORS['bg_primary']};
    --secondary-bg: {COLORS['bg_secondary']};
    --accent-orange: {COLORS['accent_orange']};
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
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
}}

/* Section headers */
.maya-section-header {{
    color: {COLORS['accent_orange']};
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 1rem;
    border-bottom: 2px solid {COLORS['accent_orange']};
    padding-bottom: 0.5rem;
}}

/* Primary button */
.maya-btn-primary {{
    background: linear-gradient(135deg, {COLORS['accent_orange']}, {COLORS['accent_orange_dark']});
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.75rem 1.5rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: 0 3px 8px rgba(234, 88, 12, 0.4);
}}

.maya-btn-primary:hover {{
    background: linear-gradient(135deg, {COLORS['accent_orange_hover']}, {COLORS['accent_orange']});
    box-shadow: 0 5px 15px rgba(234, 88, 12, 0.5);
    transform: translateY(-2px);
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
    box-shadow: 0 0 0 3px rgba(234, 88, 12, 0.15);
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
    border-color: {COLORS['accent_orange']};
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
    background: linear-gradient(90deg, {COLORS['accent_orange']}, {COLORS['accent_orange_hover']});
    height: 100%;
    transition: width 0.3s;
    box-shadow: 0 0 10px rgba(234, 88, 12, 0.4);
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
    accent-color: {COLORS['accent_orange']};
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
    background-color: {COLORS['accent_orange']};
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
    color: {COLORS['accent_orange']} !important;
}}

.q-linear-progress__track {{
    background-color: {COLORS['bg_tertiary']} !important;
}}

.q-linear-progress__model {{
    background: linear-gradient(90deg, {COLORS['accent_orange']}, {COLORS['accent_orange_hover']}) !important;
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
