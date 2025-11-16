#!/usr/bin/env python3
"""
MayaBook Web UI - Standalone Entry Point

Launch the NiceGUI-based web interface for MayaBook.
Access the audiobook generation pipeline from any browser on your local network.

Usage:
    python webui.py                    # Run on default port 8080
    python webui.py --port 8000        # Run on custom port
    python webui.py --host 127.0.0.1   # Run on localhost only
    python webui.py --dev              # Enable auto-reload for development
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from webui.app import create_ui, run_web_ui


def main():
    parser = argparse.ArgumentParser(
        description='MayaBook Web UI - Browser-based TTS audiobook generation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python webui.py                    # Default: 0.0.0.0:8080
  python webui.py --port 8000        # Custom port
  python webui.py --host 127.0.0.1   # Localhost only
  python webui.py --dev              # Development mode with auto-reload

The web interface will be accessible at:
  - Local machine: http://localhost:8080
  - Local network: http://<your-ip>:8080
        """
    )

    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host address (default: 0.0.0.0 for local network access, use 127.0.0.1 for localhost only)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Port number (default: 8080)'
    )

    parser.add_argument(
        '--dev',
        action='store_true',
        help='Enable development mode with auto-reload'
    )

    args = parser.parse_args()

    # Banner
    print('=' * 60)
    print('🎙️  MayaBook Web UI')
    print('=' * 60)
    print(f'Starting web interface on {args.host}:{args.port}')
    print()
    print('Access the UI at:')
    if args.host == '0.0.0.0':
        print(f'  • Local:   http://localhost:{args.port}')
        print(f'  • Network: http://<your-ip>:{args.port}')
    else:
        print(f'  • URL: http://{args.host}:{args.port}')
    print()
    print('Press Ctrl+C to stop the server')
    print('=' * 60)
    print()

    # Create UI and run
    create_ui()
    run_web_ui(
        host=args.host,
        port=args.port,
        reload=args.dev
    )


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n👋 MayaBook Web UI stopped')
        sys.exit(0)
