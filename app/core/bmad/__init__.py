"""
CAAS BMAD Package

Breakthrough Method for Agile AI-driven Development 구현체입니다.

주요 구성요소:
- BMADEngine: 메인 엔진 (4단계 프로세스 조율)
- RequirementAnalyzer: 요구사항 분석기
- RoleMapper: 역할-태스크-도구 매퍼
- SprintPlanner: 스프린트 계획기

🆕 Phase 1-3 확장:
- DocumentSharder: 문서 샤딩 (90% 토큰 절감)
- ReflectionEngine: 반성 엔진 (CORE)
- ScaleAdaptiveEngine: 규모 적응형 엔진
- PersonalityManager: 에이전트 성격 관리
- MultiLanguageCodeGenerator: 다국어 코드 생성
"""

from app.core.bmad.engine import (
    BMADPhase,
    PhaseStatus,
    FeatureItem,
    SprintItem,
    BMADContext,
    BMADEngine,
)
from app.core.bmad.analyzer import (
    RequirementAnalyzer,
    AnalysisResult,
    ExtractedFeature,
    DomainContext,
    RequirementType,
)
from app.core.bmad.mapper import RoleMapper
from app.core.bmad.models import (
    MappingResult,
    AgentMapping,
    TaskMapping,
)
from app.core.bmad.planner import (
    SprintPlanner,
    SprintPlan,
    Sprint,
    PlannedTask,
    SprintStatus,
    TaskPriority,
)

# 🆕 Phase 1: 핵심 BMAD 기능
from app.core.bmad.sharding import (
    DocumentSharder,
    DocumentShard,
    ShardingStrategy,
    ShardingResult,
)
from app.core.bmad.reflection import (
    ReflectionEngine,
    ReflectionResult,
    ReflectionFeedback,
)

# 🆕 Phase 2: 지능화
from app.core.bmad.adaptive import (
    ScaleAdaptiveEngine,
    ProjectScale,
    AdaptiveWorkflowConfig,
)

# 🆕 Phase 3: 개선
from app.core.bmad.personality import (
    PersonalityManager,
    AgentPersonality,
    PersonalityTone,
    VerbosityLevel,
    RiskTolerance,
    PersonalityPreset,
)

__all__ = [
    # Engine
    "BMADPhase",
    "PhaseStatus",
    "FeatureItem",
    "SprintItem",
    "BMADContext",
    "BMADEngine",
    # Analyzer
    "RequirementAnalyzer",
    "AnalysisResult",
    "ExtractedFeature",
    "DomainContext",
    "RequirementType",
    # Mapper
    "RoleMapper",
    "MappingResult",
    "AgentMapping",
    "TaskMapping",
    # Planner
    "SprintPlanner",
    "SprintPlan",
    "Sprint",
    "PlannedTask",
    "SprintStatus",
    "TaskPriority",
    # Phase 1: 핵심 BMAD
    "DocumentSharder",
    "DocumentShard",
    "ShardingStrategy",
    "ShardingResult",
    "ReflectionEngine",
    "ReflectionResult",
    "ReflectionFeedback",
    # Phase 2: 지능화
    "ScaleAdaptiveEngine",
    "ProjectScale",
    "AdaptiveWorkflowConfig",
    # Phase 3: 개선
    "PersonalityManager",
    "AgentPersonality",
    "PersonalityTone",
    "VerbosityLevel",
    "RiskTolerance",
    "PersonalityPreset",
]
