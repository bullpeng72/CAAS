#!/usr/bin/env python3
"""
Comprehensive Backward Compatibility Test Suite

Tests that the migration from app.models to caas_framework.models
maintains 100% backward compatibility while issuing deprecation warnings.
"""

import sys
import warnings
from typing import Any


def test_basic_imports():
    """Test 1: Basic imports from both old and new locations work"""
    print("\n=== Test 1: Basic Imports ===")

    # New imports (framework)
    from caas_framework.models import (
        RequirementAnalysis,
        ArchitectureDesign,
        QualityMetrics,
        AgentRequirement,
        TaskRequirement,
        ArtifactType,
        DomainType,
        ToolRegistry,
    )

    # Old imports (app) - should still work
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always", DeprecationWarning)

        from app.models import (
            RequirementAnalysis as AppRA,
            ArchitectureDesign as AppAD,
            ArtifactType as AppAT,
        )

        # Verify deprecation warning was issued
        assert len(w) > 0, "Expected deprecation warning"
        assert issubclass(w[0].category, DeprecationWarning), "Wrong warning type"
        assert "app.models is deprecated" in str(w[0].message), "Wrong warning message"

    print("✓ Both old and new imports work")
    print(f"✓ Deprecation warning issued: {w[0].message}")

    return True


def test_identity_check():
    """Test 2: Old and new imports refer to the same classes"""
    print("\n=== Test 2: Identity Check ===")

    from caas_framework.models import (
        RequirementAnalysis,
        ArchitectureDesign,
        AgentRequirement,
        TaskRequirement,
        ArtifactType,
        DomainType,
        ToolMetadata,
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)

        from app.models import (
            RequirementAnalysis as AppRA,
            ArchitectureDesign as AppAD,
            AgentRequirement as AppAR,
            TaskRequirement as AppTR,
            ArtifactType as AppAT,
            DomainType as AppDT,
            ToolMetadata as AppTM,
        )

    # Identity checks - should be the exact same class objects
    assert RequirementAnalysis is AppRA, "RequirementAnalysis identity mismatch"
    assert ArchitectureDesign is AppAD, "ArchitectureDesign identity mismatch"
    assert AgentRequirement is AppAR, "AgentRequirement identity mismatch"
    assert TaskRequirement is AppTR, "TaskRequirement identity mismatch"
    assert ArtifactType is AppAT, "ArtifactType identity mismatch"
    assert DomainType is AppDT, "DomainType identity mismatch"
    assert ToolMetadata is AppTM, "ToolMetadata identity mismatch"

    print("✓ All classes have identical references")
    print("✓ Old imports resolve to exact same objects as new imports")

    return True


def test_legacy_module_imports():
    """Test 3: Legacy module-specific imports work"""
    print("\n=== Test 3: Legacy Module Imports ===")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)

        # Test module aliases
        from app.models import specifications
        from app.models import validation
        from app.models import artifact_types
        from app.models import domain_types
        from app.models import tool_registry

        # Test that these are actual modules
        assert hasattr(specifications, 'AgentSpecModel'), "specifications module missing AgentSpecModel"
        assert hasattr(validation, 'ValidationResult'), "validation module missing ValidationResult"
        assert hasattr(artifact_types, 'ArtifactType'), "artifact_types module missing ArtifactType"
        assert hasattr(domain_types, 'DomainType'), "domain_types module missing DomainType"
        assert hasattr(tool_registry, 'ToolRegistry'), "tool_registry module missing ToolRegistry"

    print("✓ Module-specific imports work (app.models.specifications, etc.)")
    print("✓ All legacy module aliases functional")

    return True


def test_schemas_alias():
    """Test 4: Legacy app.models.schemas alias works"""
    print("\n=== Test 4: app.models.schemas Alias ===")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)

        # This was the old import path - should now alias to specifications
        from app.models.schemas import (
            AgentSpecModel,
            TaskSpecModel,
            ConcretizedRequirement,
        )

        # Verify these are the right classes
        from caas_framework.models.specifications import (
            AgentSpecModel as FrameworkASM,
            TaskSpecModel as FrameworkTSM,
            ConcretizedRequirement as FrameworkCR,
        )

        assert AgentSpecModel is FrameworkASM, "AgentSpecModel alias mismatch"
        assert TaskSpecModel is FrameworkTSM, "TaskSpecModel alias mismatch"
        assert ConcretizedRequirement is FrameworkCR, "ConcretizedRequirement alias mismatch"

    print("✓ app.models.schemas → specifications alias working")
    print("✓ Old 'schemas' module path resolves correctly")

    return True


def test_model_instantiation():
    """Test 5: Models can be instantiated from both import paths"""
    print("\n=== Test 5: Model Instantiation ===")

    from caas_framework.models import (
        AgentRequirement,
        TaskRequirement,
        RequirementAnalysis,
        WorkflowType,
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from app.models import (
            AgentRequirement as AppAR,
            TaskRequirement as AppTR,
        )

    # Create instances using framework import
    agent1 = AgentRequirement(
        role="Test Agent",
        goal="Test goal",
        skills=["skill1"],
        priority=3
    )

    # Create instances using app import
    agent2 = AppAR(
        role="Test Agent 2",
        goal="Test goal 2",
        skills=["skill2"],
        priority=2
    )

    task1 = TaskRequirement(
        name="task1",
        description="Task from framework import",
        assigned_agent="Test Agent"
    )

    task2 = AppTR(
        name="task2",
        description="Task from app import",
        assigned_agent="Test Agent 2"
    )

    # Create complex model with both types
    analysis = RequirementAnalysis(
        domain="test",
        summary="Test analysis",
        agents=[agent1, agent2],  # Mixed instances
        tasks=[task1, task2],     # Mixed instances
        workflow_type=WorkflowType.SEQUENTIAL
    )

    assert len(analysis.agents) == 2, "Agents not added correctly"
    assert len(analysis.tasks) == 2, "Tasks not added correctly"

    # Test quality metrics
    metrics = analysis.compute_quality_metrics()
    assert metrics.overall_quality is not None, "Quality metrics not computed"

    print(f"✓ Created {len(analysis.agents)} agents from mixed imports")
    print(f"✓ Created {len(analysis.tasks)} tasks from mixed imports")
    print(f"✓ Quality metrics computed: overall={metrics.overall_quality}")

    return True


def test_validator_compatibility():
    """Test 6: GoldenDataValidator still works with migrated models"""
    print("\n=== Test 6: Validator Compatibility ===")

    try:
        from caas_framework.validation.golden_validator import GoldenDataValidator
        from caas_framework.models import (
            RequirementAnalysis,
            ArchitectureDesign,
            AgentRequirement,
            TaskRequirement,
        )

        # Create test data
        agent = AgentRequirement(
            role="Test Agent",
            goal="Test goal",
            skills=["test"],
            priority=3
        )

        task = TaskRequirement(
            name="test_task",
            description="Test task",
            assigned_agent="Test Agent"
        )

        analysis = RequirementAnalysis(
            domain="test",
            summary="Test",
            agents=[agent],
            tasks=[task]
        )

        # Validator should be able to import successfully
        # (Not instantiating as it requires golden_data parameter)
        assert GoldenDataValidator is not None, "GoldenDataValidator import failed"

        # Test that validator can reference the migrated models
        # The validator imports these models internally
        print("✓ GoldenDataValidator imported successfully")
        print("✓ Validator can reference migrated models (imports work)")

    except Exception as e:
        print(f"✗ Validator compatibility test failed: {e}")
        return False

    return True


def test_all_exports():
    """Test 7: All expected exports are available from both paths"""
    print("\n=== Test 7: Complete Export Coverage ===")

    framework_exports = [
        'ValidationIssue', 'ValidationSeverity', 'ValidationResult',
        'GoldenValidationReport', 'MissingItem', 'ExtraItem', 'MismatchedItem',
        'ComplianceStatus', 'DependencyIssue',
        'AgentSpecModel', 'TaskSpecModel', 'ConcretizedRequirement',
        'FeatureSpec', 'DataModel', 'NonFunctionalRequirements',
        'ArtifactType', 'ArtifactFormat', 'ArtifactMetadata', 'Artifact',
        'ArtifactGenerationConfig',
        'DomainType', 'ExecutionPattern', 'DomainClassification',
        'ToolMetadata', 'MCPServerConfig', 'ToolRegistry', 'get_tool_registry',
        'RequirementAnalysis', 'ArchitectureDesign', 'QualityMetrics',
        'AgentRequirement', 'TaskRequirement',
    ]

    # Check framework imports
    from caas_framework import models as framework_models

    missing_from_framework = []
    for export in framework_exports:
        if not hasattr(framework_models, export):
            missing_from_framework.append(export)

    if missing_from_framework:
        print(f"✗ Missing from framework: {missing_from_framework}")
        return False

    print(f"✓ All {len(framework_exports)} expected exports available from caas_framework.models")

    # Check backward compatibility
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from app import models as app_models

        missing_from_app = []
        for export in framework_exports:
            if not hasattr(app_models, export):
                missing_from_app.append(export)

        if missing_from_app:
            print(f"✗ Missing from app.models: {missing_from_app}")
            return False

    print(f"✓ All {len(framework_exports)} expected exports available from app.models (backward compat)")

    return True


def main():
    """Run all backward compatibility tests"""
    print("=" * 70)
    print("BACKWARD COMPATIBILITY TEST SUITE")
    print("=" * 70)

    tests = [
        ("Basic Imports", test_basic_imports),
        ("Identity Check", test_identity_check),
        ("Legacy Module Imports", test_legacy_module_imports),
        ("schemas Alias", test_schemas_alias),
        ("Model Instantiation", test_model_instantiation),
        ("Validator Compatibility", test_validator_compatibility),
        ("Complete Export Coverage", test_all_exports),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ ALL TESTS PASSED - Backward compatibility verified!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
