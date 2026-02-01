# CAAS 프로젝트 리팩토링 마스터 플랜

**작성일:** 2026-02-01
**버전:** 1.0
**목표:** 코드 품질 개선, 중복 제거, 유지보수성 향상

---

## 📊 현황 분석 요약

### 발견된 문제점

| 카테고리 | 수량 | 영향도 | 예상 절감 |
|---------|------|--------|----------|
| **중복 코드** | 2,900+ 라인 | 🔴 Critical | 8-10% 코드베이스 |
| **Dead Code** | 165+ 라인 | 🟡 Medium | 40+ 파일 |
| **긴 함수 (>50 라인)** | 50개 | 🔴 Critical | 유지보수성 ↓↓ |
| **많은 파라미터 (>5개)** | 22개 함수 | 🟠 High | 가독성 ↓ |
| **깊은 중첩 (>3 레벨)** | 30+ 함수 | 🟠 High | 복잡도 ↑↑ |

### 핵심 문제 영역

```
코드 중복 분포:
├── Duplicate Validators: 200+ lines (2개 파일)
├── Duplicate Engines: 1,300+ lines (2개 파일)
├── Duplicate Generators: 1,000+ lines (22개 파일)
└── Duplicate Patterns: 400+ lines

품질 이슈:
├── execute_development(): 391 lines, 6 params, 6 nesting levels
├── _load_builtin_patterns(): 379 lines (hardcoded data)
├── _generate_readme(): 357 lines
└── generate_all_artifacts(): 15 parameters
```

---

## 🎯 리팩토링 목표

### 주요 목표

1. **코드 중복 제거:** 2,900+ 라인 → 0 (100% 제거)
2. **Dead Code 제거:** 165+ 라인 → 0 (100% 제거)
3. **함수 길이 정규화:** 50+ 긴 함수 → <50 라인
4. **파라미터 수 감소:** 22개 함수 → <5 파라미터
5. **복잡도 감소:** 깊은 중첩 30+ → <3 레벨

### 품질 지표 목표

| 지표 | 현재 | 목표 | 개선 |
|------|------|------|------|
| 코드 중복률 | 8-10% | <2% | -80% |
| 평균 함수 길이 | 45 lines | 25 lines | -44% |
| 평균 파라미터 수 | 3.5 | 2.5 | -29% |
| 순환 복잡도 | 8.5 | 5.0 | -41% |
| 테스트 커버리지 | 1% | 60% | +5900% |

---

## 📅 4단계 리팩토링 로드맵

### Phase 1: 긴급 수정 (1-2주) 🔴

**목표:** Critical 이슈 해결, 즉각적인 품질 개선

#### Task 1.1: execute_development() 분해 [CRITICAL]
- **파일:** `app/core/bmad/engine.py:830-1221`
- **현재:** 391 lines, 6 params, 6 nesting
- **목표:** <50 lines per method
- **작업:**
  ```python
  # Before: 391 lines 단일 함수
  def execute_development(self, requirement, context, ...):
      # 391 lines...

  # After: 분해된 메서드들
  def execute_development(self, requirement, context, ...):
      """Main orchestration (20-30 lines)."""
      patterns = self._match_patterns(requirement)
      spec = self._generate_spec(patterns, context)
      spec = self._apply_reflection(spec)
      self._validate_traceability(spec)
      return spec

  def _match_patterns(self, requirement):
      """Pattern matching logic (40-50 lines)."""
      ...

  def _generate_spec(self, patterns, context):
      """Spec generation (40-50 lines)."""
      ...

  def _apply_reflection(self, spec):
      """Reflection application (40-50 lines)."""
      ...

  def _validate_traceability(self, spec):
      """Traceability validation (40-50 lines)."""
      ...
  ```
- **노력:** 2-3일
- **영향:** 중복도 ↓, 가독성 ↑↑, 테스트 가능성 ↑↑

#### Task 1.2: 패턴 데이터 외부화 [CRITICAL]
- **파일:** `app/knowledge/graph/patterns.py:639-1018`
- **현재:** 379 lines hardcoded data
- **목표:** YAML/JSON 설정 파일
- **작업:**
  ```bash
  # 1. 패턴 데이터 추출
  mkdir -p caas_framework/data

  # 2. patterns.yaml 생성
  cat > caas_framework/data/patterns.yaml << 'EOF'
  patterns:
    - id: "user_authentication"
      name: "User Authentication"
      description: "..."
      agents:
        - role: "Authentication Agent"
          tools: ["login", "logout"]
      tasks:
        - description: "Verify user credentials"
  EOF

  # 3. 로더 함수 단순화
  def _load_builtin_patterns(self):
      """Load patterns from YAML (5-10 lines)."""
      import yaml
      with open("caas_framework/data/patterns.yaml") as f:
          return yaml.safe_load(f)["patterns"]
  ```
- **노력:** 1일
- **영향:** 유지보수성 ↑↑, 테스트 용이성 ↑

#### Task 1.3: ArtifactGenerationContext 도입 [CRITICAL]
- **파일:** `app/artifacts/generator.py:240`
- **현재:** 15 parameters
- **목표:** 1 context object
- **작업:**
  ```python
  # Before: 15 parameters
  def generate_all_artifacts(
      self, project_name, requirement, golden_data, bmad_mapping,
      agents, tasks, test_summary, test_results, coverage,
      validation_result, code_files, code_metrics, security_issues,
      performance_issues, output_dir
  ):
      ...

  # After: Context object
  @dataclass
  class ArtifactGenerationContext:
      """Context for artifact generation."""
      project_name: str
      requirement: str
      golden_data: GoldenData
      bmad_mapping: dict
      agents: List[Agent]
      tasks: List[Task]
      test_summary: dict
      test_results: List[TestResult]
      coverage: CoverageReport
      validation_result: ValidationResult
      code_files: Dict[str, str]
      code_metrics: CodeMetrics
      security_issues: List[SecurityIssue]
      performance_issues: List[PerformanceIssue]
      output_dir: Path

  def generate_all_artifacts(self, context: ArtifactGenerationContext):
      """Generate all artifacts (simplified signature)."""
      ...
  ```
- **노력:** 1일
- **영향:** 가독성 ↑↑, 확장성 ↑

**Phase 1 산출물:**
- ✅ execute_development() 리팩토링 완료
- ✅ patterns.yaml 생성
- ✅ ArtifactGenerationContext 클래스 생성
- ✅ 단위 테스트 추가

---

### Phase 2: 중복 제거 (2-3주) 🟠

**목표:** 중복 코드 통합, Single Source of Truth 확립

#### Task 2.1: Validator 통합 [HIGH]
- **파일:**
  - `caas_framework/validation/golden_validator.py`
  - `app/core/validation/golden_validator.py`
- **현재:** 2개 중복 구현 (200+ lines)
- **목표:** 1개 통합 validator
- **작업:**
  ```python
  # 통합 전략:
  # 1. app 버전을 기본으로 사용 (더 완전한 기능)
  # 2. caas_framework 버전의 추가 기능 병합
  # 3. caas_framework/validation/golden_validator.py를 canonical로 유지

  # caas_framework/validation/golden_validator.py (통합)
  class GoldenDataValidator:
      """Unified golden data validator."""

      def __init__(self, strict_mode: bool = True):
          self.strict_mode = strict_mode

      def validate(self, golden_data: GoldenData) -> ValidationResult:
          """Validate golden data."""
          # Merged logic from both versions
          errors = []
          errors.extend(self._validate_features(golden_data))
          errors.extend(self._validate_priorities(golden_data))
          errors.extend(self._validate_dependencies(golden_data))
          errors.extend(self._validate_discovery(golden_data))  # From app version
          return ValidationResult(errors=errors)

  # app/core/validation/golden_validator.py (삭제 또는 wrapper)
  # Option 1: Delete file completely
  # Option 2: Keep as thin wrapper (deprecated)
  from caas_framework.validation.golden_validator import GoldenDataValidator
  # Deprecated: Use caas_framework.validation.golden_validator instead
  ```
- **노력:** 2일
- **영향:** 중복 -200 lines, 유지보수 ↑

#### Task 2.2: BMADEngine 통합 [HIGH]
- **파일:**
  - `app/core/bmad/engine.py` (1796 lines)
  - `caas_framework/bmad/engine.py` (1317 lines)
- **현재:** 2개 엔진, 불명확한 책임
- **목표:** 1개 통합 엔진 + 선택적 모니터링
- **전략:**
  ```python
  # 1. app/core/bmad/engine.py를 canonical로 선택 (더 완전한 기능)
  # 2. caas_framework/bmad/engine.py 제거
  # 3. 모니터링 기능을 mixin/decorator로 분리

  # caas_framework/bmad/engine.py (새로운 통합 버전)
  class BMADEngine:
      """Unified BMAD engine."""

      def __init__(
          self,
          llm_plugin: LLMPlugin,
          enable_monitoring: bool = False,
          enable_reflection: bool = True,
          ...
      ):
          self.llm = llm_plugin
          self.monitoring = MonitoringMixin() if enable_monitoring else None
          ...

  # caas_framework/bmad/monitoring_mixin.py (새로 생성)
  class MonitoringMixin:
      """Optional monitoring capabilities."""

      def track_phase(self, phase_name: str):
          """Track phase execution."""
          ...

  # app/core/bmad/engine.py (삭제 또는 re-export)
  from caas_framework.bmad.engine import BMADEngine
  # For backwards compatibility
  ```
- **노력:** 3일
- **영향:** 중복 -1300 lines, 명확성 ↑↑

#### Task 2.3: Generator 아키텍처 통합 [HIGH]
- **현재:** 22개 generator 파일
- **목표:** 5개 핵심 generator + 플러그인
- **새로운 구조:**
  ```
  caas_framework/codegen/
  ├── base_generator.py          # Abstract base
  ├── ast_code_generator.py      # AST-based generation
  ├── template_generator.py      # Template-based generation
  ├── specialized/
  │   ├── backend_generator.py   # Backend code
  │   ├── frontend_generator.py  # UI code
  │   └── test_generator.py      # Test code
  └── plugins/
      ├── artifact_plugin.py
      └── multi_generator_plugin.py
  ```
- **작업:**
  ```python
  # base_generator.py
  class BaseGenerator(ABC):
      """Base generator interface."""

      @abstractmethod
      def generate(self, spec: Spec, context: GenerationContext) -> str:
          """Generate code from specification."""
          pass

  # Consolidate similar generators
  # Delete: app/codegen/artifact_generator.py (merge to base)
  # Delete: app/codegen/multi_generator.py (convert to plugin)
  # Keep: caas_framework/codegen/ast_code_generator.py (specialized)
  ```
- **노력:** 5-7일
- **영향:** 중복 -1000 lines, 일관성 ↑↑

**Phase 2 산출물:**
- ✅ 통합된 GoldenDataValidator
- ✅ 통합된 BMADEngine
- ✅ 재구조화된 Generator 계층
- ✅ Migration 가이드 문서

---

### Phase 3: Dead Code 제거 (1주) 🟡

**목표:** 미사용 코드, import, 주석 제거

#### Task 3.1: 미사용 Import 제거
- **영향 범위:** 40+ 파일, 150+ 라인
- **도구:** `pylint --disable=all --enable=unused-import`
- **작업:**
  ```bash
  # 1. 미사용 import 탐지
  pylint --disable=all --enable=unused-import \
         caas_framework/ app/ > unused_imports.txt

  # 2. 자동 제거
  autoflake --remove-all-unused-imports --in-place \
            --recursive caas_framework/ app/

  # 3. 검증
  pytest tests/
  ```
- **주요 파일:**
  - `app/__init__.py`: settings, logger
  - `app/artifacts/__init__.py`: 다수의 artifact types
  - `app/codegen/__init__.py`: 미사용 generators
  - `app/core/bmad/engine.py:712`: workflow_selector
- **노력:** 0.5일
- **영향:** -150 lines, 명확성 ↑

#### Task 3.2: 주석 처리된 코드 제거
- **영향 범위:** 3 파일, 15+ 라인
- **작업:**
  ```bash
  # 파일 1: caas_framework/codegen/ast_code_generator.py:443-530
  # 제거: 5 lines of commented code

  # 파일 2: caas_framework/codegen/ast_code_generator.py:593-627
  # 제거: 4 lines of commented code

  # 파일 3: app/core/bmad/deployer.py:263-266
  # 제거: 3 lines of commented code
  ```
- **노력:** 0.25일
- **영향:** -15 lines, 가독성 ↑

#### Task 3.3: 미사용 메서드 제거
- **작업:** 코드 커버리지 분석으로 미사용 메서드 식별
- **도구:**
  ```bash
  # 1. Coverage 측정
  pytest --cov=caas_framework --cov=app \
         --cov-report=html tests/

  # 2. 0% coverage methods 식별
  # 3. Static analysis로 호출 확인
  # 4. Dead method 제거
  ```
- **예상 대상:**
  - `_create_fallback_*` methods in agents
  - Unreachable `_validate_*` helpers
- **노력:** 1일
- **영향:** TBD after analysis

**Phase 3 산출물:**
- ✅ 미사용 import 0개
- ✅ 주석 코드 0개
- ✅ Dead method 리스트 및 제거 계획

---

### Phase 4: 코드 품질 정규화 (2-3주) 🟢

**목표:** 함수 크기, 복잡도, 중첩 정규화

#### Task 4.1: 긴 함수 리팩토링 (Top 10)
| 순위 | 함수 | 파일 | 현재 | 목표 | 방법 |
|-----|------|------|------|------|------|
| 1 | execute_development() | engine.py:830 | 391 | <50 | Extract Method |
| 2 | _load_builtin_patterns() | patterns.py:639 | 379 | <10 | Extract Data |
| 3 | _generate_readme() | multi_generator.py:1454 | 357 | <50 | Template Engine |
| 4 | generate_all_tests() | test_generator.py:613 | 344 | <50 | Strategy Pattern |
| 5 | generate_initial_ontology() | tool_data_generator.py:17 | 350 | <10 | Extract Data |
| 6 | _build_context() | generator.py:322 | 117 | <30 | Builder Pattern |
| 7 | Collaboration.__init__() | collaboration.py:454 | 111 | <20 | Factory Method |
| 8 | _update_session_analytics() | usage_analytics.py:501 | 95 | <40 | Extract Method |
| 9 | apply_auto_fix() | ontology_validator.py:548 | 89 | <40 | Strategy Pattern |
| 10 | _parse_task_call() | code_analyzer.py:394 | 82 | <40 | Visitor Pattern |

**작업 전략:**
```python
# Extract Method Pattern
# Before:
def long_function():
    # 100+ lines
    # Step 1: validation (20 lines)
    # Step 2: processing (30 lines)
    # Step 3: formatting (25 lines)
    # Step 4: saving (15 lines)

# After:
def long_function():
    """Main orchestration."""
    data = self._validate_input()
    result = self._process_data(data)
    formatted = self._format_result(result)
    self._save_output(formatted)

def _validate_input(self):
    """Validation logic (20 lines)."""
    ...

def _process_data(self, data):
    """Processing logic (30 lines)."""
    ...
```

#### Task 4.2: 파라미터 수 감소 (Context Objects)
- **대상:** 22개 함수 (>5 params)
- **방법:** Introduce Parameter Object
- **예시:**
  ```python
  # Before:
  def save_pattern(self, id, name, desc, agents, tasks,
                   workflow, complexity, domain, tags, version):
      ...

  # After:
  @dataclass
  class PatternConfig:
      id: str
      name: str
      description: str
      agents: List[Agent]
      tasks: List[Task]
      workflow: WorkflowType
      complexity: int
      domain: str
      tags: List[str]
      version: str

  def save_pattern(self, config: PatternConfig):
      ...
  ```

#### Task 4.3: 중첩 깊이 감소
- **대상:** 30+ 함수 (>3 nesting)
- **방법:**
  1. Early Return
  2. Guard Clauses
  3. Extract Method
  4. Replace Nested Conditionals with Polymorphism
- **예시:**
  ```python
  # Before: 8 nesting levels
  def process(self, data):
      if data:
          if data.valid:
              if data.type == "A":
                  if data.has_config:
                      # ... 4 more levels

  # After: 1-2 nesting levels
  def process(self, data):
      if not data or not data.valid:
          return None

      processor = self._get_processor(data.type)
      if not processor:
          return None

      return processor.process(data)
  ```

**Phase 4 산출물:**
- ✅ 모든 함수 <50 lines
- ✅ 모든 함수 <5 parameters
- ✅ 모든 함수 <3 nesting levels
- ✅ 순환 복잡도 <10

---

## 📋 실행 계획

### 우선순위 매트릭스

```
영향도
 ↑
 │  P1: 즉시    │ P2: 계획
 │  ─────────────┼──────────────
 │  execute_dev │ Validator통합
 │  patterns외부화│ Engine통합
 │  Context도입  │ Generator통합
 │              │
 │  ─────────────┼──────────────
 │  P4: 보류    │ P3: 일정잡기
 │              │ Dead code제거
 │              │ 함수정규화
 └──────────────────────────────→
                                노력
```

### 타임라인

```
Week 1-2:  Phase 1 (긴급 수정)
  ├─ Day 1-3:   execute_development() 분해
  ├─ Day 4:     patterns.yaml 외부화
  └─ Day 5:     ArtifactGenerationContext

Week 3-5:  Phase 2 (중복 제거)
  ├─ Day 6-7:   Validator 통합
  ├─ Day 8-10:  Engine 통합
  └─ Day 11-15: Generator 재구조화

Week 6:    Phase 3 (Dead Code)
  ├─ Day 16:    미사용 import 제거
  ├─ Day 17:    주석 코드 제거
  └─ Day 18:    미사용 메서드 제거

Week 7-9:  Phase 4 (정규화)
  ├─ Day 19-23: 긴 함수 리팩토링 (Top 10)
  ├─ Day 24-25: 파라미터 수 감소
  └─ Day 26-27: 중첩 깊이 감소
```

### 마일스톤

- **M1 (Week 2):** Critical 이슈 해결 완료
- **M2 (Week 5):** 중복 코드 50% 감소
- **M3 (Week 6):** Dead code 100% 제거
- **M4 (Week 9):** 코드 품질 목표 달성

---

## 🧪 검증 전략

### 자동화된 검증

```yaml
# .github/workflows/code-quality.yml
code_quality_gates:
  - name: "No code duplication"
    tool: "pylint --duplicate-code"
    threshold: "similarity < 5%"

  - name: "Function length"
    tool: "radon cc --min C"
    threshold: "all functions < 50 lines"

  - name: "Parameter count"
    tool: "pylint --max-args=5"
    threshold: "all functions <= 5 params"

  - name: "Cyclomatic complexity"
    tool: "radon cc --min C"
    threshold: "complexity < 10"

  - name: "No dead code"
    tool: "vulture"
    threshold: "0 unused code"
```

### 수동 검토 체크리스트

#### 각 리팩토링 후:
- [ ] 모든 기존 테스트 통과
- [ ] 새로운 단위 테스트 추가
- [ ] 문서 업데이트 (docstring, README)
- [ ] Code review 승인
- [ ] Performance 회귀 없음

#### Phase 완료 후:
- [ ] 통합 테스트 통과
- [ ] E2E 테스트 통과
- [ ] 품질 게이트 통과
- [ ] 릴리즈 노트 작성

---

## 📊 진행 상황 추적

### 대시보드 메트릭

```python
# 주간 추적 메트릭
metrics = {
    "code_duplication": {
        "current": 2900,
        "target": 0,
        "unit": "lines"
    },
    "dead_code": {
        "current": 165,
        "target": 0,
        "unit": "lines"
    },
    "long_functions": {
        "current": 50,
        "target": 0,
        "unit": "count"
    },
    "high_param_functions": {
        "current": 22,
        "target": 0,
        "unit": "count"
    },
    "deep_nesting": {
        "current": 30,
        "target": 0,
        "unit": "count"
    }
}
```

### 보고서 템플릿

```markdown
## 주간 리팩토링 리포트 - Week X

### 완료된 작업
- [ ] Task 1.1: execute_development() 분해
- [ ] Task 1.2: patterns.yaml 외부화
- ...

### 메트릭 개선
| 메트릭 | 이전 | 현재 | 개선 |
|--------|------|------|------|
| 코드 중복 | 2900 | 2500 | -400 (-14%) |
| Dead code | 165 | 120 | -45 (-27%) |
| 긴 함수 | 50 | 47 | -3 (-6%) |

### 다음 주 계획
- Task 2.1: Validator 통합 시작
- ...

### 이슈 및 리스크
- 없음 / [이슈 설명]
```

---

## 🚨 리스크 관리

### 식별된 리스크

| 리스크 | 확률 | 영향 | 완화 전략 |
|--------|------|------|----------|
| **하위 호환성 파괴** | Medium | High | 1. Deprecation warnings<br>2. Migration guide<br>3. Compatibility layer |
| **테스트 커버리지 부족** | High | High | 1. 리팩토링 전 테스트 추가<br>2. 최소 60% 커버리지 요구 |
| **Performance 회귀** | Low | Medium | 1. 벤치마크 테스트<br>2. 프로파일링 |
| **일정 지연** | Medium | Medium | 1. 주간 체크포인트<br>2. Scope 조정 가능 |

### 롤백 계획

각 Phase마다:
1. **Git branch 전략:** `refactor/phase-X`
2. **태깅:** `v1.0.3-pre-phase-X`
3. **롤백 절차:**
   ```bash
   # 문제 발생 시
   git checkout v1.0.3-pre-phase-X
   git checkout -b hotfix/rollback
   ```

---

## 📚 참고 자료

### 리팩토링 패턴

- **Extract Method:** 긴 함수 분해
- **Introduce Parameter Object:** 파라미터 수 감소
- **Replace Conditional with Polymorphism:** 중첩 감소
- **Extract Data Class:** 하드코드 데이터 외부화
- **Replace Inheritance with Delegation:** 중복 제거

### 도구

- **pylint:** 코드 품질 분석
- **radon:** 복잡도 측정
- **vulture:** Dead code 탐지
- **autoflake:** 자동 import 정리
- **black:** 코드 포맷팅
- **coverage.py:** 테스트 커버리지

### 문서

- Martin Fowler - "Refactoring: Improving the Design of Existing Code"
- Robert C. Martin - "Clean Code"
- Steve McConnell - "Code Complete"

---

## ✅ 체크리스트

### Phase 1 시작 전
- [ ] 현재 코드 백업 (git tag v1.0.3)
- [ ] 기존 테스트 스위트 100% 통과 확인
- [ ] 리팩토링 브랜치 생성 (`refactor/phase-1`)
- [ ] 팀 리뷰 및 승인

### 각 Task 완료 후
- [ ] 단위 테스트 추가/업데이트
- [ ] 기존 테스트 통과
- [ ] Code review
- [ ] 문서 업데이트
- [ ] Commit with descriptive message

### Phase 완료 후
- [ ] 모든 테스트 통과
- [ ] 성능 벤치마크 통과
- [ ] 메트릭 개선 확인
- [ ] Migration guide 작성 (breaking changes 있는 경우)
- [ ] PR 생성 및 리뷰
- [ ] Merge to main
- [ ] 릴리즈 노트 작성

---

## 📞 연락처 및 지원

**리팩토링 리드:** [담당자 이름]
**기술 검토:** [검토자 이름]
**질문/이슈:** GitHub Issues에 `refactoring` 태그로 등록

---

**마지막 업데이트:** 2026-02-01
**다음 리뷰:** 매주 금요일
**버전:** 1.0
