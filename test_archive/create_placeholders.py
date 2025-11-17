#!/usr/bin/env python3
"""
Creates placeholder files for testing MayaBook without real assets.

This script generates:
- Dummy GGUF model file (empty, for path testing only)
- Sample cover image (100x100 black square)
- Sample EPUB file (minimal valid EPUB structure)

Usage:
    python create_placeholders.py
"""

import os
from pathlib import Path
import zipfile
from PIL import Image


def create_dummy_gguf(path: Path):
    """Create an empty placeholder GGUF file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        # Write minimal GGUF header (just for file existence, not functional)
        f.write(b'GGUF')
        f.write(b'\x00' * 96)  # Minimal padding
    print(f"✓ Created dummy GGUF: {path}")


def create_cover_image(path: Path):
    """Create a simple black square cover image."""
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new('RGB', (100, 100), color='black')
    img.save(path)
    print(f"✓ Created cover image: {path}")


def create_sample_epub(path: Path):
    """Create a minimal valid EPUB file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as epub:
        # mimetype (must be first, uncompressed)
        epub.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)

        # META-INF/container.xml
        epub.writestr('META-INF/container.xml', '''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>''')

        # OEBPS/content.opf
        epub.writestr('OEBPS/content.opf', '''<?xml version="1.0"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="book-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Sample Book for Testing</dc:title>
    <dc:creator>MayaBook Test Suite</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id="book-id">test-book-001</dc:identifier>
  </metadata>
  <manifest>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>''')

        # OEBPS/chapter1.xhtml
        epub.writestr('OEBPS/chapter1.xhtml', '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>Chapter 1</title>
</head>
<body>
  <h1>Chapter 1: The Beginning</h1>
  <p>This is a sample paragraph for testing the MayaBook text-to-speech pipeline.
  The quick brown fox jumps over the lazy dog. This sentence contains enough
  text to generate a meaningful audio chunk during synthesis.</p>
  <p>Here is a second paragraph to ensure the chunking algorithm has multiple
  sentences to work with. Testing is essential for quality assurance.</p>
</body>
</html>''')

    print(f"✓ Created sample EPUB: {path}")


def main():
    """Create all placeholder files."""
    print("Creating placeholder files for MayaBook testing...\n")

    # Get project root (where this script is located)
    project_root = Path(__file__).parent
    assets_dir = project_root / "assets"

    # Create placeholder files
    try:
        create_dummy_gguf(assets_dir / "models" / "maya1.i1-Q5_K_M.gguf")
        create_cover_image(assets_dir / "test" / "cover.jpg")
        create_sample_epub(assets_dir / "test" / "sample.epub")

        print("\n✓ All placeholder files created successfully!")
        print("\nNote: The GGUF file is a dummy placeholder.")
        print("Download the real model from: https://huggingface.co/maya-research/maya1")
        print("Place it at: assets/models/maya1.i1-Q5_K_M.gguf")

    except ImportError as e:
        if "PIL" in str(e):
            print("\n⚠ PIL/Pillow not installed. Creating placeholder without cover image.")
            print("Install with: pip install Pillow")
            create_dummy_gguf(assets_dir / "models" / "maya1.i1-Q5_K_M.gguf")
            create_sample_epub(assets_dir / "test" / "sample.epub")
            # Create empty cover as fallback
            cover_path = assets_dir / "test" / "cover.jpg"
            cover_path.parent.mkdir(parents=True, exist_ok=True)
            cover_path.touch()
            print(f"✓ Created empty cover placeholder: {cover_path}")
    except Exception as e:
        print(f"\n✗ Error creating placeholders: {e}")
        raise


if __name__ == "__main__":
    main()
