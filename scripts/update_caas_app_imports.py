#!/usr/bin/env python3
"""
Update imports in caas_app/ from app.* to caas_app.*
"""

import re
from pathlib import Path


def update_imports(file_path: Path) -> bool:
    """Update imports in a single file"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original = content

        # Replace app.* imports with caas_app.*
        # But keep caas_framework imports as-is
        content = re.sub(
            r'\bfrom app\.([a-zA-Z_][a-zA-Z0-9_.]*) import',
            r'from caas_app.\1 import',
            content
        )
        content = re.sub(
            r'\bimport app\.([a-zA-Z_][a-zA-Z0-9_.]*)',
            r'import caas_app.\1',
            content
        )

        if content != original:
            file_path.write_text(content, encoding='utf-8')
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    project_root = Path(__file__).parent.parent
    caas_app_dir = project_root / "caas_app"

    if not caas_app_dir.exists():
        print("caas_app/ directory not found!")
        return

    modified = []
    for py_file in caas_app_dir.rglob("*.py"):
        if update_imports(py_file):
            modified.append(py_file.relative_to(project_root))
            print(f"✓ Updated: {py_file.relative_to(project_root)}")

    print(f"\nUpdated {len(modified)} file(s)")


if __name__ == "__main__":
    main()
