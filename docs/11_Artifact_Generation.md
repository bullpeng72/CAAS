# 산출물 자동 생성 (Artifact Generation)

## 개요

CAAS는 개발 과정에서 자동으로 다양한 산출물(문서)을 생성하는 기능을 제공합니다. 이를 통해 각 단계의 품질을 확인하고, 프로젝트 문서화를 자동화할 수 있습니다.

**v0.4.1 상태**: ✅ 완전 구현됨 (10개 산출물 타입, 10개 Jinja2 템플릿 포함)

## 지원하는 산출물 타입 (10종)

| 타입 | 한글명 | 설명 | 생성 단계 |
|---|---|---|---|
| `PROJECT_PROPOSAL` | 프로젝트 기획서 | 프로젝트 배경, 목적, 범위, 기대 효과 | 요구사항 입력 후 |
| `REQUIREMENTS_SPEC` | 요구사항 명세서 | 기능/비기능 요구사항, 사용자 스토리 | Golden Data 생성 후 |
| `ARCHITECTURE_DESIGN` | 아키텍처 설계서 | 시스템 구조, 컴포넌트 설계, 통신 흐름 | CAAS 6-Phase Architecture 후 |
| `DATA_DESIGN` | 데이터 설계서 | 데이터 모델, 스키마, ERD | Agent 설계 후 |
| `API_DESIGN` | API 설계서 | REST API 엔드포인트, 요청/응답 스키마 | Agent 설계 후 |
| `AGENT_DESIGN` | 에이전트 설계서 | Agent 역할, 목표, 할당된 도구, Task 워크플로우 | Agent/Task 설계 후 |
| `TEST_PLAN` | 테스트 계획서 | 테스트 전략, 시나리오, 예상 결과 | 코드 생성 전 |
| `TEST_REPORT` | 테스트 결과 리포트 | 테스트 실행 결과, 커버리지, 성공/실패 분석 | 테스트 실행 후 |
| `CODE_REVIEW` | 코드 리뷰 리포트 | 생성된 코드의 품질, 스타일, 잠재적 이슈 분석 | 코드 생성 후 |
| `DEPLOYMENT_GUIDE` | 배포 가이드 | 배포 절차, 환경 설정, 실행 방법 | 코드 생성 후 |

## 설정 방법

### 1. 환경 변수 설정 (.env)

```bash
# 산출물 생성 활성화
ARTIFACT_GENERATION_ENABLED=true

# 생성할 산출물 목록 (쉼표로 구분, 'all'로 전체 선택)
ENABLED_ARTIFACTS=PROJECT_PROPOSAL,REQUIREMENTS_SPEC,AGENT_DESIGN

# 출력 포맷 (markdown, html, pdf, json)
ARTIFACT_OUTPUT_FORMAT=markdown

# 출력 디렉토리
ARTIFACT_OUTPUT_DIR=./artifacts
```

### 2. 코드에서 설정

```python
from caas_framework.artifacts import ArtifactGenerationConfig, ArtifactGenerator

# 설정 생성
config = ArtifactGenerationConfig(
    enabled=True,

    # 생성할 산출물 타입 지정
    enabled_artifacts=[
        "PROJECT_PROPOSAL",
        "REQUIREMENTS_SPEC",
        "AGENT_DESIGN"
    ],

    # 출력 설정
    output_format="markdown",
    output_directory="./artifacts",

    # 추가 옵션
    include_diagrams=True,
    include_code_samples=True,
    language="ko",
)

# Generator 생성
generator = ArtifactGenerator(config=config)
```

## 사용 방법

### 방법 1: 단일 산출물 생성

```python
from caas_framework.artifacts import ArtifactGenerator
from caas_framework.models.artifact_types import ArtifactType

generator = ArtifactGenerator(config=config)

# 프로젝트 기획서 생성
artifact = generator.generate_artifact(
    artifact_type=ArtifactType.PROJECT_PROPOSAL,
    context={
        "requirement": "기업 동향 분석 시스템 개발",
        "description": "AI 에이전트 기반 자동화 시스템",
    },
    project_name="CompanyAnalysisSystem",
)

print(f"Generated: {artifact.metadata.title}")
print(f"File: {artifact.file_path}")
```

### 방법 2: 워크플로우에 통합하여 자동 생성

```python
from caas_framework.framework import CrewAIFramework
from caas_framework.plugins.llm.openai import OpenAIPlugin

# Framework 초기화
llm = OpenAIPlugin(model="gpt-4o-mini")
framework = CrewAIFramework(llm_plugin=llm)
await framework.initialize()

# 프로젝트 생성 (artifact 생성 활성화 시 자동 생성)
result = await framework.generate_from_requirement(
    requirement="기업 동향 분석 시스템 만들기",
    domain_hint="WORKFLOW_AUTOMATION"
)

# 생성된 산출물 확인
if hasattr(result, 'artifacts'):
    print(f"Generated {len(result.artifacts)} artifacts")
    for artifact in result.artifacts:
        print(f"- {artifact.metadata.title}: {artifact.file_path}")
```

## 출력 구조

```
./artifacts/
└── CompanyAnalysisSystem/
    ├── project_proposal_20260202_103000.md
    ├── requirements_spec_20260202_103005.md
    ├── architecture_design_20260202_103010.md
    └── agent_design_20260202_103015.md
```

## 템플릿 커스터마이징

산출물 템플릿은 Jinja2 형식으로 작성되어 있으며, `data/templates/artifacts/` 디렉토리에서 수정할 수 있습니다.

### 템플릿 위치 (10개 템플릿 모두 구현됨 ✅)

| 산출물 타입 | 템플릿 파일 | 크기 |
|------------|-----------|------|
| 프로젝트 기획서 | `project_proposal.md.j2` | 3.7 KB |
| 요구사항 명세서 | `requirements_spec.md.j2` | 6.0 KB |
| 아키텍처 설계서 | `architecture_design.md.j2` | 9.0 KB |
| 데이터 설계서 | `data_design.md.j2` | 5.6 KB |
| API 설계서 | `api_design.md.j2` | 1.8 KB |
| 에이전트 설계서 | `agent_design.md.j2` | 5.9 KB |
| 테스트 계획서 | `test_plan.md.j2` | 8.4 KB |
| 테스트 결과 리포트 | `test_report.md.j2` | 13 KB |
| 코드 리뷰 리포트 | `code_review.md.j2` | 11 KB |
| 배포 가이드 | `deployment_guide.md.j2` | 2.0 KB |

### 템플릿 변수 예시

```jinja2
# {{ metadata.title }}

- **버전**: {{ metadata.version }}
- **생성일**: {{ metadata.created_at }}

## 1. 개요
원본 요구사항: {{ requirement }}

## 2. 기능 목록
{% for feature in golden_data.features %}
- **{{ feature.id }}**: {{ feature.name }} (우선순위: {{ feature.priority }})
{% endfor %}

## 3. 에이전트 설계
{% for agent in agents %}
### {{ agent.role }}
- **목표**: {{ agent.goal }}
- **도구**: {{ agent.tools | join(', ') }}
{% endfor %}
```

## CLI에서 사용

### 환경 변수 설정

```bash
# .env 파일 또는 직접 export
export ARTIFACT_GENERATION_ENABLED=true
export ENABLED_ARTIFACTS=all  # 또는 특정 타입: PROJECT_PROPOSAL,AGENT_DESIGN
export ARTIFACT_OUTPUT_FORMAT=markdown
export ARTIFACT_OUTPUT_DIR=./artifacts
```

### CLI 명령어

```bash
# 프로젝트 생성 시 자동으로 산출물 생성
caas generate "기업 동향 분석 시스템" --output ./my_project

# 생성된 산출물 확인
ls -la ./artifacts/

# 특정 산출물 타입만 생성하려면
export ENABLED_ARTIFACTS=AGENT_DESIGN,REQUIREMENTS_SPEC
caas generate "할일 관리 시스템" --domain TASK_MANAGEMENT
```

### 출력 예시

```
./artifacts/
└── CompanyAnalysisSystem_20260206_143022/
    ├── project_proposal_20260206_143022.md     (3.8 KB)
    ├── requirements_spec_20260206_143025.md    (12 KB)
    ├── architecture_design_20260206_143030.md  (15 KB)
    ├── agent_design_20260206_143035.md         (8.5 KB)
    ├── test_plan_20260206_143040.md            (11 KB)
    └── deployment_guide_20260206_143045.md     (4.2 KB)
```

## 활용 사례

- **품질 검증**: 각 단계별 산출물을 검토하여 프로젝트 품질을 확인합니다.
- **문서화 자동화**: 수동으로 작성해야 하는 문서를 자동으로 생성하여 시간을 절약합니다.
- **커뮤니케이션**: 생성된 산출물을 팀원이나 이해관계자와 공유하여 명확한 소통을 돕습니다.
- **아카이빙**: 프로젝트 이력을 문서로 보존합니다.

## 제한 사항

1. **포맷 지원**: 현재 Markdown 포맷을 가장 잘 지원합니다. (HTML, PDF는 실험적 기능)
2. **다이어그램**: Mermaid.js를 이용한 다이어그램 생성을 일부 지원합니다.
3. **LLM 의존성**: 일부 고급 산출물은 LLM을 사용하여 동적으로 생성됩니다.

## 로드맵

- [x] ✅ 10개 산출물 타입 모두 구현 (v0.4.1)
- [x] ✅ 모든 산출물 타입에 대한 Jinja2 템플릿 완성 (v0.4.1)
- [ ] PDF 및 HTML 출력 지원 안정화
- [ ] 다이어그램 자동 생성 기능 개선 (Mermaid.js)
- [ ] 다국어 지원 확대 (현재는 한국어/영어 중심)
- [ ] 산출물 버전 관리 및 diff 기능

---

## 참고 자료

### CAAS 핵심 파일

- **산출물 생성기**: `caas_framework/artifacts/generator.py`
- **산출물 타입 정의**: `caas_framework/models/artifact_types.py`
- **Jinja2 템플릿**: `data/templates/artifacts/` (10개 템플릿)
- **CAAS 6-Phase Engine**: `caas_framework/methodology/engine.py`

### CAAS 문서

- [01_README_KO.md](01_README_KO.md) - 프로젝트 개요
- [03_Quick_Start_Guide.md](03_Quick_Start_Guide.md) - 빠른 시작 가이드
- [04_CLI_Usage_Guide.md](04_CLI_Usage_Guide.md) - CLI 사용 가이드 (29 commands)
- [05_Expert_Methodology_Guide.md](05_Expert_Methodology_Guide.md) - CAAS 6-Phase 방법론
- [06_Architecture_Guide.md](06_Architecture_Guide.md) - 아키텍처 가이드
- [CLAUDE.md](../CLAUDE.md) - 프로젝트 컨텍스트

### 외부 문서

- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Mermaid.js Documentation](https://mermaid.js.org/)

---

**최종 업데이트**: 2026-02-06
**CAAS 버전**: v0.4.1
**문서 버전**: 1.1.0
**상태**: Production Ready ✅ (10/10 템플릿 구현 완료)
