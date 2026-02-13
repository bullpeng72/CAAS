#!/usr/bin/env python3
"""
Extract generated code from files JSON to actual Python files

Usage:
    python scripts/extract_generated_code.py generated/
"""

import json
import sys
from pathlib import Path


def extract_code(generated_dir: Path):
    """Extract code from files JSON to actual files"""
    files_json = generated_dir / "files"

    if not files_json.exists():
        print(f"❌ Error: {files_json} not found")
        return False

    # Load files JSON
    with open(files_json, 'r', encoding='utf-8') as f:
        code_files = json.load(f)

    # Filter out metadata
    code_files = {k: v for k, v in code_files.items()
                  if not k.startswith('_') and isinstance(v, str)}

    print(f"📦 Found {len(code_files)} files in JSON")

    # Create output directory
    output_dir = generated_dir / "src"
    output_dir.mkdir(exist_ok=True)

    # Write each file
    success_count = 0
    for filename, content in code_files.items():
        output_path = output_dir / filename

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

            size = len(content)
            print(f"✅ {filename:20s} ({size:6,d} bytes) → {output_path}")
            success_count += 1

        except Exception as e:
            print(f"❌ {filename}: {e}")

    print(f"\n🎉 Extracted {success_count}/{len(code_files)} files to {output_dir}/")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_generated_code.py <generated_dir>")
        print("Example: python extract_generated_code.py generated/")
        sys.exit(1)

    generated_dir = Path(sys.argv[1])

    if not generated_dir.exists():
        print(f"❌ Directory not found: {generated_dir}")
        sys.exit(1)

    success = extract_code(generated_dir)
    sys.exit(0 if success else 1)
