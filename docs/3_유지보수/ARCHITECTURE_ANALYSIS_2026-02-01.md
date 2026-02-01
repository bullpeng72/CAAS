# CAAS 프로젝트 아키텍처 분석 리포트

**날짜:** 2026-02-01
**목적:** app/ vs caas_framework/ 역할 분리 분석
**상태:** 🔴 심각한 아키텍처 위반 발견

---

## 🎯 아키텍처 원칙 (목표)

사용자가 제시한 올바른 아키텍처:

```
✅ 핵심 기능은 모두 framework에 있어야 함
✅ 프레임워크와 UI는 독립적이어야 함
✅ Framework는 독립적으로 배포 가능해야 함
```

### 올바른 구조

```
caas_framework/          ← 모든 핵심 비즈니스 로직
├── models/              ← 데이터 모델 (전체)
├── bmad/                ← BMAD 엔진 (전체)
├── codegen/             ← 코드 생성 (전체)
├── validation/          ← 검증 로직 (전체)
├── llm/                 ← LLM 통합 (전체)
├── ontology/            ← 온톨로지 (전체)
└── ...                  ← 기타 핵심 기능

app/                     ← UI/CLI/응용 레이어만
├── cli/                 ← CLI 인터페이스
├── web/                 ← 웹 UI (있다면)
├── config/              ← 앱 설정
└── orchestration/       ← 워크플로우 오케스트레이션
```

---

## 🔴 현재 상태: 심각한 위반

### 1. Framework가 app/에 의존 (치명적)

**발견된 역방향 의존성:**

```python
# caas_framework/validation/golden_validator.py:28
from app.models.schemas import (  # ❌ WRONG!
    ConcretizedRequirement,
    RequirementAnalysis,
    ArchitectureDesign,
)

# caas_framework/codegen/llm_code_generator.py:14
from app.utils.logger import get_logger  # ❌ WRONG!
```

**문제점:**
- ❌ Framework를 독립적으로 사용 불가
- ❌ 순환 의존성 위험
- ❌ Framework를 라이브러리로 배포 불가

### 2. 핵심 비즈니스 로직이 app/에 위치

| 모듈 | 현재 위치 | 올바른 위치 | LOC | 영향도 |
|------|----------|------------|-----|--------|
| **Models** | app/models/ | caas_framework/models/ | 891 | 🔴 Critical |
| **BMAD Engine** | app/core/bmad/ | caas_framework/bmad/ | 3000+ | 🔴 Critical |
| **LLM Chains** | app/llm/ | caas_framework/llm/ | 1488 | 🔴 Critical |
| **SDD Engine** | app/core/sdd/ | caas_framework/sdd/ | 1200+ | 🔴 Critical |
| **Factory** | app/core/factory/ | caas_framework/factory/ | 1500+ | 🔴 Critical |
| **Fixing** | app/core/fixing/ | caas_framework/fixing/ | 150+ | 🟡 High |
| **Validation** | app/core/validation/ | caas_framework/validation/ | 600+ | 🟡 High |
| **Ontology** | app/core/ontology/ | caas_framework/ontology/ | 500+ | 🟡 High |

**총 이동 필요:** ~9,329 LOC

---

## 📊 상세 모듈 분석

### 1. Models (🔴 Critical - 891 LOC)

**현재:**
- `app/models/schemas.py` (891 LOC) - 모든 데이터 모델
- `caas_framework/models/specifications.py` - 일부 모델만 중복

**문제:**
```python
# Framework가 app에서 import
from app.models.schemas import AgentSpecModel  # ❌
```

**해결:**
```python
# 1. app/models/ → caas_framework/models/ 완전 이동
# 2. app/에서는 framework import
from caas_framework.models import AgentSpecModel  # ✅
```

**우선순위:** 🔴 최우선 (다른 모든 모듈이 의존)

---

### 2. BMAD Engine (🔴 Critical - 3000+ LOC)

**현재 상태:**
```
app/core/bmad/              3000+ LOC (완전한 구현)
├── engine.py               1796 LOC - 메인 엔진 (Phase 1 리팩토링 완료)
├── bmad_context.py         - Context 관리
├── document_sharder.py     - 문서 샤딩
├── reflection_engine.py    - Reflection 루프
├── personality_engine.py   - Personality 관리
├── adaptive_engine.py      - Scale-adaptive
└── ...

caas_framework/bmad/        400 LOC (단순 래퍼)
└── engine.py               - GoldenData 통합만
```

**문제:**
- 핵심 BMAD 구현이 app/에 있음
- Framework 버전은 단순 래퍼
- P2.2에서 이것을 통합하려 했으나 복잡도로 보류

**해결 전략:**
```
1. app/core/bmad/ 전체를 caas_framework/bmad/core/로 이동
2. GoldenData 통합 유지
3. app/core/bmad/는 re-export wrapper로 변경
```

**우선순위:** 🔴 최우선 (Phase 2의 핵심)

---

### 3. Code Generation (🟡 High - 각각 3K LOC)

**현재 중복:**
```
app/codegen/                16 files, ~3K LOC
├── generator.py            557 LOC - Jinja2 기반
├── multi_generator.py      2204 LOC - 전체 오케스트레이터
├── ast_generator.py        480 LOC - AST 기반
├── backend_generator.py    257 LOC
├── ui_generator.py         224 LOC
└── ...

caas_framework/codegen/     17 files, ~3K LOC
├── ast_code_generator.py   683 LOC - AST 기반 (중복)
├── engine.py               - 메인 엔진
├── production_generator.py
└── ...
```

**문제:**
- 60% 기능 중복
- 역할이 불명확

**해결 전략 (P2.3):**
```
1. app/codegen/ 통합을 caas_framework/codegen/으로
2. app/codegen/는 UI 특화 오케스트레이터만 유지
3. 핵심 생성 로직은 framework로
```

**우선순위:** 🟡 High (P2.3 작업)

---

### 4. LLM Chains (🔴 Critical - 1488 LOC)

**현재:**
```
app/llm/chains.py           1488 LOC
├── RequirementConcretizationChain
├── RequirementAnalysisChain
├── SystemArchitectChain
├── AgentDesignChain
├── TaskDesignChain
└── SpecGenerationChain
```

**문제:**
- LLM 통합은 핵심 기능인데 app/에 위치
- Framework에서 사용할 수 없음

**해결:**
```
app/llm/chains.py → caas_framework/llm/chains.py
```

**우선순위:** 🔴 최우선

---

### 5. SDD Engine (🔴 Critical - 1200+ LOC)

**현재:**
```
app/core/sdd/
├── engine.py               - SDD 메인 엔진
└── ...
```

**문제:**
- Software Design Document 생성은 핵심 기능
- Framework에 없음

**해결:**
```
app/core/sdd/ → caas_framework/sdd/
```

**우선순위:** 🔴 최우선

---

### 6. Factory Pattern (🔴 Critical - 1500+ LOC)

**현재:**
```
app/core/factory/
├── agent_factory.py
├── task_factory.py
├── crew_assembler.py
└── ...
```

**문제:**
- Agent/Task 생성은 핵심 기능
- 코드 생성에 필수

**해결:**
```
app/core/factory/ → caas_framework/factory/
```

**우선순위:** 🔴 최우선

---

### 7. Validation (🟡 High - 600 LOC)

**현재 분산:**
```
app/core/validation/        600 LOC
├── discovery_validator.py
├── architecture_validator.py
└── design_validator.py

caas_framework/validation/
├── golden_validator.py     - Golden Data 검증
└── ...
```

**역할 재정의:**
- Framework: 스펙 검증 로직 (모든 validator)
- App: Phase orchestration

**해결:**
```
app/core/validation/ → caas_framework/validation/phases/
```

**우선순위:** 🟡 High

---

### 8. Ontology (🟡 High - 500 LOC)

**현재 분산:**
```
app/core/ontology/          Tool 중심
├── tool_ontology.py
└── tool_manager.py

caas_framework/ontology/    Domain 중심
├── domain_ontology.py
├── api_ontology.py
└── ecommerce_ontology.py
```

**해결:**
```
app/core/ontology/ → caas_framework/ontology/tools/
```

**우선순위:** 🟡 High

---

### 9. Fixing Module (🟡 Medium - 150 LOC)

**현재:**
```
app/core/fixing/            150 LOC - 기본 구현
caas_framework/fixing/      1200 LOC - 3-level 시스템
```

**해결:**
```
app/core/fixing/ 제거, framework 버전 사용
```

**우선순위:** 🟢 Medium

---

## 🎯 올바른 아키텍처로 재구성

### Framework (caas_framework/)

**역할:** 독립적으로 실행 가능한 핵심 라이브러리

```
caas_framework/
├── models/                 ← FROM app/models/
│   ├── schemas.py          (모든 데이터 모델)
│   ├── specifications.py
│   └── validation.py
│
├── bmad/                   ← FROM app/core/bmad/
│   ├── core/
│   │   ├── engine.py       (메인 BMAD 엔진)
│   │   ├── context.py
│   │   ├── document_sharder.py
│   │   ├── reflection_engine.py
│   │   └── ...
│   └── golden_data.py      (Golden Data 통합)
│
├── llm/                    ← FROM app/llm/
│   ├── chains.py           (모든 LLM chains)
│   ├── plugin.py
│   └── providers/
│
├── codegen/                ← Consolidated
│   ├── engine.py
│   ├── ast_generator.py
│   ├── generators/
│   └── ...
│
├── sdd/                    ← FROM app/core/sdd/
│   └── engine.py
│
├── factory/                ← FROM app/core/factory/
│   ├── agent_factory.py
│   ├── task_factory.py
│   └── crew_assembler.py
│
├── validation/             ← FROM app/core/validation/
│   ├── golden_validator.py
│   ├── phases/
│   │   ├── discovery_validator.py
│   │   ├── architecture_validator.py
│   │   └── design_validator.py
│   └── ...
│
├── ontology/               ← FROM app/core/ontology/
│   ├── domain_ontology.py
│   ├── tools/
│   │   ├── tool_ontology.py
│   │   └── tool_manager.py
│   └── ...
│
├── fixing/                 ← Keep framework version
├── testing/
├── automation/
├── security/
└── utils/                  ← All utilities
```

### Application (app/)

**역할:** UI, CLI, Workflow 오케스트레이션

```
app/
├── cli/                    ← CLI 인터페이스
│   ├── commands/
│   └── ...
│
├── web/                    ← 웹 UI (만약 있다면)
│   ├── routes/
│   ├── templates/
│   └── ...
│
├── workflow/               ← 워크플로우 오케스트레이션
│   ├── orchestrator.py     (Framework 함수 호출)
│   └── langgraph_engine.py
│
├── artifacts/              ← 출력 아티팩트 관리
│   ├── generator.py        (Framework 사용)
│   └── ...
│
├── monitoring/             ← 앱 레벨 모니터링
│   ├── dashboard.py
│   └── ...
│
├── config/                 ← 앱 설정
│   └── settings.py
│
└── utils/                  ← 앱 전용 유틸리티
    └── ...
```

---

## 🚀 마이그레이션 로드맵

### Phase 1: Critical Dependencies (Week 1)

**목표:** Framework 독립성 확보

**Tasks:**
1. ✅ **app/models/ → caas_framework/models/** (891 LOC)
   - 모든 import 경로 수정
   - Framework 역방향 의존성 제거

2. ✅ **app/llm/ → caas_framework/llm/** (1488 LOC)
   - LLM chains 이동
   - Prompts 모듈 통합

3. ✅ **Framework의 app/ import 제거**
   - golden_validator.py 수정
   - llm_code_generator.py 수정
   - 모든 역방향 의존성 제거

**예상 절감:** ~2,379 LOC 이동
**검증:** `grep -r "^from app\." caas_framework/` → 0 results

---

### Phase 2: Core Engines (Week 2-3)

**목표:** 핵심 엔진 통합

**Tasks:**
1. ✅ **app/core/bmad/ → caas_framework/bmad/** (3000+ LOC)
   - P2.2 완료
   - 모든 BMAD 기능 통합

2. ✅ **app/core/sdd/ → caas_framework/sdd/** (1200+ LOC)
   - SDD 엔진 이동

3. ✅ **app/core/factory/ → caas_framework/factory/** (1500+ LOC)
   - Factory pattern 이동

**예상 절감:** ~5,700 LOC 이동

---

### Phase 3: Supporting Modules (Week 4)

**목표:** 지원 모듈 통합

**Tasks:**
1. ✅ **app/core/validation/ → caas_framework/validation/** (600 LOC)
2. ✅ **app/core/ontology/ → caas_framework/ontology/** (500 LOC)
3. ✅ **app/codegen/ 통합** (P2.3 완료)
4. ✅ **app/core/fixing/ 제거** (150 LOC)

**예상 절감:** ~1,250 LOC 이동/제거

---

### Phase 4: Cleanup (Week 5)

**목표:** 정리 및 검증

**Tasks:**
1. ✅ app/core/ 폴더 제거 또는 최소화
2. ✅ Import 경로 정리
3. ✅ 문서 업데이트
4. ✅ 테스트 검증
5. ✅ Framework 독립 배포 테스트

---

## 📏 영향 분석

### Before (현재)

```
caas_framework/: 51,802 LOC
├── Core logic: ~25K LOC (50%)
├── UI logic: ~15K LOC (30%)
└── Duplication: ~11K LOC (20%)

app/: 48,403 LOC
├── Core logic: ~16K LOC (33%) ← WRONG!
├── UI logic: ~20K LOC (42%)
└── Duplication: ~12K LOC (25%)
```

**문제:**
- ❌ Framework에 UI 로직 30%
- ❌ App에 Core 로직 33%
- ❌ 중복 20-25%

### After (목표)

```
caas_framework/: ~55K LOC
├── Core logic: ~55K LOC (100%) ✅
└── No UI logic

app/: ~25K LOC
├── UI/CLI: ~20K LOC (80%)
├── Orchestration: ~5K LOC (20%)
└── No core logic ✅
```

**개선:**
- ✅ Framework 100% core
- ✅ App 100% UI/orchestration
- ✅ 명확한 분리
- ✅ 중복 최소화 (<5%)

---

## 🎯 성공 기준

### 1. 의존성 방향 검증

```bash
# Framework는 app/에 의존하지 않음
grep -r "^from app\." caas_framework/
# Expected: No results

# App은 framework만 import
grep -r "^from caas_framework\." app/
# Expected: All imports valid
```

### 2. Framework 독립성 테스트

```python
# Framework만으로 실행 가능
from caas_framework.bmad import BMADEngine
from caas_framework.models import ConcretizedRequirement

engine = BMADEngine(llm_plugin=plugin)
result = await engine.run(requirement="...")
# Should work without any app/ imports
```

### 3. 중복 코드 제거

```bash
# Before: ~23K LOC 중복
# After: <5K LOC 중복
# Target: 78%+ reduction
```

---

## 💡 핵심 권장사항

### 즉시 조치 (Critical)

1. **Phase 1 시작: Models 이동**
   ```bash
   # 1. app/models/ → caas_framework/models/
   # 2. 모든 import 경로 수정
   # 3. Framework의 역방향 의존성 제거
   ```

2. **역방향 의존성 즉시 제거**
   ```python
   # caas_framework/validation/golden_validator.py
   - from app.models.schemas import ...
   + from caas_framework.models.schemas import ...
   ```

### 중기 조치 (High Priority)

3. **BMAD Engine 통합 (P2.2)**
   - app/core/bmad/ → caas_framework/bmad/
   - 가장 큰 영향 (~3K LOC)

4. **LLM Chains 이동**
   - app/llm/ → caas_framework/llm/
   - Framework 핵심 기능

### 장기 조치 (Medium Priority)

5. **Code Generation 통합 (P2.3)**
   - 중복 제거
   - Framework 중심으로 통합

6. **app/core/ 최소화**
   - 모든 core 로직 framework로
   - app/core/는 deprecate

---

## 🏁 결론

**현재 아키텍처는 사용자 요구사항을 위반하고 있습니다:**

| 요구사항 | 현재 상태 | 평가 |
|---------|----------|------|
| 핵심 기능은 모두 framework에 | app/에 ~16K LOC core 로직 | ❌ 실패 |
| Framework와 UI 독립적 | Framework가 app/ import | ❌ 실패 |
| Framework 독립 배포 가능 | app/ 의존성으로 불가 | ❌ 실패 |

**제안:**
1. Phase 1-4 마이그레이션 로드맵 실행
2. Models → LLM → BMAD → SDD → Factory 순서로 이동
3. 5주 완료 목표
4. ~9,300 LOC 재구성

이 리팩토링이 완료되면:
- ✅ Framework 독립 실행 가능
- ✅ 명확한 책임 분리
- ✅ 중복 78% 감소
- ✅ 유지보수성 대폭 향상

---

**작성자:** Architecture Analysis Team
**날짜:** 2026-02-01
**다음 액션:** Phase 1 (Models + LLM Migration) 시작 승인 대기
