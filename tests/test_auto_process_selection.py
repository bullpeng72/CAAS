"""
Test Automatic Process Type Selection Integration

Tests that process type (sequential/hierarchical) is automatically selected
based on project complexity in the BMAD Engine.
"""

from caas_framework.utils.workflow_selector import (
    ComplexityMetrics,
    WorkflowType,
    analyze_coordination_complexity,
    calculate_dependency_depth,
    determine_workflow_type,
    get_workflow_recommendation,
    requires_dynamic_allocation,
)


def test_workflow_type_enum():
    """Test WorkflowType enum"""
    assert WorkflowType.SEQUENTIAL.value == "sequential"
    assert WorkflowType.HIERARCHICAL.value == "hierarchical"


def test_complexity_metrics_simple_project():
    """Test complexity metrics for simple project"""
    metrics = ComplexityMetrics(
        agent_count=2,
        task_count=3,
        dependency_depth=1,
        domain="TASK_MANAGEMENT",
        has_complex_coordination=False,
        requires_dynamic_allocation=False
    )

    # Simple project should have low complexity
    assert metrics.complexity_score < 40


def test_complexity_metrics_complex_project():
    """Test complexity metrics for complex project"""
    metrics = ComplexityMetrics(
        agent_count=8,
        task_count=20,
        dependency_depth=5,
        domain="FINANCE",
        has_complex_coordination=True,
        requires_dynamic_allocation=True
    )

    # Complex project should have high complexity
    assert metrics.complexity_score >= 60


def test_calculate_dependency_depth_simple():
    """Test dependency depth calculation for linear tasks"""
    tasks = [
        {"id": "task1", "dependencies": []},
        {"id": "task2", "dependencies": ["task1"]},
        {"id": "task3", "dependencies": ["task2"]},
    ]

    depth = calculate_dependency_depth(tasks)
    assert depth == 3  # Linear chain


def test_calculate_dependency_depth_complex():
    """Test dependency depth calculation for branched tasks"""
    tasks = [
        {"id": "task1", "dependencies": []},
        {"id": "task2", "dependencies": []},
        {"id": "task3", "dependencies": ["task1", "task2"]},
        {"id": "task4", "dependencies": ["task3"]},
        {"id": "task5", "dependencies": ["task3"]},
    ]

    depth = calculate_dependency_depth(tasks)
    assert depth >= 2  # At least 2 levels deep


def test_analyze_coordination_complexity_simple():
    """Test coordination complexity analysis for simple tasks"""
    tasks = [
        {"description": "Create a file", "goal": "Write data"},
        {"description": "Read a file", "goal": "Get data"},
    ]

    is_complex = analyze_coordination_complexity(tasks)
    assert not is_complex  # No coordination keywords


def test_analyze_coordination_complexity_with_coordination():
    """Test coordination complexity analysis with coordination tasks"""
    tasks = [
        {"description": "Coordinate team members", "goal": "Manage workflow"},
        {"description": "Delegate tasks to agents", "goal": "Orchestrate"},
    ]

    is_complex = analyze_coordination_complexity(tasks)
    assert is_complex  # Has coordination keywords


def test_requires_dynamic_allocation_simple():
    """Test dynamic allocation detection for simple requirements"""
    requirement = "Build a simple todo list application"
    tasks = [
        {"name": "create_task"},
        {"name": "list_tasks"},
    ]

    needs_dynamic = requires_dynamic_allocation(requirement, tasks)
    assert not needs_dynamic


def test_requires_dynamic_allocation_dynamic():
    """Test dynamic allocation detection for dynamic requirements"""
    requirement = "Build a real-time adaptive workflow system"
    tasks = [
        {"name": "task1"},
        {"name": "task2"},
        {"name": "task3"},
    ]

    needs_dynamic = requires_dynamic_allocation(requirement, tasks)
    assert needs_dynamic  # Has "real-time" and "adaptive"


def test_determine_workflow_type_simple_project():
    """Test workflow type selection for simple project"""
    workflow = determine_workflow_type(
        requirement="Build a simple blog application",
        agents=[
            {"role": "developer", "goal": "write code"}
        ],
        tasks=[
            {"name": "create_post"},
            {"name": "list_posts"},
        ],
        domain="CONTENT_GENERATION"
    )

    assert workflow == WorkflowType.SEQUENTIAL


def test_determine_workflow_type_complex_project():
    """Test workflow type selection for complex project"""
    # Create 8 agents
    agents = [
        {"role": f"agent_{i}", "goal": f"handle task {i}"}
        for i in range(8)
    ]

    # Create 15 tasks with dependencies
    tasks = [
        {"id": f"task_{i}", "name": f"task_{i}", "dependencies": []}
        for i in range(15)
    ]

    workflow = determine_workflow_type(
        requirement="Build enterprise financial trading platform",
        agents=agents,
        tasks=tasks,
        domain="FINANCE"
    )

    assert workflow == WorkflowType.HIERARCHICAL


def test_determine_workflow_type_high_agent_count():
    """Test that high agent count triggers hierarchical"""
    agents = [{"role": f"agent_{i}"} for i in range(6)]
    tasks = [{"name": f"task_{i}"} for i in range(3)]

    workflow = determine_workflow_type(
        requirement="Multi-agent system",
        agents=agents,
        tasks=tasks
    )

    assert workflow == WorkflowType.HIERARCHICAL


def test_determine_workflow_type_deep_dependencies():
    """Test that deep dependency chains trigger hierarchical"""
    tasks = [
        {"id": "task1", "dependencies": []},
        {"id": "task2", "dependencies": ["task1"]},
        {"id": "task3", "dependencies": ["task2"]},
        {"id": "task4", "dependencies": ["task3"]},
        {"id": "task5", "dependencies": ["task4"]},
    ]

    workflow = determine_workflow_type(
        requirement="Complex pipeline",
        agents=[{"role": "agent1"}],
        tasks=tasks
    )

    assert workflow == WorkflowType.HIERARCHICAL


def test_determine_workflow_type_force_sequential():
    """Test forcing sequential workflow"""
    # Even with many agents, force sequential
    agents = [{"role": f"agent_{i}"} for i in range(8)]
    tasks = [{"name": f"task_{i}"} for i in range(10)]

    workflow = determine_workflow_type(
        requirement="Complex project",
        agents=agents,
        tasks=tasks,
        force_type="sequential"
    )

    assert workflow == WorkflowType.SEQUENTIAL


def test_determine_workflow_type_force_hierarchical():
    """Test forcing hierarchical workflow"""
    # Even with few agents, force hierarchical
    agents = [{"role": "agent1"}]
    tasks = [{"name": "task1"}]

    workflow = determine_workflow_type(
        requirement="Simple project",
        agents=agents,
        tasks=tasks,
        force_type="hierarchical"
    )

    assert workflow == WorkflowType.HIERARCHICAL


def test_get_workflow_recommendation_simple():
    """Test workflow recommendation with explanation for simple project"""
    recommendation = get_workflow_recommendation(
        requirement="Build a chatbot",
        agents=[{"role": "bot_agent"}],
        tasks=[{"name": "respond_to_user"}],
        domain="CHATBOT"
    )

    assert recommendation["workflow_type"] == "sequential"
    assert isinstance(recommendation["complexity_score"], float)
    assert isinstance(recommendation["reasons"], list)
    assert "metrics" in recommendation


def test_get_workflow_recommendation_complex():
    """Test workflow recommendation with explanation for complex project"""
    agents = [{"role": f"agent_{i}"} for i in range(7)]
    tasks = [
        {"id": f"task_{i}", "name": f"task_{i}", "dependencies": []}
        for i in range(12)
    ]

    recommendation = get_workflow_recommendation(
        requirement="Build enterprise workflow system",
        agents=agents,
        tasks=tasks,
        domain="WORKFLOW"
    )

    assert recommendation["workflow_type"] == "hierarchical"
    # Note: Domain preference (WORKFLOW) can select hierarchical even with lower complexity
    assert recommendation["complexity_score"] >= 30
    assert len(recommendation["reasons"]) > 0
    assert recommendation["metrics"]["agent_count"] == 7
    assert recommendation["metrics"]["task_count"] == 12


def test_bmad_integration_pattern():
    """Test the integration pattern used in BMAD Engine"""
    # Simulate what happens in BMAD Engine execute_design

    # 1. Context has agent_specs and task_specs
    agent_specs = [
        {"id": "agent1", "role": "Developer"},
        {"id": "agent2", "role": "Tester"},
    ]

    task_specs = [
        {"id": "task1", "name": "write_code"},
        {"id": "task2", "name": "test_code"},
        {"id": "task3", "name": "deploy_code"},
    ]

    requirement = "Build a simple web application"
    domain = "SIMPLE_API"

    # 2. Get workflow recommendation
    recommendation = get_workflow_recommendation(
        requirement=requirement,
        agents=agent_specs,
        tasks=task_specs,
        domain=domain
    )

    # 3. Extract workflow type
    workflow_type = recommendation["workflow_type"]
    complexity_score = recommendation["complexity_score"]
    reasons = recommendation["reasons"]

    # 4. Verify results
    assert workflow_type in ["sequential", "hierarchical"]
    assert 0 <= complexity_score <= 100
    assert isinstance(reasons, list)

    # 5. Simulate updating context.analysis
    analysis = {
        "workflow_type": workflow_type,
        "workflow_complexity_score": complexity_score,
        "workflow_selection_reasons": reasons
    }

    assert analysis["workflow_type"] in ["sequential", "hierarchical"]
    assert "workflow_complexity_score" in analysis
    assert "workflow_selection_reasons" in analysis


def test_domain_preference_hierarchical():
    """Test that hierarchical domains prefer hierarchical workflow"""
    for domain in ["WORKFLOW", "FINANCE", "HEALTHCARE", "ENTERPRISE"]:
        workflow = determine_workflow_type(
            requirement=f"Build {domain.lower()} system",
            agents=[{"role": "agent1"}],
            tasks=[{"name": "task1"}],
            domain=domain
        )
        assert workflow == WorkflowType.HIERARCHICAL


def test_domain_preference_sequential():
    """Test that sequential domains prefer sequential workflow"""
    for domain in ["TASK_MANAGEMENT", "CHATBOT", "SIMPLE_API"]:
        workflow = determine_workflow_type(
            requirement=f"Build {domain.lower()} system",
            agents=[{"role": "agent1"}],
            tasks=[{"name": "task1"}],
            domain=domain
        )
        assert workflow == WorkflowType.SEQUENTIAL


if __name__ == "__main__":
    # Run tests
    test_workflow_type_enum()
    test_complexity_metrics_simple_project()
    test_complexity_metrics_complex_project()
    test_calculate_dependency_depth_simple()
    test_calculate_dependency_depth_complex()
    test_analyze_coordination_complexity_simple()
    test_analyze_coordination_complexity_with_coordination()
    test_requires_dynamic_allocation_simple()
    test_requires_dynamic_allocation_dynamic()
    test_determine_workflow_type_simple_project()
    test_determine_workflow_type_complex_project()
    test_determine_workflow_type_high_agent_count()
    test_determine_workflow_type_deep_dependencies()
    test_determine_workflow_type_force_sequential()
    test_determine_workflow_type_force_hierarchical()
    test_get_workflow_recommendation_simple()
    test_get_workflow_recommendation_complex()
    test_bmad_integration_pattern()
    test_domain_preference_hierarchical()
    test_domain_preference_sequential()

    print("\n" + "="*70)
    print("✅ All Auto Process Selection tests passed!")
    print("="*70)
