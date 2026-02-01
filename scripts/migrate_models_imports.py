#!/usr/bin/env python3
"""
Migration script to replace app.models imports with caas_framework.models
"""

import os
import re
from pathlib import Path

# Map of app.models classes to their new locations in caas_framework.models
CLASS_MAPPINGS = {
    # From app.models.schemas - Specifications
    "ConcretizedRequirement": "specifications",
    "FeatureSpec": "specifications",
    "DataModel": "specifications",
    "NonFunctionalRequirements": "specifications",
    "AgentSpecModel": "specifications",
    "TaskSpecModel": "specifications",

    # From app.models.schemas - Analysis
    "RequirementAnalysis": "analysis",
    "QualityMetrics": "analysis",
    "ArchitectureDesign": "analysis",
    "AgentRequirement": "analysis",
    "TaskRequirement": "analysis",
    "UIComponentRequirement": "analysis",
    "UIPageRequirement": "analysis",
    "BackendAPIRequirement": "analysis",
    "WorkflowType": "analysis",
    "ProjectTemplate": "analysis",
    "HTTPMethod": "analysis",
    "LLMConfigSpec": "analysis",
    "ArchitecturalPattern": "analysis",
    "ComponentType": "analysis",
    "ComponentSpec": "analysis",
    "DataFlow": "analysis",
    "TechnologyStack": "analysis",

    # From app.models.artifact_types
    "ArtifactType": "artifact_types",
    "ArtifactFormat": "artifact_types",
    "ArtifactMetadata": "artifact_types",
    "Artifact": "artifact_types",
    "ArtifactGenerationConfig": "artifact_types",

    # From app.models.domain_types
    "DomainType": "domain_types",
    "ExecutionPattern": "domain_types",
    "DomainClassification": "domain_types",
}


def parse_import_line(line: str):
    """
    Parse an import line to extract the imported items.

    Returns:
        tuple: (module_path, imported_items)
    """
    # Match "from app.models.X import Y, Z"
    match = re.match(r'from (app\.models\.\w+) import (.+)', line)
    if not match:
        return None, None

    module_path = match.group(1)
    imports_str = match.group(2)

    # Handle parenthesized imports
    if '(' in imports_str:
        return module_path, None  # Will be handled differently

    # Split by comma and clean
    items = [item.strip() for item in imports_str.split(',')]

    return module_path, items


def migrate_import_line(line: str) -> str:
    """
    Migrate a single import line.

    Returns:
        str: Migrated line or original if no changes needed
    """
    # Simple replacements for common patterns
    simple_replacements = [
        # Direct module replacements
        (r'from app\.models\.artifact_types import',
         r'from caas_framework.models.artifact_types import'),
        (r'from app\.models\.domain_types import',
         r'from caas_framework.models.domain_types import'),
    ]

    for pattern, replacement in simple_replacements:
        if re.search(pattern, line):
            return re.sub(pattern, replacement, line)

    # Handle app.models.schemas imports with class mapping
    if 'from app.models.schemas import' in line:
        module_path, items = parse_import_line(line)

        if items is None:
            # Multiline import - skip for now
            return line

        # Group items by their new module
        grouped = {}
        for item in items:
            clean_item = item.strip()
            if clean_item in CLASS_MAPPINGS:
                new_module = CLASS_MAPPINGS[clean_item]
                if new_module not in grouped:
                    grouped[new_module] = []
                grouped[new_module].append(clean_item)
            else:
                # Unknown item - keep original
                return line

        # Generate new import lines
        new_lines = []
        for module, classes in grouped.items():
            new_lines.append(f"from caas_framework.models.{module} import {', '.join(classes)}")

        return '\n'.join(new_lines)

    # Handle app.models.tool_registry
    if 'from app.models.tool_registry import' in line:
        return re.sub(
            r'from app\.models\.tool_registry import',
            r'from caas_framework.models.tool_registry import',
            line
        )

    return line


def migrate_file(file_path: Path) -> bool:
    """
    Migrate a single file.

    Returns:
        bool: True if file was modified
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        lines = content.split('\n')

        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]

            # Check if this is an import line we need to migrate
            if 'from app.models.' in line:
                migrated = migrate_import_line(line)
                if migrated != line:
                    # Import was changed
                    new_lines.append(migrated)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

            i += 1

        new_content = '\n'.join(new_lines)

        # Write back if changed
        if new_content != original_content:
            file_path.write_text(new_content, encoding='utf-8')
            return True

        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main migration function"""
    project_root = Path(__file__).parent.parent

    # Directories to process (exclude backups and tests for now)
    dirs_to_process = [
        project_root / "app",
        project_root / "caas_framework",
        project_root / "caas_cli",
    ]

    # Directories to exclude
    exclude_patterns = [
        "*backup*",
        "app_*_backup",
        "__pycache__",
        ".git",
        "venv",
        ".venv",
        "test_app_integration.py",
        "test_backward_compatibility.py",
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
