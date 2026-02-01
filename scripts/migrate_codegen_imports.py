#!/usr/bin/env python3
"""
Migration script to replace app.codegen imports with caas_framework.codegen
"""

import os
import re
from pathlib import Path

# Map of app.codegen imports to their new locations
REPLACEMENTS = [
    # Direct module replacements for components in caas_framework
    (r'from app\.codegen\.formatter import', r'from caas_framework.codegen.validation.code_validator import'),
    (r'from app\.codegen\.validator import', r'from caas_framework.codegen.validation import'),
    (r'from app\.codegen\.ast_generator import', r'from caas_framework.codegen.ast_generator import'),
    (r'from app\.codegen\.domain_strategy import', r'from caas_framework.codegen.domain_strategy import'),
    (r'from app\.codegen\.tool_generator import', r'from caas_framework.codegen import'),
    (r'from app\.codegen\.crud_entity_extractor import', r'from caas_framework.codegen import'),
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

        # For now, let's just map the common patterns
        # Since this is complex, we'll handle it more carefully

        # Safer approach: only migrate for caas_framework files
        if 'caas_framework' in str(file_path):
            # Migrate specific imports
            content = re.sub(
                r'from app\.codegen\.tool_generator import',
                r'from caas_app.codegen.tool_generator import',  # Keep for now
                content
            )
            content = re.sub(
                r'from app\.codegen\.crud_entity_extractor import',
                r'from caas_app.codegen.crud_entity_extractor import',  # Keep for now
                content
            )
            content = re.sub(
                r'from app\.codegen\.domain_strategy import',
                r'from caas_app.codegen.domain_strategy import',  # Keep for now
                content
            )

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
    print("Phase 3.1: Codegen import migration")
    print("=" * 60)
    print("Note: app.codegen has both shims and real implementations.")
    print("Strategy: Keep app.codegen imports for now, will be moved to")
    print("caas_app/ in Phase 4.")
    print("=" * 60)

    # For Phase 3.1, we'll just document the status
    # The actual migration will happen in Phase 4 when we move to caas_app/

    project_root = Path(__file__).parent.parent

    print("\nCurrent app.codegen structure:")
    codegen_dir = project_root / "app" / "codegen"
    if codegen_dir.exists():
        py_files = list(codegen_dir.glob("*.py"))
        print(f"  Total files: {len(py_files)}")

        shims = []
        real_impl = []

        for f in py_files:
            if f.name == "__init__.py":
                continue
            content = f.read_text()
            if "DEPRECATED" in content or "shim" in content.lower():
                shims.append(f.name)
            else:
                real_impl.append(f.name)

        print(f"  Shims: {len(shims)}")
        print(f"  Real implementations: {len(real_impl)}")

        if real_impl:
            print("\n  Real implementation files:")
            for name in sorted(real_impl):
                print(f"    - {name}")

    print("\n" + "=" * 60)
    print("Phase 3.1 Status:")
    print("  - app.codegen contains real implementations")
    print("  - These will be moved to caas_app/codegen in Phase 4")
    print("  - No migration needed at this stage")
    print("=" * 60)


if __name__ == "__main__":
    main()
