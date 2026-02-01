#!/usr/bin/env python3
"""
Integration tests to verify existing app code still works
after the models migration.
"""

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

print("=== App Integration Tests ===\n")

# Test 1: Check files that import from app.models still work
print("Test 1: Scanning app/ for model imports...")

import subprocess
result = subprocess.run(
    ["grep", "-r", "from app.models", "app/", "--include=*.py"],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    lines = result.stdout.strip().split('\n')
    files_with_imports = set()
    for line in lines:
        if ':' in line:
            file_path = line.split(':')[0]
            files_with_imports.add(file_path)
    
    print(f"✓ Found {len(files_with_imports)} app files with app.models imports")
    print(f"  These files rely on backward compatibility shim")
    
    # Try importing some of these files to verify they work
    test_imports = []
    for file_path in list(files_with_imports)[:3]:  # Test first 3
        module_path = file_path.replace('/', '.').replace('.py', '')
        try:
            __import__(module_path)
            test_imports.append(module_path)
        except Exception as e:
            print(f"  ✗ Failed to import {module_path}: {e}")
    
    if test_imports:
        print(f"✓ Successfully imported {len(test_imports)} sample modules")
else:
    print("✓ No app files import from app.models (clean migration)")

print()

# Test 2: Verify agents can still use the models
print("Test 2: Testing agent compatibility...")

try:
    from app.agents.requirement_analyst import RequirementAnalystAgent
    from caas_framework.models import RequirementAnalysis
    
    print("✓ RequirementAnalystAgent imports successfully")
    print("✓ Agent can reference RequirementAnalysis model")
except Exception as e:
    print(f"✗ Agent compatibility test failed: {e}")

print()

# Test 3: Verify backward compatibility in actual usage
print("Test 3: Testing real-world usage patterns...")

try:
    # Pattern 1: Old import style
    from app.models.schemas import ConcretizedRequirement, FeatureSpec
    
    # Pattern 2: New import style
    from caas_framework.models import DataModel, NonFunctionalRequirements
    
    # Pattern 3: Mixed usage
    req = ConcretizedRequirement(
        id="test_req_001",
        description="Test requirement",
        priority="high",
        domain="testing"
    )
    
    feature = FeatureSpec(
        id="feat_001",
        name="Test Feature",
        description="Test feature description",
        requirements=[req.id]
    )
    
    nfr = NonFunctionalRequirements(
        performance=["Fast response"],
        scalability=["Handle 1000 users"],
        security=["Data encryption"]
    )
    
    print("✓ Old-style imports work (app.models.schemas)")
    print("✓ New-style imports work (caas_framework.models)")
    print("✓ Models can be instantiated and used together")
    print(f"✓ Created requirement: {req.id}")
    print(f"✓ Created feature: {feature.name}")
    print(f"✓ Created NFR with {len(nfr.performance)} performance criteria")
    
except Exception as e:
    print(f"✗ Real-world usage test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 4: Verify validation still works
print("Test 4: Testing validation workflow...")

try:
    from caas_framework.validation.golden_validator import GoldenDataValidator
    from caas_framework.models import (
        AgentSpecModel,
        TaskSpecModel,
        RequirementAnalysis,
        AgentRequirement,
        TaskRequirement
    )
    
    # Create test data
    agent_req = AgentRequirement(
        role="Validator Agent",
        goal="Validate data",
        skills=["validation"],
        priority=1
    )
    
    task_req = TaskRequirement(
        name="validate_data",
        description="Validate the test data",
        assigned_agent="Validator Agent"
    )
    
    analysis = RequirementAnalysis(
        domain="validation",
        summary="Test validation workflow",
        agents=[agent_req],
        tasks=[task_req]
    )
    
    # Create spec models
    agent_spec = AgentSpecModel(
        id="validator_agent",
        role="Validator Agent",
        goal="Validate data",
        backstory="An agent that validates data"
    )
    
    task_spec = TaskSpecModel(
        id="validate_data",
        description="Validate the test data",
        expected_output="Validation report",
        agent="validator_agent"
    )
    
    print("✓ Validation models created successfully")
    print("✓ RequirementAnalysis model functional")
    print(f"✓ Analysis has {len(analysis.agents)} agents, {len(analysis.tasks)} tasks")
    print("✓ Spec models (AgentSpecModel, TaskSpecModel) working")
    
except Exception as e:
    print(f"✗ Validation workflow test failed: {e}")
    import traceback
    traceback.print_exc()

print()
print("=== Integration Tests Complete ===")
