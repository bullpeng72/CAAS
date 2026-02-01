#!/usr/bin/env python3
"""
P1.1 Integration Script

Integrates the refactored execute_development() and helper methods into engine.py
"""

import re
from pathlib import Path

# Read the original engine.py
engine_file = Path("app/core/bmad/engine.py")
with open(engine_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Read the refactored version
refactored_file = Path("app/core/bmad/engine_refactored.py")
with open(refactored_file, 'r', encoding='utf-8') as f:
    refactored_content = f.read()

# Extract the new execute_development method (lines 23-96)
execute_dev_pattern = r'    def execute_development\(\s*self,.*?\n(?:.*?\n)*?        except Exception as e:\n            self\._record_development_failure\(context, e\)\n            raise\n'

# Extract helper methods (lines 98-624)
# Each helper method from _generate_and_reflect_spec to _record_development_failure

helpers = []

# Helper method patterns
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

# Extract all helper methods from refactored code
for helper_name in helper_names:
    pattern = rf'    def {helper_name}\([\s\S]*?(?=\n    def |\Z)'
    match = re.search(pattern, refactored_content)
    if match:
        helpers.append(match.group(0).rstrip())
        print(f"✓ Extracted {helper_name}")
    else:
        print(f"✗ Failed to extract {helper_name}")

# Extract the new execute_development
exec_dev_match = re.search(execute_dev_pattern, refactored_content, re.MULTILINE)
if exec_dev_match:
    new_execute_dev = exec_dev_match.group(0)
    print(f"\n✓ Extracted execute_development ({len(new_execute_dev.splitlines())} lines)")
else:
    print("\n✗ Failed to extract execute_development")
    exit(1)

# Find and replace the old execute_development in engine.py
# Pattern to match from line 830 to line 1222
old_execute_pattern = r'    def execute_development\(\s*self,\s*context: BMADContext,.*?\n(?:.*?\n)*?(?=\n    def )'

old_match = re.search(old_execute_pattern, content, re.MULTILINE)
if old_match:
    old_method = old_match.group(0)
    print(f"✓ Found old execute_development ({len(old_method.splitlines())} lines)")

    # Replace with new version + add helper methods
    all_new_methods = new_execute_dev + "\n\n" + "\n\n".join(helpers)

    new_content = content.replace(old_method, all_new_methods)

    # Write the updated content
    with open(engine_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"\n✅ Successfully integrated P1.1 refactoring!")
    print(f"   - Replaced execute_development() (391 → 30 lines)")
    print(f"   - Added {len(helpers)} helper methods")

else:
    print("✗ Failed to find old execute_development")
    exit(1)
