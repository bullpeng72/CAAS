#!/usr/bin/env python3
"""
Final cleanup: Replace all remaining app.* imports
"""

import re
from pathlib import Path


# Mapping of old imports to new ones
REPLACEMENTS = [
    # In caas_app/
    (r'from app\.tools\.', r'from caas_app.tools.'),
    (r'from app\.utils\.', r'from caas_app.utils.'),
    (r'from app\.config import', r'from caas_app.config import'),
    (r'from app\.knowledge\.', r'from caas_app.knowledge.'),

    # In caas_framework/ - knowledge
    (r'from app\.knowledge\.graph\.', r'from caas_framework.knowledge.graph.'),
    (r'from app\.knowledge\.ontology\.', r'from caas_framework.knowledge.ontology.'),
    (r'from app\.knowledge\.', r'from caas_framework.knowledge.'),

    # In caas_framework/ - core.ontology
    (r'from app\.core\.ontology\.', r'from caas_framework.knowledge.ontology.'),
    (r'from app\.core\.ontology import', r'from caas_framework.knowledge.ontology import'),

    # In caas_framework/ - codegen
    (r'from app\.codegen\.', r'from caas_app.codegen.'),

    # In caas_framework/ - artifacts
    (r'from app\.artifacts\.', r'from caas_app.artifacts.'),
]


def update_file(file_path: Path) -> bool:
    """Update imports in a single file"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original = content

        for pattern, replacement in REPLACEMENTS:
            content = re.sub(pattern, replacement, content)

        if content != original:
            file_path.write_text(content, encoding='utf-8')
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    project_root = Path(__file__).parent.parent

    modified = []
    for py_file in project_root.rglob("*.py"):
        # Skip app/ directory and backups
        if "app/" in str(py_file) or "backup" in str(py_file).lower():
            continue
        if "__pycache__" in str(py_file):
            continue

        if update_file(py_file):
            modified.append(py_file.relative_to(project_root))
            print(f"✓ {py_file.relative_to(project_root)}")

    print(f"\nUpdated {len(modified)} file(s)")


if __name__ == "__main__":
    main()
