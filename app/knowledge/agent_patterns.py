"""
Agent Patterns

Domain Type별 실행 Agent 패턴 정의
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from app.models.domain_types import DomainType, ExecutionPattern


class AgentPattern:
    """Agent 패턴 정의"""

    def __init__(
        self,
        execution_agents: List[Dict[str, str]],
        avoid_agents: List[str],
        execution_pattern: ExecutionPattern,
        description: str
    ):
        self.execution_agents = execution_agents
        self.avoid_agents = avoid_agents
        self.execution_pattern = execution_pattern
        self.description = description


# Agent patterns cache
_AGENT_PATTERNS_CACHE: Optional[Dict[DomainType, AgentPattern]] = None


def load_agent_patterns() -> Dict[DomainType, AgentPattern]:
    """
    Agent patterns를 JSON 파일에서 로드합니다.

    Returns:
        Dict[DomainType, AgentPattern]: Domain type별 agent 패턴 매핑
    """
    global _AGENT_PATTERNS_CACHE

    if _AGENT_PATTERNS_CACHE is not None:
        return _AGENT_PATTERNS_CACHE

    try:
        # Try to load from data/ontology/agent_patterns.json
        from app.utils.config import PROJECT_ROOT
        patterns_path = PROJECT_ROOT / "data" / "ontology" / "agent_patterns.json"

        if patterns_path.exists():
            with open(patterns_path, "r", encoding="utf-8") as f:
                patterns_data = json.load(f)

            # Convert to AgentPattern objects
            patterns_map = {}
            for domain_str, pattern_dict in patterns_data.items():
                try:
                    domain_type = DomainType(domain_str)
                    execution_pattern = ExecutionPattern(pattern_dict["execution_pattern"])

                    pattern = AgentPattern(
                        execution_agents=pattern_dict["execution_agents"],
                        avoid_agents=pattern_dict["avoid_agents"],
                        execution_pattern=execution_pattern,
                        description=pattern_dict["description"]
                    )
                    patterns_map[domain_type] = pattern
                except (ValueError, KeyError) as e:
                    # Skip invalid patterns
                    print(f"Warning: Failed to load pattern for {domain_str}: {e}")
                    continue

            _AGENT_PATTERNS_CACHE = patterns_map
            return patterns_map
        else:
            # Fallback to empty dict if file not found
            print(f"Warning: Agent patterns file not found at {patterns_path}")
            _AGENT_PATTERNS_CACHE = {}
            return {}

    except Exception as e:
        # Fallback on error
        print(f"Warning: Failed to load agent patterns: {e}")
        _AGENT_PATTERNS_CACHE = {}
        return {}


# Build Agents (CAAS 개발 단계에서만 사용)
BUILD_AGENTS = [
    "frontend_developer",
    "backend_developer",
    "data_engineer",
    "architect",
    "devops_engineer",
    "qa_engineer",
    "ux_designer",
    "database_designer",
]


def get_agent_pattern(domain_type: DomainType) -> AgentPattern:
    """
    Domain Type에 맞는 Agent 패턴 반환

    Args:
        domain_type: Domain Type

    Returns:
        AgentPattern: Agent 패턴
    """
    patterns_map = load_agent_patterns()
    return patterns_map.get(
        domain_type,
        AgentPattern(
            execution_agents=[],
            avoid_agents=BUILD_AGENTS,
            execution_pattern=ExecutionPattern.CRUD_APPLICATION,
            description="Custom domain pattern"
        )
    )


def is_build_agent(role: str) -> bool:
    """
    빌드 Agent 여부 확인 (CAAS 개발 단계에서만 사용)

    Args:
        role: Agent role

    Returns:
        bool: 빌드 Agent 여부
    """
    return role.lower() in [agent.lower() for agent in BUILD_AGENTS]


def is_execution_agent(role: str, domain_type: DomainType) -> bool:
    """
    실행 Agent 여부 확인 (생성된 시스템에서 사용)

    Args:
        role: Agent role
        domain_type: Domain Type

    Returns:
        bool: 실행 Agent 여부
    """
    pattern = get_agent_pattern(domain_type)
    execution_roles = [agent["role"].lower() for agent in pattern.execution_agents]
    return role.lower() in execution_roles
