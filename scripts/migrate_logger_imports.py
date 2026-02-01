#!/usr/bin/env python3
"""
Migration script to replace app.utils.logger imports with caas_framework.utils.logger
"""

import os
import re
from pathlib import Path

# Patterns to replace
REPLACEMENTS = [
    # Basic import
    (r'from app\.utils\.logger import get_logger',
     r'from caas_framework.utils.logger import get_logger'),

    # Import with LoggerMixin
    (r'from app\.utils\.logger import get_logger, LoggerMixin',
     r'from caas_framework.utils.logger import get_logger, LoggerMixin'),

    # Import LoggerMixin only
    (r'from app\.utils\.logger import LoggerMixin',
     r'from caas_framework.utils.logger import LoggerMixin'),

    # Import logger
    (r'from app\.utils\.logger import logger',
     r'from caas_framework.utils.logger import logger'),

    # Import all variants
    (r'from app\.utils\.logger import \(([^)]+)\)',
     r'from caas_framework.utils.logger import (\1)'),
]

def migrate_file(file_path: Path) -> bool:
    """
    Migrate a single file.

    Returns:
        bool: True if file was modified
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        # Apply all replacements
        for pattern, replacement in REPLACEMENTS:
            content = re.sub(pattern, replacement, content)

        # Write back if changed
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True

        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main migration function"""
    project_root = Path(__file__).parent.parent

    # Directories to process (exclude backups)
    dirs_to_process = [
        project_root / "app",
        project_root / "caas_framework",
        project_root / "caas_cli",
        project_root / "scripts",
    ]

    # Directories to exclude
    exclude_patterns = [
        "*backup*",
        "app_*_backup",
        "__pycache__",
        ".git",
        "venv",
        ".venv",
    ]

    modified_files = []

    for base_dir in dirs_to_process:
        if not base_dir.exists():
            continue

        for py_file in base_dir.rglob("*.py"):
            # Skip excluded directories
            if any(pattern in str(py_file) for pattern in exclude_patterns):
                continue

            if migrate_file(py_file):
                modified_files.append(py_file)
                print(f"✓ Modified: {py_file.relative_to(project_root)}")

    print(f"\n{'='*60}")
    print(f"Migration complete!")
    print(f"Modified {len(modified_files)} file(s)")
    print(f"{'='*60}")

    if modified_files:
        print("\nModified files:")
        for f in modified_files:
            print(f"  - {f.relative_to(project_root)}")


if __name__ == "__main__":
    main()
