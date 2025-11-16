"""
MayaBook Web UI - NiceGUI Application

Standalone web interface for the MayaBook TTS pipeline.
Provides browser-based access to all MayaBook features.
"""

import os
import sys
import threading
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple, Dict
import logging

from nicegui import ui, app as nicegui_app

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import pipeline
from core.epub_extract import extract_chapters
from core.voice_presets import get_preset_names, get_preset_by_name, PREVIEW_TEXT
from core.voice_preview import generate_voice_preview
from core.gpu_utils import get_gpu_info, get_recommended_gguf_settings, format_vram_info
from core.config_manager import get_smart_defaults
from webui.theme import apply_theme, COLORS


# Global state
class AppState:
    """Application state management"""

    def __init__(self):
        self.epub_path: Optional[str] = None
        self.cover_path: Optional[str] = None
        self.model_path: Optional[str] = None

        self.chapters: List[Tuple[str, str]] = []
        self.metadata: Dict[str, str] = {}

        self.is_running: bool = False
        self.stop_flag: Optional[threading.Event] = None
        self.current_progress: int = 0
        self.total_progress: int = 0

        self.output_files: List[str] = []
        self.log_messages: List[str] = []

    def reset(self):
        """Reset processing state"""
        self.is_running = False
        self.stop_flag = None
        self.current_progress = 0
        self.total_progress = 0
        self.output_files = []

    def add_log(self, message: str):
        """Add a log message"""
        self.log_messages.append(message)
        if len(self.log_messages) > 500:  # Keep last 500 messages
            self.log_messages = self.log_messages[-500:]


state = AppState()


# Logging setup
def setup_logging():
    """Configure logging to capture messages for display"""

    class WebUILogHandler(logging.Handler):
        def emit(self, record):
            msg = self.format(record)
            state.add_log(msg)

    handler = WebUILogHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# Model detection
def detect_available_models():
    """Scan for available GGUF models in the assets/models directory"""
    models = []

    # Check standard location
    project_root = Path(__file__).parent.parent
    models_dir = project_root / 'assets' / 'models'

    if models_dir.exists():
        # Find all .gguf files
        gguf_files = list(models_dir.glob('*.gguf'))
        for model_file in sorted(gguf_files):
            # Get relative path for display, absolute for actual use
            models.append({
                'name': model_file.name,
                'path': str(model_file.absolute()),
                'size_gb': model_file.stat().st_size / (1024**3)  # Size in GB
            })

    return models


def create_ui():
    """Create the main NiceGUI interface"""

    # Apply theme
    apply_theme()

    # Header
    with ui.header().classes('bg-transparent'):
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('MayaBook Web UI').classes('text-2xl font-bold').style(
                f'color: {COLORS["accent_orange"]}'
            )
            ui.badge('v2.0 Enhanced', color='orange').classes('text-sm')

    # Main container - wider layout for better space utilization
    with ui.column().classes('w-full max-w-[1600px] mx-auto p-4 gap-4'):

        # Tab layout for organized sections
        with ui.tabs().classes('w-full') as tabs:
            tab_files = ui.tab('Files & Model', icon='upload_file')
            tab_voice = ui.tab('Voice & TTS', icon='record_voice_over')
            tab_output = ui.tab('Output & Metadata', icon='settings')
            tab_test = ui.tab('Quick Test', icon='play_circle')
            tab_generate = ui.tab('Generate', icon='auto_awesome')

        with ui.tab_panels(tabs, value=tab_files).classes('w-full'):

            # ==========================
            # FILES & MODEL TAB
            # ==========================
            with ui.tab_panel(tab_files):
                # Smart Defaults Banner
                with ui.row().classes('w-full items-center gap-4 mb-4 p-3 rounded').style(
                    f'background: {COLORS["bg_tertiary"]}'
                ):
                    ui.icon('auto_awesome', size='md').style(f'color: {COLORS["accent_orange"]}')
                    ui.label('Quick Start').classes('flex-1 font-semibold')
                    ui.button(
                        'Load Smart Defaults',
                        icon='download',
                        on_click=lambda: load_smart_defaults()
                    ).classes('maya-btn-secondary').props('dense')

                def load_smart_defaults():
                    """Load smart default file paths"""
                    defaults = get_smart_defaults()

                    if defaults['model_path']:
                        model_path_input.value = defaults['model_path']
                        state.model_path = defaults['model_path']
                        ui.notify(f"✓ Auto-loaded model", type='positive')

                    if defaults['epub_path']:
                        state.epub_path = defaults['epub_path']
                        epub_status.set_text(f"Auto-found: {Path(defaults['epub_path']).name}")
                        ui.notify(f"✓ Auto-found EPUB", type='positive')

                    if defaults['cover_path']:
                        state.cover_path = defaults['cover_path']
                        cover_status.set_text(f"Auto-found: {Path(defaults['cover_path']).name}")
                        ui.notify(f"✓ Auto-found cover", type='positive')

                    if defaults['model_path'] or defaults['epub_path'] or defaults['cover_path']:
                        ui.notify('Smart defaults loaded!', type='positive')
                    else:
                        ui.notify('No defaults found - add files to assets/ folder', type='info')

                with ui.card().classes('maya-card'):
                    ui.label('File Uploads').classes('maya-section-header')

                    with ui.row().classes('w-full gap-4'):
                        # EPUB upload
                        with ui.column().classes('flex-1'):
                            ui.label('EPUB File').classes('font-semibold mb-2')
                            epub_upload = ui.upload(
                                on_upload=lambda e: handle_epub_upload(e),
                                auto_upload=True
                            ).props('accept=".epub"').classes('w-full maya-upload')
                            epub_status = ui.label('No file selected').classes('text-sm mt-2').style(
                                f'color: {COLORS["text_muted"]}'
                            )

                        # Cover image upload
                        with ui.column().classes('flex-1'):
                            ui.label('Cover Image (Optional)').classes('font-semibold mb-2')
                            cover_upload = ui.upload(
                                on_upload=lambda e: handle_cover_upload(e),
                                auto_upload=True
                            ).props('accept="image/*"').classes('w-full maya-upload')
                            cover_status = ui.label('No file selected').classes('text-sm mt-2').style(
                                f'color: {COLORS["text_muted"]}'
                            )

                with ui.card().classes('maya-card'):
                    ui.label('Model Configuration').classes('maya-section-header')

                    # GPU Status Banner
                    with ui.row().classes('w-full items-center gap-4 mb-4 p-3 rounded').style(
                        f'background: {COLORS["bg_tertiary"]}'
                    ):
                        gpu_status_icon = ui.icon('computer', size='md')
                        gpu_status_label = ui.label('Detecting GPU...').classes('flex-1').style(
                            f'color: {COLORS["text_secondary"]}'
                        )

                        gpu_auto_btn = ui.button(
                            'Auto-Configure GPU',
                            icon='auto_fix_high',
                            on_click=lambda: auto_configure_gpu()
                        ).classes('maya-btn-secondary').props('dense')

                        gpu_refresh_btn = ui.button(
                            icon='refresh',
                            on_click=lambda: detect_gpu()
                        ).props('flat dense').tooltip('Refresh GPU info')

                    # Detect GPU on load
                    def detect_gpu():
                        """Detect and display GPU information"""
                        gpu_info = get_gpu_info()

                        if gpu_info['available']:
                            vram_total = format_vram_info(gpu_info['vram_total_mb'])
                            vram_free = format_vram_info(gpu_info['vram_free_mb'])
                            status_text = f"✓ {gpu_info['name']} | {vram_total} total | {vram_free} free"
                            gpu_status_label.set_text(status_text)
                            gpu_status_label.style(f'color: {COLORS["success"]}')
                            gpu_status_icon.props('name=check_circle color=positive')
                        else:
                            gpu_status_label.set_text('⚠️ No GPU detected - CPU mode (slow)')
                            gpu_status_label.style(f'color: {COLORS["warning"]}')
                            gpu_status_icon.props('name=warning color=orange')

                    def auto_configure_gpu():
                        """Auto-configure GPU settings based on detection"""
                        if not state.model_path:
                            ui.notify('Please select a model first', type='warning')
                            return

                        settings = get_recommended_gguf_settings(state.model_path)

                        # Apply settings
                        n_gpu_layers_input.value = settings['n_gpu_layers']
                        n_ctx_input.value = settings['n_ctx']

                        ui.notify(f"✓ {settings['explanation']}", type='positive')

                        if settings['warnings']:
                            for warning in settings['warnings']:
                                ui.notify(f"⚠️ {warning}", type='warning')

                    # Run GPU detection on page load
                    ui.timer(0.1, detect_gpu, once=True)

                    # Detect available models
                    available_models = detect_available_models()

                    # Model path input (defined first so we can reference it)
                    model_path_input = ui.input(
                        label='Model Path',
                        placeholder='/path/to/maya1.gguf or /path/to/model_directory'
                    ).classes('w-full maya-input')

                    # Update state when model path changes
                    def on_model_path_change(e):
                        state.model_path = model_path_input.value

                    model_path_input.on_value_change(on_model_path_change)

                    if available_models:
                        # Create model options for dropdown
                        model_options = ['Custom (manual path)'] + [
                            f"{m['name']} ({m['size_gb']:.1f} GB)" for m in available_models
                        ]

                        ui.label('Quick Select from Detected Models:').classes('text-sm mt-4 mb-2').style(
                            f'color: {COLORS["text_secondary"]}'
                        )

                        with ui.row().classes('w-full gap-4'):
                            model_select = ui.select(
                                label='Detected Models',
                                options=model_options,
                                value=model_options[1] if len(model_options) > 1 else model_options[0]
                            ).classes('flex-1')

                            ui.button(
                                icon='refresh',
                                on_click=lambda: refresh_models()
                            ).props('flat dense').classes('mt-6').tooltip('Refresh model list')

                        def on_model_select(e):
                            """Update model path when dropdown selection changes"""
                            selected = model_select.value
                            if selected and selected != 'Custom (manual path)':
                                # Find the model by name
                                for model in available_models:
                                    if selected.startswith(model['name']):
                                        model_path_input.value = model['path']
                                        state.model_path = model['path']
                                        ui.notify(f'Selected: {model["name"]}', type='positive')
                                        break

                        model_select.on_value_change(on_model_select)

                        # Auto-select first model and populate path
                        if len(available_models) > 0:
                            model_path_input.value = available_models[0]['path']
                            state.model_path = available_models[0]['path']

                        def refresh_models():
                            """Refresh the model list"""
                            ui.notify('Refreshing model list...', type='info')
                            new_models = detect_available_models()
                            if len(new_models) > len(available_models):
                                ui.notify(f'Found {len(new_models)} models', type='positive')
                            elif len(new_models) == 0:
                                ui.notify('No models found in assets/models/', type='warning')
                            else:
                                ui.notify(f'{len(new_models)} models available', type='info')
                    else:
                        ui.label('⚠ No models found in assets/models/ - Please enter path manually or add models to the folder').classes('text-sm mb-2').style(
                            f'color: {COLORS["warning"]}'
                        )

                    ui.label('Model Settings').classes('text-sm mt-4 mb-2').style(
                        f'color: {COLORS["text_secondary"]}'
                    )
                    with ui.row().classes('w-full gap-4'):
                        model_type_select = ui.select(
                            label='Model Type',
                            options=['gguf', 'huggingface', 'vllm'],
                            value='gguf'
                        ).classes('flex-1').tooltip('vLLM: High-performance inference engine (GGUF support experimental)')

                        n_ctx_input = ui.number(
                            label='Context Size (n_ctx)',
                            value=4096,
                            min=512,
                            max=8192,
                            step=512
                        ).classes('flex-1')

                        n_gpu_layers_input = ui.number(
                            label='GPU Layers (-1 = all)',
                            value=-1,
                            min=-1,
                            max=100
                        ).classes('flex-1')

            # ==========================
            # VOICE & TTS TAB
            # ==========================
            with ui.tab_panel(tab_voice):
                # Two-column layout for better space utilization
                with ui.row().classes('w-full gap-4'):
                    # Left column: Voice Selection
                    with ui.column().classes('flex-1'):
                        with ui.card().classes('maya-card h-full'):
                            ui.label('Voice Selection').classes('maya-section-header')

                            # Voice preset selector
                            preset_names = ['Custom'] + get_preset_names()
                            voice_preset_select = ui.select(
                                label='Voice Preset',
                                options=preset_names,
                                value='Young Adult Female (Energetic)'
                            ).classes('w-full')

                            # Custom voice description - more rows for better editing
                            voice_desc_input = ui.textarea(
                                label='Voice Description',
                                placeholder='Describe the voice characteristics...'
                            ).classes('w-full maya-input').props('rows=8')

                            # Update voice description when preset changes
                            def update_voice_description():
                                preset_name = voice_preset_select.value
                                if preset_name != 'Custom':
                                    preset = get_preset_by_name(preset_name)
                                    if preset:
                                        voice_desc_input.value = preset['description']

                            voice_preset_select.on_value_change(lambda: update_voice_description())

                            # Voice preview button
                            with ui.row().classes('w-full gap-2 mt-4'):
                                preview_btn = ui.button(
                                    'Preview Voice',
                                    icon='play_arrow',
                                    on_click=lambda: generate_preview()
                                ).classes('maya-btn-secondary')
                                preview_status = ui.label('').classes('text-sm')

                    # Right column: TTS Parameters
                    with ui.column().classes('flex-1'):
                        with ui.card().classes('maya-card h-full'):
                            ui.label('TTS Parameters').classes('maya-section-header')

                            ui.label('Temperature').classes('text-sm mb-1').style(
                                f'color: {COLORS["text_secondary"]}'
                            )
                            with ui.row().classes('w-full gap-4 mb-6'):
                                temperature_slider = ui.slider(
                                    min=0.0,
                                    max=1.0,
                                    step=0.05,
                                    value=0.45
                                ).classes('flex-1 maya-slider')
                                temperature_label = ui.label('0.45').classes('w-16 text-right font-semibold')

                                temperature_slider.on_value_change(
                                    lambda e: temperature_label.set_text(f'{e.value:.2f}')
                                )

                            ui.label('Top-p (Nucleus Sampling)').classes('text-sm mb-1').style(
                                f'color: {COLORS["text_secondary"]}'
                            )
                            with ui.row().classes('w-full gap-4 mb-6'):
                                top_p_slider = ui.slider(
                                    min=0.0,
                                    max=1.0,
                                    step=0.05,
                                    value=0.92
                                ).classes('flex-1 maya-slider')
                                top_p_label = ui.label('0.92').classes('w-16 text-right font-semibold')

                                top_p_slider.on_value_change(
                                    lambda e: top_p_label.set_text(f'{e.value:.2f}')
                                )

                            with ui.row().classes('w-full gap-4'):
                                chunk_size_input = ui.number(
                                    label='Chunk Size (words)',
                                    value=70,
                                    min=20,
                                    max=150,
                                    step=10
                                ).classes('flex-1')

                                gap_input = ui.number(
                                    label='Gap Between Chunks (s)',
                                    value=0.25,
                                    min=0.0,
                                    max=2.0,
                                    step=0.05,
                                    format='%.2f'
                                ).classes('flex-1')

            # ==========================
            # OUTPUT & METADATA TAB
            # ==========================
            with ui.tab_panel(tab_output):
                # Two-column layout for better space utilization
                with ui.row().classes('w-full gap-4'):
                    # Left column: Output Configuration
                    with ui.column().classes('flex-1'):
                        with ui.card().classes('maya-card h-full'):
                            ui.label('Output Configuration').classes('maya-section-header')

                            output_format_select = ui.select(
                                label='Output Format',
                                options=['m4b', 'wav'],
                                value='m4b'
                            ).classes('w-full')

                            ui.label('Chapter Options').classes('text-sm mt-4 mb-2').style(
                                f'color: {COLORS["text_secondary"]}'
                            )
                            with ui.column().classes('w-full gap-2'):
                                enable_chapters_switch = ui.switch('Enable Chapter-Aware Processing', value=True)
                                save_chapters_switch = ui.switch('Save Chapters Separately', value=False)
                                merge_chapters_switch = ui.switch('Create Merged File', value=True)

                                chapter_silence_input = ui.number(
                                    label='Silence Between Chapters (s)',
                                    value=2.0,
                                    min=0.0,
                                    max=10.0,
                                    step=0.5,
                                    format='%.1f'
                                ).classes('w-full mt-2')

                    # Right column: Metadata
                    with ui.column().classes('flex-1'):
                        with ui.card().classes('maya-card h-full'):
                            ui.label('Metadata (Optional)').classes('maya-section-header')

                            with ui.row().classes('w-full gap-4'):
                                title_input = ui.input(label='Title', placeholder='Book Title').classes('flex-1')
                                author_input = ui.input(label='Author', placeholder='Author Name').classes('flex-1')

                            with ui.row().classes('w-full gap-4'):
                                album_input = ui.input(label='Album/Series', placeholder='Series Name').classes('flex-1')
                                year_input = ui.input(label='Year', placeholder='2025').classes('flex-1')

                            genre_input = ui.input(label='Genre', placeholder='Fiction, Fantasy, etc.').classes('w-full')

            # ==========================
            # QUICK TEST TAB
            # ==========================
            with ui.tab_panel(tab_test):
                with ui.card().classes('maya-card'):
                    ui.label('Quick Test').classes('maya-section-header')
                    ui.label('Test TTS generation without uploading an EPUB file.').classes('text-sm mb-4').style(
                        f'color: {COLORS["text_secondary"]}'
                    )

                    # Larger text area with more breathing room
                    test_text_input = ui.textarea(
                        label='Test Text',
                        placeholder='Enter text to synthesize...',
                        value=PREVIEW_TEXT
                    ).classes('w-full maya-input').props('rows=12')

                    with ui.row().classes('w-full gap-2 mt-4'):
                        test_btn = ui.button(
                            'Generate Test Audio',
                            icon='play_circle',
                            on_click=lambda: run_quick_test()
                        ).classes('maya-btn-primary')

                        test_status = ui.label('').classes('text-sm')

            # ==========================
            # GENERATE TAB
            # ==========================
            with ui.tab_panel(tab_generate):
                with ui.card().classes('maya-card'):
                    ui.label('Generation Control').classes('maya-section-header')

                    # Progress bar
                    with ui.column().classes('w-full gap-2 mb-4'):
                        progress_label = ui.label('Ready to generate').classes('font-semibold')
                        progress_bar = ui.linear_progress(value=0, show_value=False).classes('w-full')
                        progress_detail = ui.label('').classes('text-sm').style(
                            f'color: {COLORS["text_secondary"]}'
                        )

                    # Control buttons
                    with ui.row().classes('w-full gap-4'):
                        generate_btn = ui.button(
                            'Start Generation',
                            icon='play_arrow',
                            on_click=lambda: start_generation()
                        ).classes('maya-btn-primary flex-1')

                        cancel_btn = ui.button(
                            'Cancel',
                            icon='stop',
                            on_click=lambda: cancel_generation()
                        ).classes('maya-btn-secondary flex-1').props('disable')

                    # Log display
                    ui.label('Generation Log').classes('font-semibold mt-6 mb-2')
                    log_display = ui.log(max_lines=100).classes('w-full maya-log')

                with ui.card().classes('maya-card'):
                    ui.label('Output Files').classes('maya-section-header')

                    output_list = ui.column().classes('w-full gap-2')
                    ui.label('No files generated yet.').classes('text-sm').style(
                        f'color: {COLORS["text_muted"]}'
                    ).bind_visibility_from(state, 'output_files', lambda files: len(files) == 0)

    # ==========================
    # EVENT HANDLERS
    # ==========================

    def handle_epub_upload(event):
        """Handle EPUB file upload"""
        # Save uploaded file
        upload_dir = Path(tempfile.gettempdir()) / 'mayabook_uploads'
        upload_dir.mkdir(exist_ok=True)

        file_path = upload_dir / event.name
        with open(file_path, 'wb') as f:
            f.write(event.content.read())

        state.epub_path = str(file_path)
        epub_status.text = f'✓ {event.name}'
        epub_status.style(f'color: {COLORS["success"]}')

        # Extract chapters and metadata
        try:
            metadata, chapters = extract_chapters(str(file_path))
            state.chapters = chapters
            state.metadata = metadata

            # Auto-fill metadata if available
            if 'title' in metadata:
                title_input.value = metadata['title']
            if 'author' in metadata:
                author_input.value = metadata['author']

            log_display.push(f'✓ EPUB loaded: {len(chapters)} chapters extracted')
        except Exception as e:
            log_display.push(f'✗ Error extracting EPUB: {str(e)}')

    def handle_cover_upload(event):
        """Handle cover image upload"""
        upload_dir = Path(tempfile.gettempdir()) / 'mayabook_uploads'
        upload_dir.mkdir(exist_ok=True)

        file_path = upload_dir / event.name
        with open(file_path, 'wb') as f:
            f.write(event.content.read())

        state.cover_path = str(file_path)
        cover_status.text = f'✓ {event.name}'
        cover_status.style(f'color: {COLORS["success"]}')
        log_display.push(f'✓ Cover image uploaded')

    def generate_preview():
        """Generate voice preview"""
        if not state.model_path:
            preview_status.text = '✗ Model path required'
            preview_status.style(f'color: {COLORS["error"]}')
            return

        preview_status.text = 'Generating preview...'
        preview_status.style(f'color: {COLORS["info"]}')
        preview_btn.props('disable')

        def _generate():
            try:
                preview_path = generate_voice_preview(
                    voice_description=voice_desc_input.value or 'A clear, natural voice',
                    model_path=state.model_path,
                    temperature=temperature_slider.value,
                    top_p=top_p_slider.value,
                    n_ctx=int(n_ctx_input.value),
                    n_gpu_layers=int(n_gpu_layers_input.value),
                )

                state.output_files.append(preview_path)
                preview_status.text = '✓ Preview generated'
                preview_status.style(f'color: {COLORS["success"]}')
                log_display.push(f'✓ Voice preview generated: {preview_path}')

                # Add download link
                update_output_list()

            except Exception as e:
                preview_status.text = f'✗ Error: {str(e)}'
                preview_status.style(f'color: {COLORS["error"]}')
                log_display.push(f'✗ Preview error: {str(e)}')
            finally:
                preview_btn.props(remove='disable')

        threading.Thread(target=_generate, daemon=True).start()

    def run_quick_test():
        """Run quick test generation"""
        if not state.model_path:
            test_status.text = '✗ Model path required'
            test_status.style(f'color: {COLORS["error"]}')
            return

        if not test_text_input.value:
            test_status.text = '✗ Test text required'
            test_status.style(f'color: {COLORS["error"]}')
            return

        test_status.text = 'Generating...'
        test_status.style(f'color: {COLORS["info"]}')
        test_btn.props('disable')

        def _generate():
            try:
                output_dir = Path(tempfile.gettempdir()) / 'mayabook_quick_test'
                output_dir.mkdir(exist_ok=True)

                out_wav = output_dir / 'quick_test.wav'

                # Use default cover if none provided
                cover = state.cover_path or None

                pipeline.run_pipeline(
                    epub_text=test_text_input.value,
                    model_path=state.model_path,
                    voice_desc=voice_desc_input.value or 'A clear, natural voice',
                    chunk_size=int(chunk_size_input.value),
                    gap_s=gap_input.value,
                    out_wav=str(out_wav),
                    out_mp4=None,
                    cover_image=cover,
                    temperature=temperature_slider.value,
                    top_p=top_p_slider.value,
                    n_ctx=int(n_ctx_input.value),
                    n_gpu_layers=int(n_gpu_layers_input.value),
                    max_tokens=2500,
                    model_type=model_type_select.value,
                )

                state.output_files.append(str(out_wav))

                test_status.text = '✓ Test completed'
                test_status.style(f'color: {COLORS["success"]}')
                log_display.push(f'✓ Quick test completed')

                update_output_list()

            except Exception as e:
                test_status.text = f'✗ Error: {str(e)}'
                test_status.style(f'color: {COLORS["error"]}')
                log_display.push(f'✗ Quick test error: {str(e)}')
            finally:
                test_btn.props(remove='disable')

        threading.Thread(target=_generate, daemon=True).start()

    def start_generation():
        """Start the main generation process"""
        # Validation
        if not state.epub_path:
            log_display.push('✗ Please upload an EPUB file')
            return

        if not state.model_path:
            log_display.push('✗ Please provide model path')
            return

        # Prepare state
        state.reset()
        state.is_running = True
        state.stop_flag = threading.Event()

        # Update UI
        generate_btn.props('disable')
        cancel_btn.props(remove='disable')
        progress_label.text = 'Starting generation...'
        progress_bar.value = 0

        log_display.push('━' * 50)
        log_display.push('Starting audiobook generation...')

        def progress_callback(current, total, chapter_info=None):
            """Progress callback for pipeline"""
            state.current_progress = current
            state.total_progress = total

            progress_value = current / total if total > 0 else 0
            progress_bar.value = progress_value
            progress_detail.text = f'Processing: {current} / {total} chunks'

            if chapter_info:
                progress_label.text = f'Chapter: {chapter_info}'

        def _generate():
            try:
                output_dir = Path.home() / 'MayaBook_Output'
                output_dir.mkdir(exist_ok=True)

                # Build output filename
                base_name = title_input.value or 'audiobook'
                base_name = base_name.replace(' ', '_').replace('/', '_')
                output_base = output_dir / base_name

                # Prepare metadata
                metadata = {
                    'title': title_input.value,
                    'author': author_input.value,
                    'album': album_input.value,
                    'year': year_input.value,
                    'genre': genre_input.value,
                }

                # Run pipeline
                if enable_chapters_switch.value and state.chapters:
                    # Chapter-aware processing
                    result = pipeline.run_pipeline_with_chapters(
                        chapters=state.chapters,
                        metadata=metadata,
                        model_path=state.model_path,
                        voice_desc=voice_desc_input.value or 'A clear, natural voice',
                        chunk_size=int(chunk_size_input.value),
                        gap_s=gap_input.value,
                        output_base_path=str(output_base),
                        cover_image=state.cover_path,
                        output_format=output_format_select.value,
                        save_chapters_separately=save_chapters_switch.value,
                        merge_chapters=merge_chapters_switch.value,
                        chapter_silence=chapter_silence_input.value,
                        temperature=temperature_slider.value,
                        top_p=top_p_slider.value,
                        n_ctx=int(n_ctx_input.value),
                        n_gpu_layers=int(n_gpu_layers_input.value),
                        max_tokens=2500,
                        model_type=model_type_select.value,
                        progress_cb=progress_callback,
                        stop_flag=state.stop_flag,
                    )

                    if result.get('merged_path'):
                        state.output_files.append(result['merged_path'])
                    if result.get('chapter_paths'):
                        state.output_files.extend(result['chapter_paths'])
                else:
                    # Simple processing
                    # Extract text from chapters
                    full_text = '\n\n'.join([text for _, text in state.chapters]) if state.chapters else ''

                    out_wav = str(output_base) + '.wav'

                    pipeline.run_pipeline(
                        epub_text=full_text,
                        model_path=state.model_path,
                        voice_desc=voice_desc_input.value or 'A clear, natural voice',
                        chunk_size=int(chunk_size_input.value),
                        gap_s=gap_input.value,
                        out_wav=out_wav,
                        out_mp4=None,
                        cover_image=state.cover_path,
                        temperature=temperature_slider.value,
                        top_p=top_p_slider.value,
                        n_ctx=int(n_ctx_input.value),
                        n_gpu_layers=int(n_gpu_layers_input.value),
                        max_tokens=2500,
                        model_type=model_type_select.value,
                        progress_cb=progress_callback,
                        stop_flag=state.stop_flag,
                    )

                    state.output_files.append(out_wav)

                if not state.stop_flag.is_set():
                    progress_label.text = '✓ Generation completed!'
                    progress_label.style(f'color: {COLORS["success"]}')
                    log_display.push('✓ Audiobook generation completed successfully')
                else:
                    progress_label.text = '⚠ Generation cancelled'
                    progress_label.style(f'color: {COLORS["warning"]}')
                    log_display.push('⚠ Generation was cancelled by user')

                update_output_list()

            except Exception as e:
                progress_label.text = f'✗ Error: {str(e)}'
                progress_label.style(f'color: {COLORS["error"]}')
                log_display.push(f'✗ Generation error: {str(e)}')
                import traceback
                log_display.push(traceback.format_exc())

            finally:
                state.is_running = False
                generate_btn.props(remove='disable')
                cancel_btn.props('disable')

        threading.Thread(target=_generate, daemon=True).start()

    def cancel_generation():
        """Cancel the generation process"""
        if state.stop_flag:
            state.stop_flag.set()
            log_display.push('⚠ Cancellation requested...')
            cancel_btn.props('disable')

    def update_output_list():
        """Update the output files list"""
        output_list.clear()

        for file_path in state.output_files:
            if Path(file_path).exists():
                file_name = Path(file_path).name
                file_size = Path(file_path).stat().st_size / (1024 * 1024)  # MB

                with output_list:
                    with ui.row().classes('w-full items-center justify-between p-3').style(
                        f'background-color: {COLORS["bg_tertiary"]}; border-radius: 8px;'
                    ):
                        with ui.column().classes('gap-1'):
                            ui.label(file_name).classes('font-semibold')
                            ui.label(f'{file_size:.2f} MB').classes('text-sm').style(
                                f'color: {COLORS["text_secondary"]}'
                            )

                        ui.button(
                            icon='download',
                            on_click=lambda fp=file_path: download_file(fp)
                        ).classes('maya-btn-secondary').props('flat')

    def download_file(file_path: str):
        """Trigger file download"""
        # NiceGUI file download
        nicegui_app.download(file_path)

    # Initialize voice description with first preset
    update_voice_description()


def run_web_ui(host: str = '0.0.0.0', port: int = 8080, reload: bool = False):
    """
    Run the MayaBook Web UI

    Args:
        host: Host address (default: 0.0.0.0 for local network access)
        port: Port number (default: 8080)
        reload: Enable auto-reload for development (default: False)
    """
    setup_logging()

    ui.run(
        host=host,
        port=port,
        title='MayaBook Web UI',
        favicon='🎙️',
        reload=reload,
        dark=True,
        show=False,  # Don't auto-open browser
    )


if __name__ == '__main__':
    create_ui()
    run_web_ui()
