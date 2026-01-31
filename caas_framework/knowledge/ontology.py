"""
CAAS Framework Ontology

Ontology-based knowledge management for agent-task-tool relationships.
Provides semantic validation and recommendation capabilities.
"""

from typing import Dict, List, Set
from enum import Enum


# =============================================================================
# Ontology Enums
# =============================================================================

class AgentRole(str, Enum):
    """Agent role ontology (BMAD-extended)"""
    # Core roles
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    WRITER = "writer"
    REVIEWER = "reviewer"
    CODER = "coder"
    MANAGER = "manager"
    PLANNER = "planner"
    EXECUTOR = "executor"

    # BMAD specialized roles - Architecture
    ARCHITECT = "architect"
    TEST_ARCHITECT = "test_architect"
    SECURITY_ARCHITECT = "security_architect"

    # BMAD specialized roles - Product
    PRODUCT_MANAGER = "product_manager"
    TECH_WRITER = "tech_writer"
    QA_ENGINEER = "qa_engineer"

    # BMAD specialized roles - Development
    UX_DESIGNER = "ux_designer"
    BACKEND_DEVELOPER = "backend_developer"
    FRONTEND_DEVELOPER = "frontend_developer"
    DATA_ENGINEER = "data_engineer"

    # BMAD specialized roles - Leadership
    SCRUM_MASTER = "scrum_master"
    BMAD_MASTER = "bmad_master"
    DEVOPS_ENGINEER = "devops_engineer"


class TaskType(str, Enum):
    """Task type ontology (BMAD-extended)"""
    # Core tasks
    RESEARCH = "research"
    ANALYSIS = "analysis"
    WRITING = "writing"
    CODING = "coding"
    REVIEW = "review"
    PLANNING = "planning"
    EXECUTION = "execution"
    SYNTHESIS = "synthesis"

    # BMAD specialized tasks - Architecture & Design
    SYSTEM_DESIGN = "system_design"
    API_DESIGN = "api_design"
    DATABASE_DESIGN = "database_design"
    UI_DESIGN = "ui_design"
    UX_RESEARCH = "ux_research"
    PROTOTYPING = "prototyping"

    # BMAD specialized tasks - Testing & Quality
    TEST_PLANNING = "test_planning"
    TEST_AUTOMATION = "test_automation"
    QUALITY_ASSURANCE = "quality_assurance"
    SECURITY_AUDIT = "security_audit"
    PERFORMANCE_TESTING = "performance_testing"

    # BMAD specialized tasks - Development
    FRONTEND_DEVELOPMENT = "frontend_development"
    BACKEND_DEVELOPMENT = "backend_development"
    DATA_PROCESSING = "data_processing"
    DATA_PIPELINE = "data_pipeline"

    # BMAD specialized tasks - Agile & Operations
    SPRINT_PLANNING = "sprint_planning"
    RETROSPECTIVE = "retrospective"
    TEAM_COORDINATION = "team_coordination"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    DOCUMENTATION = "documentation"

    # BMAD specialized tasks - Product
    PRODUCT_PLANNING = "product_planning"
    USER_STORY_WRITING = "user_story_writing"
    REQUIREMENT_ANALYSIS = "requirement_analysis"

    # Other
    GENERAL = "general"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"


class ToolCapability(str, Enum):
    """Tool capability ontology"""
    SEARCH = "search"
    READ = "read"
    WRITE = "write"
    COMPUTE = "compute"
    COMMUNICATE = "communicate"
    VISUALIZE = "visualize"


# =============================================================================
# Role-Task-Tool Mappings
# =============================================================================

ROLE_TASK_MAPPINGS: Dict[AgentRole, List[TaskType]] = {
    # Core roles
    AgentRole.RESEARCHER: [TaskType.RESEARCH, TaskType.ANALYSIS, TaskType.UX_RESEARCH],
    AgentRole.ANALYST: [TaskType.ANALYSIS, TaskType.SYNTHESIS, TaskType.DATA_PROCESSING],
    AgentRole.WRITER: [TaskType.WRITING, TaskType.SYNTHESIS, TaskType.DOCUMENTATION],
    AgentRole.REVIEWER: [TaskType.REVIEW, TaskType.ANALYSIS, TaskType.QUALITY_ASSURANCE],
    AgentRole.CODER: [TaskType.CODING, TaskType.EXECUTION, TaskType.BACKEND_DEVELOPMENT],
    AgentRole.MANAGER: [TaskType.PLANNING, TaskType.REVIEW, TaskType.TEAM_COORDINATION],
    AgentRole.PLANNER: [TaskType.PLANNING, TaskType.ANALYSIS, TaskType.SPRINT_PLANNING],
    AgentRole.EXECUTOR: [TaskType.EXECUTION, TaskType.CODING, TaskType.DEPLOYMENT],

    # BMAD specialized roles - Architecture
    AgentRole.ARCHITECT: [
        TaskType.SYSTEM_DESIGN,
        TaskType.API_DESIGN,
        TaskType.DATABASE_DESIGN,
        TaskType.PLANNING,
    ],
    AgentRole.TEST_ARCHITECT: [
        TaskType.TEST_PLANNING,
        TaskType.TEST_AUTOMATION,
        TaskType.QUALITY_ASSURANCE,
    ],
    AgentRole.SECURITY_ARCHITECT: [
        TaskType.SECURITY_AUDIT,
        TaskType.SYSTEM_DESIGN,
        TaskType.REVIEW,
    ],

    # BMAD specialized roles - Product
    AgentRole.PRODUCT_MANAGER: [
        TaskType.PRODUCT_PLANNING,
        TaskType.USER_STORY_WRITING,
        TaskType.REQUIREMENT_ANALYSIS,
        TaskType.SPRINT_PLANNING,
    ],
    AgentRole.TECH_WRITER: [
        TaskType.DOCUMENTATION,
        TaskType.WRITING,
        TaskType.TRANSLATION,
    ],
    AgentRole.QA_ENGINEER: [
        TaskType.QUALITY_ASSURANCE,
        TaskType.TEST_AUTOMATION,
        TaskType.REVIEW,
    ],

    # BMAD specialized roles - Development
    AgentRole.UX_DESIGNER: [
        TaskType.UI_DESIGN,
        TaskType.UX_RESEARCH,
        TaskType.PROTOTYPING,
    ],
    AgentRole.BACKEND_DEVELOPER: [
        TaskType.BACKEND_DEVELOPMENT,
        TaskType.API_DESIGN,
        TaskType.DATABASE_DESIGN,
        TaskType.CODING,
        TaskType.EXECUTION,
    ],
    AgentRole.FRONTEND_DEVELOPER: [
        TaskType.FRONTEND_DEVELOPMENT,
        TaskType.UI_DESIGN,
        TaskType.CODING,
        TaskType.EXECUTION,
    ],
    AgentRole.DATA_ENGINEER: [
        TaskType.DATA_PROCESSING,
        TaskType.DATA_PIPELINE,
        TaskType.DATABASE_DESIGN,
    ],

    # BMAD specialized roles - Leadership
    AgentRole.SCRUM_MASTER: [
        TaskType.SPRINT_PLANNING,
        TaskType.RETROSPECTIVE,
        TaskType.TEAM_COORDINATION,
    ],
    AgentRole.BMAD_MASTER: [
        TaskType.PLANNING,
        TaskType.TEAM_COORDINATION,
        TaskType.REQUIREMENT_ANALYSIS,
        TaskType.QUALITY_ASSURANCE,
    ],
    AgentRole.DEVOPS_ENGINEER: [
        TaskType.DEPLOYMENT,
        TaskType.MONITORING,
        TaskType.PERFORMANCE_OPTIMIZATION,
    ],
}

# Task types to required tool capabilities
TASK_TOOL_MAPPINGS: Dict[TaskType, List[ToolCapability]] = {
    # Core tasks
    TaskType.RESEARCH: [ToolCapability.SEARCH, ToolCapability.READ],
    TaskType.ANALYSIS: [ToolCapability.COMPUTE, ToolCapability.VISUALIZE],
    TaskType.WRITING: [ToolCapability.WRITE, ToolCapability.READ],
    TaskType.CODING: [ToolCapability.COMPUTE, ToolCapability.WRITE],
    TaskType.REVIEW: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.PLANNING: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.EXECUTION: [ToolCapability.COMPUTE, ToolCapability.WRITE],
    TaskType.SYNTHESIS: [ToolCapability.READ, ToolCapability.WRITE],

    # BMAD specialized tasks
    TaskType.SYSTEM_DESIGN: [ToolCapability.READ, ToolCapability.WRITE, ToolCapability.VISUALIZE],
    TaskType.API_DESIGN: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.DATABASE_DESIGN: [ToolCapability.READ, ToolCapability.WRITE, ToolCapability.COMPUTE],
    TaskType.UI_DESIGN: [ToolCapability.VISUALIZE, ToolCapability.WRITE],
    TaskType.UX_RESEARCH: [ToolCapability.SEARCH, ToolCapability.READ, ToolCapability.VISUALIZE],
    TaskType.PROTOTYPING: [ToolCapability.WRITE, ToolCapability.VISUALIZE],
    TaskType.TEST_PLANNING: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.TEST_AUTOMATION: [ToolCapability.COMPUTE, ToolCapability.WRITE],
    TaskType.QUALITY_ASSURANCE: [ToolCapability.READ, ToolCapability.COMPUTE],
    TaskType.SECURITY_AUDIT: [ToolCapability.READ, ToolCapability.COMPUTE],
    TaskType.PERFORMANCE_TESTING: [ToolCapability.COMPUTE, ToolCapability.VISUALIZE],
    TaskType.FRONTEND_DEVELOPMENT: [ToolCapability.WRITE, ToolCapability.COMPUTE],
    TaskType.BACKEND_DEVELOPMENT: [ToolCapability.WRITE, ToolCapability.COMPUTE],
    TaskType.DATA_PROCESSING: [ToolCapability.COMPUTE, ToolCapability.READ, ToolCapability.WRITE],
    TaskType.DATA_PIPELINE: [ToolCapability.COMPUTE, ToolCapability.WRITE],
    TaskType.SPRINT_PLANNING: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.RETROSPECTIVE: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.TEAM_COORDINATION: [ToolCapability.COMMUNICATE, ToolCapability.WRITE],
    TaskType.DEPLOYMENT: [ToolCapability.COMPUTE, ToolCapability.WRITE],
    TaskType.MONITORING: [ToolCapability.COMPUTE, ToolCapability.VISUALIZE],
    TaskType.DOCUMENTATION: [ToolCapability.WRITE, ToolCapability.READ],
    TaskType.PRODUCT_PLANNING: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.USER_STORY_WRITING: [ToolCapability.WRITE],
    TaskType.REQUIREMENT_ANALYSIS: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.GENERAL: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.SUMMARIZATION: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.TRANSLATION: [ToolCapability.READ, ToolCapability.WRITE],
    TaskType.PERFORMANCE_OPTIMIZATION: [ToolCapability.COMPUTE, ToolCapability.READ, ToolCapability.WRITE],
}

# Tool capabilities (basic set - can be extended)
TOOL_CAPABILITIES: Dict[str, List[ToolCapability]] = {
    "web_search": [ToolCapability.SEARCH],
    "file_read": [ToolCapability.READ],
    "file_write": [ToolCapability.WRITE],
    "code_interpreter": [ToolCapability.COMPUTE, ToolCapability.WRITE],
    "scrape_website": [ToolCapability.SEARCH, ToolCapability.READ],
    "calculator": [ToolCapability.COMPUTE],
    "data_visualizer": [ToolCapability.VISUALIZE],
}


# =============================================================================
# Ontology Manager
# =============================================================================

class OntologyManager:
    """
    Ontology Manager

    Manages semantic relationships between agents, tasks, and tools.
    Provides role inference, task type detection, and tool recommendations.
    """

    def __init__(self, tool_capabilities: Dict[str, List[ToolCapability]] = None):
        """
        Initialize the ontology manager.

        Args:
            tool_capabilities: Optional custom tool capabilities mapping.
                              If None, uses default TOOL_CAPABILITIES.
        """
        self.role_task_map = ROLE_TASK_MAPPINGS
        self.task_tool_map = TASK_TOOL_MAPPINGS
        self.tool_capabilities = tool_capabilities or dict(TOOL_CAPABILITIES)

    def get_suitable_roles(self, task_type: TaskType) -> List[AgentRole]:
        """Get roles suitable for a given task type."""
        suitable_roles = []
        for role, tasks in self.role_task_map.items():
            if task_type in tasks:
                suitable_roles.append(role)
        return suitable_roles

    def get_suitable_tasks(self, role: AgentRole) -> List[TaskType]:
        """Get task types suitable for a given role."""
        return self.role_task_map.get(role, [])

    def get_required_capabilities(self, task_type: TaskType) -> List[ToolCapability]:
        """Get capabilities required for a given task type."""
        return self.task_tool_map.get(task_type, [])

    def get_suitable_tools(self, task_type: TaskType) -> List[str]:
        """Get tools suitable for a given task type."""
        required_caps = set(self.get_required_capabilities(task_type))
        suitable_tools = []

        for tool, caps in self.tool_capabilities.items():
            if required_caps & set(caps):  # Intersection
                suitable_tools.append(tool)

        return suitable_tools

    def recommend_agent_tools(
        self,
        role: AgentRole,
        assigned_tasks: List[TaskType],
    ) -> List[str]:
        """
        Recommend tools for an agent based on role and assigned tasks.

        Args:
            role: Agent role
            assigned_tasks: List of assigned task types

        Returns:
            List of recommended tool IDs
        """
        all_tools: Set[str] = set()

        for task_type in assigned_tasks:
            tools = self.get_suitable_tools(task_type)
            all_tools.update(tools)

        return list(all_tools)

    def infer_role_from_description(self, description: str) -> AgentRole:
        """
        Infer agent role from description text.

        Args:
            description: Role/task description

        Returns:
            Inferred agent role
        """
        description_lower = description.lower()

        # Priority 1: Exact role name match
        for role in AgentRole:
            role_variants = [
                role.value,
                role.value.replace("_", " "),
                role.value.replace("_", "-"),
            ]
            for variant in role_variants:
                if f" {variant} " in f" {description_lower} " or description_lower.startswith(f"{variant} "):
                    return role

        # Priority 2: Keyword matching
        role_keywords = {
            AgentRole.RESEARCHER: ["research", "investigate", "find", "search", "discover"],
            AgentRole.ANALYST: ["analyze", "analyse", "examine", "study", "evaluate"],
            AgentRole.WRITER: ["write", "create", "compose", "draft", "document"],
            AgentRole.REVIEWER: ["review", "check", "verify", "validate", "audit"],
            AgentRole.CODER: ["code", "program", "develop", "implement", "build"],
            AgentRole.MANAGER: ["manage", "coordinate", "oversee", "lead", "supervise"],
            AgentRole.PLANNER: ["plan", "schedule", "organize", "strategize", "design"],
            AgentRole.EXECUTOR: ["execute", "run", "perform", "accomplish", "complete"],
            AgentRole.FRONTEND_DEVELOPER: ["frontend", "ui", "react", "vue", "streamlit"],
            AgentRole.BACKEND_DEVELOPER: ["backend", "api", "server", "fastapi", "endpoint"],
            AgentRole.DATA_ENGINEER: ["data engineer", "etl", "data pipeline", "storage"],
            AgentRole.UX_DESIGNER: ["ux", "user experience", "interface design", "wireframe"],
            AgentRole.ARCHITECT: ["architect", "architecture", "system design"],
            AgentRole.QA_ENGINEER: ["qa", "quality assurance", "tester", "testing"],
            AgentRole.DEVOPS_ENGINEER: ["devops", "deployment", "ci/cd", "kubernetes"],
        }

        scores: Dict[AgentRole, int] = {role: 0 for role in AgentRole}

        for role, keywords in role_keywords.items():
            for keyword in keywords:
                if keyword in description_lower:
                    scores[role] += 1

        best_role = max(scores, key=scores.get)

        if scores[best_role] == 0:
            return AgentRole.EXECUTOR

        return best_role

    def infer_task_type_from_description(self, description: str) -> TaskType:
        """
        Infer task type from description text.

        Args:
            description: Task description

        Returns:
            Inferred task type
        """
        description_lower = description.lower()

        # Priority 1: Specialized task types
        priority_keywords = {
            TaskType.BACKEND_DEVELOPMENT: ["backend development", "backend api", "server development"],
            TaskType.FRONTEND_DEVELOPMENT: ["frontend development", "ui development", "streamlit"],
            TaskType.DATA_PIPELINE: ["data pipeline", "etl pipeline"],
            TaskType.UI_DESIGN: ["ui design", "interface design", "ux design"],
            TaskType.API_DESIGN: ["api design", "endpoint design", "rest api"],
            TaskType.DATABASE_DESIGN: ["database design", "schema design", "data model"],
            TaskType.SYSTEM_DESIGN: ["system design", "architecture design"],
            TaskType.TEST_AUTOMATION: ["test automation", "automated testing"],
        }

        for task_type, keywords in priority_keywords.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return task_type

        # Priority 2: General task types
        general_keywords = {
            TaskType.RESEARCH: ["research", "find", "search", "gather", "explore"],
            TaskType.ANALYSIS: ["analyze", "analyse", "examine", "evaluate"],
            TaskType.WRITING: ["write", "create", "compose", "document"],
            TaskType.CODING: ["code", "program", "implement", "develop"],
            TaskType.REVIEW: ["review", "check", "verify", "validate"],
            TaskType.PLANNING: ["plan", "schedule", "organize", "strategize"],
            TaskType.EXECUTION: ["execute", "run", "perform", "accomplish"],
            TaskType.SYNTHESIS: ["synthesize", "combine", "integrate", "summarize"],
            TaskType.DATA_PROCESSING: ["data processing", "data storage", "store data"],
            TaskType.DEPLOYMENT: ["deployment", "deploy", "release"],
            TaskType.DOCUMENTATION: ["documentation", "write docs"],
        }

        scores: Dict[TaskType, int] = {tt: 0 for tt in general_keywords.keys()}
        for task_type, keywords in general_keywords.items():
            for keyword in keywords:
                if keyword in description_lower:
                    scores[task_type] += 1

        best_task = max(scores, key=scores.get) if scores else None
        if best_task and scores[best_task] > 0:
            return best_task

        return TaskType.EXECUTION

    def validate_assignment(
        self,
        role: AgentRole,
        task_type: TaskType,
    ) -> bool:
        """
        Validate if a role is suitable for a task type.

        Args:
            role: Agent role
            task_type: Task type

        Returns:
            True if assignment is valid
        """
        suitable_tasks = self.get_suitable_tasks(role)
        return task_type in suitable_tasks

    def register_tool(self, tool_id: str, capabilities: List[ToolCapability]):
        """
        Register a new tool with its capabilities.

        Args:
            tool_id: Tool identifier
            capabilities: List of tool capabilities
        """
        self.tool_capabilities[tool_id] = capabilities
