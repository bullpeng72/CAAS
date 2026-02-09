# 요구사항 정제 및 TDD 통합 가이드

**CAAS Requirement Refinement & TDD Integration**

이 가이드는 CAAS의 요구사항 정제 및 TDD 통합 기능을 설명합니다.

**최종 업데이트**: 2026-02-06
**CAAS 버전**: v0.4.1
**상태**: Production Ready ✅

---

## 📋 목차

- [개요](#개요)
- [Step 1: 요구사항 정제](#step-1-요구사항-정제)
- [Step 2: 추적성 강화](#step-2-추적성-강화)
- [Step 3: TDD 통합](#step-3-tdd-통합)
- [CLI를 이용한 통합 워크플로우](#cli를-이용한-통합-워크플로우)
- [API 레퍼런스](#api-레퍼런스)

---

## 개요

### 문제 정의

기존 CAAS는 "완전한 요구사항"을 기대했지만, 실제 사용자는 **짧고 불충분한 요구사항**을 제공하는 경우가 많습니다.

**Before (기존)**:
```
User: "할일 관리 앱 만들어줘"
CAAS: → 기본적인 CRUD만 생성 (많은 기능 누락)
```

**After (개선)**:
```
User: "할일 관리 앱 만들어줘"
CAAS: → Gap Analysis (갭 분석)
      → Interactive Questions (대화형 질문)
      → Auto-Expansion (자동 확장)
      → Traceability Matrix (추적성)
      → TDD (테스트 우선 개발)
      → 완전하고 검증된 코드 생성
```

### 주요 기능

| 기능 | 설명 | 모듈 | 상태 |
|------|------|------|------|
| **Gap Analysis** | 누락된 요구사항 자동 탐지 | `caas_framework.refinement.gap_analyzer` | ✅ |
| **Auto-Expansion** | 자동 요구사항 확장 | `caas_framework.refinement.expander` | ✅ |
| **Interactive Questions** | 사용자 대화형 질문 생성 | `caas_framework.refinement.question_generator` | ✅ |
| **Traceability Matrix** | 요구사항-코드 추적 | `caas_framework.validation.traceability` | ✅ |
| **Test Scenario Generation** | BDD 테스트 시나리오 생성 | `caas_framework.testing.test_scenario` | ✅ |
| **Test-First Code Gen** | Pytest 테스트 코드 생성 | `caas_framework.testing.bdd_test_generator` | ✅ |
| **Test Execution** | 테스트 자동 실행 및 분석 | `caas_framework.testing.test_executor` | ✅ |
| **TDD Orchestrator** | TDD 워크플로우 통합 관리 | `caas_framework.testing.tdd_orchestrator` | ✅ |

---

## Step 1: 요구사항 정제

### 1.1 Gap Analysis (갭 분석)

**목적**: 누락되거나 불충분한 요구사항 항목을 자동으로 탐지합니다.

#### 탐지되는 갭 타입
- `MISSING_NFR`: 비기능 요구사항 (성능, 보안, 확장성 등) 누락
- `MISSING_DATA_MODEL`: 데이터 모델 미정의
- `MISSING_UI_SPEC`: UI 명세 부족
- `MISSING_ACCEPTANCE`: 인수 기준 부재
- `MISSING_SECURITY`: 보안 요구사항 누락
- `MISSING_ERROR_HANDLING`: 에러 처리 미정의

### 1.2 Auto-Expansion (자동 확장)

**목적**: 분석된 갭 중 자동 수정 가능한 항목을 LLM 또는 휴리스틱으로 채웁니다. 예를 들어, 기능 명세로부터 데이터 모델을 추론하거나, 도메인에 맞는 표준 비기능 요구사항을 추가합니다.

### 1.3 Interactive Questions (인터랙티브 질문)

**목적**: 시스템이 스스로 해결할 수 없는 갭에 대해, 사용자에게 명확한 선택지나 정보를 요구하는 질문을 생성합니다.

---

## Step 2: 추적성 강화

### Traceability Matrix (추적성 매트릭스)
**목적**: `요구사항 → 기능 → 에이전트 → 태스크 → 코드`로 이어지는 전체 개발 과정을 추적할 수 있는 매트릭스를 구축하여, 모든 요구사항이 최종 코드에 반영되었는지 검증합니다.

---

## Step 3: TDD 통합

### Test Scenario & Code Generation
**목적**: BDD(행위 주도 개발) 스타일의 테스트 시나리오를 먼저 생성하고, 이를 바탕으로 `pytest` 테스트 코드를 자동으로 생성하여 테스트 우선 개발을 지원합니다.

---

## CLI를 이용한 통합 워크플로우

이러한 정제 기능들은 **28개 CLI 명령어** 중 일부를 통해 유기적으로 사용할 수 있습니다.

### 관련 CLI 명령어

| 명령어 | 파일 | 설명 |
|--------|------|------|
| `caas analyze-gaps` | `caas_cli/commands/analyze_gaps.py` | 요구사항 갭 분석 |
| `caas questions` | `caas_cli/commands/interactive_questions.py` | 대화형 질문 생성 |
| `caas expand` | `caas_cli/commands/expand_requirement.py` | 요구사항 자동 확장 |
| `caas traceability` | `caas_cli/commands/traceability.py` | 추적성 매트릭스 생성 |
| `caas validate` | `caas_cli/commands/validate.py` | 설계 검증 |

### 예제: "할일 앱" 요구사항 구체화하기

#### 1. 갭 분석 (`analyze-gaps`)
모호한 초기 요구사항("할일 앱 만들어줘")에서 어떤 점이 부족한지 분석합니다.

```bash
caas analyze-gaps "할일 앱 만들어줘" --output gaps.json
```
- **결과**: `gaps.json` 파일에 "데이터 모델 누락", "비기능 요구사항 부재" 등의 갭이 리포트됩니다.

#### 2. 대화형 질문 (`questions`)
분석된 갭을 해결하기 위해 시스템이 사용자에게 질문합니다.

```bash
caas questions --gaps gaps.json --domain TASK_MANAGEMENT
```
- **실행 결과**:
  ```
  Q: 데이터베이스는 어떤 것을 사용하시겠습니까? (a) SQLite (b) PostgreSQL (c) MySQL
  > b
  Q: 사용자 인증 기능이 필요한가요? (y/n)
  > y
  ```
- **결과**: 사용자의 답변은 다음 단계를 위해 세션에 저장됩니다.

#### 3. 요구사항 확장 (`expand`)
사용자 답변을 바탕으로 초기 요구사항을 구체화하고 확장합니다.

```bash
caas expand "할일 앱 만들어줘" \
  --gaps gaps.json \
  --golden-data initial_golden_data.json \
  --output expanded_golden_data.json
```
- `initial_golden_data.json`: `caas generate` 초기 실행 시 `artifacts` 폴더에 생성된 파일
- `expanded_golden_data.json`: 사용자 인증, PostgreSQL DB 사용 등의 내용이 추가된 새로운 요구사항 명세
- **결과**: 훨씬 구체적이고 완전한 `expanded_golden_data.json` 파일이 생성됩니다.

이 확장된 `golden_data`를 `caas generate --golden-data expanded_golden_data.json` 명령의 입력으로 사용하면, 훨씬 완성도 높은 코드를 생성할 수 있습니다.

---

## API 레퍼런스

각 기능은 `caas_framework` 내의 모듈을 통해 프로그래밍 방식으로도 사용할 수 있습니다.

### 1. Gap Analysis (갭 분석)

```python
from caas_framework.refinement import (
    RequirementGapAnalyzer,
    GapType,
    GapAnalysisResult
)

# Analyzer 초기화
analyzer = RequirementGapAnalyzer(llm_plugin=llm)

# 요구사항 갭 분석
gap_result: GapAnalysisResult = await analyzer.analyze_gaps(
    requirement="할일 관리 앱 만들기",
    domain_hint="TASK_MANAGEMENT"
)

# 분석된 갭 출력
for gap in gap_result.gaps:
    print(f"Gap Type: {gap.gap_type}")
    print(f"Description: {gap.description}")
    print(f"Severity: {gap.severity}")
```

### 2. Auto-Expansion (자동 확장)

```python
from caas_framework.refinement import (
    RequirementExpander,
    ExpandedRequirement
)

# Expander 초기화
expander = RequirementExpander(llm_plugin=llm)

# 요구사항 자동 확장
expanded: ExpandedRequirement = await expander.expand_requirement(
    requirement="할일 관리 앱",
    gap_analysis_result=gap_result,
    user_answers={"database": "PostgreSQL", "auth": True}
)

print(f"Expanded Requirement: {expanded.enhanced_requirement}")
print(f"Added Features: {len(expanded.added_features)}")
```

### 3. Interactive Questions (대화형 질문)

```python
from caas_framework.refinement import (
    InteractiveQuestionGenerator,
    QuestionType,
    QuestionnaireResult
)

# Question Generator 초기화
question_gen = InteractiveQuestionGenerator(llm_plugin=llm)

# 질문 생성
questions = await question_gen.generate_questions(
    gap_analysis_result=gap_result,
    requirement="할일 관리 앱",
    domain_hint="TASK_MANAGEMENT"
)

# 질문 표시 및 답변 수집
for question in questions:
    print(f"Q: {question.question_text}")
    print(f"Options: {question.options}")
    # user_answer = input("> ")
```

### 4. Traceability Matrix (추적성)

```python
from caas_framework.validation.traceability import (
    TraceabilityManager,
    TraceabilityReport
)

# Traceability Manager 초기화
trace_manager = TraceabilityManager()

# 워크플로우로부터 추적성 구축
trace_manager.build_from_workflow(
    golden_data=golden_data,
    agents=agents,
    tasks=tasks,
    code_files=code_files
)

# 추적성 리포트 생성
report: TraceabilityReport = trace_manager.generate_report()
print(f"Coverage: {report.coverage_percentage}%")
```

### 5. TDD Workflow (테스트 주도 개발)

```python
from caas_framework.testing import (
    TestScenarioGenerator,
    TestFirstGenerator,
    TestExecutor,
    TDDOrchestrator
)

# 1. Test Scenario 생성
scenario_gen = TestScenarioGenerator(llm_plugin=llm)
scenarios = await scenario_gen.generate_scenarios(
    golden_data=golden_data,
    agents=agents,
    tasks=tasks
)

# 2. Test Code 생성
test_gen = TestFirstGenerator(llm_plugin=llm)
test_code = await test_gen.generate_test_code(
    scenarios=scenarios,
    framework="pytest"
)

# 3. Test 실행
executor = TestExecutor()
test_result = await executor.execute_tests(
    test_code_path="./tests/test_generated.py"
)

print(f"Tests Passed: {test_result.passed}/{test_result.total}")
print(f"Coverage: {test_result.coverage}%")

# 또는 TDD Orchestrator로 통합 실행
orchestrator = TDDOrchestrator(llm_plugin=llm)
tdd_result = await orchestrator.run_tdd_cycle(
    golden_data=golden_data,
    agents=agents,
    tasks=tasks
)
```

---

## 참고 자료

### CAAS 핵심 파일

**Refinement Module** (`caas_framework/refinement/`):
- `gap_analyzer.py` (27.6 KB) - 요구사항 갭 분석
- `expander.py` (15.3 KB) - 자동 요구사항 확장
- `question_generator.py` (21.5 KB) - 대화형 질문 생성

**Testing Module** (`caas_framework/testing/`):
- `test_scenario.py` (7.5 KB) - BDD 테스트 시나리오 생성
- `bdd_test_generator.py` (4.7 KB) - Pytest 코드 생성
- `test_executor.py` (7.0 KB) - 테스트 실행 및 분석
- `tdd_orchestrator.py` (15.4 KB) - TDD 워크플로우 통합

**Validation Module** (`caas_framework/validation/`):
- `traceability.py` - 추적성 매트릭스 관리

**CLI Commands** (`caas_cli/commands/`):
- `analyze_gaps.py` (7.9 KB)
- `expand_requirement.py` (9.8 KB)
- `interactive_questions.py` (11.9 KB)
- `traceability.py`

### CAAS 문서

- [01_README_KO.md](01_README_KO.md) - 프로젝트 개요
- [03_Quick_Start_Guide.md](03_Quick_Start_Guide.md) - 빠른 시작 가이드
- [04_CLI_Usage_Guide.md](04_CLI_Usage_Guide.md) - CLI 사용 가이드 (29 commands)
- [05_Expert_Methodology_Guide.md](05_Expert_Methodology_Guide.md) - CAAS 6-Phase 방법론 및 실전 예제
- [06_Architecture_Guide.md](06_Architecture_Guide.md) - 아키텍처 가이드
- [CLAUDE.md](../CLAUDE.md) - 프로젝트 컨텍스트

### 외부 문서

- [Pytest Documentation](https://docs.pytest.org/)
- [BDD with Pytest](https://pytest-bdd.readthedocs.io/)

---

**최종 업데이트**: 2026-02-06
**CAAS 버전**: v0.4.1
**문서 버전**: 1.1.0
**상태**: Production Ready ✅

**Made with ❤️ by bullpeng72**
