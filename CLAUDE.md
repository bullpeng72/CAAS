# CLAUDE.md - CAAS Project Context

## 프로젝트 개요

**CAAS (CrewAI Agent Auto-generation System)** v1.0.0

자연어 요구사항을 입력받아 프로덕션 레디 멀티 에이전트 시스템 코드를 자동으로 생성하는 Framework-First CLI 도구입니다.

- **핵심 목표**: 자연어 → Golden Data → Agent/Task 설계 → Production Code 자동 생성
- **방법론**: BMAD 6-Phase 프로세스 (Concretization → Discovery → Architecture → Design → Development → Delivery)
- **강점**: CrewAI 멀티 에이전트 시스템 98.7% 구현률 달성
- **아키텍처**: Framework-First (UI-독립적 코어 + 다중 인터페이스)

## 프로젝트 구조

```
caas/
├── caas_framework/          # 🎯 코어 프레임워크 (UI-독립적)
│   ├── agents/              # 5개 Expert Agents (Requirement Analyst, System Architect, Agent Designer, QA, Code Generator)
│   │   ├── collaboration.py # 에이전트 협업 오케스트레이터 (Quality Gate 포함)
│   │   ├── requirement_analyst.py
│   │   ├── system_architect.py
│   │   ├── agent_designer.py
│   │   ├── qa_specialist.py
│   │   └── code_generator.py
│   ├── bmad/                # BMAD 6-Phase Engine
│   │   ├── engine.py        # Phase 오케스트레이터
│   │   └── golden_data.py   # Phase 0: Concretization
│   ├── codegen/             # Code Generation
│   │   ├── generators/      # 도메인별 코드 생성기
│   │   └── templates/       # Jinja2 템플릿
│   ├── validation/          # 6개 Validator (Ontology, Golden, Dependency, Python311, CrewAI, All)
│   │   └── orchestrator.py  # 검증 오케스트레이터
│   ├── fixing/              # 3-Level Auto-Fixing (Template/Rule/LLM)
│   │   └── auto_fixer.py
│   ├── plugins/             # Plugin System
│   │   ├── llm/             # LLM Provider Plugins (OpenAI, Anthropic, Multi-Model Router)
│   │   ├── graphdb/         # Graph DB Plugins (Neo4j, Embedded)
│   │   └── vectordb/        # Vector DB Plugins (선택적)
│   ├── knowledge/           # Ontology & Knowledge Graph
│   ├── config/              # Configuration Management
│   ├── session/             # Session Management
│   ├── workflow/            # Workflow Orchestration
│   ├── testing/             # Test Generation & Execution
│   ├── refinement/          # Requirement Refinement (Gap Analysis, Expand)
│   └── models/              # Pydantic Models (specifications.py)
│
├── caas_cli/                # CLI Interface (20 commands)
│   ├── cli.py               # Click-based CLI 진입점
│   └── commands/            # CLI 명령어 구현
│
├── caas_sdk/                # Python SDK (선택적)
│   └── client.py            # Sync/Async clients
│
├── caas_app/                # Shared utilities (legacy, 점진적 제거 중)
│
├── data/
│   ├── templates/           # Jinja2 코드 템플릿
│   └── golden_examples/     # Golden Data 예시
│
├── docs/                    # 한국어 문서 (13개)
│   ├── 1_시작하기/
│   ├── 2_개발_방법론/
│   ├── 3_시스템_문서/
│   └── 4_기능_가이드/
│
└── tests/                   # 100+ 테스트
    ├── test_e2e_*.py        # E2E 통합 테스트
    ├── test_bmad/           # BMAD 엔진 테스트
    ├── test_codegen/        # 코드 생성 테스트
    └── test_validation/     # 검증 시스템 테스트
```

### 주요 디렉토리 설명

- **`caas_framework/`**: UI-독립적 코어. 모든 비즈니스 로직 포함.
- **`caas_cli/`**: CLI 전용. Framework를 얇게 감싸는 인터페이스 레이어.
- **`caas_sdk/`**: Python SDK. 프로그래밍 방식 사용 지원.
- **`caas_app/`**: Legacy shared utilities. **점진적 제거 중** (refactor/fundamental-redesign 브랜치).

## 핵심 아키텍처

### 1. Framework-First Architecture

```
┌─────────────────────────────────────────────────┐
│            Interface Layer (선택)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │   CLI    │  │   SDK    │  │   UI     │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
└───────┼─────────────┼─────────────┼─────────────┘
        │             │             │
        └──────────┬──┴─────────────┘
                   │
        ┌──────────▼──────────────────────────────┐
        │    caas_framework (Core Engine)         │
        │  ┌────────────────────────────────────┐ │
        │  │   BMAD 6-Phase Workflow           │ │
        │  │   - Phase 0: Concretization       │ │
        │  │   - Phase 1-5: BMAD Phases        │ │
        │  └────────────────────────────────────┘ │
        │  ┌────────────────────────────────────┐ │
        │  │   5 Expert Agents Collaboration   │ │
        │  │   - Quality Gate System           │ │
        │  └────────────────────────────────────┘ │
        │  ┌────────────────────────────────────┐ │
        │  │   Plugin System                   │ │
        │  │   - LLM, Graph DB, Vector DB      │ │
        │  └────────────────────────────────────┘ │
        └─────────────────────────────────────────┘
```

### 2. BMAD 6-Phase Workflow

```
Phase 0: Concretization
  └─> Golden Data (구조화된 요구사항)

Phase 1: Discovery
  └─> Requirement Analysis (도메인 분류, 기능 분석)

Phase 2: Architecture
  └─> System Design (아키텍처 설계 + Traceability 검증)

Phase 3: Design
  └─> Agent/Task 설계 (Completeness 검증)

Phase 4: Development
  └─> Spec Generation (명세 생성)

Phase 5: Delivery
  └─> Production Code (main.py, agents.py, tasks.py, tools.py, tests, deployment)
```

**중요**: Quality Gate 시스템이 v1.0.0에서 일부 Phase에서 임시 우회됨 (무한 대기 문제 해결). v1.1.0에서 근본 수정 예정.

### 3. 5 Expert Agents Collaboration

```python
# caas_framework/agents/collaboration.py

class ExpertAgentCollaboration:
    """
    5개 전문가 에이전트 협업 관리

    Agents:
    1. Requirement Analyst - 요구사항 분석 및 Golden Data 생성
    2. System Architect - 시스템 아키텍처 설계
    3. Agent Designer - CrewAI Agent/Task 설계 및 최적화
    4. QA Specialist - 검증 및 완전성 체크
    5. Code Generator - 프로덕션 코드 생성
    """
```

### 4. Plugin System

```python
# caas_framework/plugins/

# LLM Plugins
- OpenAI (기본)
- Anthropic
- Multi-Model Router (동적 라우팅)

# Graph DB Plugins
- Neo4j
- Embedded (in-memory)

# Vector DB Plugins (선택적)
```

### 5. 3-Level Auto-Fixing System

```
Level 1: Template-based
  - 빠름, 결정론적
  - 간단한 패턴 수정

Level 2: Rule-based
  - 중간 속도
  - 패턴 매칭 기반

Level 3: LLM-based ⭐
  - 느림, 지능적
  - 복잡한 로직 수정
```

## 주요 컴포넌트 상세

### 1. CrewAIFramework (caas_framework/framework.py)

```python
class CrewAIFramework:
    """
    메인 프레임워크 진입점

    주요 메서드:
    - generate_from_requirement(): 요구사항 → 코드 전체 워크플로우
    - analyze_requirement(): 요구사항 분석
    - validate_design(): 설계 검증
    - generate_code(): 코드 생성
    """
```

### 2. BMADEngine (caas_framework/bmad/engine.py)

```python
class BMADEngine:
    """
    BMAD 6-Phase 워크플로우 오케스트레이터

    주요 메서드:
    - execute_phase(): 특정 Phase 실행
    - execute_full_workflow(): 전체 Phase 순차 실행
    """
```

### 3. ValidationOrchestrator (caas_framework/validation/orchestrator.py)

```python
class ValidationOrchestrator:
    """
    6개 Validator 통합 실행

    Validators:
    1. OntologyValidator - 온톨로지 검증
    2. GoldenDataValidator - Golden Data 완전성 검증
    3. DependencyValidator - Task 의존성 검증
    4. Python311Validator - Python 3.11+ 호환성 검증
    5. CrewAIValidator - CrewAI 호환성 검증
    6. AllValidator - 전체 검증
    """
```

### 4. AutoFixer (caas_framework/fixing/auto_fixer.py)

```python
class AutoFixer:
    """
    3-Level 자동 수정 시스템

    fix_agents(): Agent 설계 수정
    fix_tasks(): Task 설계 수정
    fix_golden_data(): Golden Data 수정
    """
```

## 코딩 컨벤션 및 가이드라인

### 파일 명명 규칙

- **모듈**: `snake_case.py`
- **클래스**: `PascalCase`
- **함수/메서드**: `snake_case()`
- **상수**: `UPPER_SNAKE_CASE`

### 코드 스타일

```python
# Black formatter 사용 (line-length: 100)
# Import 순서: isort profile="black"

# 1. Standard library
import logging
from typing import Dict, List, Optional

# 2. Third-party
from pydantic import BaseModel

# 3. Local
from caas_framework.models import AgentSpecModel
```

### 타입 힌트

```python
# 모든 public 함수/메서드에 타입 힌트 필수
def generate_code(
    agents: List[AgentSpecModel],
    tasks: List[TaskSpecModel],
    output_dir: Path
) -> Dict[str, Any]:
    """명확한 docstring 작성"""
    pass
```

### Pydantic 모델 사용

```python
# caas_framework/models/specifications.py

class AgentSpecModel(BaseModel):
    """모든 데이터 모델은 Pydantic 사용"""
    name: str
    role: str
    goal: str
    backstory: str
    tools: List[str] = []
```

### 에러 처리

```python
# 명확한 예외 메시지
try:
    result = generate_code(agents, tasks)
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
    raise ValidationError(
        f"Agent validation failed for {agent_name}: {e}"
    ) from e
```

### 로깅

```python
import logging

logger = logging.getLogger(__name__)

# 로그 레벨 가이드:
# - DEBUG: 상세한 디버깅 정보
# - INFO: 주요 진행 상황
# - WARNING: 예상 가능한 문제
# - ERROR: 오류 발생
# - CRITICAL: 치명적 오류
```

## 개발 워크플로우

### 새로운 기능 추가

1. **Framework Layer부터 시작**
   ```bash
   # caas_framework/에 새로운 모듈 추가
   # 테스트 작성 (tests/)
   # CLI 인터페이스 추가 (caas_cli/)
   ```

2. **테스트 작성 (TDD 권장)**
   ```bash
   pytest tests/test_new_feature.py -v
   ```

3. **타입 체크**
   ```bash
   mypy caas_framework/new_module.py
   ```

4. **코드 포맷팅**
   ```bash
   black caas_framework/
   isort caas_framework/
   ```

### Git 브랜치 전략

현재 브랜치: `refactor/fundamental-redesign`
- 메인 브랜치: (설정 필요)
- Feature 브랜치: `feature/새기능명`
- Bugfix 브랜치: `fix/버그명`

### 커밋 메시지 컨벤션

```
✨ feat: 새로운 기능 추가
🐛 fix: 버그 수정
📝 docs: 문서 수정
♻️ refactor: 리팩토링
✅ test: 테스트 추가/수정
🔧 chore: 빌드/설정 변경
🚀 perf: 성능 개선
```

## 테스트 전략

### 테스트 구조

```
tests/
├── test_e2e_*.py              # E2E 통합 테스트 (실제 LLM 호출)
├── test_bmad/                 # BMAD 엔진 유닛 테스트
├── test_codegen/              # 코드 생성 테스트
├── test_validation/           # 검증 시스템 테스트
├── test_fixing/               # Auto-fixing 테스트
└── test_feedback_loop.py      # 피드백 루프 테스트
```

### 테스트 실행

```bash
# 전체 테스트
pytest

# 특정 카테고리
pytest tests/test_bmad/

# 커버리지 포함
pytest --cov=caas_framework --cov=caas_cli --cov-report=html

# 병렬 실행
pytest -n auto

# E2E 테스트 (시간 소요)
pytest tests/test_e2e_todo_app.py -v
```

### Mock 사용

```python
# LLM 호출이 필요한 테스트는 Mock 사용
from unittest.mock import Mock, patch

@patch('caas_framework.plugins.llm.openai.OpenAIPlugin.generate')
def test_requirement_analysis(mock_generate):
    mock_generate.return_value = "Mocked response"
    # Test logic
```

## 중요한 주의사항

### 1. app/ 디렉토리 제거 진행 중 ⚠️

- **현재 상태**: `app/` 디렉토리가 완전히 제거됨 (최근 커밋)
- **마이그레이션**: 모든 기능이 `caas_framework/`로 이동 완료
- **주의**: `app/`에서 import하는 코드는 더 이상 작동하지 않음

```python
# ❌ 구식 (작동 안 함)
from app.knowledge.graph_client import GraphClient

# ✅ 신식
from caas_framework.knowledge.graph_client import GraphClient
```

### 2. Quality Gate 임시 우회 ⚠️

- **파일**: `caas_framework/agents/collaboration.py`
- **문제**: `QualityGateSystem.evaluate_gate()` 무한 대기
- **해결**: Phase 1, 2, 3, 5의 Quality Gate 임시 우회
- **영향**: 워크플로우는 정상 동작하지만 자동 품질 검증 비활성화
- **계획**: v1.1.0에서 근본 수정

### 3. tools.py 3-Layer Defense

```python
# caas_framework/codegen/generators/tools_generator.py

# 항상 실행 가능한 tools.py 생성 보장:
# 1. Validation: 한국어 도구명 자동 번역 (40+ 쌍)
# 2. LLM Generation: BaseTool 상속, 에러 핸들링 포함
# 3. Fallback: LLM 실패 시 stub 자동 생성
```

### 4. 지원되는 도메인

| 도메인 | 전략 | 구현률 |
|--------|------|--------|
| CONVERSATIONAL_AI | AGENT_BASED | 98.7% ⭐ |
| CONTENT_CREATION | AGENT_BASED | 98.7% ⭐ |
| DATA_ANALYSIS | HYBRID | 98.3% ⭐ |
| WORKFLOW_AUTOMATION | HYBRID | 높음 |
| TASK_MANAGEMENT | CRUD_BASED | 중간 |
| E_COMMERCE | CRUD_BASED | 중간 |
| PROJECT_MANAGEMENT | CRUD_BASED | 중간 |
| CUSTOMER_SUPPORT | AGENT_BASED | 높음 |

**추천**: CrewAI 멀티 에이전트 시스템, 데이터 분석 워크플로우

### 5. 환경 변수 설정

```bash
# .env 파일 (루트 디렉토리)
OPENAI_API_KEY=sk-...          # 필수 (또는 ANTHROPIC_API_KEY)
NEO4J_URI=bolt://localhost:7687 # 선택적
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### 6. 플러그인 우선순위

```python
# LLM Provider 우선순위:
# 1. OpenAI (기본, 가장 안정적)
# 2. Anthropic (대안)
# 3. Multi-Model Router (동적 선택)

# Graph DB:
# 1. Embedded (기본, 설정 불필요)
# 2. Neo4j (프로덕션 권장)
```

## 디버깅 팁

### 1. Phase별 실행

```bash
# 특정 Phase만 디버깅
caas generate-phase --phase 0 "요구사항"  # Concretization
caas generate-phase --phase 1 "요구사항"  # Discovery
# ... Phase 2-5
```

### 2. 로그 레벨 조정

```python
# 상세 로깅
logging.basicConfig(level=logging.DEBUG)
```

### 3. 검증 실패 시

```bash
# 1. 검증 실행
caas validate --validator all --agents agents.json --tasks tasks.json

# 2. 자동 수정 시도
caas fix --level 3 --agents agents.json --tasks tasks.json

# 3. 재검증
caas validate --validator all --agents fixed_agents.json --tasks fixed_tasks.json
```

### 4. 생성된 코드 테스트

```bash
cd output_directory
pip install -r requirements.txt
python main.py
pytest tests/
```

## 유용한 리소스

### 문서
- [README.md](README.md) - 프로젝트 개요
- [docs/README_KO.md](docs/README_KO.md) - 한국어 문서 색인
- [docs/2_개발_방법론/초보자_가이드.md](docs/2_개발_방법론/초보자_가이드.md) - 실전 활용 가이드
- [docs/3_시스템_문서/아키텍처_가이드.md](docs/3_시스템_문서/아키텍처_가이드.md) - 아키텍처 설명

### 예시 프로젝트
- `data/golden_examples/` - Golden Data 예시
- `tests/test_e2e_*.py` - E2E 테스트로 실제 사용 예시 확인

### CLI 치트시트

```bash
# 초기 설정
caas init
caas env --create

# 빠른 생성
caas generate "요구사항" --output ./project

# 검증 & 수정
caas validate --validator all --agents agents.json --tasks tasks.json
caas fix --level 3 --agents agents.json --tasks tasks.json

# 프로젝트 관리
caas list
caas status <id>
caas download <id> ./output
```

## 성능 고려사항

### 생성 시간 (평균)
- **전체 워크플로우**: 5-10분 (6 Phase 모두)
- **빠른 코드 생성**: 1-2분 (설계 파일 있을 때)
- **컴포넌트 재생성**: 30초-1분

### 최적화 팁
1. **캐싱 활용**: LLM 응답 캐싱 활성화
2. **병렬 처리**: 독립적인 에이전트 작업 병렬화
3. **Haiku 모델 사용**: 간단한 작업은 빠른 모델 사용

## FAQ

### Q: app/ 디렉토리는 왜 제거되었나요?
**A**: Framework-First 아키텍처로 리팩토링. 모든 기능이 `caas_framework/`로 통합되어 UI-독립성 확보.

### Q: Quality Gate가 왜 우회되었나요?
**A**: v1.0.0에서 무한 대기 버그 발견. 임시 우회로 워크플로우 정상화. v1.1.0에서 근본 수정 예정.

### Q: 웹 애플리케이션 코드는 생성할 수 없나요?
**A**: Flask/FastAPI 엔드포인트 직접 생성은 제한적. 대신 비즈니스 로직을 처리하는 CrewAI 에이전트 생성을 권장.

### Q: 어떤 도메인이 가장 잘 지원되나요?
**A**: CrewAI 멀티 에이전트 시스템 (98.7% 구현률), 데이터 분석 워크플로우 (98.3% 구현률).

### Q: 테스트 커버리지는 어떻게 되나요?
**A**: 100+ 테스트 존재. E2E 테스트로 실제 사용 시나리오 검증.

---

**Last Updated**: 2026-02-02
**Version**: 1.0.0
**Branch**: refactor/fundamental-redesign
**Status**: Production-Ready ✅

**Made with ❤️ by AIDX Team**
