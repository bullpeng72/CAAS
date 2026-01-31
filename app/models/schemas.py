"""
CAAS Common Schemas

프로젝트 전반에서 사용되는 공통 데이터 모델
"""

import re
from typing import Any, Dict, List, Optional
from enum import Enum
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


# ==================== Agent Models ====================

class AgentSpecModel(BaseModel):
    """
    에이전트 스펙 모델 (통합 버전)

    SDD, 코드 생성, 요구사항 분석 등 전반에서 사용
    """
    id: str
    role: str
    goal: str
    backstory: str
    tools: List[str] = []
    llm: Optional[LLMConfigSpec] = None
    verbose: bool = True
    memory: bool = True
    allow_delegation: bool = False
    max_iter: int = 15
    max_rpm: Optional[int] = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """ID 검증 (snake_case, 최대 64자)"""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(f"ID는 snake_case여야 합니다: {v}")
        if len(v) > 64:
            raise ValueError(f"ID가 너무 깁니다 (최대 64자): {len(v)}")
        return v

    @field_validator("role", "goal", "backstory")
    @classmethod
    def validate_text_fields(cls, v: str) -> str:
        """텍스트 필드 길이 검증"""
        if len(v) > 10_000:
            raise ValueError(f"텍스트가 너무 깁니다 (최대 10,000자): {len(v)}")
        return v

    @field_validator("tools")
    @classmethod
    def validate_tools(cls, v: List[str]) -> List[str]:
        """도구 목록 검증"""
        if len(v) > 50:
            raise ValueError(f"도구가 너무 많습니다 (최대 50개): {len(v)}")

        for tool in v:
            if not re.match(r"^[a-z][a-z0-9_]*$", tool):
                raise ValueError(f"도구 이름이 유효하지 않습니다: {tool}")

        return v


class AgentRequirement(BaseModel):
    """에이전트 요구사항 모델 (분석 단계)"""
    role: str
    goal: str
    skills: List[str]
    priority: int = Field(ge=1, le=5, default=3)


# ==================== Task Models ====================

class TaskSpecModel(BaseModel):
    """
    태스크 스펙 모델 (통합 버전)

    SDD, 코드 생성, 요구사항 분석 등 전반에서 사용
    """
    id: str
    description: str
    expected_output: str
    agent: str
    context: List[str] = []
    async_execution: bool = False
    output_file: Optional[str] = None
    human_input: bool = False

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """ID 검증 (snake_case, 최대 64자)"""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(f"ID는 snake_case여야 합니다: {v}")
        if len(v) > 64:
            raise ValueError(f"ID가 너무 깁니다 (최대 64자): {len(v)}")
        return v

    @field_validator("description", "expected_output")
    @classmethod
    def validate_text_fields(cls, v: str) -> str:
        """텍스트 필드 길이 검증"""
        if len(v) > 10_000:
            raise ValueError(f"텍스트가 너무 깁니다 (최대 10,000자): {len(v)}")
        return v

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: List[str]) -> List[str]:
        """컨텍스트 태스크 검증"""
        if len(v) > 20:
            raise ValueError(f"컨텍스트 태스크가 너무 많습니다 (최대 20개): {len(v)}")

        for task_id in v:
            if not re.match(r"^[a-z][a-z0-9_]*$", task_id):
                raise ValueError(f"태스크 ID가 유효하지 않습니다: {task_id}")

        return v


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


# ==================== Requirement Analysis ====================

class QualityMetrics(BaseModel):
    """
    요구사항 분석 품질 메트릭

    분석 결과의 품질을 다양한 측면에서 평가
    """
    completeness_score: float = Field(default=0.7, ge=0.0, le=1.0, description="요구사항 완전성 (모든 필요 정보 포함)")
    clarity_score: float = Field(default=0.7, ge=0.0, le=1.0, description="요구사항 명확성 (모호함 없음)")
    consistency_score: float = Field(default=0.7, ge=0.0, le=1.0, description="요구사항 일관성 (상충 없음)")
    feasibility_score: float = Field(default=0.7, ge=0.0, le=1.0, description="실현 가능성 (구현 가능)")
    complexity_score: int = Field(default=5, ge=1, le=10, description="복잡도 (1=매우 단순, 10=매우 복잡)")
    confidence_score: float = Field(default=0.7, ge=0.0, le=1.0, description="분석 신뢰도 (분석 품질)")

    # 전체 품질 점수 (자동 계산)
    overall_quality: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="전체 품질 점수")

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
            "confidence": 0.10
        }

        overall = (
            self.completeness_score * weights["completeness"] +
            self.clarity_score * weights["clarity"] +
            self.consistency_score * weights["consistency"] +
            self.feasibility_score * weights["feasibility"] +
            normalized_complexity * weights["complexity"] +
            self.confidence_score * weights["confidence"]
        )

        return round(overall, 3)


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

    # 품질 메트릭 (NEW!)
    quality_metrics: Optional[QualityMetrics] = None

    def compute_quality_metrics(self) -> QualityMetrics:
        """
        요구사항 분석 결과로부터 품질 메트릭을 계산합니다.

        Returns:
            QualityMetrics: 계산된 품질 메트릭
        """
        # 1. Completeness Score: 필수 필드가 모두 채워졌는지
        completeness = 0.0
        if self.domain: completeness += 0.15
        if self.summary: completeness += 0.15
        if len(self.agents) > 0: completeness += 0.20
        if len(self.tasks) > 0: completeness += 0.20
        if len(self.suggested_tools) > 0: completeness += 0.10
        if len(self.constraints) > 0: completeness += 0.10
        if len(self.success_criteria) > 0: completeness += 0.10

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
            improvement_suggestions.append("도메인, 에이전트, 태스크, 제약사항 등을 더 상세히 작성하세요.")

        if clarity < 0.6:
            quality_issues.append("요구사항 설명이 불명확합니다.")
            improvement_suggestions.append("각 에이전트와 태스크의 목적과 설명을 더 구체적으로 작성하세요.")

        if consistency < 0.8:
            quality_issues.append("Agent와 Task 할당이 일관되지 않습니다.")
            improvement_suggestions.append("모든 Task가 정의된 Agent에 할당되었는지 확인하세요.")

        if feasibility < 0.7:
            quality_issues.append("프로젝트 범위가 비현실적입니다.")
            improvement_suggestions.append("Agent와 Task 수를 적절하게 조정하세요 (권장: Agent 2-5개, Task 3-15개).")

        metrics = QualityMetrics(
            completeness_score=round(completeness, 3),
            clarity_score=round(clarity, 3),
            consistency_score=round(consistency, 3),
            feasibility_score=round(feasibility, 3),
            complexity_score=complexity,
            confidence_score=round(confidence, 3),
            quality_issues=quality_issues,
            improvement_suggestions=improvement_suggestions
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
    architecture_summary: str

    # 아키텍처 패턴 및 스타일
    architectural_pattern: ArchitecturalPattern
    pattern_justification: str  # 왜 이 패턴을 선택했는지

    # 컴포넌트 분해
    components: List[ComponentSpec]
    data_flows: List[DataFlow] = []

    # 기술 스택
    technology_stack: List[TechnologyStack]
    tech_stack_reasoning: str  # 기술 스택 선택 이유

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
    database_reasoning: Optional[str] = None

    model_config = {"extra": "forbid"}  # OpenAI Function Calling 호환성


# ==================== Crew Spec ====================

class CrewSpec(BaseModel):
    """Crew 전체 스펙"""
    name: str
    description: str
    agents: List[AgentSpecModel]
    tasks: List[TaskSpecModel]
    workflow_type: WorkflowType = WorkflowType.SEQUENTIAL
    manager_llm: Optional[LLMConfigSpec] = None
    verbose: bool = True
    memory: bool = False
    cache: bool = True
    max_rpm: Optional[int] = None


# ==================== Validation Models ====================

class ValidationIssue(BaseModel):
    """검증 이슈"""
    severity: str  # error, warning, info
    category: str
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    """검증 결과"""
    is_valid: bool
    issues: List[ValidationIssue] = []
    warnings_count: int = 0
    errors_count: int = 0
    timestamp: Optional[str] = None


# ==================== Golden Data Validation Models ====================

class MissingItem(BaseModel):
    """Golden Data에 있지만 Output에 없는 항목"""
    item_type: str  # feature, data_model, ui_component
    item_id: str
    item_name: str
    description: str
    severity: str = "high"  # critical, high, medium, low


class ExtraItem(BaseModel):
    """Output에 있지만 Golden Data에 없는 항목 (Hallucination 가능성)"""
    item_type: str
    item_id: str
    item_name: str
    description: str
    severity: str = "medium"


class MismatchedItem(BaseModel):
    """Golden Data와 Output이 불일치하는 항목"""
    item_type: str
    item_id: str
    item_name: str
    golden_value: str
    output_value: str
    mismatch_reason: str
    severity: str = "medium"


class ComplianceStatus(str, Enum):
    """준수 상태"""
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"


class GoldenValidationReport(BaseModel):
    """
    Golden Data 검증 리포트

    각 Phase 출력을 Golden Data와 비교한 결과
    """
    phase_name: str  # discovery, architecture, design, development
    coverage_score: float = Field(ge=0.0, le=1.0)
    missing_items: List[MissingItem] = []
    extra_items: List[ExtraItem] = []
    mismatched_items: List[MismatchedItem] = []
    compliance_status: ComplianceStatus
    needs_fixing: bool = False
    recommendations: List[str] = []
    timestamp: Optional[str] = None


class ComplianceReport(BaseModel):
    """
    최종 준수 리포트

    Golden Data 기준 전체 시스템 준수 여부
    """
    overall_compliance: float = Field(ge=0.0, le=1.0)
    feature_coverage: float = Field(ge=0.0, le=1.0)
    data_model_alignment: bool
    ui_coverage: float = Field(ge=0.0, le=1.0)
    nfr_satisfaction: bool
    constraint_adherence: bool
    passed: bool
    issues: List[str] = []
    recommendations: List[str] = []
    timestamp: Optional[str] = None


# ==================== Code Generation Models ====================

class GeneratedFile(BaseModel):
    """생성된 파일"""
    path: str
    content: str
    file_type: str  # python, yaml, markdown, etc.
    description: Optional[str] = None


class GeneratedProject(BaseModel):
    """생성된 프로젝트"""
    name: str
    description: str
    files: List[GeneratedFile]
    metadata: Dict[str, Any] = {}


# ==================== Golden Data Models (Concretized Requirements) ====================

class FeatureSpec(BaseModel):
    """
    구체화된 기능 명세

    Golden Data의 핵심 구성요소로, 각 기능을 명확하게 정의
    """
    id: str  # F1, F2, F3...
    name: str
    description: str
    priority: str = Field(default="medium")  # high, medium, low
    acceptance_criteria: List[str] = []
    functional_requirements: List[str] = []  # 기능적 요구사항
    user_stories: List[str] = []  # 사용자 스토리
    related_features: List[str] = []  # 관련 기능 ID
    estimated_complexity: int = Field(default=5, ge=1, le=10)

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Feature ID 검증 (F1, F2, ... 형식)"""
        if not re.match(r"^F\d+$", v):
            raise ValueError(f"Feature ID는 'F숫자' 형식이어야 합니다: {v}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """우선순위 검증"""
        if v not in ["high", "medium", "low", "critical"]:
            raise ValueError(f"우선순위는 high/medium/low/critical 중 하나여야 합니다: {v}")
        return v


class DataAttribute(BaseModel):
    """데이터 속성 정의"""
    name: str
    type: str  # string, int, float, boolean, datetime, UUID, etc.
    required: str  # "true" or "false" as string to match prompt examples
    description: Optional[str] = None


class DataRelationship(BaseModel):
    """데이터 관계 정의"""
    type: str  # one-to-one, one-to-many, many-to-one, many-to-many
    target: str  # 대상 엔티티 이름
    description: Optional[str] = None


class DataModelSpec(BaseModel):
    """
    데이터 모델 명세

    시스템에서 다루는 핵심 엔티티 정의
    """
    entity_name: str  # User, Product, Order 등
    description: str
    attributes: List[DataAttribute] = []
    relationships: List[DataRelationship] = []
    constraints: List[str] = []  # 제약사항 (unique, nullable, etc.)
    indexes: List[str] = []  # 인덱스가 필요한 필드

    @field_validator("entity_name")
    @classmethod
    def validate_entity_name(cls, v: str) -> str:
        """엔티티 이름 검증 (PascalCase)"""
        if not re.match(r"^[A-Z][a-zA-Z0-9]*$", v):
            raise ValueError(f"엔티티 이름은 PascalCase여야 합니다: {v}")
        return v


class UIComponentSpec(BaseModel):
    """
    UI 컴포넌트 명세

    사용자 인터페이스 요소를 상세히 정의
    """
    id: str  # UI1, UI2, UI3...
    component_type: str  # form, table, chart, dashboard, dialog, button, input
    page_name: str  # 어느 페이지에 속하는지
    purpose: str  # 이 컴포넌트의 목적
    data_source: Optional[str] = None  # 어떤 데이터를 표시하는지
    interactions: List[str] = []  # 사용자 상호작용 (click, submit, filter, etc.)
    related_features: List[str] = []  # 관련 기능 ID
    layout_position: Optional[str] = None  # 레이아웃 위치 (header, sidebar, main, footer)

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """UI Component ID 검증"""
        if not re.match(r"^UI\d+$", v):
            raise ValueError(f"UI Component ID는 'UI숫자' 형식이어야 합니다: {v}")
        return v


class NonFunctionalRequirementSpec(BaseModel):
    """
    비기능 요구사항 명세

    성능, 보안, 확장성 등 시스템 품질 속성 정의
    """
    performance: Optional[str] = None  # 성능 요구사항
    scalability: Optional[str] = None  # 확장성 요구사항
    security: Optional[str] = None  # 보안 요구사항
    reliability: Optional[str] = None  # 신뢰성 요구사항
    usability: Optional[str] = None  # 사용성 요구사항
    maintainability: Optional[str] = None  # 유지보수성 요구사항
    availability: Optional[str] = None  # 가용성 요구사항
    specific_requirements: List[str] = []  # 기타 구체적인 요구사항


class SystemScopeSpec(BaseModel):
    """
    시스템 범위 명세

    프로젝트의 전체 범위와 목적 정의
    """
    project_name: str
    purpose: str  # 시스템의 목적
    target_users: List[str] = []  # 대상 사용자 (예: "관리자", "일반 사용자")
    system_type: str  # web_app, cli_tool, api_service, data_pipeline, chatbot, etc.
    scope_description: str  # 시스템이 무엇을 하는지
    out_of_scope: List[str] = []  # 범위 밖의 항목 (무엇을 하지 않는지)


class ConcretizedRequirement(BaseModel):
    """
    구체화된 요구사항 (Golden Data)

    사용자 입력을 분석하여 구체화한 명확한 요구사항.
    모든 후속 단계(Discovery, Architecture, Design, Code)가 이를 참조해야 함.

    Purpose:
    - 모호한 사용자 입력을 명확하고 구체적인 요구사항으로 변환
    - 시스템의 범위, 기능, 데이터, UI, NFR을 명시적으로 정의
    - 모든 단계의 Golden Reference로 활용
    - 트레이서빌리티의 기준점
    """
    # 메타데이터
    version: str = "1.0"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # 시스템 범위
    system_scope: SystemScopeSpec

    # 기능 명세
    features: List[FeatureSpec]

    # 데이터 모델
    data_models: List[DataModelSpec] = []

    # UI 컴포넌트
    ui_components: List[UIComponentSpec] = []

    # 비기능 요구사항
    non_functional_requirements: NonFunctionalRequirementSpec

    # 제약사항 및 가정
    constraints: List[str] = []  # 기술적/비즈니스적 제약
    assumptions: List[str] = []  # 전제 조건

    # 성공 기준
    success_criteria: List[str] = []

    # 추가 컨텍스트
    domain: str  # 도메인 (e.g., "e-commerce", "healthcare", "finance")
    subdomain: Optional[str] = None

    # 품질 메트릭
    concretization_quality: Optional[QualityMetrics] = None

    def compute_concretization_quality(self) -> QualityMetrics:
        """
        구체화 품질을 계산

        Returns:
            QualityMetrics: 계산된 품질 메트릭
        """
        # 1. Completeness Score
        completeness = 0.0
        if self.system_scope.purpose: completeness += 0.15
        if len(self.features) > 0: completeness += 0.25
        if len(self.data_models) > 0: completeness += 0.15
        if len(self.ui_components) > 0: completeness += 0.10

        # Handle both dict and object formats for NFR
        nfr = self.non_functional_requirements
        if isinstance(nfr, dict):
            has_nfr = nfr.get('performance') or nfr.get('security')
        else:
            has_nfr = nfr.performance or nfr.security

        if has_nfr:
            completeness += 0.15
        if len(self.constraints) > 0: completeness += 0.10
        if len(self.success_criteria) > 0: completeness += 0.10

        # 2. Clarity Score: 각 항목의 상세도
        clarity = 0.0

        # Features가 상세한가?
        if self.features:
            avg_acceptance_criteria = sum(len(f.acceptance_criteria) for f in self.features) / len(self.features)
            clarity += min(1.0, avg_acceptance_criteria / 3.0) * 0.4

            avg_func_reqs = sum(len(f.functional_requirements) for f in self.features) / len(self.features)
            clarity += min(1.0, avg_func_reqs / 2.0) * 0.3

        # Data models가 상세한가?
        if self.data_models:
            avg_attributes = sum(len(dm.attributes) for dm in self.data_models) / len(self.data_models)
            clarity += min(1.0, avg_attributes / 3.0) * 0.3

        # 3. Consistency Score: Feature-DataModel-UI 연관성
        consistency = 1.0

        # 모든 UI Component가 관련 Feature를 가지는가?
        if self.ui_components:
            ui_with_features = sum(1 for ui in self.ui_components if ui.related_features)
            consistency = ui_with_features / len(self.ui_components)

        # 4. Feasibility Score
        feasibility = 1.0
        num_features = len(self.features)

        if num_features == 0:
            feasibility = 0.2
        elif num_features > 20:
            feasibility = 0.6  # 너무 많음

        # 5. Complexity Score
        complexity = min(10, max(1, num_features + len(self.data_models)))

        # 6. Confidence Score
        confidence = (completeness + clarity + consistency + feasibility) / 4.0

        # Quality Issues
        quality_issues = []
        improvement_suggestions = []

        if completeness < 0.7:
            quality_issues.append("구체화가 불완전합니다.")
            improvement_suggestions.append("Features, Data Models, UI Components를 더 상세히 정의하세요.")

        if clarity < 0.6:
            quality_issues.append("요구사항이 충분히 명확하지 않습니다.")
            improvement_suggestions.append("각 Feature에 Acceptance Criteria와 Functional Requirements를 추가하세요.")

        if consistency < 0.7:
            quality_issues.append("Features, Data Models, UI 간 연관성이 불명확합니다.")
            improvement_suggestions.append("UI Components에 related_features를 명시하세요.")

        metrics = QualityMetrics(
            completeness_score=round(completeness, 3),
            clarity_score=round(clarity, 3),
            consistency_score=round(consistency, 3),
            feasibility_score=round(feasibility, 3),
            complexity_score=complexity,
            confidence_score=round(confidence, 3),
            quality_issues=quality_issues,
            improvement_suggestions=improvement_suggestions
        )

        metrics.overall_quality = metrics.calculate_overall_quality()

        return metrics
