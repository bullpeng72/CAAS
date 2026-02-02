"""
Ontology Metadata Provider

Provides rich metadata for roles, tasks, and tools beyond basic enum definitions.
"""

from typing import Any, Dict, List

from caas_framework.knowledge.ontology.manager import AgentRole, TaskType

# =============================================================================
# Role Metadata
# =============================================================================

ROLE_METADATA: Dict[AgentRole, Dict[str, Any]] = {
    AgentRole.RESEARCHER: {
        "description": "정보 수집 및 리서치 수행. 웹 검색, 문서 분석, 데이터 수집 전문",
        "category": "Analysis",
        "recommended_tools": ["web_search", "file_read", "api_call"],
        "typical_duration_mins": 45,
        "complexity": "Medium",
        "success_rate": 0.92,
    },
    AgentRole.ANALYST: {
        "description": "데이터 분석 및 인사이트 도출. 통계 분석, 데이터 시각화 전문",
        "category": "Analysis",
        "recommended_tools": ["csv_search", "database_query", "code_interpreter"],
        "typical_duration_mins": 60,
        "complexity": "High",
        "success_rate": 0.89,
    },
    AgentRole.WRITER: {
        "description": "문서 및 콘텐츠 작성. 보고서, 문서화, 기술 문서 작성 전문",
        "category": "Content",
        "recommended_tools": ["file_write", "docx_search", "file_read"],
        "typical_duration_mins": 50,
        "complexity": "Medium",
        "success_rate": 0.90,
    },
    AgentRole.CODER: {
        "description": "코드 작성 및 개발. 프로그래밍, 코드 생성, 리팩토링 전문",
        "category": "Development",
        "recommended_tools": ["code_interpreter", "file_write", "github_search"],
        "typical_duration_mins": 90,
        "complexity": "High",
        "success_rate": 0.85,
    },
    AgentRole.REVIEWER: {
        "description": "검토 및 품질 보증. 코드 리뷰, 문서 검토, QA 전문",
        "category": "Quality",
        "recommended_tools": ["code_interpreter", "file_read"],
        "typical_duration_mins": 30,
        "complexity": "Medium",
        "success_rate": 0.88,
    },
    AgentRole.PLANNER: {
        "description": "프로젝트 계획 및 전략 수립. 아키텍처 설계, 작업 분해 전문",
        "category": "Management",
        "recommended_tools": ["file_write", "file_read"],
        "typical_duration_mins": 45,
        "complexity": "Medium",
        "success_rate": 0.91,
    },
    AgentRole.MANAGER: {
        "description": "팀 조정 및 프로세스 관리. 작업 분배, 일정 관리 전문",
        "category": "Management",
        "recommended_tools": ["file_read", "file_write"],
        "typical_duration_mins": 30,
        "complexity": "Low",
        "success_rate": 0.93,
    },
}


# =============================================================================
# Task Metadata
# =============================================================================

TASK_METADATA: Dict[TaskType, Dict[str, Any]] = {
    TaskType.RESEARCH: {
        "description": "정보 수집 및 조사. 웹 검색, 문헌 조사, 데이터 수집",
        "category": "Information",
        "compatible_roles": ["Researcher", "Data Analyst", "Business Analyst"],
        "required_capabilities": ["information_gathering", "analysis"],
        "avg_duration_mins": 45,
        "complexity": "Medium",
    },
    TaskType.ANALYSIS: {
        "description": "데이터 분석 및 패턴 발견. 통계 분석, 트렌드 분석",
        "category": "Analytics",
        "compatible_roles": ["Data Analyst", "Researcher", "Financial Analyst"],
        "required_capabilities": ["statistics", "data_processing", "visualization"],
        "avg_duration_mins": 60,
        "complexity": "High",
    },
    TaskType.WRITING: {
        "description": "문서 및 콘텐츠 작성. 보고서, 기술 문서, 블로그 포스트",
        "category": "Content",
        "compatible_roles": ["Writer", "Technical Writer", "Content Creator"],
        "required_capabilities": ["writing", "language", "formatting"],
        "avg_duration_mins": 50,
        "complexity": "Medium",
    },
    TaskType.CODING: {
        "description": "소프트웨어 개발 및 코드 작성. 프로그래밍, 디버깅, 리팩토링",
        "category": "Development",
        "compatible_roles": ["Developer", "Software Engineer", "Backend Developer"],
        "required_capabilities": ["programming", "problem_solving", "debugging"],
        "avg_duration_mins": 90,
        "complexity": "High",
    },
    TaskType.REVIEW: {
        "description": "코드 또는 문서 검토. 품질 검사, 베스트 프랙티스 확인",
        "category": "Quality",
        "compatible_roles": ["Reviewer", "QA Engineer", "Tech Lead"],
        "required_capabilities": ["code_review", "quality_assurance"],
        "avg_duration_mins": 30,
        "complexity": "Medium",
    },
    TaskType.TEST_PLANNING: {
        "description": "테스트 계획 수립. 테스트 전략, 테스트 케이스 설계",
        "category": "Quality",
        "compatible_roles": ["Reviewer", "QA Engineer", "Planner"],
        "required_capabilities": ["testing", "planning"],
        "avg_duration_mins": 45,
        "complexity": "Medium",
    },
    TaskType.TEST_AUTOMATION: {
        "description": "자동화 테스트 구현. 단위 테스트, 통합 테스트 자동화",
        "category": "Quality",
        "compatible_roles": ["Coder", "QA Engineer"],
        "required_capabilities": ["testing", "test_automation", "coding"],
        "avg_duration_mins": 75,
        "complexity": "High",
    },
    TaskType.QUALITY_ASSURANCE: {
        "description": "품질 보증. 코드 리뷰, 품질 검사, QA 프로세스",
        "category": "Quality",
        "compatible_roles": ["Reviewer", "QA Engineer"],
        "required_capabilities": ["quality_assurance", "review"],
        "avg_duration_mins": 40,
        "complexity": "Medium",
    },
    TaskType.PLANNING: {
        "description": "프로젝트 계획 수립. 작업 분해, 일정 수립, 리소스 할당",
        "category": "Management",
        "compatible_roles": ["Planner", "Project Manager", "Architect"],
        "required_capabilities": ["planning", "organization"],
        "avg_duration_mins": 45,
        "complexity": "Medium",
    },
}


# =============================================================================
# Helper Functions
# =============================================================================


def get_role_metadata(role: AgentRole) -> Dict[str, Any]:
    """
    Get enriched metadata for a role

    Args:
        role: AgentRole enum

    Returns:
        Dictionary with role metadata
    """
    metadata = ROLE_METADATA.get(role, {})

    return {
        "id": role.value,
        "name": role.value.replace("_", " ").title(),
        "description": metadata.get("description", f"Role for {role.value}"),
        "category": metadata.get("category", "General"),
        "recommended_tools": metadata.get("recommended_tools", []),
        "typical_duration_mins": metadata.get("typical_duration_mins", 45),
        "complexity": metadata.get("complexity", "Medium"),
        "success_rate": metadata.get("success_rate", 0.85),
    }


def get_task_metadata(task: TaskType) -> Dict[str, Any]:
    """
    Get enriched metadata for a task

    Args:
        task: TaskType enum

    Returns:
        Dictionary with task metadata
    """
    metadata = TASK_METADATA.get(task, {})

    return {
        "id": task.value,
        "name": task.value.replace("_", " ").title(),
        "description": metadata.get("description", f"Task type: {task.value}"),
        "category": metadata.get("category", "General"),
        "compatible_roles": metadata.get("compatible_roles", []),
        "required_capabilities": metadata.get("required_capabilities", []),
        "avg_duration": metadata.get("avg_duration_mins", 45),
        "complexity": metadata.get("complexity", "Medium"),
    }


def get_all_roles_with_metadata() -> List[Dict[str, Any]]:
    """Get all roles with enriched metadata"""
    from caas_framework.knowledge.ontology.manager import ROLE_TASK_MAPPINGS, AgentRole

    roles = []
    for role_enum in AgentRole:
        metadata = get_role_metadata(role_enum)

        # Add compatible tasks
        compatible_tasks = ROLE_TASK_MAPPINGS.get(role_enum, [])
        metadata["compatible_tasks"] = [t.value for t in compatible_tasks]

        roles.append(metadata)

    return roles


def get_all_tasks_with_metadata() -> List[Dict[str, Any]]:
    """Get all tasks with enriched metadata"""
    from caas_framework.knowledge.ontology.manager import TASK_TOOL_MAPPINGS, TaskType

    tasks = []
    for task_enum in TaskType:
        metadata = get_task_metadata(task_enum)

        # Add required tools
        required_tools = TASK_TOOL_MAPPINGS.get(task_enum, [])
        metadata["required_tools"] = required_tools

        tasks.append(metadata)

    return tasks
