"""
BMAD Data Models

분석 및 매핑에 사용되는 공통 데이터 모델입니다.
"""

from typing import List
from pydantic import BaseModel, Field

from caas_framework.knowledge.ontology import AgentRole, TaskType


class AgentMapping(BaseModel):
    """에이전트 매핑 정보"""
    id: str
    role: str
    role_type: AgentRole
    goal: str
    backstory: str
    assigned_tasks: List[str] = Field(default_factory=list)
    recommended_tools: List[str] = Field(default_factory=list)
    priority: int = Field(default=3, ge=1, le=5)


class TaskMapping(BaseModel):
    """태스크 매핑 정보"""
    id: str
    name: str
    description: str
    task_type: TaskType
    assigned_agent_id: str
    dependencies: List[str] = Field(default_factory=list)
    expected_output: str = ""
    required_tools: List[str] = Field(default_factory=list)


class MappingResult(BaseModel):
    """매핑 결과"""
    agents: List[AgentMapping]
    tasks: List[TaskMapping]
    workflow_type: str = "sequential"
    tool_requirements: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)
