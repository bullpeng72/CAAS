# 산출물 자동 생성 (Artifact Generation)

## 개요

CAAS는 개발 과정에서 자동으로 다양한 산출물(문서)을 생성하는 기능을 제공합니다. 이를 통해 각 단계의 품질을 확인하고, 프로젝트 문서화를 자동화할 수 있습니다.

## 지원하는 산출물 타입 (10종)

| 타입 | 한글명 | 설명 | 생성 단계 |
|---|---|---|---|
| `PROJECT_PROPOSAL` | 프로젝트 기획서 | 프로젝트 배경, 목적, 범위, 기대 효과 | 요구사항 입력 후 |
| `REQUIREMENTS_SPEC` | 요구사항 명세서 | 기능/비기능 요구사항, 사용자 스토리 | Golden Data 생성 후 |
| `ARCHITECTURE_DESIGN` | 아키텍처 설계서 | 시스템 구조, 컴포넌트 설계, 통신 흐름 | 6-Phase 매핑 후 |
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
from app.artifacts import ArtifactGenerator, ArtifactType

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
# 6-Phase Engine 실행 시, 설정에 따라 활성화된 모든 산출물이 단계별로 자동 생성됩니다.
result = await engine.run(
    requirement="기업 동향 분석 시스템 만들기",
    # ...
)

# 생성된 산출물 목록 확인
print(result.artifacts)
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

### 템플릿 위치
- `data/templates/artifacts/project_proposal.md.j2`
- `data/templates/artifacts/requirements_spec.md.j2`
- `data/templates/artifacts/agent_design.md.j2`
- 기타...

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

```bash
# 환경 변수로 산출물 생성 활성화
export ARTIFACT_GENERATION_ENABLED=true
export ENABLED_ARTIFACTS=all

# 프로젝트 생성 시 자동으로 산출물 생성
caas generate "기업 동향 분석 시스템"

# 생성된 산출물 확인
ls -la ./artifacts/
```

## 활용 사례

- **품질 검증**: 각 단계별 산출물을 검토하여 프로젝트 품질을 확인합니다.
- **문서화 자동화**: 수동으로 작성해야 하는 문서를 자동으로 생성하여 시간을 절약합니다.
- **커뮤니케이션**: 생성된 산출물을 팀원이나 이해관계자와 공유하여 명확한 소통을 돕습니다.
- **아카이빙**: 프로젝트 이력을 문서로 보존합니다.

## 제한 사항

1. **템플릿 의존성**: 일부 산출물 타입은 템플릿이 아직 제공되지 않거나, 특정 컨텍스트 데이터가 필요할 수 있습니다.
2. **포맷 지원**: 현재 Markdown 포맷을 가장 잘 지원합니다. (html, pdf는 실험적 기능)
3. **다이어그램**: Mermaid.js를 이용한 다이어그램 생성을 일부 지원합니다.

## 로드맵

- [ ] PDF 및 HTML 출력 지원 안정화
- [ ] 모든 산출물 타입에 대한 기본 템플릿 완성
- [ ] 다이어그램 자동 생성 기능 개선
- [ ] 다국어 지원 확대 (현재는 한국어/영어 중심)

---
**최종 업데이트**: 2026-02-06
**버전**: v0.4.1
