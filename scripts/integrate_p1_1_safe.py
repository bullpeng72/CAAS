#!/usr/bin/env python3
"""
P1.1 Safe Integration Script

Safely integrates the refactored execute_development() into engine.py
"""

import re
from pathlib import Path
from typing import Tuple

def extract_method(content: str, method_name: str, start_pattern: str) -> Tuple[str, int, int]:
    """Extract a method from Python source code"""
    # Find the method start
    pattern = re.compile(start_pattern, re.MULTILINE)
    match = pattern.search(content)

    if not match:
        raise ValueError(f"Could not find method {method_name}")

    start_pos = match.start()
    lines = content[:start_pos].split('\n')
    start_line = len(lines)

    # Find the method end (next method at same indentation level or class end)
    remaining = content[start_pos:]
    remaining_lines = remaining.split('\n')

    # Count leading spaces of the method def
    first_line = remaining_lines[0]
    indent = len(first_line) - len(first_line.lstrip())

    end_line_idx = 1
    for i, line in enumerate(remaining_lines[1:], 1):
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith('#'):
            continue

        # Check if we hit another method or class member at same level
        line_indent = len(line) - len(line.lstrip())
        if line_indent == indent and (line.strip().startswith('def ') or line.strip().startswith('class ')):
            end_line_idx = i
            break
    else:
        # If we didn't find another method, use all remaining lines
        end_line_idx = len(remaining_lines)

    method_text = '\n'.join(remaining_lines[:end_line_idx])
    end_pos = start_pos + len(method_text)

    return method_text, start_pos, end_pos

def main():
    print("="*70)
    print("P1.1 Integration: execute_development() Refactoring")
    print("="*70)

    # Read files
    engine_path = Path("app/core/bmad/engine.py")
    refactored_path = Path("app/core/bmad/engine_refactored.py")

    print(f"\n1. Reading files...")
    with open(engine_path, 'r', encoding='utf-8') as f:
        engine_content = f.read()

    with open(refactored_path, 'r', encoding='utf-8') as f:
        refactored_content = f.read()

    print(f"   ✓ Read {len(engine_content)} chars from engine.py")
    print(f"   ✓ Read {len(refactored_content)} chars from engine_refactored.py")

    # Extract old execute_development
    print(f"\n2. Extracting old execute_development()...")
    old_method, old_start, old_end = extract_method(
        engine_content,
        'execute_development',
        r'    def execute_development\(\s*self,\s*context: BMADContext,'
    )
    print(f"   ✓ Found at position {old_start}-{old_end}")
    print(f"   ✓ Old method: {len(old_method)} chars, {len(old_method.splitlines())} lines")

    # Extract new execute_development from refactored
    print(f"\n3. Extracting new execute_development()...")
    new_exec_dev = extract_method(
        refactored_content,
        'execute_development',
        r'    def execute_development\('
    )[0]

    # Adjust indentation and type hints
    new_exec_dev_lines = new_exec_dev.split('\n')
    # Update signature to match original (with type hints)
    new_exec_dev_lines[0] = '    def execute_development('
    new_exec_dev_lines[1] = '        self,'
    new_exec_dev_lines[2] = '        context: BMADContext,'

    # Find the docstring end and replace return type
    for i, line in enumerate(new_exec_dev_lines):
        if line.strip().startswith(') -> ') or line.strip() == '):':
            new_exec_dev_lines[i] = '    ) -> BMADContext:'
            break

    new_exec_dev = '\n'.join(new_exec_dev_lines)
    print(f"   ✓ New method: {len(new_exec_dev)} chars, {len(new_exec_dev.splitlines())} lines")

    # Extract all helper methods
    print(f"\n4. Extracting helper methods...")
    helper_names = [
        '_generate_and_reflect_spec',
        '_apply_spec_reflection',
        '_validate_traceability_if_enabled',
        '_warn_critical_traceability_issues',
        '_generate_and_reflect_code',
        '_apply_code_reflection',
        '_run_quality_pipeline_if_available',
        '_log_quality_issues',
        '_validate_golden_data_if_enabled',
        '_apply_auto_fix',
        '_validate_boundaries_if_enabled',
        '_record_development_history',
        '_check_plan_mode_gate_if_enabled',
        '_record_development_failure',
    ]

    helpers = []
    for helper_name in helper_names:
        try:
            pattern = rf'    def {helper_name}\('
            helper_text = extract_method(refactored_content, helper_name, pattern)[0]
            helpers.append(helper_text)
            print(f"   ✓ Extracted {helper_name} ({len(helper_text.splitlines())} lines)")
        except ValueError as e:
            print(f"   ✗ Failed to extract {helper_name}: {e}")

    print(f"   ✓ Extracted {len(helpers)}/{len(helper_names)} helper methods")

    # Build new content
    print(f"\n5. Building new engine.py...")

    # Combine new execute_development + helpers
    all_new_methods = new_exec_dev + "\n\n" + "\n\n".join(helpers)

    # Replace in engine.py
    new_engine_content = (
        engine_content[:old_start] +
        all_new_methods +
        engine_content[old_end:]
    )

    print(f"   ✓ New engine.py: {len(new_engine_content)} chars")
    print(f"   ✓ Change: {len(new_engine_content) - len(engine_content):+d} chars")

    # Write to a temporary file first
    temp_path = engine_path.with_suffix('.py.new')
    print(f"\n6. Writing to {temp_path}...")
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(new_engine_content)

    print(f"   ✓ Written {len(new_engine_content)} chars")

    # Verify syntax
    print(f"\n7. Verifying Python syntax...")
    import ast
    try:
        ast.parse(new_engine_content)
        print(f"   ✓ Syntax valid!")
    except SyntaxError as e:
        print(f"   ✗ Syntax error: {e}")
        print(f"   ✗ Keeping original file unchanged")
        return False

    # Ask for confirmation (or just apply if running in script)
    print(f"\n8. Applying changes...")
    import shutil

    # Create another backup
    backup_path = engine_path.with_suffix('.py.backup2')
    shutil.copy2(engine_path, backup_path)
    print(f"   ✓ Created backup: {backup_path}")

    # Apply changes
    shutil.move(temp_path, engine_path)
    print(f"   ✓ Applied changes to {engine_path}")

    print(f"\n{'='*70}")
    print(f"✅ P1.1 Integration Complete!")
    print(f"{'='*70}")
    print(f"\nChanges:")
    print(f"  - Replaced execute_development(): {len(old_method.splitlines())} → {len(new_exec_dev.splitlines())} lines")
    print(f"  - Added {len(helpers)} helper methods")
    print(f"  - Total change: {len(new_engine_content) - len(engine_content):+d} chars")
    print(f"\nBackups:")
    print(f"  - {backup_path}")
    print(f"  - app/core/bmad/engine_backup_20260201.py")
    print(f"\nNext steps:")
    print(f"  1. Run tests: pytest tests/test_bmad_engine.py -v")
    print(f"  2. If tests fail, rollback: cp {backup_path} {engine_path}")

    return True

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
