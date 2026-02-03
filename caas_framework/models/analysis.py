"""
Analysis Models

Models for requirement analysis and architecture design results.
Migrated from app/models/schemas.py for framework independence.
"""

import re
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# ==================== Enums ====================


class WorkflowType(str, Enum):
    """워크플로우 타입"""

    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"
    PARALLEL = "parallel"


class ProjectTemplate(str, Enum):
    """프로젝트 템플릿 타입"""

    AGENT_ONLY = "agent_only"
    AGENT_WITH_STREAMLIT = "agent_with_streamlit"
    FULL_STACK = "full_stack"
    CHATBOT = "chatbot"


class HTTPMethod(str, Enum):
    """HTTP 메서드"""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


# ==================== LLM Configuration ====================


class LLMConfigSpec(BaseModel):
    """LLM 설정 스펙"""

    model: str = "gpt-4o"
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    api_base: Optional[str] = None
    api_key_env: Optional[str] = None


# ==================== Requirement Models ====================


class AgentRequirement(BaseModel):
    """에이전트 요구사항 모델 (분석 단계)"""

    role: str
    goal: str
    skills: List[str]
    priority: int = Field(ge=1, le=5, default=3)


class TaskRequirement(BaseModel):
    """태스크 요구사항 모델 (분석 단계)"""

    name: str
    description: str
    assigned_agent: str
    dependencies: List[str] = []
    output_type: str = "text"


# ==================== UI Models ====================


class UIComponentRequirement(BaseModel):
    """UI 컴포넌트 요구사항"""

    component_type: str  # text_input, button, table, chart, etc.
    label: str
    description: Optional[str] = None


class UIPageRequirement(BaseModel):
    """UI 페이지 요구사항"""

    name: str
    title: str
    description: Optional[str] = None
    components: List[UIComponentRequirement] = []


# ==================== Backend API Models ====================


class BackendAPIRequirement(BaseModel):
    """Backend API 요구사항"""

    path: str
    method: HTTPMethod = HTTPMethod.GET
    description: str
    request_params: List[str] = []
    response_fields: List[str] = []

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """API 경로 검증"""
        if not v.startswith("/"):
            raise ValueError(f"API 경로는 '/'로 시작해야 합니다: {v}")
        if len(v) > 200:
            raise ValueError(f"API 경로가 너무 깁니다 (최대 200자): {len(v)}")
        return v


# ==================== Quality Metrics ====================


class QualityMetrics(BaseModel):
    """
    요구사항 분석 품질 메트릭

    분석 결과의 품질을 다양한 측면에서 평가
    """

    completeness_score: float = Field(
        default=0.7, ge=0.0, le=1.0, description="요구사항 완전성 (모든 필요 정보 포함)"
    )
    clarity_score: float = Field(
        default=0.7, ge=0.0, le=1.0, description="요구사항 명확성 (모호함 없음)"
    )
    consistency_score: float = Field(
        default=0.7, ge=0.0, le=1.0, description="요구사항 일관성 (상충 없음)"
    )
    feasibility_score: float = Field(
        default=0.7, ge=0.0, le=1.0, description="실현 가능성 (구현 가능)"
    )
    complexity_score: int = Field(
        default=5, ge=1, le=10, description="복잡도 (1=매우 단순, 10=매우 복잡)"
    )
    confidence_score: float = Field(
        default=0.7, ge=0.0, le=1.0, description="분석 신뢰도 (분석 품질)"
    )

    # 전체 품질 점수 (자동 계산)
    overall_quality: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="전체 품질 점수"
    )

    # 품질 이슈 및 개선 제안
    quality_issues: List[str] = Field(default=[], description="발견된 품질 이슈")
    improvement_suggestions: List[str] = Field(default=[], description="품질 개선 제안")

    model_config = {"extra": "forbid"}  # OpenAI Function Calling 호환성

    def calculate_overall_quality(self) -> float:
        """전체 품질 점수 계산 (가중 평균)"""
        # 복잡도는 반비례 (복잡할수록 점수 낮음)
        normalized_complexity = 1.0 - (self.complexity_score - 1) / 9.0

        weights = {
            "completeness": 0.25,
            "clarity": 0.20,
            "consistency": 0.15,
            "feasibility": 0.20,
            "complexity": 0.10,
            "confidence": 0.10,
        }

        overall = (
            self.completeness_score * weights["completeness"]
            + self.clarity_score * weights["clarity"]
            + self.consistency_score * weights["consistency"]
            + self.feasibility_score * weights["feasibility"]
            + normalized_complexity * weights["complexity"]
            + self.confidence_score * weights["confidence"]
        )

        return round(overall, 3)


# ==================== Requirement Analysis ====================


class RequirementAnalysis(BaseModel):
    """
    요구사항 분석 결과 모델 (통합 버전)

    자연어 요구사항 분석 결과를 표현
    """

    domain: str
    subdomain: Optional[str] = None
    summary: str
    agents: List[AgentRequirement]
    tasks: List[TaskRequirement]
    workflow_type: WorkflowType = WorkflowType.SEQUENTIAL
    suggested_tools: List[str] = []
    constraints: List[str] = []
    success_criteria: List[str] = []

    # Multi-Artifact 지원
    project_template: ProjectTemplate = ProjectTemplate.AGENT_ONLY
    requires_ui: bool = False
    ui_pages: List[UIPageRequirement] = []
    requires_backend: bool = False
    backend_apis: List[BackendAPIRequirement] = []
    requires_database: bool = False
    database_tables: List[str] = []

    # 분석 이유 (Reasoning)
    agents_reasoning: Optional[str] = None
    tasks_reasoning: Optional[str] = None
    tools_reasoning: Optional[str] = None
    ui_reasoning: Optional[str] = None
    backend_reasoning: Optional[str] = None

    # 품질 메트릭
    quality_metrics: Optional[QualityMetrics] = None

    def compute_quality_metrics(self) -> QualityMetrics:
        """
        요구사항 분석 결과로부터 품질 메트릭을 계산합니다.

        Returns:
            QualityMetrics: 계산된 품질 메트릭
        """
        # 1. Completeness Score: 필수 필드가 모두 채워졌는지
        completeness = 0.0
        if self.domain:
            completeness += 0.15
        if self.summary:
            completeness += 0.15
        if len(self.agents) > 0:
            completeness += 0.20
        if len(self.tasks) > 0:
            completeness += 0.20
        if len(self.suggested_tools) > 0:
            completeness += 0.10
        if len(self.constraints) > 0:
            completeness += 0.10
        if len(self.success_criteria) > 0:
            completeness += 0.10

        # 2. Clarity Score: 설명이 충분히 상세한지
        clarity = 0.0
        avg_agent_desc_length = sum(len(a.goal) for a in self.agents) / max(len(self.agents), 1)
        avg_task_desc_length = sum(len(t.description) for t in self.tasks) / max(len(self.tasks), 1)

        clarity += min(1.0, len(self.summary) / 100) * 0.3
        clarity += min(1.0, avg_agent_desc_length / 50) * 0.35
        clarity += min(1.0, avg_task_desc_length / 50) * 0.35

        # 3. Consistency Score: Agent와 Task가 일관되게 매칭되는지
        consistency = 1.0
        agent_roles = {a.role for a in self.agents}
        assigned_roles = {t.assigned_agent for t in self.tasks if t.assigned_agent}

        # 할당된 역할이 모두 정의된 agent에 있는지
        if assigned_roles:
            matching = len(assigned_roles & agent_roles) / len(assigned_roles)
            consistency = matching

        # 4. Feasibility Score: Agent와 Task 수가 적절한지
        feasibility = 1.0
        num_agents = len(self.agents)
        num_tasks = len(self.tasks)

        if num_agents == 0 or num_tasks == 0:
            feasibility = 0.3
        elif num_agents > 10 or num_tasks > 20:
            feasibility = 0.6  # 너무 복잡
        elif num_tasks < num_agents:
            feasibility = 0.7  # Task가 Agent보다 적으면 비효율적

        # 5. Complexity Score: Agent와 Task 수로 복잡도 추정
        complexity = min(10, max(1, (num_agents + num_tasks // 2)))

        # 6. Confidence Score: 전체적인 신뢰도 (다른 점수들의 평균)
        confidence = (completeness + clarity + consistency + feasibility) / 4.0

        # Quality Issues 및 Improvement Suggestions
        quality_issues = []
        improvement_suggestions = []

        if completeness < 0.7:
            quality_issues.append("요구사항 정보가 불완전합니다.")
            improvement_suggestions.append(
                "도메인, 에이전트, 태스크, 제약사항 등을 더 상세히 작성하세요."
            )

        if clarity < 0.6:
            quality_issues.append("요구사항 설명이 불명확합니다.")
            improvement_suggestions.append(
                "각 에이전트와 태스크의 목적과 설명을 더 구체적으로 작성하세요."
            )

        if consistency < 0.8:
            quality_issues.append("Agent와 Task 할당이 일관되지 않습니다.")
            improvement_suggestions.append("모든 Task가 정의된 Agent에 할당되었는지 확인하세요.")

        if feasibility < 0.7:
            quality_issues.append("프로젝트 범위가 비현실적입니다.")
            improvement_suggestions.append(
                "Agent와 Task 수를 적절하게 조정하세요 (권장: Agent 2-5개, Task 3-15개)."
            )

        metrics = QualityMetrics(
            completeness_score=round(completeness, 3),
            clarity_score=round(clarity, 3),
            consistency_score=round(consistency, 3),
            feasibility_score=round(feasibility, 3),
            complexity_score=complexity,
            confidence_score=round(confidence, 3),
            quality_issues=quality_issues,
            improvement_suggestions=improvement_suggestions,
        )

        # Overall quality 계산
        metrics.overall_quality = metrics.calculate_overall_quality()

        return metrics


# ==================== Architecture Design Models ====================


class ArchitecturalPattern(str, Enum):
    """아키텍처 패턴"""

    LAYERED = "layered"
    MICROSERVICES = "microservices"
    EVENT_DRIVEN = "event_driven"
    PIPELINE = "pipeline"
    PLUGIN = "plugin"
    MONOLITHIC = "monolithic"


class ComponentType(str, Enum):
    """컴포넌트 타입"""

    AGENT = "agent"
    SERVICE = "service"
    DATABASE = "database"
    QUEUE = "queue"
    API = "api"
    UI = "ui"
    UTILITY = "utility"


class ComponentSpec(BaseModel):
    """컴포넌트 사양"""

    id: str
    name: str
    type: ComponentType
    description: str
    responsibilities: List[str]
    interfaces: List[str] = []  # 제공하는 인터페이스
    dependencies: List[str] = []  # 의존하는 컴포넌트 ID
    technologies: List[str] = []  # 사용하는 기술

    model_config = {"extra": "forbid"}  # OpenAI Function Calling 호환성

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """ID 검증 (snake_case)"""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(f"ID는 snake_case여야 합니다: {v}")
        return v


class DataFlow(BaseModel):
    """데이터 흐름"""

    from_component: str
    to_component: str
    data_type: str
    description: str
    is_async: bool = False

    model_config = {"extra": "forbid"}  # OpenAI Function Calling 호환성


class TechnologyStack(BaseModel):
    """기술 스택"""

    category: str  # framework, library, tool, infrastructure
    name: str
    version: Optional[str] = None
    purpose: str  # 사용 목적

    model_config = {"extra": "forbid"}  # OpenAI Function Calling 호환성


class ArchitectureDesign(BaseModel):
    """
    시스템 아키텍처 설계 결과

    System Architect Agent의 출력 모델
    RequirementAnalysis를 기반으로 시스템 아키텍처를 설계
    """

    # 기본 정보
    project_name: str
    description: str

    # 아키텍처 패턴 및 스타일
    architectural_pattern: ArchitecturalPattern
    pattern_justification: str  # 왜 이 패턴을 선택했는지

    # 컴포넌트 분해
    components: List[ComponentSpec]
    data_flows: List[DataFlow] = []

    # 기술 스택
    technology_stack: List[TechnologyStack] = []

    # 비기능 요구사항 (NFR) 대응
    scalability_strategy: Optional[str] = None
    reliability_strategy: Optional[str] = None
    security_strategy: Optional[str] = None
    performance_strategy: Optional[str] = None

    # 구현 계획
    implementation_phases: List[str] = []  # 구현 단계
    critical_paths: List[str] = []  # 핵심 경로
    risk_areas: List[str] = []  # 위험 영역

    # 품질 속성
    quality_attributes: Optional[Dict[str, str]] = None  # 품질 속성과 달성 방법

    # 트레이드오프 및 결정 사항
    architectural_decisions: List[str] = []  # ADR (Architecture Decision Records)
    tradeoffs: List[str] = []  # 트레이드오프 분석

    # 메타데이터
    design_confidence: float = Field(default=0.7, ge=0.0, le=1.0)  # 설계 신뢰도
    complexity_estimate: int = Field(default=5, ge=1, le=10)  # 복잡도 추정
