# API 레퍼런스

## 🎯 이 문서에서 배울 것
- [ ] Python API 완전 레퍼런스
- [ ] CLI 명령어 상세 사용법
- [ ] 환경 변수 및 설정
- [ ] 플러그인 API

⏱️ **예상 시간**: 참고용 (필요 시 검색)

---

## 1. Python API

### 1.1 CrewAIFramework 클래스

```python
from caas_framework.framework import CrewAIFramework
```

#### 초기화

```python
framework = CrewAIFramework(
    llm_provider: str = "openai",  # "openai", "anthropic", "ollama"
    llm_model: str = "gpt-4",  # 모델 ID
    graph_db: str = "embedded",  # "embedded", "neo4j"
    enable_quality_gates: bool = True,
    enable_distributed: bool = True,
    logger: Optional[logging.Logger] = None
)
```

**파라미터**:
- `llm_provider`: LLM 공급자 ("openai", "anthropic", "ollama")
- `llm_model`: 모델 ID (예: "gpt-4", "claude-3-5-sonnet-20241022")
- `graph_db`: Graph DB 타입 ("embedded", "neo4j")
- `enable_quality_gates`: Quality Gate 활성화 여부
- `enable_distributed`: 병렬 처리 활성화 여부
- `logger`: 커스텀 로거 (선택)

#### 메서드

**initialize()**
```python
await framework.initialize()
```
- 프레임워크 초기화 (LLM, Graph DB 연결)
- 비동기 메서드
- 반환: `None`

**generate_from_requirement()**
```python
result = await framework.generate_from_requirement(
    requirement: str,
    output_dir: Path,
    domain: Optional[str] = None,
    ui: str = "none",
    strict_quality_gates: bool = True
) -> GenerationResult
```
- 요구사항 → 코드 생성 (전체 워크플로우)
- **파라미터**:
  - `requirement`: 자연어 요구사항
  - `output_dir`: 출력 디렉토리
  - `domain`: 도메인 (자동 감지 시 `None`)
  - `ui`: UI 타입 ("none", "streamlit", "gradio")
  - `strict_quality_gates`: 엄격한 Quality Gate 여부
- **반환**: `GenerationResult`
  ```python
  @dataclass
  class GenerationResult:
      success: bool
      output_dir: Path
      files: Dict[str, str]  # 파일명: 경로
      code_quality: float
      test_coverage: float
      error: Optional[str] = None
  ```

**analyze_requirement()**
```python
result = await framework.analyze_requirement(
    requirement: str
) -> RequirementAnalysisResult
```
- Phase 1: 요구사항 분석만 실행
- **반환**: `RequirementAnalysisResult`

**validate_design()**
```python
result = await framework.validate_design(
    golden_data: Dict,
    architecture: Dict,
    agents: List[Dict],
    tasks: List[Dict]
) -> ValidationResult
```
- Phase 2-3 산출물 검증

**generate_code()**
```python
result = await framework.generate_code(
    agents: List[AgentSpecModel],
    tasks: List[TaskSpecModel],
    output_dir: Path
) -> Dict[str, str]
```
- Phase 5: 코드 생성만 실행

---

### 1.2 SixPhaseEngine 클래스

```python
from caas_framework.methodology.engine import SixPhaseEngine
```

#### 메서드

**execute_phase()**
```python
result = await engine.execute_phase(
    phase: Phase,
    inputs: Dict[str, Any]
) -> PhaseResult
```
- 특정 Phase만 실행

**execute_full_workflow()**
```python
result = await engine.execute_full_workflow(
    requirement: str
) -> WorkflowResult
```
- Phase 0-5 전체 실행

---

### 1.3 ExpertAgentCollaboration 클래스

```python
from caas_framework.agents.collaboration import ExpertAgentCollaboration
```

#### 초기화

```python
collaboration = ExpertAgentCollaboration(
    llm_plugin: LLMPlugin,
    golden_data: Dict,
    enable_quality_gates: bool = True,
    strict_quality_gates: bool = True,  # v0.4.1+
    enable_distributed: bool = True
)
```

#### 메서드

**execute_full_workflow()**
```python
result = await collaboration.execute_full_workflow(
    requirement: str
) -> CollaborationResult
```

**execute_phase_with_feedback()**
```python
result = await collaboration.execute_phase_with_feedback(
    agent: BaseExpertAgent,
    context: CollaborationContext,
    max_iterations: int = 3
) -> AgentWorkResult
```

---

### 1.4 ValidationOrchestrator 클래스

```python
from caas_framework.validation.orchestrator import ValidationOrchestrator
```

#### 메서드

**validate_all()**
```python
result = validator.validate_all(
    agents: List[Dict],
    tasks: List[Dict],
    golden_data: Dict,
    code_artifacts: Dict[str, str]
) -> ValidationReport
```

**validate_single()**
```python
result = validator.validate_single(
    validator_name: str,  # "code-quality", "crewai", "dependency", ...
    **kwargs
) -> ValidatorResult
```

---

## 2. CLI 명령어 레퍼런스

### 2.1 프로젝트 생성

**caas generate**
```bash
caas generate <REQUIREMENT> [OPTIONS]
```

**필수 인자**:
- `REQUIREMENT`: 자연어 요구사항

**옵션**:
```bash
--output PATH          # 출력 디렉토리 (기본: ./generated)
--domain DOMAIN        # 도메인 명시 (기본: 자동 감지)
--ui {none,streamlit,gradio}  # UI 타입 (기본: none)
--model {gpt-4,gpt-3.5-turbo,claude-3-5-sonnet,haiku,opus}
--distributed          # 분산 병렬 실행 활성화
--workers INT          # Worker 수 (기본: 4)
--cache / --no-cache   # LLM 캐싱 (기본: true)
--streaming            # 대규모 프로젝트 스트리밍 모드
```

**예시**:
```bash
# 기본 생성
caas generate "할일 관리 시스템"

# 도메인 지정 + UI 포함
caas generate "챗봇" --domain conversational_ai --ui streamlit

# 분산 병렬 처리 + 커스텀 모델
caas generate "데이터 분석" --distributed --model haiku --output ./analytics
```

---

### 2.2 Phase별 생성

**caas generate-phase**
```bash
caas generate-phase --phase <PHASE_NUM> <REQUIREMENT> [OPTIONS]
```

**필수 인자**:
- `--phase {0,1,2,3,4,5}`: Phase 번호

**옵션**:
```bash
--output PATH          # 출력 디렉토리
--force                # 기존 파일 덮어쓰기
--golden-data PATH     # Golden Data 파일 경로 (Phase 1+)
```

**예시**:
```bash
# Phase 2만 실행 (Architecture)
caas generate-phase --phase 2 "할일 관리" --output ./todo

# Phase 5 재생성 (코드만)
caas generate-phase --phase 5 "할일 관리" --output ./todo --force
```

---

### 2.3 검증 (Validation)

**caas validate**
```bash
caas validate --validator <VALIDATOR> [OPTIONS]
```

**Validator 종류**:
- `all`: 모든 검증 실행
- `ontology`: Agent/Task 온톨로지 구조 검증
- `golden`: Golden Data 완전성 검증
- `dependency`: Task 의존성 검증
- `python311`: Python 3.11+ 호환성 검증
- `crewai`: CrewAI 프레임워크 준수 검증

**옵션**:
```bash
--project PATH         # 프로젝트 디렉토리
--agents PATH          # agents.json 경로
--tasks PATH           # tasks.json 경로
--golden-data PATH     # golden_data.json 경로
--output PATH          # 검증 리포트 JSON 파일 경로
--verbose, -v          # 상세 검증 출력
```

**예시**:
```bash
# 전체 검증
caas validate --validator all \
  --agents ./todo/agents.json \
  --tasks ./todo/tasks.json

# Golden Data 검증
caas validate --validator golden \
  --agents ./todo/agents.json \
  --tasks ./todo/tasks.json \
  --golden-data ./todo/golden_data.json

# Traceability 검증 (독립 명령어)
caas traceability \
  --golden-data ./todo/golden_data.json \
  --agents ./todo/agents.json \
  --tasks ./todo/tasks.json
```

---

### 2.4 자동 수정 (Fix)

**caas fix**
```bash
caas fix [OPTIONS]
```

**옵션**:
```bash
--level {1,2,3}        # 수정 레벨 (1: Template, 2: Rule, 3: LLM)
--project PATH         # 프로젝트 디렉토리
--agents PATH          # agents.json 경로
--tasks PATH           # tasks.json 경로
--security             # 보안 이슈만 수정
--code-quality         # 코드 품질만 수정
--apply                # 변경사항 적용 (기본: dry-run)
--backup               # 백업 생성
```

**예시**:
```bash
# Level 3 (LLM) 전체 수정
caas fix --level 3 --project ./todo --apply --backup

# 보안 이슈만 자동 수정
caas fix --level 3 --security --project ./todo --apply
```

---

### 2.5 TDD 자동화

**caas tdd generate-tests**
```bash
caas tdd generate-tests <GOLDEN_DATA_PATH> [OPTIONS]
```

**옵션**:
```bash
--output-dir PATH      # 테스트 출력 디렉토리 (기본: ./tests)
--test-framework TEXT  # 테스트 프레임워크 (기본: pytest)
```

**예시**:
```bash
caas tdd generate-tests ./golden_data.json --output-dir ./tests
```

**caas tdd analyze-code**
```bash
caas tdd analyze-code <PROJECT_DIR> [OPTIONS]
```

**옵션**:
```bash
--detailed             # 상세 분석 리포트
```

**예시**:
```bash
caas tdd analyze-code ./todo-system --detailed
```

**caas tdd workflow**
```bash
caas tdd workflow <PROJECT_DIR> <GOLDEN_DATA_PATH> [OPTIONS]
```

**설명**: 완전한 TDD 워크플로우 실행 (RED → GREEN → REFACTOR)

**예시**:
```bash
caas tdd workflow ./todo ./golden_data.json
```

---

### 2.6 QA 자동화

**caas qa security**
```bash
caas qa security [OPTIONS]
```

**옵션**:
```bash
--project PATH         # 프로젝트 디렉토리  [required]
--output PATH          # JSON 리포트 출력 경로
```

**예시**:
```bash
caas qa security --project ./todo --output security_report.json
```

**caas qa performance**
```bash
caas qa performance [OPTIONS]
```

**옵션**:
```bash
--project PATH         # 프로젝트 디렉토리  [required]
--output PATH          # JSON 리포트 출력 경로
```

**예시**:
```bash
caas qa performance --project ./todo --output perf_report.json
```

**caas qa compliance**
```bash
caas qa compliance [OPTIONS]
```

**옵션**:
```bash
--project PATH         # 프로젝트 디렉토리  [required]
--output PATH          # JSON 리포트 출력 경로
```

**예시**:
```bash
caas qa compliance --project ./todo --output compliance_report.json
```

**caas qa report**
```bash
caas qa report [OPTIONS]
```

**옵션**:
```bash
--project PATH         # 프로젝트 디렉토리  [required]
--output PATH          # HTML 또는 JSON 리포트 출력 경로
```

**설명**: 모든 QA 검사를 통합 실행 (보안, 성능, 컴플라이언스)

**예시**:
```bash
# 통합 리포트 생성
caas qa report --project ./todo --output qa_report.html
```

---

### 2.7 Checkpoint 관리

**CAAS-E Human Approval Checkpoint** (v0.6.2)

7개의 Human Checkpoint (CP-1 ~ CP-7)를 관리하는 PM 승인 워크플로우 명령어입니다.

**caas checkpoint list**
```bash
caas checkpoint list [OPTIONS]
```

**설명**: 7개 CAAS-E 체크포인트 목록 표시

**예시**:
```bash
caas checkpoint list
# 출력:
# CP-1: Phase 0 (Concretization) - Golden Data 검토
# CP-2: Phase 1 (Discovery) - 요구사항 분석 승인
# CP-3: Phase 2 (Architecture) - 아키텍처 설계 승인
# ...
```

**caas checkpoint approve**
```bash
caas checkpoint approve [OPTIONS]
```

**옵션**:
```bash
-p, --project TEXT        # 프로젝트 이름  [required]
-c, --checkpoint-id TEXT  # 체크포인트 ID (CP-1 ~ CP-7)  [required]
-r, --reviewer TEXT       # 검토자 이름  [required]
-m, --comment TEXT        # 검토 코멘트 (repeatable)
```

**예시**:
```bash
# CP-3 (Architecture) 승인
caas checkpoint approve \
  --project todo-system \
  --checkpoint-id CP-3 \
  --reviewer "김PM" \
  --comment "아키텍처 설계 검토 완료. 승인합니다."
```

**참고**:
- **Version Control Checkpoint** (save/restore/diff/export) 기능은 v0.7.0+에서 계획 중
- 현재는 Human Approval Checkpoint만 지원 (PM 승인 워크플로우)
- 자세한 내용: [52_Checkpoint_활용법.md](../5_엔터프라이즈_기능/52_Checkpoint_활용법.md)

---

### 2.8 설정 관리

**caas config**
```bash
caas config [OPTIONS]
```

**옵션**:
```bash
--set <KEY VALUE>...   # 설정 값 지정 (여러 번 사용 가능)
--get KEY              # 특정 설정 값 조회
--list                 # 모든 설정 목록 표시
--reset                # 설정 초기화
```

**예시**:
```bash
# 값 설정
caas config --set llm_provider ollama
caas config --set default_domain FINANCE
caas config --set enable_validation true

# 여러 값 동시 설정
caas config \
  --set llm_provider ollama \
  --set default_domain HEALTHCARE \
  --set enable_validation true

# 값 조회
caas config --get llm_provider
caas config --get default_domain

# 전체 설정 목록
caas config --list
# 또는
caas config  # (--list와 동일)

# 설정 초기화
caas config --reset
```

**사용 가능한 설정 키**:
- `api_url`: API 서버 URL
- `api_key`: API 인증 키
- `default_domain`: 기본 도메인
- `default_deployment`: 기본 배포 대상
- `output_dir`: 기본 출력 디렉토리
- `enable_validation`: 검증 기본 활성화
- `enable_auto_fix`: 자동 수정 기본 활성화
- `enable_tests`: 테스트 생성 기본 활성화

---

## 3. 환경 변수

### 3.1 LLM 설정

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."
export OPENAI_ORG_ID="org-..."  # 선택

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Ollama
export OLLAMA_API_BASE="http://localhost:11434/v1"
```

### 3.2 Graph DB 설정

```bash
# Neo4j
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="password"
```

### 3.3 기타

```bash
# 로깅 레벨
export CAAS_LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR

# 캐시 설정
export CAAS_CACHE_DIR="~/.caas/cache"
export CAAS_CACHE_TTL="604800"  # 7일 (초)

# 병렬 처리
export CAAS_MAX_WORKERS="4"
```

---

## 4. 플러그인 API

### 4.1 LLM Plugin 개발

```python
from caas_framework.plugins.llm.base import BaseLLMPlugin

class MyLLMPlugin(BaseLLMPlugin):
    """커스텀 LLM 플러그인"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.client = MyLLMClient(api_key)

    async def ainvoke(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """비동기 LLM 호출"""
        response = await self.client.chat(messages, **kwargs)
        return response.text

    def invoke(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """동기 LLM 호출"""
        import asyncio
        return asyncio.run(self.ainvoke(messages, **kwargs))
```

**등록**:
```python
from caas_framework.framework import CrewAIFramework

framework = CrewAIFramework(
    llm_provider="custom",
    llm_plugin_class=MyLLMPlugin,
    llm_plugin_kwargs={"api_key": "..."}
)
```

---

### 4.2 Graph DB Plugin 개발

```python
from caas_framework.plugins.graphdb.base import BaseGraphDBPlugin

class MyGraphDBPlugin(BaseGraphDBPlugin):
    """커스텀 Graph DB 플러그인"""

    async def connect(self):
        self.client = MyGraphDBClient(uri=self.uri, auth=self.auth)

    async def execute_query(self, query: str) -> List[Dict]:
        return await self.client.run(query)

    async def close(self):
        await self.client.close()
```

---

## 5. 설정 파일

### 5.1 .caas/config.json

```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 4000,
    "cache": true,
    "cache_ttl": 604800
  },
  "graph_db": {
    "type": "embedded",
    "uri": null,
    "user": null,
    "password": null
  },
  "quality_gates": {
    "enabled": true,
    "strict": true,
    "thresholds": {
      "code_quality": 8.5,
      "test_coverage": 80.0,
      "security_score": 9.0
    }
  },
  "performance": {
    "parallel": true,
    "max_workers": 4,
    "streaming": false,
    "chunk_size": 100,
    "aggressive_gc": false
  },
  "checkpoint": {
    "auto_save": false,
    "retention_days": 30,
    "max_checkpoints": 100
  }
}
```

---

## 6. 데이터 모델

### 6.1 GoldenData

```python
from pydantic import BaseModel

class GoldenData(BaseModel):
    domain: str
    features: List[Feature]
    entities: List[Entity]
    constraints: List[Constraint]
    business_rules: List[BusinessRule]
```

### 6.2 AgentSpecModel

```python
class AgentSpecModel(BaseModel):
    id: str
    role: str
    goal: str
    backstory: str
    tools: List[str]
    llm: Optional[str] = None
```

### 6.3 TaskSpecModel

```python
class TaskSpecModel(BaseModel):
    id: str
    description: str
    expected_output: str
    agent: str  # Agent ID
    context: List[str] = []  # Task IDs
    async_execution: bool = False
```

---

## 📚 관련 문서
- **[01_CAAS_소개_및_설치.md](../1_시작하기/01_CAAS_소개_및_설치.md)** - 설치 방법
- **[20_CLI_명령어_레퍼런스.md](../2_개발_실무_가이드/20_CLI_명령어_레퍼런스.md)** - CLI 상세 사용법
- **[CLAUDE.md](../../CLAUDE.md)** - 코딩 컨벤션

---

**작성일**: 2026-02-14
**버전**: v0.5.1 (Core) + v0.6.3 (CAAS-E)
**대상**: 시니어 개발자, SDK 사용자
**난이도**: ⭐⭐⭐ 고급 (참고용)
