"""
Workflow Type Auto-Selection Module

This module provides heuristics to automatically determine whether
a CrewAI workflow should use Sequential or Hierarchical process mode
based on complexity analysis.
"""

from typing import List, Dict, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class WorkflowType(str, Enum):
    """Workflow process types"""
    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"


class ComplexityMetrics:
    """Complexity metrics for workflow analysis"""

    def __init__(
        self,
        agent_count: int = 0,
        task_count: int = 0,
        dependency_depth: int = 0,
        domain: Optional[str] = None,
        has_complex_coordination: bool = False,
        requires_dynamic_allocation: bool = False
    ):
        self.agent_count = agent_count
        self.task_count = task_count
        self.dependency_depth = dependency_depth
        self.domain = domain
        self.has_complex_coordination = has_complex_coordination
        self.requires_dynamic_allocation = requires_dynamic_allocation

    @property
    def complexity_score(self) -> float:
        """
        Calculate overall complexity score (0-100)

        Higher scores indicate more complex workflows that may benefit
        from hierarchical process mode.
        """
        score = 0.0

        # Agent count contribution (0-30 points)
        if self.agent_count >= 7:
            score += 30
        elif self.agent_count >= 5:
            score += 20
        elif self.agent_count >= 3:
            score += 10

        # Task count contribution (0-20 points)
        if self.task_count >= 15:
            score += 20
        elif self.task_count >= 10:
            score += 15
        elif self.task_count >= 5:
            score += 10

        # Dependency depth contribution (0-20 points)
        if self.dependency_depth >= 5:
            score += 20
        elif self.dependency_depth >= 3:
            score += 15
        elif self.dependency_depth >= 2:
            score += 10

        # Coordination complexity (0-15 points)
        if self.has_complex_coordination:
            score += 15

        # Dynamic allocation (0-15 points)
        if self.requires_dynamic_allocation:
            score += 15

        return min(score, 100.0)


# Domain patterns that typically benefit from hierarchical workflow
HIERARCHICAL_DOMAINS = {
    "WORKFLOW",           # Business process automation
    "FINANCE",            # Financial analysis and trading
    "HEALTHCARE",         # Patient care coordination
    "LEGAL",              # Legal document processing
    "CUSTOMER_SERVICE",   # Multi-tier support
    "DATA_PIPELINE",      # Complex ETL processes
    "ANALYTICS",          # Multi-stage data analysis
    "MONITORING",         # System monitoring and alerting
    "ORCHESTRATION",      # Service orchestration
    "ENTERPRISE",         # Enterprise workflows
}

# Domain patterns that work well with sequential workflow
SEQUENTIAL_DOMAINS = {
    "TASK_MANAGEMENT",    # Simple CRUD operations
    "CONTENT_GENERATION", # Linear content creation
    "DOCUMENT_MANAGEMENT", # Document storage
    "SIMPLE_API",         # Basic REST API
    "CHATBOT",           # Single-purpose bots
}


def calculate_dependency_depth(tasks: List[Dict[str, Any]]) -> int:
    """
    Calculate maximum dependency chain depth

    Args:
        tasks: List of task specifications

    Returns:
        Maximum depth of task dependency graph
    """
    if not tasks:
        return 0

    # Build dependency graph
    task_deps = {}
    for task in tasks:
        task_id = task.get("id") or task.get("name")
        deps = task.get("dependencies", []) or task.get("depends_on", [])
        task_deps[task_id] = deps

    # Calculate depth using DFS
    def get_depth(task_id: str, visited: set) -> int:
        if task_id in visited:
            return 0  # Avoid cycles

        visited.add(task_id)
        deps = task_deps.get(task_id, [])

        if not deps:
            return 1

        max_dep_depth = max((get_depth(dep, visited.copy()) for dep in deps), default=0)
        return max_dep_depth + 1

    # Find maximum depth across all tasks
    max_depth = 0
    for task_id in task_deps:
        depth = get_depth(task_id, set())
        max_depth = max(max_depth, depth)

    return max_depth


def analyze_coordination_complexity(tasks: List[Dict[str, Any]]) -> bool:
    """
    Determine if tasks require complex coordination

    Args:
        tasks: List of task specifications

    Returns:
        True if complex coordination is required
    """
    # Check for indicators of complex coordination
    coordination_keywords = [
        "coordinate", "orchestrate", "manage", "delegate",
        "prioritize", "schedule", "allocate", "route"
    ]

    for task in tasks:
        description = task.get("description", "").lower()
        goal = task.get("goal", "").lower()

        if any(keyword in description or keyword in goal for keyword in coordination_keywords):
            return True

    # Check if multiple tasks target same resources
    resource_usage = {}
    for task in tasks:
        resources = task.get("resources", [])
        for resource in resources:
            if resource not in resource_usage:
                resource_usage[resource] = 0
            resource_usage[resource] += 1

    # If multiple tasks share resources, coordination may be needed
    if any(count >= 3 for count in resource_usage.values()):
        return True

    return False


def requires_dynamic_allocation(requirement: str, tasks: List[Dict[str, Any]]) -> bool:
    """
    Determine if workflow requires dynamic task allocation

    Args:
        requirement: Original requirement text
        tasks: List of task specifications

    Returns:
        True if dynamic allocation is beneficial
    """
    # Check requirement for dynamic allocation indicators
    dynamic_keywords = [
        "dynamic", "adaptive", "flexible", "responsive",
        "real-time", "on-demand", "context-aware"
    ]

    requirement_lower = requirement.lower()
    if any(keyword in requirement_lower for keyword in dynamic_keywords):
        return True

    # Check for variable task execution patterns
    task_count = len(tasks)
    conditional_tasks = sum(
        1 for task in tasks
        if "condition" in task or "optional" in str(task).lower()
    )

    # If >30% of tasks are conditional, dynamic allocation helps
    if task_count > 0 and (conditional_tasks / task_count) > 0.3:
        return True

    return False


def determine_workflow_type(
    requirement: str,
    agents: Optional[List[Dict[str, Any]]] = None,
    tasks: Optional[List[Dict[str, Any]]] = None,
    domain: Optional[str] = None,
    force_type: Optional[str] = None
) -> WorkflowType:
    """
    Determine optimal workflow type based on complexity analysis

    Args:
        requirement: Natural language requirement
        agents: List of agent specifications (optional)
        tasks: List of task specifications (optional)
        domain: Domain hint (optional)
        force_type: Force specific workflow type (optional)

    Returns:
        Recommended workflow type (sequential or hierarchical)

    Examples:
        >>> determine_workflow_type(
        ...     "Build a simple todo app",
        ...     agents=[{"role": "developer"}],
        ...     tasks=[{"name": "create_api"}]
        ... )
        <WorkflowType.SEQUENTIAL: 'sequential'>

        >>> determine_workflow_type(
        ...     "Build enterprise financial platform",
        ...     agents=[...],  # 8 agents
        ...     tasks=[...],   # 20 tasks
        ...     domain="FINANCE"
        ... )
        <WorkflowType.HIERARCHICAL: 'hierarchical'>
    """
    # Force specific type if requested
    if force_type:
        if force_type.lower() in ["sequential", "hierarchical"]:
            logger.info(f"Using forced workflow type: {force_type}")
            return WorkflowType(force_type.lower())
        else:
            logger.warning(f"Invalid force_type: {force_type}, using auto-detection")

    agents = agents or []
    tasks = tasks or []

    # Calculate metrics
    agent_count = len(agents)
    task_count = len(tasks)
    dependency_depth = calculate_dependency_depth(tasks)
    has_coordination = analyze_coordination_complexity(tasks)
    requires_dynamic = requires_dynamic_allocation(requirement, tasks)

    metrics = ComplexityMetrics(
        agent_count=agent_count,
        task_count=task_count,
        dependency_depth=dependency_depth,
        domain=domain,
        has_complex_coordination=has_coordination,
        requires_dynamic_allocation=requires_dynamic
    )

    # Rule 1: Explicit domain preference
    if domain:
        domain_upper = domain.upper()
        if domain_upper in HIERARCHICAL_DOMAINS:
            logger.info(f"Domain {domain} typically uses hierarchical workflow")
            return WorkflowType.HIERARCHICAL
        elif domain_upper in SEQUENTIAL_DOMAINS and agent_count <= 3:
            logger.info(f"Domain {domain} typically uses sequential workflow")
            return WorkflowType.SEQUENTIAL

    # Rule 2: High agent count (5+)
    if agent_count >= 5:
        logger.info(f"High agent count ({agent_count}) → hierarchical")
        return WorkflowType.HIERARCHICAL

    # Rule 3: Complex task dependencies
    if dependency_depth >= 4:
        logger.info(f"Deep dependency chain (depth {dependency_depth}) → hierarchical")
        return WorkflowType.HIERARCHICAL

    # Rule 4: Complex coordination required
    if has_coordination and agent_count >= 3:
        logger.info("Complex coordination detected → hierarchical")
        return WorkflowType.HIERARCHICAL

    # Rule 5: Dynamic allocation needed
    if requires_dynamic and task_count >= 10:
        logger.info("Dynamic task allocation needed → hierarchical")
        return WorkflowType.HIERARCHICAL

    # Rule 6: Overall complexity score
    complexity = metrics.complexity_score
    if complexity >= 60:
        logger.info(f"High complexity score ({complexity:.1f}) → hierarchical")
        return WorkflowType.HIERARCHICAL

    # Default: Sequential for simpler workflows
    logger.info(f"Complexity score ({complexity:.1f}) → sequential")
    return WorkflowType.SEQUENTIAL


def get_workflow_recommendation(
    requirement: str,
    agents: Optional[List[Dict[str, Any]]] = None,
    tasks: Optional[List[Dict[str, Any]]] = None,
    domain: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get workflow recommendation with detailed explanation

    Args:
        requirement: Natural language requirement
        agents: List of agent specifications
        tasks: List of task specifications
        domain: Domain hint

    Returns:
        Dict with workflow_type and explanation
    """
    workflow_type = determine_workflow_type(requirement, agents, tasks, domain)

    agents = agents or []
    tasks = tasks or []

    metrics = ComplexityMetrics(
        agent_count=len(agents),
        task_count=len(tasks),
        dependency_depth=calculate_dependency_depth(tasks),
        domain=domain,
        has_complex_coordination=analyze_coordination_complexity(tasks),
        requires_dynamic_allocation=requires_dynamic_allocation(requirement, tasks)
    )

    reasons = []

    if workflow_type == WorkflowType.HIERARCHICAL:
        if metrics.agent_count >= 5:
            reasons.append(f"High agent count ({metrics.agent_count} agents)")
        if metrics.dependency_depth >= 4:
            reasons.append(f"Deep dependency chain (depth {metrics.dependency_depth})")
        if metrics.has_complex_coordination:
            reasons.append("Complex coordination required")
        if metrics.requires_dynamic_allocation:
            reasons.append("Dynamic task allocation needed")
        if domain and domain.upper() in HIERARCHICAL_DOMAINS:
            reasons.append(f"Domain {domain} benefits from hierarchical workflow")
    else:
        if metrics.agent_count <= 3:
            reasons.append(f"Small agent count ({metrics.agent_count} agents)")
        if metrics.dependency_depth <= 2:
            reasons.append("Simple task dependencies")
        if domain and domain.upper() in SEQUENTIAL_DOMAINS:
            reasons.append(f"Domain {domain} works well with sequential workflow")

    return {
        "workflow_type": workflow_type.value,
        "complexity_score": metrics.complexity_score,
        "reasons": reasons,
        "metrics": {
            "agent_count": metrics.agent_count,
            "task_count": metrics.task_count,
            "dependency_depth": metrics.dependency_depth,
            "has_complex_coordination": metrics.has_complex_coordination,
            "requires_dynamic_allocation": metrics.requires_dynamic_allocation
        }
    }
