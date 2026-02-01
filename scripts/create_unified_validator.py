#!/usr/bin/env python3
"""
Create Unified GoldenDataValidator

Merges app/core and caas_framework versions into a single unified validator.

Strategy:
1. Use app/core as base (has all 4 phases)
2. Add null safety from caas_framework
3. Update imports to caas_framework models
4. Save to caas_framework location
"""

from pathlib import Path

def create_unified_validator():
    """Create the unified validator file"""

    # Read the app/core version (complete implementation)
    app_core_file = Path("app/core/validation/golden_validator.py")
    with open(app_core_file, 'r', encoding='utf-8') as f:
        app_core_content = f.read()

    print(f"✓ Read app/core version: {len(app_core_content)} chars")

    # Create unified version with modifications
    unified_content = app_core_content

    # 1. Update docstring
    unified_content = unified_content.replace(
        '"""\nGolden Data Validator\n\nConcretizedRequirement (Golden Data)를 기준으로 각 Phase 출력을 검증합니다.\n"""',
        '''"""
Golden Data Validator (Unified)

Validates all pipeline phases against Golden Data (ConcretizedRequirement).

This is a unified version merged from:
- app/core/validation/golden_validator.py (4 phases, logging, NFR validation)
- caas_framework/validation/golden_validator.py (null safety)

Version: 2.0 (Unified - Phase 2.1)
Date: 2026-02-01

Supports:
- Phase 1: Discovery (RequirementAnalysis)
- Phase 2: Architecture (ArchitectureDesign)
- Phase 3: Design (AgentSpecs + TaskSpecs)
- Phase 4: Development (YAML code spec)

Features:
- Null-safe feature/data model access
- Comprehensive logging with emojis
- NFR (Non-Functional Requirements) validation
- Coverage scoring with compliance thresholds
"""'''
    )

    # 2. Update imports - change app.models to caas_framework.models
    import_replacements = {
        'from app.models.schemas import': 'from caas_framework.models.specifications import',
        'from caas_framework.utils.logger import get_logger': 'from caas_framework.utils.logger import get_logger',
    }

    for old_import, new_import in import_replacements.items():
        if old_import in unified_content:
            unified_content = unified_content.replace(old_import, new_import)
            print(f"✓ Updated import: {old_import} -> {new_import}")

    # 3. Add null safety to __init__
    unified_content = unified_content.replace(
        '        self.golden_data = golden_data\n        logger.info(f"🎯 Golden Data Validator initialized with {len(golden_data.features)} features")',
        '''        self.golden_data = golden_data

        # Null-safe feature count
        feature_count = len(golden_data.features) if golden_data.features else 0
        logger.info(f"🎯 Golden Data Validator initialized with {feature_count} features")'''
    )
    print("✓ Added null safety to __init__")

    # 4. Add null safety to validate_discovery
    # Replace direct feature access with null-safe version
    unified_content = unified_content.replace(
        '        # 1. Feature Coverage 검증\n        golden_feature_names = {f.name.lower() for f in self.golden_data.features}',
        '''        # 1. Feature Coverage 검증 (null-safe)
        features = self.golden_data.features if self.golden_data.features else []
        golden_feature_names = {f.name.lower() for f in features}'''
    )

    unified_content = unified_content.replace(
        '        golden_features_dict = {f.name.lower(): f for f in self.golden_data.features}',
        '        golden_features_dict = {f.name.lower(): f for f in features}'
    )

    # Fix the line counting issue
    unified_content = unified_content.replace(
        '        # 3. Calculate Coverage Score\n        total_golden_items = len(self.golden_data.features) + len(self.golden_data.data_models)',
        '''        # 3. Calculate Coverage Score (null-safe)
        data_models = self.golden_data.data_models if self.golden_data.data_models else []
        total_golden_items = len(features) + len(data_models)'''
    )

    print("✓ Added null safety to validate_discovery")

    # 5. Add null safety to validate_architecture
    unified_content = unified_content.replace(
        '        # 1. Component Coverage 검증\n        # Golden Data의 각 Feature가 Architecture의 Component로 매핑되어야 함\n        golden_features = {f.name.lower(): f for f in self.golden_data.features}',
        '''        # 1. Component Coverage 검증 (null-safe)
        # Golden Data의 각 Feature가 Architecture의 Component로 매핑되어야 함
        features = self.golden_data.features if self.golden_data.features else []
        golden_features = {f.name.lower(): f for f in features}'''
    )

    # Fix data_models access in validate_architecture
    unified_content = unified_content.replace(
        '        # 2. Data Flow Coverage\n        # Golden Data의 Data Models가 Architecture의 data flows에 반영되어야 함\n        if self.golden_data.data_models:',
        '''        # 2. Data Flow Coverage (null-safe)
        # Golden Data의 Data Models가 Architecture의 data flows에 반영되어야 함
        data_models = self.golden_data.data_models if self.golden_data.data_models else []
        if data_models:'''
    )

    unified_content = unified_content.replace(
        '            golden_entities = {dm.entity_name.lower() for dm in self.golden_data.data_models}',
        '            golden_entities = {dm.entity_name.lower() for dm in data_models}'
    )

    # Fix total_checks calculation
    unified_content = unified_content.replace(
        '        # 4. Calculate Coverage Score\n        total_checks = len(golden_features) + len(self.golden_data.data_models) + 2  # +2 for NFRs',
        '''        # 4. Calculate Coverage Score (null-safe)
        total_checks = len(golden_features) + len(data_models) + 2  # +2 for NFRs'''
    )

    print("✓ Added null safety to validate_architecture")

    # 6. Add null safety to validate_design
    unified_content = unified_content.replace(
        '        # 1. Feature Coverage by Tasks\n        golden_features = {f.name.lower(): f for f in self.golden_data.features}',
        '''        # 1. Feature Coverage by Tasks (null-safe)
        features = self.golden_data.features if self.golden_data.features else []
        golden_features = {f.name.lower(): f for f in features}'''
    )

    # Fix UI components check
    unified_content = unified_content.replace(
        '        # 2. UI Component Coverage\n        if self.golden_data.ui_components:',
        '''        # 2. UI Component Coverage (null-safe)
        ui_components = self.golden_data.ui_components if self.golden_data.ui_components else []
        if ui_components:'''
    )

    unified_content = unified_content.replace(
        '            golden_ui_pages = {ui.page_name.lower() for ui in self.golden_data.ui_components}',
        '            golden_ui_pages = {ui.page_name.lower() for ui in ui_components}'
    )

    unified_content = unified_content.replace(
        '            if len(self.golden_data.ui_components) > 0 and len(ui_related_tasks) == 0:',
        '            if len(ui_components) > 0 and len(ui_related_tasks) == 0:'
    )

    unified_content = unified_content.replace(
        '                    description=f"Golden Data has {len(self.golden_data.ui_components)} UI components but no UI-related tasks found",',
        '                    description=f"Golden Data has {len(ui_components)} UI components but no UI-related tasks found",'
    )

    # Fix coverage calculation
    unified_content = unified_content.replace(
        '        # 3. Calculate Coverage Score\n        total_golden_items = len(self.golden_data.features)',
        '''        # 3. Calculate Coverage Score (null-safe)
        total_golden_items = len(features)'''
    )

    print("✓ Added null safety to validate_design")

    # 7. Add null safety to validate_code
    unified_content = unified_content.replace(
        '        golden_features = {f.name.lower(): f for f in self.golden_data.features}\n\n        # 각 Golden Feature가 Task description에 언급되는지 확인',
        '''        # Null-safe feature extraction
        features = self.golden_data.features if self.golden_data.features else []
        golden_features = {f.name.lower(): f for f in features}

        # 각 Golden Feature가 Task description에 언급되는지 확인'''
    )

    # Fix coverage calculation in validate_code
    unified_content = unified_content.replace(
        '        # 3. Calculate Coverage Score\n        total_golden_items = len(self.golden_data.features)',
        '''        # 3. Calculate Coverage Score (null-safe)
        total_golden_items = len(features)'''
    )

    print("✓ Added null safety to validate_code")

    # 8. Add validation models import
    # Need to add validation models to imports
    old_imports = '''from caas_framework.models.specifications import (
    ConcretizedRequirement,
    RequirementAnalysis,
    ArchitectureDesign,
    AgentSpecModel,
    TaskSpecModel,
    GoldenValidationReport,
    MissingItem,
    ExtraItem,
    MismatchedItem,
    ComplianceStatus,
)'''

    new_imports = '''from caas_framework.models.specifications import (
    ConcretizedRequirement,
    RequirementAnalysis,
    ArchitectureDesign,
    AgentSpecModel,
    TaskSpecModel,
)
from caas_framework.models.validation import (
    GoldenValidationReport,
    MissingItem,
    ExtraItem,
    MismatchedItem,
    ComplianceStatus,
)'''

    unified_content = unified_content.replace(old_imports, new_imports)
    print("✓ Split imports (specifications vs validation)")

    # Write to caas_framework location
    output_file = Path("caas_framework/validation/golden_validator.py")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(unified_content)

    print(f"\n✅ Created unified validator: {output_file}")
    print(f"   Size: {len(unified_content)} chars, {len(unified_content.splitlines())} lines")

    return output_file

def create_reexport_wrapper():
    """Create re-export wrapper in app/core"""

    wrapper_content = '''"""
Golden Data Validator (Deprecated)

This module is deprecated. Please use caas_framework.validation.golden_validator instead.

The implementation has been unified and moved to caas_framework for better modularity.

For backward compatibility, this module re-exports the unified validator.
"""

import warnings

# Re-export from unified location
from caas_framework.validation.golden_validator import GoldenDataValidator

# Issue deprecation warning
warnings.warn(
    "app.core.validation.golden_validator is deprecated. "
    "Use caas_framework.validation.golden_validator instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ['GoldenDataValidator']
'''

    wrapper_file = Path("app/core/validation/golden_validator.py")
    with open(wrapper_file, 'w', encoding='utf-8') as f:
        f.write(wrapper_content)

    print(f"✅ Created re-export wrapper: {wrapper_file}")
    print(f"   Size: {len(wrapper_content)} chars")

    return wrapper_file

if __name__ == "__main__":
    print("="*70)
    print("P2.1: Creating Unified GoldenDataValidator")
    print("="*70)

    try:
        # Step 1: Create unified validator
        print("\n[Step 1] Creating unified validator...")
        unified_file = create_unified_validator()

        # Step 2: Create re-export wrapper
        print("\n[Step 2] Creating re-export wrapper...")
        wrapper_file = create_reexport_wrapper()

        # Summary
        print("\n" + "="*70)
        print("✅ P2.1 Integration Complete!")
        print("="*70)
        print("\nFiles created:")
        print(f"  1. {unified_file} (unified validator)")
        print(f"  2. {wrapper_file} (backward compatibility)")
        print("\nBackups available:")
        print(f"  - app/core/validation/golden_validator_backup_20260201.py")
        print(f"  - caas_framework/validation/golden_validator_backup_20260201.py")
        print("\nNext steps:")
        print("  1. Test the unified validator")
        print("  2. Update imports across the project (optional)")
        print("  3. Run integration tests")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
