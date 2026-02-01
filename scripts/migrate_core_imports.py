#!/usr/bin/env python3
"""
Migration script to replace app.core imports with caas_framework
"""

import os
import re
from pathlib import Path

# Direct module replacements
REPLACEMENTS = [
    # BMAD
    (r'from app\.core\.bmad import', r'from caas_framework.bmad import'),
    (r'from app\.core\.bmad\.', r'from caas_framework.bmad.'),

    # SDD
    (r'from app\.core\.sdd import', r'from caas_framework.sdd import'),
    (r'from app\.core\.sdd\.', r'from caas_framework.sdd.'),

    # Factory
    (r'from app\.core\.factory import', r'from caas_framework.factory import'),
    (r'from app\.core\.factory\.', r'from caas_framework.factory.'),

    # Ontology - These need special handling as they're in app.core.ontology
    # and should go to caas_framework.knowledge.ontology
    (r'from app\.core\.ontology import', r'from caas_framework.knowledge.ontology import'),
    (r'from app\.core\.ontology\.', r'from caas_framework.knowledge.ontology.'),
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

    # Directories to process
    dirs_to_process = [
        project_root / "caas_framework",
        project_root / "caas_cli",
        # Note: Not processing app/ since those files will be moved to caas_app/ later
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
