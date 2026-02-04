```markdown
# 코드 분석 가이드 (Code Analysis Guide)

CAAS v0.4.0의 새로운 Code Analysis Agent를 활용한 코드 품질 보증 가이드입니다.

**버전**: v0.4.0
**최종 업데이트**: 2026-02-04

---

## 목차

- [개요](#개요)
- [Code Analysis Agent 소개](#code-analysis-agent-소개)
- [주요 기능](#주요-기능)
- [CLI 명령어](#cli-명령어)
- [사용 예시](#사용-예시)
- [워크플로우 패턴](#워크플로우-패턴)
- [고급 활용](#고급-활용)

---

## 개요

Code Analysis Agent는 CAAS의 **6번째 Expert Agent**로, 생성된 코드의 품질을 보증합니다:

- ✅ **완전성 분석**: Golden Data 요구사항 대비 구현 완성도 검증
- ✅ **런타임 에러 자동 수정**: Python 에러 자동 감지 및 수정
- ✅ **비즈니스 룰 검증**: 업무 규칙 및 acceptance criteria 준수 확인
- ✅ **추적성 분석**: 요구사항-코드 매핑 및 갭 분석

### ROI

- **구현률 향상**: 98.7% → 99.5%+
- **비용**: $17/month (LLM 사용 증가분)
- **절감**: $9,150/month (디버깅 시간 절약)
- **투자 대비 효과**: **538x**

---

## Code Analysis Agent 소개

### 역할

```
Phase: CODE_ANALYSIS (Post-generation Quality Assurance)
Expertise:
  - Implementation completeness analysis
  - Runtime error detection and fixing
  - Business logic verification
  - Traceability analysis
  - Code quality assurance
  - Requirement coverage validation
  - Automatic bug fixing
```

### 핵심 메서드

#### 1. `analyze_implementation()`
Golden Data와 실제 구현을 비교하여 완전성을 분석합니다.

```python
from caas_framework.agents import CodeAnalysisAgent

agent = CodeAnalysisAgent(llm_plugin=llm, golden_data=golden_data)

result = await agent.analyze_implementation(
    project_path=Path("./generated_project"),
    golden_data=golden_data
)

print(f"Coverage: {result.overall_coverage}%")
print(f"Implemented: {result.implemented_features}/{result.total_features}")
```

#### 2. `analyze_runtime_error()`
런타임 에러를 분석하고 자동 수정 방안을 제시합니다.

```python
error_log = """
Traceback (most recent call last):
  File "main.py", line 5
    import missing_module
ModuleNotFoundError: No module named 'missing_module'
"""

fix = await agent.analyze_runtime_error(
    error_log=error_log,
    project_path=Path("./project")
)

print(f"Root cause: {fix.root_cause}")
print(f"Strategy: {fix.fix_strategy}")
```

#### 3. `verify_business_rules()`
비즈니스 룰 위반 사항을 감지합니다.

```python
violations = await agent.verify_business_rules(
    project_path=Path("./project"),
    golden_data=golden_data
)

for v in violations:
    print(f"{v.severity}: {v.description}")
```

---

## 주요 기능

### 1. 구현 완전성 분석

**기능**:
- Golden Data feature 대비 구현 커버리지 계산
- 누락된 acceptance criteria 식별
- 구현 파일 추적성 매트릭스 생성
- 우선순위별 갭 분석

**출력**:
```
📊 COVERAGE SUMMARY:
  Total Features:        5
  ✅ Implemented:        4
  ⚠️  Partial:            1
  ❌ Missing:            0
  📈 Overall Coverage:   85.0%

💡 RECOMMENDATIONS:
  • Improve implementation for 1 features with <50% coverage
  • Address 2 high-priority implementation gaps
```

### 2. 런타임 에러 자동 수정

**지원 에러 타입** (8+):
- `ImportError` / `ModuleNotFoundError` - 누락된 import
- `NameError` - 정의되지 않은 변수
- `AttributeError` - 누락된 속성/메서드
- `TypeError` - 타입 불일치
- `KeyError` - 누락된 딕셔너리 키
- `IndexError` - 리스트 인덱스 오류
- `ValueError` - 잘못된 값
- `SyntaxError` - Python 문법 오류

**3-Layer Defense** (tools.py 생성):
1. **Validation**: 입력값 검증 (한국어 도구명 번역 등)
2. **LLM Generation**: LLM 기반 코드 생성
3. **Fallback**: 실패 시 실행 가능한 stub 생성

### 3. 비즈니스 룰 검증

**검증 항목**:
- Acceptance criteria 구현 여부
- Functional requirements 충족 여부
- User stories 반영 여부
- Non-functional requirements 준수

**위반 유형**:
- `missing`: 구현 누락
- `incorrect`: 잘못된 구현
- `incomplete`: 부분 구현

---

## CLI 명령어

### `caas analyze-completeness`

구현 완전성을 분석합니다.

#### 기본 사용법

```bash
caas analyze-completeness \
  --project ./generated_project \
  --golden-data golden_data.json
```

#### 옵션

| 옵션 | 설명 |
|------|------|
| `--project`, `-p` | 프로젝트 디렉토리 경로 (필수) |
| `--golden-data`, `-g` | Golden Data JSON 파일 경로 (필수) |
| `--output`, `-o` | 분석 리포트 JSON 저장 경로 |
| `--detailed`, `-d` | 상세 추적성 분석 표시 |

#### 예시

```bash
# 1. 기본 분석
caas analyze-completeness -p ./project -g golden_data.json

# 2. 상세 분석 + 리포트 저장
caas analyze-completeness \
  -p ./project \
  -g golden_data.json \
  --detailed \
  --output completeness_report.json

# 3. 커버리지 빠른 확인
caas analyze-completeness -p ./project -g golden_data.json | grep "Coverage"
```

#### 출력 해석

| 커버리지 | 평가 | 조치 |
|---------|------|------|
| ≥ 90% | 우수 - 프로덕션 준비 완료 | 배포 가능 |
| 70-90% | 양호 - 사소한 갭 허용 | 검토 후 배포 |
| 50-70% | 보통 - 누락 기능 검토 필요 | 주요 갭 수정 |
| < 50% | 미흡 - 주요 기능 누락 | 재개발 필요 |

### `caas fix-runtime-error`

런타임 에러를 자동으로 수정합니다.

#### 기본 사용법

```bash
# Preview mode (기본)
caas fix-runtime-error \
  --project ./project \
  --error-log error.log

# Apply mode (수정 적용)
caas fix-runtime-error \
  --project ./project \
  --error-log error.log \
  --apply --backup
```

#### 옵션

| 옵션 | 설명 |
|------|------|
| `--project`, `-p` | 프로젝트 디렉토리 (필수) |
| `--error-log`, `-e` | 에러 로그 파일 (선택 - 없으면 대화형) |
| `--apply`, `-a` | 수정 자동 적용 (기본: false) |
| `--backup`, `-b` | 수정 전 백업 생성 (기본: true) |
| `--output`, `-o` | 수정 리포트 JSON 저장 경로 |

#### 예시

```bash
# 1. 에러 분석만 (Preview)
caas fix-runtime-error -p ./project -e error.log

# 2. 에러 수정 적용 + 백업
caas fix-runtime-error -p ./project -e error.log --apply --backup

# 3. 대화형 모드 (에러 로그 직접 붙여넣기)
caas fix-runtime-error -p ./project
# 프롬프트에서 traceback 붙여넣기

# 4. 수정 + 리포트 저장
caas fix-runtime-error \
  -p ./project \
  -e error.log \
  --apply \
  --output fix_report.json
```

#### 안전 장치

- ✅ **Preview mode**: 기본값, `--apply` 필요
- ✅ **Auto Backup**: 수정 전 `.backup` 파일 생성
- ✅ **Confidence Score**: 각 수정안의 신뢰도 표시
- ✅ **Manual Review**: 낮은 신뢰도 수정은 검토 권장

---

## 사용 예시

### 예시 1: 새 프로젝트 검증

```bash
# 1. 코드 생성
caas generate "할일 관리 시스템" --output ./todo_app

# 2. 완전성 검증
caas analyze-completeness \
  -p ./todo_app \
  -g ./todo_app/golden_data.json \
  --detailed

# 출력:
# ✨ Excellent coverage - production ready!
# Coverage: 98.5%
```

### 예시 2: 런타임 에러 수정

```bash
# 1. 앱 실행 중 에러 발생
python ./todo_app/main.py 2> error.log

# 2. 에러 분석
caas fix-runtime-error -p ./todo_app -e error.log

# 출력:
# 🔴 Error Type: ImportError
# 🔍 ROOT CAUSE: Missing 'requests' module
# 🛠️ FIX STRATEGY: Install dependency

# 3. 수정 적용
caas fix-runtime-error -p ./todo_app -e error.log --apply

# 4. 재실행 검증
python ./todo_app/main.py  # ✓ 성공
```

### 예시 3: 반복 개선 워크플로우

```bash
# 1. 초기 생성
caas generate "블로그 시스템" -o ./blog

# 2. 완전성 분석
caas analyze-completeness -p ./blog -g ./blog/golden_data.json
# Coverage: 75% (보통)

# 3. 누락 기능 확인 및 재생성
caas generate-code \
  --agents ./blog/agents.json \
  --tasks ./blog/tasks.json \
  --output ./blog

# 4. 재검증
caas analyze-completeness -p ./blog -g ./blog/golden_data.json
# Coverage: 92% (우수)
```

---

## 워크플로우 패턴

### Pattern 1: Quick Validation (빠른 검증)

```bash
# 생성 → 검증 → 배포
caas generate "요구사항" -o ./project
caas analyze-completeness -p ./project -g ./project/golden_data.json
# Coverage ≥ 90% → 배포
```

**소요 시간**: 5-10분
**적합 사례**: 간단한 프로젝트, POC

### Pattern 2: Iterative Improvement (반복 개선)

```bash
# 생성 → 검증 → 수정 → 재검증
caas generate "요구사항" -o ./project
caas analyze-completeness -p ./project -g ./project/golden_data.json
# Coverage: 70%

caas fix --level 3 --agents ./project/agents.json
caas generate-code --output ./project
caas analyze-completeness -p ./project -g ./project/golden_data.json
# Coverage: 95%
```

**소요 시간**: 15-30분
**적합 사례**: 프로덕션 프로젝트, 높은 품질 요구

### Pattern 3: Production-Ready (프로덕션 준비)

```bash
# 전체 자동화 + 검증 + 에러 수정
caas auto-deploy "요구사항" --target docker

# 완전성 검증
caas analyze-completeness -p ./output -g ./output/golden_data.json

# 통합 테스트 실행
cd ./output && pytest tests/

# 런타임 에러 발견 시
caas fix-runtime-error -p ./output -e test_errors.log --apply

# 최종 검증
caas validate --validator all --agents ./output/agents.json --tasks ./output/tasks.json
```

**소요 시간**: 30-60분
**적합 사례**: 엔터프라이즈 프로젝트, CI/CD 통합

---

## 고급 활용

### 1. CI/CD 통합

**GitHub Actions 예시**:

```yaml
name: CAAS Quality Check

on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install CAAS
        run: pip install caas

      - name: Analyze Completeness
        run: |
          caas analyze-completeness \
            --project . \
            --golden-data golden_data.json \
            --output completeness_report.json

      - name: Check Coverage
        run: |
          coverage=$(jq '.summary.overall_coverage' completeness_report.json)
          if (( $(echo "$coverage < 90" | bc -l) )); then
            echo "Coverage $coverage% is below 90%"
            exit 1
          fi
```

### 2. Python API 활용

```python
from pathlib import Path
from caas_framework.agents import CodeAnalysisAgent
from caas_framework.models.specifications import ConcretizedRequirement
from caas_framework.plugins.llm.factory import create_llm_plugin
from caas_framework.config.loader import load_config

async def analyze_project(project_path: Path, golden_path: Path):
    # Setup
    config = load_config()
    llm = create_llm_plugin(config)
    golden_data = ConcretizedRequirement.parse_file(golden_path)

    # Create agent
    agent = CodeAnalysisAgent(llm_plugin=llm, golden_data=golden_data)

    # Analyze
    result = await agent.analyze_implementation(
        project_path=project_path,
        golden_data=golden_data
    )

    # Report
    print(f"Coverage: {result.overall_coverage}%")
    for gap in result.implementation_gaps:
        print(f"Gap: {gap.feature_name} - {gap.impact}")

    return result
```

### 3. 커스텀 리포팅

```python
import json
from pathlib import Path

def generate_html_report(report_path: Path):
    """Generate HTML report from JSON"""
    data = json.loads(report_path.read_text())

    html = f"""
    <html>
    <head><title>Analysis Report</title></head>
    <body>
        <h1>{data['summary']['project_name']}</h1>
        <p>Coverage: {data['summary']['overall_coverage']:.1f}%</p>
        <ul>
        {"".join(f"<li>{rec}</li>" for rec in data['implementation_analysis']['recommendations'])}
        </ul>
    </body>
    </html>
    """

    output = report_path.with_suffix('.html')
    output.write_text(html)
    print(f"HTML report: {output}")
```

### 4. 일괄 프로젝트 분석

```bash
#!/bin/bash
# analyze_all.sh - 여러 프로젝트 일괄 분석

for project in projects/*/; do
    echo "Analyzing $project..."

    caas analyze-completeness \
        -p "$project" \
        -g "$project/golden_data.json" \
        -o "reports/$(basename $project)_report.json"

    coverage=$(jq '.summary.overall_coverage' "reports/$(basename $project)_report.json")
    echo "$project: $coverage%"
done
```

---

## 베스트 프랙티스

### ✅ DO

1. **생성 후 즉시 검증**: 코드 생성 직후 `analyze-completeness` 실행
2. **Preview 먼저**: `fix-runtime-error`는 항상 `--apply` 없이 먼저 실행
3. **백업 유지**: `--backup` 옵션 항상 활성화
4. **낮은 신뢰도 검토**: Confidence < 60% 수정은 수동 검토
5. **반복 검증**: 수정 후 재검증으로 개선 확인

### ❌ DON'T

1. **맹목적 적용 금지**: 수정안을 검토 없이 적용하지 말 것
2. **과도한 자동화**: 중요 프로젝트는 수동 검토 병행
3. **단일 실행 의존**: 한 번의 분석만으로 판단하지 말 것
4. **백업 생략**: `--no-backup` 사용 지양
5. **에러 무시**: 낮은 Coverage나 Critical 위반 방치 금지

---

## 문제 해결

### Q1: Coverage가 낮게 나옵니다

**원인**:
- Feature 이름과 코드 간 키워드 불일치
- 구현은 되었으나 파일명/변수명이 상이

**해결**:
```bash
# 상세 분석으로 누락 항목 확인
caas analyze-completeness -p ./project -g golden_data.json --detailed

# Feature별 coverage 확인
# Missing requirements 섹션 검토
```

### Q2: 수정이 제대로 적용되지 않습니다

**원인**:
- 낮은 confidence score
- 복잡한 에러 패턴

**해결**:
```bash
# 1. Preview로 수정안 확인
caas fix-runtime-error -p ./project -e error.log

# 2. Confidence 확인
# 3. 60% 이하는 수동 수정
```

### Q3: LLM 비용이 과도합니다

**해결**:
- Haiku 모델 사용: 간단한 분석은 빠른 모델
- 배치 처리: 여러 에러를 하나의 로그로 통합
- 캐싱 활용: LLM 응답 캐시 활성화

```bash
# Haiku 모델 사용
export CAAS_MODEL=haiku
caas analyze-completeness -p ./project -g golden_data.json
```

---

## 참고 자료

- [전문가 방법론 가이드](./05_전문가_방법론_가이드.md)
- [CLI 사용 가이드](./04_CLI_사용_가이드.md)
- [배포 가이드](./09_배포_가이드.md)
- [아키텍처 가이드](./06_아키텍처_가이드.md)

---

**Last Updated**: 2026-02-04
**Version**: v0.4.0
```
