# CAAS 프로젝트 근본적 재설계 및 리팩토링 마스터 플랜

**버전:** 2.0
**날짜:** 2026-02-01
**목적:** 구조적 문제 해결 및 장기 확장성 확보
**기반:** Claude Architecture Analysis + Gemini Structural Analysis

---

## 🎯 Executive Summary

### 현재 상태 진단

CAAS 프로젝트는 **기능적으로 뛰어나지만**, 다음과 같은 **구조적 치명적 결함**을 가지고 있습니다:

| 문제 영역 | 심각도 | 영향 | 출처 |
|---------|--------|------|------|
| Framework가 app/에 의존 | 🔴 Critical | Framework 독립 배포 불가 | Claude |
| 핵심 로직이 app/에 위치 | 🔴 Critical | 역할 분리 실패 | Claude |
| 설정 관리 파편화 | 🔴 Critical | 유지보수 비용 증가 | Gemini |
| 높은 결합도 (Tight Coupling) | 🔴 Critical | 확장성 제한 | Gemini |
| 코드 중복 (~23K LOC) | 🟡 High | 개발 생산성 저하 | Claude |

### 재설계 목표

```
✅ Framework 100% 독립성 확보
✅ 명확한 모듈 책임 분리
✅ 플러그인 아키텍처 도입 (Agent Registry)
✅ 단일 설정 관리 시스템
✅ 코드 중복 80% 제거
✅ 테스트 커버리지 60% 달성
```

### 예상 효과

- **단기 (1-2개월):** 유지보수성 3배 향상, 버그 50% 감소
- **중기 (3-6개월):** 개발 속도 2배 향상, 새 기능 추가 시간 70% 단축
- **장기 (6-12개월):** Framework 오픈소스 배포, 커뮤니티 기여 가능

---

## Part 1: 구조적 문제 통합 분석

### 문제 1: Framework-App 의존성 역전 (Claude 분석)

#### 현재 상태

```python
# ❌ CRITICAL VIOLATION
# caas_framework/validation/golden_validator.py:28
from app.models.schemas import ConcretizedRequirement  # Framework → App 의존

# caas_framework/codegen/llm_code_generator.py:14
from app.utils.logger import get_logger  # Framework → App 의존
```

**문제점:**
- Framework를 독립적으로 사용 불가
- 라이브러리로 배포 불가
- 순환 의존성 위험

#### 영향 범위

| 모듈 | 잘못된 위치 | 올바른 위치 | LOC |
|------|------------|------------|-----|
| Models | app/models/ | caas_framework/models/ | 891 |
| BMAD Engine | app/core/bmad/ | caas_framework/bmad/ | 3,000+ |
| LLM Chains | app/llm/ | caas_framework/llm/ | 1,488 |
| SDD Engine | app/core/sdd/ | caas_framework/sdd/ | 1,200+ |
| Factory | app/core/factory/ | caas_framework/factory/ | 1,500+ |

**총 영향:** ~9,300 LOC 이동 필요

---

### 문제 2: 파편화된 설정 관리 (Gemini 분석)

#### 현재 상태

```
app/utils/config.py              ← 시스템 1 (시크릿 관리 우수)
caas_framework/config/loader.py  ← 시스템 2 (YAML 처리 우수)
```

**문제점:**
- 설정 값 중복
- 어느 시스템을 따를지 혼란
- 유지보수 비용 2배

#### 발견된 중복 설정

```python
# app/utils/config.py
class AppConfig:
    openai_api_key: str
    anthropic_api_key: str
    neo4j_uri: str
    # ...

# caas_framework/config/loader.py
class FrameworkConfig:
    llm_provider: str
    api_keys: Dict[str, str]
    database_config: Dict
    # 동일한 설정을 다른 구조로 관리
```

---

### 문제 3: 높은 결합도 - DIP 위반 (Gemini 분석)

#### 현재 구조 (Tight Coupling)

```python
# caas_framework/agents/collaboration.py
class ExpertAgentCollaboration:
    def run(self, phase: AgentPhase):
        # ❌ 구체적인 에이전트 클래스에 직접 의존
        if phase == AgentPhase.DISCOVERY:
            agent = RequirementAnalystAgent(...)  # Hard-coded
        elif phase == AgentPhase.ARCHITECTURE:
            agent = SystemArchitect(...)  # Hard-coded
        elif phase == AgentPhase.DESIGN:
            agent = AgentDesigner(...)  # Hard-coded
        # ...
```

**문제점:**
- 새 에이전트 추가 시 ExpertAgentCollaboration 수정 필요
- 에이전트 교체 어려움
- 테스트 어려움 (Mock 불가)
- 확장성 제한

#### 영향 분석

```
새 에이전트 추가 시:
1. 새 에이전트 클래스 작성
2. ExpertAgentCollaboration 수정  ← 불필요한 수정
3. 모든 의존 코드 재테스트           ← 리스크 증가
4. 배포                             ← 전체 재배포 필요

예상 작업 시간: 2-3일
실제 필요 시간: 30분 (Agent Registry 사용 시)
```

---

### 문제 4: 모듈 책임 모호 (Claude + Gemini)

#### app/ vs caas_framework/ 중복

| 기능 | app/ | caas_framework/ | 문제 |
|------|------|-----------------|------|
| **llm** | app/llm/chains.py (1488 LOC) | caas_framework/llm/ | 역할 불명확 |
| **workflow** | app/workflow/ | caas_framework/workflow/ | 중복 |
| **codegen** | app/codegen/ (16 files) | caas_framework/codegen/ (17 files) | 60% 중복 |
| **validation** | app/core/validation/ | caas_framework/validation/ | 분산됨 |

**근본 원인:**
- Framework(재사용 엔진) vs App(구체적 구현) 경계 불명확
- 점진적 개발 과정에서 중복 발생
- 리팩토링 부재

---

## Part 2: 목표 아키텍처 설계

### 핵심 설계 원칙

#### 1. Clean Architecture (Uncle Bob)

```
┌─────────────────────────────────────────────────────────┐
│                    External Interfaces                   │
│              (CLI, Web UI, API, Tests)                   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                 Application Layer (app/)                 │
│        (Use Cases, Orchestration, UI Logic)             │
│     ┌─────────────────────────────────────┐             │
│     │  Workflow Orchestrators             │             │
│     │  CLI Commands                       │             │
│     │  Configuration Integration          │             │
│     └─────────────────────────────────────┘             │
└──────────────────────┬──────────────────────────────────┘
                       │ Uses (Dependency →)
┌──────────────────────▼──────────────────────────────────┐
│            Framework Layer (caas_framework/)            │
│         (Domain Logic, Core Engines, Plugins)           │
│     ┌─────────────────────────────────────┐             │
│     │  BMAD Engine                        │             │
│     │  Agent Registry & Base Classes      │             │
│     │  LLM Chains                         │             │
│     │  Code Generators                    │             │
│     │  Validators                         │             │
│     │  Models                             │             │
│     └─────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────┘
```

**의존성 규칙:**
- ✅ App → Framework (OK)
- ❌ Framework → App (FORBIDDEN)
- ✅ Framework 내부: Interface → Concrete (DIP)

---

#### 2. Dependency Inversion Principle (DIP)

**Before (현재):**
```python
class ExpertAgentCollaboration:  # High-level
    def run(self):
        agent = RequirementAnalystAgent()  # ← 구체 클래스 의존 (BAD)
        result = agent.analyze(...)
```

**After (목표):**
```python
# Interface (Abstract)
class BaseExpertAgent(ABC):
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        pass

# High-level module
class ExpertAgentCollaboration:
    def run(self, phase: AgentPhase):
        agent = AgentRegistry.get(phase)  # ← 추상화 의존 (GOOD)
        result = await agent.execute(context)

# Concrete implementation (Low-level)
@AgentRegistry.register(phase=AgentPhase.DISCOVERY)
class RequirementAnalystAgent(BaseExpertAgent):
    async def execute(self, context):
        # Implementation
```

**효과:**
- ✅ 새 에이전트 추가: 파일 1개 추가만
- ✅ 에이전트 교체: 설정 변경만
- ✅ 테스트: Mock Agent 주입 가능
- ✅ 플러그인: 런타임에 에이전트 로딩 가능

---

#### 3. Single Responsibility Principle (SRP)

**모듈별 단일 책임:**

```
caas_framework/
├── models/           ← 데이터 모델만
├── bmad/             ← BMAD 엔진만
├── agents/           ← 에이전트 베이스 & 레지스트리만
├── llm/              ← LLM 통합만
├── codegen/          ← 코드 생성만
├── validation/       ← 검증만
└── config/           ← 설정 관리만 (SINGLE SOURCE)

app/
├── cli/              ← CLI만
├── orchestration/    ← 워크플로우 조합만
└── config/           ← 앱 레벨 설정 오버라이드만
```

---

### 목표 구조 상세

#### caas_framework/ (Core Library)

```
caas_framework/
│
├── config/                          ← 🆕 SINGLE SOURCE OF TRUTH
│   ├── __init__.py
│   ├── base.py                      # BaseConfig (Pydantic)
│   ├── loader.py                    # Unified config loader
│   ├── validators.py                # Config validation
│   └── defaults/
│       ├── llm.yaml
│       ├── database.yaml
│       └── agents.yaml
│
├── models/                          ← FROM app/models/
│   ├── schemas.py                   # ALL data models
│   ├── specifications.py
│   └── validation.py
│
├── agents/                          ← 🆕 Agent Registry Pattern
│   ├── __init__.py
│   ├── base.py                      # BaseExpertAgent (ABC)
│   ├── registry.py                  # AgentRegistry
│   ├── context.py                   # AgentContext, AgentResult
│   └── experts/                     # Concrete agents
│       ├── requirement_analyst.py   # @register(DISCOVERY)
│       ├── system_architect.py      # @register(ARCHITECTURE)
│       ├── agent_designer.py        # @register(DESIGN)
│       └── ...
│
├── bmad/                            ← FROM app/core/bmad/
│   ├── core/
│   │   ├── engine.py                # Main BMAD engine
│   │   ├── context.py
│   │   ├── document_sharder.py
│   │   ├── reflection_engine.py
│   │   └── adaptive_engine.py
│   ├── orchestration.py             # High-level orchestrator
│   └── golden_data.py
│
├── llm/                             ← FROM app/llm/
│   ├── chains/
│   │   ├── requirement_chain.py
│   │   ├── architecture_chain.py
│   │   └── ...
│   ├── plugin.py                    # LLMPlugin interface
│   └── providers/
│       ├── openai.py
│       ├── anthropic.py
│       └── ...
│
├── codegen/                         ← Unified generators
│   ├── engine.py                    # CodeGenerationEngine
│   ├── generators/
│   │   ├── base.py                  # BaseGenerator (ABC)
│   │   ├── ast_generator.py
│   │   ├── test_generator.py
│   │   └── ...
│   └── templates/
│
├── validation/                      ← Unified validation
│   ├── golden_validator.py
│   ├── phases/
│   │   ├── discovery.py
│   │   ├── architecture.py
│   │   └── design.py
│   ├── quality_gates.py             # 🆕 Quality gates
│   └── feedback_loops.py            # 🆕 Feedback system
│
├── factory/                         ← FROM app/core/factory/
│   ├── agent_factory.py
│   ├── task_factory.py
│   └── crew_assembler.py
│
├── sdd/                             ← FROM app/core/sdd/
│   └── engine.py
│
├── ontology/                        ← Unified
│   ├── domain_ontology.py
│   └── tools/
│       ├── tool_ontology.py
│       └── tool_manager.py
│
├── workflow/                        ← Framework workflows
│   ├── base.py                      # BaseWorkflow
│   └── patterns/
│       ├── sequential.py
│       └── hierarchical.py
│
└── utils/                           ← Framework utilities
    ├── logger.py
    ├── file_utils.py
    └── ...
```

#### app/ (Application Layer)

```
app/
│
├── config/                          ← App-level overrides only
│   └── app_settings.py              # Load from framework config
│
├── cli/                             ← CLI interface
│   ├── __init__.py
│   └── commands/
│       ├── generate.py
│       ├── validate.py
│       └── ...
│
├── orchestration/                   ← 🆕 High-level workflows
│   ├── full_pipeline.py             # Complete BMAD pipeline
│   ├── phase_runner.py              # Individual phase runner
│   └── hooks/                       # User-defined hooks
│
├── monitoring/                      ← App-level monitoring
│   ├── dashboard.py
│   └── metrics.py
│
├── artifacts/                       ← Output management
│   ├── generator.py
│   └── formatters/
│
└── utils/                           ← App-specific utilities
```

---

## Part 3: 재설계 핵심 컴포넌트

### 1. Unified Configuration System

#### 설계

```python
# caas_framework/config/base.py
from pydantic import BaseModel, Field, SecretStr
from typing import Dict, Optional, List
from pathlib import Path

class LLMConfig(BaseModel):
    """LLM provider configuration"""
    provider: str = "openai"
    api_key: SecretStr
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000

class DatabaseConfig(BaseModel):
    """Database configuration"""
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr
    use_neo4j: bool = False

class AgentConfig(BaseModel):
    """Agent system configuration"""
    use_expert_agents: bool = True
    max_feedback_loops: int = 3
    enable_reflection: bool = True
    registry_path: Optional[Path] = None

class CaaSConfig(BaseModel):
    """Master configuration - Single Source of Truth"""

    # LLM settings
    llm: LLMConfig

    # Database settings
    database: DatabaseConfig

    # Agent settings
    agents: AgentConfig

    # Output settings
    output_dir: Path = Field(default=Path("./output"))

    # Feature flags
    enable_validation: bool = True
    enable_quality_gates: bool = True
    enable_plan_mode: bool = False

    class Config:
        env_prefix = "CAAS_"
        env_file = ".env"
        env_file_encoding = "utf-8"


# caas_framework/config/loader.py
from typing import Optional
import yaml
from pathlib import Path

class ConfigLoader:
    """Unified configuration loader

    Priority (high → low):
    1. Environment variables
    2. User YAML file (--config)
    3. Project .caas.yaml
    4. Default YAML files
    5. Hardcoded defaults
    """

    _instance: Optional['CaaSConfig'] = None

    @classmethod
    def load(
        cls,
        config_file: Optional[Path] = None,
        **overrides
    ) -> CaaSConfig:
        """Load configuration with priority cascade"""

        if cls._instance is not None:
            return cls._instance

        # 1. Load defaults
        config_dict = cls._load_defaults()

        # 2. Override with project .caas.yaml
        project_config = Path.cwd() / ".caas.yaml"
        if project_config.exists():
            config_dict.update(cls._load_yaml(project_config))

        # 3. Override with user config file
        if config_file and config_file.exists():
            config_dict.update(cls._load_yaml(config_file))

        # 4. Override with explicit parameters
        config_dict.update(overrides)

        # 5. Environment variables handled by Pydantic
        cls._instance = CaaSConfig(**config_dict)
        return cls._instance

    @staticmethod
    def _load_defaults() -> Dict:
        """Load default configuration from framework"""
        defaults_dir = Path(__file__).parent / "defaults"
        config = {}

        for yaml_file in defaults_dir.glob("*.yaml"):
            with open(yaml_file) as f:
                config.update(yaml.safe_load(f))

        return config

    @staticmethod
    def _load_yaml(path: Path) -> Dict:
        """Load YAML configuration file"""
        with open(path) as f:
            return yaml.safe_load(f) or {}

    @classmethod
    def reset(cls):
        """Reset singleton (for testing)"""
        cls._instance = None


# Usage example
def get_config(**overrides) -> CaaSConfig:
    """Get current configuration"""
    return ConfigLoader.load(**overrides)
```

#### 마이그레이션 전략

```python
# Phase 1: Create unified config
# 1. Merge app/utils/config.py + caas_framework/config/loader.py
# 2. Create CaaSConfig with all settings

# Phase 2: Update all imports
# Before:
from app.utils.config import settings  # ❌
from caas_framework.config import load_config  # ❌

# After:
from caas_framework.config import get_config  # ✅
config = get_config()

# Phase 3: Deprecate old configs
# - Add deprecation warnings to old config modules
# - Remove after 2 releases
```

---

### 2. Agent Registry Pattern

#### 설계

```python
# caas_framework/agents/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel
from enum import Enum

class AgentPhase(Enum):
    """BMAD phases"""
    CONCRETIZATION = "concretization"
    DISCOVERY = "discovery"
    ARCHITECTURE = "architecture"
    DESIGN = "design"
    DEVELOPMENT = "development"
    DELIVERY = "delivery"

class AgentContext(BaseModel):
    """Context passed to agents"""
    phase: AgentPhase
    requirement: str
    previous_results: Dict[str, Any] = {}
    config: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}

class AgentResult(BaseModel):
    """Result from agent execution"""
    success: bool
    output: Any
    metadata: Dict[str, Any] = {}
    errors: list = []

class BaseExpertAgent(ABC):
    """Base class for all expert agents"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute agent logic"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Agent description"""
        pass


# caas_framework/agents/registry.py
from typing import Dict, Type, Optional, Callable
import inspect
from .base import BaseExpertAgent, AgentPhase

class AgentRegistry:
    """Global agent registry for dynamic agent discovery

    Enables plug-in architecture where agents can be:
    - Added without modifying orchestrator
    - Replaced at runtime
    - Mocked for testing
    - Loaded from external plugins
    """

    _agents: Dict[AgentPhase, Type[BaseExpertAgent]] = {}
    _factories: Dict[AgentPhase, Callable] = {}

    @classmethod
    def register(
        cls,
        phase: AgentPhase,
        agent_class: Optional[Type[BaseExpertAgent]] = None
    ):
        """Register an agent for a phase

        Can be used as decorator:
            @AgentRegistry.register(phase=AgentPhase.DISCOVERY)
            class MyAgent(BaseExpertAgent):
                ...

        Or called directly:
            AgentRegistry.register(AgentPhase.DISCOVERY, MyAgent)
        """
        def decorator(agent_cls: Type[BaseExpertAgent]):
            # Validate agent class
            if not issubclass(agent_cls, BaseExpertAgent):
                raise TypeError(
                    f"{agent_cls} must inherit from BaseExpertAgent"
                )

            # Register
            cls._agents[phase] = agent_cls
            print(f"✓ Registered {agent_cls.__name__} for {phase.value}")

            return agent_cls

        # Called as decorator with phase
        if agent_class is None:
            return decorator

        # Called directly
        return decorator(agent_class)

    @classmethod
    def register_factory(
        cls,
        phase: AgentPhase,
        factory: Callable[[], BaseExpertAgent]
    ):
        """Register a factory function for custom instantiation"""
        cls._factories[phase] = factory

    @classmethod
    def get(
        cls,
        phase: AgentPhase,
        config: Optional[Dict] = None
    ) -> BaseExpertAgent:
        """Get agent instance for a phase"""

        # Check factory first
        if phase in cls._factories:
            return cls._factories[phase]()

        # Get from registry
        if phase not in cls._agents:
            raise ValueError(
                f"No agent registered for phase {phase.value}. "
                f"Available phases: {list(cls._agents.keys())}"
            )

        agent_class = cls._agents[phase]
        return agent_class(config=config)

    @classmethod
    def list_agents(cls) -> Dict[AgentPhase, str]:
        """List all registered agents"""
        return {
            phase: agent_cls.__name__
            for phase, agent_cls in cls._agents.items()
        }

    @classmethod
    def clear(cls):
        """Clear registry (for testing)"""
        cls._agents.clear()
        cls._factories.clear()


# caas_framework/agents/experts/requirement_analyst.py
from ..base import BaseExpertAgent, AgentContext, AgentResult, AgentPhase
from ..registry import AgentRegistry

@AgentRegistry.register(phase=AgentPhase.DISCOVERY)
class RequirementAnalystAgent(BaseExpertAgent):
    """Expert agent for requirement analysis"""

    @property
    def name(self) -> str:
        return "Requirement Analyst"

    @property
    def description(self) -> str:
        return "Analyzes and structures user requirements"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Analyze requirements"""

        # Actual implementation
        from caas_framework.llm.chains import RequirementAnalysisChain

        chain = RequirementAnalysisChain(config=self.config)
        result = await chain.run(context.requirement)

        return AgentResult(
            success=True,
            output=result,
            metadata={"agent": self.name}
        )


# caas_framework/agents/collaboration.py (REFACTORED)
from .registry import AgentRegistry
from .base import AgentPhase, AgentContext, AgentResult

class ExpertAgentCollaboration:
    """Orchestrates expert agents using registry

    NO LONGER depends on concrete agent classes!
    """

    async def run_phase(
        self,
        phase: AgentPhase,
        context: AgentContext
    ) -> AgentResult:
        """Run a single phase using registered agent"""

        # Get agent from registry (dynamic!)
        agent = AgentRegistry.get(phase, config=self.config)

        # Execute
        result = await agent.execute(context)

        return result
```

#### 사용 예시

```python
# 1. Agent auto-registration on import
from caas_framework.agents.experts import (
    requirement_analyst,  # Auto-registers for DISCOVERY
    system_architect,     # Auto-registers for ARCHITECTURE
    agent_designer,       # Auto-registers for DESIGN
)

# 2. Run without knowing concrete classes
orchestrator = ExpertAgentCollaboration()
result = await orchestrator.run_phase(
    phase=AgentPhase.DISCOVERY,
    context=AgentContext(requirement="Build a todo app")
)

# 3. Override agent at runtime
@AgentRegistry.register(phase=AgentPhase.DISCOVERY)
class CustomRequirementAgent(BaseExpertAgent):
    async def execute(self, context):
        # Custom implementation
        ...

# 4. Mock for testing
class MockAgent(BaseExpertAgent):
    async def execute(self, context):
        return AgentResult(success=True, output="Mock result")

AgentRegistry.register(AgentPhase.DISCOVERY, MockAgent)
```

---

### 3. Quality Gates & Feedback Loops

#### 설계

```python
# caas_framework/validation/quality_gates.py
from typing import List, Optional
from pydantic import BaseModel
from enum import Enum

class QualityLevel(Enum):
    """Quality assessment levels"""
    FAIL = 0
    POOR = 1
    ACCEPTABLE = 2
    GOOD = 3
    EXCELLENT = 4

class QualityMetric(BaseModel):
    """Single quality metric"""
    name: str
    value: float  # 0.0 - 1.0
    threshold: float = 0.7
    weight: float = 1.0

    @property
    def passed(self) -> bool:
        return self.value >= self.threshold

    @property
    def level(self) -> QualityLevel:
        if self.value >= 0.9:
            return QualityLevel.EXCELLENT
        elif self.value >= 0.8:
            return QualityLevel.GOOD
        elif self.value >= 0.7:
            return QualityLevel.ACCEPTABLE
        elif self.value >= 0.5:
            return QualityLevel.POOR
        else:
            return QualityLevel.FAIL

class QualityReport(BaseModel):
    """Quality assessment report"""
    phase: str
    metrics: List[QualityMetric]
    overall_score: float
    passed: bool
    recommendations: List[str] = []

    @classmethod
    def from_metrics(cls, phase: str, metrics: List[QualityMetric]):
        # Calculate weighted average
        total_weight = sum(m.weight for m in metrics)
        overall = sum(m.value * m.weight for m in metrics) / total_weight

        # Check if all critical metrics passed
        passed = all(m.passed for m in metrics if m.weight >= 1.0)

        # Generate recommendations
        recommendations = [
            f"Improve {m.name} (current: {m.value:.2%}, threshold: {m.threshold:.2%})"
            for m in metrics if not m.passed
        ]

        return cls(
            phase=phase,
            metrics=metrics,
            overall_score=overall,
            passed=passed,
            recommendations=recommendations
        )

class QualityGate:
    """Quality gate that blocks progression if quality insufficient"""

    def __init__(
        self,
        phase: str,
        thresholds: Optional[Dict[str, float]] = None
    ):
        self.phase = phase
        self.thresholds = thresholds or {}

    async def evaluate(self, artifact: Any) -> QualityReport:
        """Evaluate artifact quality"""

        # Run all validators
        metrics = []

        # Completeness
        completeness = await self._check_completeness(artifact)
        metrics.append(QualityMetric(
            name="completeness",
            value=completeness,
            threshold=self.thresholds.get("completeness", 0.9),
            weight=2.0  # Critical
        ))

        # Correctness
        correctness = await self._check_correctness(artifact)
        metrics.append(QualityMetric(
            name="correctness",
            value=correctness,
            threshold=self.thresholds.get("correctness", 0.8),
            weight=2.0  # Critical
        ))

        # Consistency
        consistency = await self._check_consistency(artifact)
        metrics.append(QualityMetric(
            name="consistency",
            value=consistency,
            threshold=self.thresholds.get("consistency", 0.7),
            weight=1.0
        ))

        return QualityReport.from_metrics(self.phase, metrics)

    async def _check_completeness(self, artifact) -> float:
        """Check if artifact is complete"""
        # Implementation
        ...

    async def _check_correctness(self, artifact) -> float:
        """Check if artifact is correct"""
        # Implementation
        ...

    async def _check_consistency(self, artifact) -> float:
        """Check if artifact is consistent"""
        # Implementation
        ...


# caas_framework/validation/feedback_loops.py
from typing import Callable, Any

class SafeFeedbackLoop:
    """Feedback loop for iterative improvement

    Pattern:
    1. Producer generates artifact
    2. Critic evaluates artifact
    3. If not acceptable, producer refines
    4. Repeat until acceptable or max iterations
    """

    def __init__(
        self,
        producer: Callable,
        critic: Callable,
        max_iterations: int = 3,
        quality_threshold: float = 0.7
    ):
        self.producer = producer
        self.critic = critic
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold

    async def run(self, initial_input: Any) -> tuple[Any, QualityReport]:
        """Run feedback loop until quality acceptable"""

        current_input = initial_input
        iteration = 0

        while iteration < self.max_iterations:
            # Produce artifact
            artifact = await self.producer(current_input)

            # Evaluate quality
            report = await self.critic(artifact)

            # Check if acceptable
            if report.overall_score >= self.quality_threshold:
                return artifact, report

            # Refine input for next iteration
            current_input = {
                "previous_artifact": artifact,
                "critique": report.recommendations,
                "iteration": iteration + 1
            }

            iteration += 1

        # Return best effort after max iterations
        return artifact, report
```

---

## Part 4: 실행 계획

### Phase 0: 준비 (1주)

#### 목표
- 현재 코드 동결
- 브랜치 전략 수립
- 백업 생성

#### Tasks
1. **Git 브랜치 생성**
   ```bash
   git checkout -b refactor/fundamental-redesign
   git checkout -b refactor/phase-1-config
   git checkout -b refactor/phase-2-dip
   git checkout -b refactor/phase-3-migration
   ```

2. **전체 백업**
   ```bash
   cp -r caas_framework caas_framework.backup.$(date +%Y%m%d)
   cp -r app app.backup.$(date +%Y%m%d)
   ```

3. **테스트 베이스라인 구축**
   ```bash
   # 현재 통과하는 테스트 목록 저장
   pytest --collect-only > tests_baseline.txt
   ```

4. **문서화**
   - 현재 아키텍처 다이어그램 생성
   - 주요 데이터 흐름 문서화
   - 외부 의존성 목록 작성

---

### Phase 1: 구조적 기반 마련 (2주)

#### Week 1: Unified Configuration System

**목표:** 설정 관리 단일화

**Tasks:**
1. ✅ **caas_framework/config/ 생성**
   - base.py: CaaSConfig (Pydantic models)
   - loader.py: ConfigLoader
   - defaults/: Default YAML files

2. ✅ **app/utils/config.py 마이그레이션**
   - 모든 설정 → CaaSConfig로 통합
   - 시크릿 관리 로직 이식

3. ✅ **caas_framework/config/loader.py 개선**
   - YAML 우선순위 로직 통합
   - Environment variable 처리

4. ✅ **전체 import 경로 변경**
   ```bash
   # Find all config imports
   grep -r "from app.utils.config import" .
   grep -r "from caas_framework.config import" .

   # Replace with unified import
   # from caas_framework.config import get_config
   ```

5. ✅ **테스트 작성**
   - Config priority tests
   - YAML loading tests
   - Environment variable tests

**검증:**
```python
# All config usage should be:
from caas_framework.config import get_config
config = get_config()
```

---

#### Week 2: Dependency Inversion & Agent Registry

**목표:** 낮은 결합도, 높은 확장성

**Tasks:**
1. ✅ **BaseExpertAgent 정의**
   - caas_framework/agents/base.py
   - AgentContext, AgentResult models

2. ✅ **AgentRegistry 구현**
   - caas_framework/agents/registry.py
   - Decorator-based registration
   - Factory support

3. ✅ **기존 에이전트 리팩토링**
   - RequirementAnalystAgent → BaseExpertAgent
   - SystemArchitect → BaseExpertAgent
   - AgentDesigner → BaseExpertAgent
   - 각각 @register decorator 추가

4. ✅ **ExpertAgentCollaboration 리팩토링**
   - 구체 클래스 의존성 제거
   - AgentRegistry.get() 사용

5. ✅ **테스트 작성**
   - Registry registration tests
   - Mock agent tests
   - Collaboration tests

**검증:**
```python
# New agent can be added without modifying orchestrator
@AgentRegistry.register(phase=AgentPhase.QA)
class QAAgent(BaseExpertAgent):
    ...

# Agent can be replaced at runtime
AgentRegistry.register(AgentPhase.DISCOVERY, CustomAgent)
```

---

### Phase 2: 핵심 로직 마이그레이션 (3주)

#### Week 3: Models & LLM Migration

**목표:** Framework 독립성 확보

**Tasks:**
1. ✅ **app/models/ → caas_framework/models/**
   ```bash
   # Move models
   mv app/models/schemas.py caas_framework/models/schemas.py

   # Update all imports
   find . -type f -name "*.py" -exec sed -i \
     's/from app\.models\.schemas/from caas_framework.models.schemas/g' {} +
   ```

2. ✅ **app/llm/ → caas_framework/llm/**
   ```bash
   # Move LLM chains
   mv app/llm/chains.py caas_framework/llm/chains.py
   mv app/llm/prompts/ caas_framework/llm/prompts/

   # Update imports
   find . -type f -name "*.py" -exec sed -i \
     's/from app\.llm/from caas_framework.llm/g' {} +
   ```

3. ✅ **역방향 의존성 제거**
   ```bash
   # Find all framework → app imports
   grep -r "^from app\." caas_framework/

   # Should return: 0 results
   ```

4. ✅ **테스트 수정 및 실행**
   ```bash
   pytest caas_framework/models/
   pytest caas_framework/llm/
   ```

**검증:**
```bash
# Framework can be imported without app/
python -c "
from caas_framework.bmad import BMADEngine
from caas_framework.models import ConcretizedRequirement
print('✓ Framework is independent')
"
```

---

#### Week 4-5: BMAD, SDD, Factory Migration

**목표:** 핵심 엔진 통합

**Tasks:**
1. ✅ **app/core/bmad/ → caas_framework/bmad/**
   - engine.py (1796 LOC)
   - document_sharder.py
   - reflection_engine.py
   - adaptive_engine.py
   - personality_engine.py

2. ✅ **app/core/sdd/ → caas_framework/sdd/**
   - engine.py (1200+ LOC)

3. ✅ **app/core/factory/ → caas_framework/factory/**
   - agent_factory.py
   - task_factory.py
   - crew_assembler.py

4. ✅ **Import 경로 업데이트**
   ```bash
   find . -type f -name "*.py" -exec sed -i \
     's/from app\.core\.bmad/from caas_framework.bmad/g' {} +
   ```

5. ✅ **통합 테스트**
   ```bash
   pytest tests/integration/test_bmad_pipeline.py
   ```

**검증:**
- All BMAD features work from caas_framework
- No app/ dependencies in framework
- Tests pass

---

### Phase 3: 품질 시스템 구축 (2주)

#### Week 6: Quality Gates & Feedback Loops

**Tasks:**
1. ✅ **Quality Gates 구현**
   - caas_framework/validation/quality_gates.py
   - QualityMetric, QualityReport models
   - Phase-specific gates

2. ✅ **Feedback Loops 구현**
   - caas_framework/validation/feedback_loops.py
   - SafeFeedbackLoop class
   - Producer-Critic pattern

3. ✅ **통합**
   - BMAD engine에 quality gates 추가
   - 각 phase 후 feedback loop 실행

4. ✅ **테스트**
   - Quality gate tests
   - Feedback loop tests
   - Integration tests

---

#### Week 7: Code Analysis & Validation

**Tasks:**
1. ✅ **Static Analysis 통합**
   - ruff linter 자동 실행
   - mypy type checker
   - CodeGeneratorAgent 통합

2. ✅ **Dynamic Testing**
   - LLM 기반 테스트 케이스 생성
   - 자동 테스트 실행

3. ✅ **Critic Agents 구현**
   ```python
   @AgentRegistry.register(phase=AgentPhase.CRITIQUE_DISCOVERY)
   class BusinessDomainCritic(BaseExpertAgent):
       """비즈니스 관점에서 요구사항 검토"""
       ...

   @AgentRegistry.register(phase=AgentPhase.CRITIQUE_ARCHITECTURE)
   class ScalabilitySecurityCritic(BaseExpertAgent):
       """확장성과 보안 관점에서 아키텍처 검토"""
       ...
   ```

---

### Phase 4: 정리 및 최적화 (2주)

#### Week 8: Code Deduplication

**Tasks:**
1. ✅ **Generator 통합 (P2.3)**
   - AST generators consolidation
   - CI/CD generators consolidation
   - Test generators unification

2. ✅ **Validation 통합**
   - app/core/validation/ → caas_framework/validation/phases/

3. ✅ **Ontology 통합**
   - app/core/ontology/ → caas_framework/ontology/tools/

**예상 절감:** ~1,500-2,000 LOC

---

#### Week 9: Cleanup & Documentation

**Tasks:**
1. ✅ **app/core/ 정리**
   - 이동한 모듈 제거
   - Re-export wrappers 생성 (deprecation warnings)

2. ✅ **문서 업데이트**
   - Architecture guide
   - Migration guide
   - API documentation
   - Example code

3. ✅ **테스트 커버리지**
   - 목표: 60%
   - Critical paths 100% coverage

4. ✅ **Performance 최적화**
   - Profiling
   - Bottleneck 제거

---

### Phase 5: Human-in-the-Loop 개선 (1주)

#### Week 10: Interactive Plan Mode

**Tasks:**
1. ✅ **대화형 피드백 구현**
   - 사용자 수정 의견 입력 UI
   - AI 반영 로직

2. ✅ **선택지 제시 시스템**
   - 기술적 대안 생성
   - 장단점 분석
   - 사용자 선택 통합

3. ✅ **Plan Mode 통합**
   - BMAD pipeline 통합
   - 각 phase 후 승인 게이트

---

## Part 5: 성공 지표 (KPI)

### 아키텍처 품질

| 지표 | Before | Target | 측정 방법 |
|------|--------|--------|----------|
| Framework 독립성 | ❌ 0% | ✅ 100% | `grep -r "^from app\." caas_framework/` → 0 |
| 설정 시스템 통합 | ❌ 2개 | ✅ 1개 | Single ConfigLoader |
| Agent 결합도 | ❌ High | ✅ Low | DIP compliance |
| 코드 중복률 | 🟡 20-25% | ✅ <5% | Tool analysis |

### 코드 품질

| 지표 | Before | Target | 측정 방법 |
|------|--------|--------|----------|
| 테스트 커버리지 | 1% | 60% | pytest --cov |
| Linter 경고 | ~500 | <50 | ruff check |
| Type 커버리지 | 0% | 80% | mypy |
| Cyclomatic Complexity | 평균 8.5 | 평균 5.0 | radon |

### 개발 생산성

| 지표 | Before | Target | 측정 방법 |
|------|--------|--------|----------|
| 새 에이전트 추가 시간 | 2-3일 | 30분 | Time tracking |
| 설정 변경 시간 | 1시간 | 5분 | Single config file |
| 버그 수정 시간 | 평균 2일 | 평균 4시간 | Issue tracker |
| 새 기능 추가 시간 | 평균 1주 | 평균 2일 | Feature tracking |

### 품질 개선

| 지표 | Before | Target | 측정 방법 |
|------|--------|--------|----------|
| 버그 발생률 | 기준 | -50% | Bug count |
| 코드 리뷰 시간 | 평균 2시간 | 평균 30분 | Review time |
| 품질 게이트 통과율 | N/A | 90% | Gate metrics |
| 피드백 루프 효과 | N/A | +30% quality | Quality scores |

---

## Part 6: 리스크 관리

### High-Risk Areas

#### 1. 대규모 마이그레이션 (Models, LLM, BMAD)

**리스크:**
- Import 경로 변경 시 놓친 파일
- 런타임 에러 발생
- 테스트 중단

**완화 방안:**
- 자동화된 import 교체 스크립트
- 단계별 검증 (unit → integration → e2e)
- 점진적 rollout (feature flag 사용)

#### 2. Agent Registry 도입

**리스크:**
- 기존 코드와 호환성 문제
- 성능 오버헤드
- 디버깅 어려움 (동적 로딩)

**완화 방안:**
- Backward compatibility layer 유지
- 성능 벤치마크
- 상세 로깅 & tracing

#### 3. 설정 시스템 변경

**리스크:**
- 기존 설정 파일 호환성
- 환경별 설정 불일치
- 시크릿 노출

**완화 방안:**
- Legacy config adapter 제공
- 마이그레이션 스크립트
- 설정 validation 강화

---

## Part 7: 롤백 계획

### 각 Phase별 Rollback Point

```bash
# Phase 1 rollback
git checkout refactor/phase-0-backup
git reset --hard <commit-before-phase-1>

# Phase 2 rollback
git revert <phase-2-commits>

# Phase 3 rollback
# Feature flags로 새 기능 비활성화
ENABLE_QUALITY_GATES=false
ENABLE_FEEDBACK_LOOPS=false
```

### Rollback 결정 기준

**즉시 Rollback:**
- 프로덕션 장애 발생
- 테스트 통과율 <80%
- 성능 50% 이상 저하

**Phase 재검토:**
- 버그 발생률 +30% 이상
- 개발 속도 -20% 이상
- 사용자 불만 증가

---

## Part 8: 결론

### 왜 이 재설계가 필요한가?

현재 CAAS는 **기능적으로는 뛰어나지만**, 다음과 같은 **구조적 한계**로 인해 **지속 가능한 성장이 어렵습니다**:

1. **Framework를 독립적으로 사용 불가** → 라이브러리 배포 불가
2. **설정이 파편화되어 관리 어려움** → 운영 비용 증가
3. **높은 결합도로 확장 어려움** → 새 기능 추가 시간 증가
4. **코드 중복 25%** → 버그 수정 시 여러 곳 수정 필요

### 재설계 후 기대 효과

**단기 (1-2개월):**
- ✅ 유지보수 시간 70% 단축
- ✅ 버그 발생률 50% 감소
- ✅ 설정 관리 복잡도 90% 감소

**중기 (3-6개월):**
- ✅ 새 기능 추가 시간 70% 단축
- ✅ 코드 리뷰 시간 75% 단축
- ✅ 테스트 커버리지 60배 증가 (1% → 60%)

**장기 (6-12개월):**
- ✅ Framework 오픈소스 배포 가능
- ✅ 플러그인 생태계 구축
- ✅ 커뮤니티 기여 활성화

### 실행 로드맵 요약

```
Phase 0: 준비 (1주)
  └─ 백업, 브랜치, 문서화

Phase 1: 구조적 기반 (2주)
  ├─ Week 1: Unified Config System
  └─ Week 2: Agent Registry (DIP)

Phase 2: 핵심 마이그레이션 (3주)
  ├─ Week 3: Models & LLM
  ├─ Week 4: BMAD Engine
  └─ Week 5: SDD & Factory

Phase 3: 품질 시스템 (2주)
  ├─ Week 6: Quality Gates
  └─ Week 7: Code Analysis

Phase 4: 정리 (2주)
  ├─ Week 8: Deduplication
  └─ Week 9: Documentation

Phase 5: UX 개선 (1주)
  └─ Week 10: Human-in-the-Loop

총 기간: 10주 (2.5개월)
```

### 다음 단계

**즉시 시작:**
1. ✅ Phase 0 준비 작업 (백업, 브랜치)
2. ✅ Phase 1 Week 1 시작 (Unified Config)

**의사 결정 필요:**
- [ ] 로드맵 승인
- [ ] 리소스 할당
- [ ] 타임라인 확정

---

**문서 작성자:** Architecture Redesign Team (Claude + Gemini Analysis)
**날짜:** 2026-02-01
**버전:** 2.0
**다음 액션:** Phase 0 시작 승인 대기
