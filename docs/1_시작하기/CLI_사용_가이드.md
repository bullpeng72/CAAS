# CAAS CLI 사용 가이드

CAAS 명령줄 인터페이스(CLI) 완전 가이드입니다.

---

## 개요

CAAS CLI는 자연어 요구사항으로부터 멀티 에이전트 시스템을 생성할 수 있는 터미널 기반 인터페이스를 제공합니다.

**주요 기능:**
- 명령줄에서 완전한 CrewAI 프로젝트 생성
- 직접 프레임워크 사용 (API 서버 불필요)
- Phase 1-3 통합 기능 (추적성, 완전성 검증)
- 17개 도메인 타입 지원
- 유연한 출력 제어

---

## 설치

### 사전 준비사항

- Python 3.11+
- Git
- OpenAI 또는 Anthropic API 키

### CLI 설치

```bash
# 리포지토리 클론
git clone https://github.com/aidx/caas.git
cd caas

# CLI 지원 포함 설치
pip install -e ".[cli]"

# 설치 확인
caas --help
```

### 환경 설정

프로젝트 루트에 `.env` 파일 생성:

```env
# 필수: LLM API 키
OPENAI_API_KEY=sk-your-openai-key-here
# 또는
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# 선택사항
CAAS_LOG_LEVEL=INFO
```

---

## 중요: CLI 아키텍처

**CLI는 `caas_framework`를 직접 사용**하며 FastAPI 서버 실행이 필요하지 않습니다.

```
CLI 명령 → caas_framework → 코드 생성
    (API 서버 관여 없음)
```

이는 API 서버가 필요한 SDK 및 VS Code 확장과 다릅니다.

---

## 기본 사용법

### generate 명령

프로젝트 생성을 위한 메인 명령:

```bash
caas generate <요구사항> [옵션]
```

**기본 예시:**
```bash
caas generate "사용자 인증 기능이 있는 할일 관리 시스템 만들기"
```

**옵션 포함:**
```bash
caas generate "블로그 플랫폼 만들기" \
  --domain CONTENT_CREATION \
  --output ./my-blog \
  --deployment kubernetes
```

---

## 전체 CLI 명령어

CAAS CLI는 **20개 메인 명령어**와 **19개 서브명령어**를 제공합니다.

### Setup & Configuration (설정 및 구성)

#### 1. `caas init`
대화형 설정 마법사

```bash
caas init
```

**기능**:
- 프로젝트 디렉토리 초기화
- 환경 변수 설정 (.env 파일 생성)
- API 키 구성
- 기본 설정 파일 생성

#### 2. `caas config`
설정 관리

```bash
# 설정 보기
caas config list

# 설정 값 변경
caas config set <key> <value>

# 설정 값 가져오기
caas config get <key>
```

#### 3. `caas env`
환경 변수 관리

```bash
# 환경 변수 나열
caas env list

# 환경 변수 설정
caas env set OPENAI_API_KEY sk-...

# 환경 변수 삭제
caas env unset VARIABLE_NAME
```

---

### Requirement Refinement (요구사항 정제)

#### 4. `caas analyze-gaps`
요구사항 gap 분석

```bash
caas analyze-gaps <requirement> [--output gaps.json]
```

**기능**:
- 누락된 요구사항 탐지
- 불완전한 항목 식별
- Gap 리포트 생성

#### 5. `caas expand`
요구사항 자동 확장

```bash
caas expand <requirement> --gaps gaps.json [--output expanded.json]
```

**기능**:
- 데이터 모델 자동 생성
- UI 컴포넌트 추가
- NFR (비기능 요구사항) 생성
- 인수 기준 생성

#### 6. `caas questions`
대화형 질문 생성

```bash
caas questions <requirement> --gaps gaps.json
```

**기능**:
- 수동 입력 필요 항목에 대한 질문 생성
- 사용자 친화적 질문 형식
- 대화형 요구사항 정제

---

### Code Generation (코드 생성)

#### 7. `caas generate`
**전체 워크플로우** (5-10분)

```bash
caas generate <requirement> [옵션]
```

**기능**:
- BMAD 6-Phase 전체 실행
- Traceability Matrix 구축
- Completeness Validation
- Gap Filling (옵션)
- 최종 코드 생성

**예시**:
```bash
caas generate "할일 관리 앱 만들기" --output ./todo-app
```

#### 8. `caas generate-code`
**빠른 코드 생성** (1-2분)

```bash
caas generate-code --agents agents.json --tasks tasks.json [--output ./code]
```

**기능**:
- 기존 Agent/Task 스펙에서 바로 코드 생성
- Phase 1-4 건너뛰기
- 빠른 프로토타이핑

#### 9. `caas codegen`
**컴포넌트 전용 생성**

```bash
caas codegen --component agents --spec spec.json
caas codegen --component tasks --spec spec.json
caas codegen --component tools --spec spec.json
```

**기능**:
- 특정 컴포넌트만 생성
- Fine-grained 제어

#### 10. `caas generate-phase`
**Phase별 실행**

```bash
caas generate-phase --phase 1 <requirement>
caas generate-phase --phase 2 --golden golden.json
caas generate-phase --phase 3 --golden golden.json
```

**기능**:
- 특정 Phase만 실행
- 디버깅 및 테스트
- 점진적 생성

---

### Validation & Fixing (검증 및 수정)

#### 11. `caas validate`
설계 검증

```bash
caas validate --validator <type> --input <file>
```

**Validator 타입**:
- `ontology` - 온톨로지 준수 검증
- `golden` - Golden Data 정렬 검증
- `dependency` - Task 의존성 검증
- `python311` - Python 3.11+ 호환성
- `crewai` - CrewAI 프레임워크 준수
- `traceability` - Feature 추적 검증

**예시**:
```bash
caas validate --validator completeness --agents agents.json --golden golden.json
```

#### 12. `caas fix`
자동 수정

```bash
caas fix --input <file> --validator <type> [--output fixed.json]
```

**기능**:
- 3-Level Auto-Fixing
  - Template Fix (규칙 기반)
  - Rule Fix (패턴 기반)
  - LLM Fix (LLM 기반)

#### 13. `caas traceability`
추적성 매트릭스 생성

```bash
caas traceability --golden golden.json --agents agents.json --tasks tasks.json --code ./src
```

**기능**:
- Requirement → Feature → Agent → Task → Code 추적
- 전방/후방 추적
- Coverage 리포트

---

### Testing (테스트)

#### 14. `caas test`
테스트 실행

```bash
caas test --project ./generated [--coverage] [--report]
```

**기능**:
- 생성된 테스트 실행
- Coverage 측정
- 테스트 리포트 생성

---

### Management (관리)

#### 15. `caas plugins`
플러그인 관리 (6개 서브명령어)

```bash
# 플러그인 목록
caas plugins list

# 플러그인 설치
caas plugins install <name>

# 플러그인 제거
caas plugins uninstall <name>

# 플러그인 활성화/비활성화
caas plugins enable <name>
caas plugins disable <name>

# 플러그인 정보
caas plugins info <name>
```

#### 16. `caas session`
세션 관리 (7개 서브명령어)

```bash
# 세션 생성
caas session create <name>

# 세션 목록
caas session list

# 세션 전환
caas session switch <name>

# 세션 삭제
caas session delete <name>

# 세션 정보
caas session info <name>

# 세션 내보내기/가져오기
caas session export <name> --output session.json
caas session import --input session.json
```

#### 17. `caas workflow`
워크플로우 제어 (6개 서브명령어)

```bash
# 워크플로우 시작
caas workflow start <name>

# 워크플로우 중지
caas workflow stop <id>

# 워크플로우 상태
caas workflow status <id>

# 워크플로우 목록
caas workflow list

# 워크플로우 로그
caas workflow logs <id>

# 워크플로우 재시작
caas workflow restart <id>
```

#### 18. `caas status`
프로젝트 상태

```bash
caas status [--project ./generated]
```

**기능**:
- 프로젝트 상태 요약
- 생성 진행률
- 검증 결과

#### 19. `caas download`
산출물 다운로드

```bash
caas download --project ./generated --artifact <type> [--output ./artifacts]
```

**산출물 타입**:
- `all` - 모든 산출물
- `golden` - Golden Data
- `agents` - Agent 스펙
- `tasks` - Task 스펙
- `reports` - 검증 리포트

#### 20. `caas list`
프로젝트 목록

```bash
caas list [--filter <type>] [--sort <field>]
```

**기능**:
- 생성된 프로젝트 목록
- 필터링 및 정렬
- 프로젝트 요약

---

## 명령 옵션

### 핵심 옵션

| 옵션 | 설명 | 기본값 |
|-----|------|--------|
| `--domain, -d` | 도메인 힌트 (TASK_MANAGEMENT, CHATBOT 등) | 자동 감지 |
| `--output, -o` | 출력 디렉토리 | `./generated` |
| `--deployment` | 배포 대상 (docker, kubernetes, serverless) | `docker` |
| `--golden-data, -g` | 기존 Golden Data JSON 파일 | None |

### Phase 제어 옵션 (v1.0.0+)

| 옵션 | 설명 | 기본값 |
|-----|------|--------|
| `--no-traceability` | Phase 2 추적성 추적 비활성화 | 활성화됨 |
| `--no-completeness` | Phase 3 완전성 검증 비활성화 | 활성화됨 |
| `--gap-filling` | 누락된 기능에 대한 자동 갭 채우기 활성화 | 비활성화됨 |

### 품질 옵션

| 옵션 | 설명 | 기본값 |
|-----|------|--------|
| `--no-validation` | 검증 비활성화 | 활성화됨 |
| `--no-auto-fix` | 자동 수정 비활성화 | 활성화됨 |

---

## 도메인 타입

CAAS는 최적화된 생성을 위해 17개 도메인 타입을 지원합니다:

| 도메인 | 타입 | 사용 사례 |
|--------|------|----------|
| `TASK_MANAGEMENT` | CRUD | 할일 앱, 프로젝트 트래커 |
| `CONTENT_GENERATION` | Agent | 보고서 생성기, 블로그 작성기 |
| `CHATBOT` | Agent | 고객 지원, FAQ 봇 |
| `DATA_PIPELINE` | Agent | ETL, 데이터 동기화 |
| `ECOMMERCE` | Mixed | 온라인 쇼핑몰, 마켓플레이스 |
| `FINANCE` | Agent | 투자 분석, 트레이딩 |
| `HEALTHCARE` | Mixed | 환자 관리, 스케줄링 |
| `EDUCATION` | Mixed | LMS, 퀴즈 시스템 |
| `SOCIAL_MEDIA` | CRUD | 소셜 네트워크, 피드 |
| `IOT` | Agent | 디바이스 관리, 모니터링 |
| `ANALYTICS` | Agent | 데이터 분석, 시각화 |
| `SEARCH` | Mixed | 검색 엔진, 추천 |
| `WORKFLOW` | Agent | 비즈니스 프로세스 자동화 |
| `COMMUNICATION` | Mixed | 메시징, 이메일 시스템 |
| `GAMING` | Mixed | 게임 서버, 매치메이킹 |
| `DOCUMENT_MANAGEMENT` | CRUD | 문서 저장, 버전 관리 |
| `MONITORING` | Agent | 시스템 모니터링, 알림 |

---

## 사용 예시

### 예시 1: 간단한 할일 앱

```bash
caas generate "사용자가 할일을 생성, 편집, 삭제할 수 있는 할일 목록 애플리케이션 만들기"
```

**출력:**
- FastAPI 백엔드 (CRUD 엔드포인트)
- SQLite 데이터베이스
- Task 모델 및 API 라우트
- Docker 배포 파일
- ~10-15개 파일 생성

---

### 예시 2: AI 에이전트 시스템

```bash
caas generate "뉴스를 수집하고, 감성을 분석하고, 보고서를 생성하는 금융 뉴스 분석기 만들기" \
  --domain FINANCE \
  --output ./fin-analyzer
```

**출력:**
- 멀티 에이전트 CrewAI 시스템
- 뉴스 수집 에이전트
- 감성 분석 에이전트
- 보고서 생성 에이전트
- Streamlit UI
- ~20-25개 파일 생성

---

### 예시 3: Phase 기능 포함

```bash
caas generate "게시물, 댓글, 카테고리가 있는 블로그 관리 REST API 만들기" \
  --domain CONTENT_CREATION \
  --gap-filling \
  --output ./blog-api
```

**출력 포함:**
- Phase 1: 계층적 기능 (인증, CRUD, 관계)
- Phase 2: 추적성 매트릭스 (기능 → 태스크 → 코드)
- Phase 3: 완전성 보고서 (87.5/100 점수)
- 누락된 기능 자동 갭 채우기
- ~30+ 파일 생성

---

### 예시 4: 커스텀 Golden Data

이미 정제된 요구사항이 있는 경우:

```bash
caas generate "전자상거래 플랫폼 만들기" \
  --golden-data ./my-requirements.json \
  --deployment kubernetes \
  --output ./ecommerce
```

---

### 예시 5: 빠른 프로토타입 (검증 건너뛰기)

빠른 프로토타이핑을 위해:

```bash
caas generate "간단한 챗봇 만들기" \
  --no-validation \
  --no-traceability \
  --no-completeness \
  --output ./chatbot-proto
```

---

## 출력 구조

생성된 프로젝트 구조:

```
./generated/
├── agents/              # CrewAI 에이전트 정의
│   ├── agent_1.yaml
│   └── agent_2.yaml
├── tasks/               # 태스크 정의
│   ├── task_1.yaml
│   └── task_2.yaml
├── crew.yaml            # Crew 설정
├── main.py              # 진입점
├── requirements.txt     # 의존성
├── Dockerfile           # 컨테이너 정의
├── docker-compose.yml   # 멀티 서비스 오케스트레이션
├── README.md            # 프로젝트 문서
└── tests/               # 생성된 테스트
    └── test_crew.py
```

---

## 생성 출력

### 성공 출력 예시

```
╔══════════════════════════════════════════════════════════════╗
║                  CAAS 코드 생성                               ║
║            (caas_framework 직접 사용)                         ║
╚══════════════════════════════════════════════════════════════╝

✓ Framework initialized
✓ Generating code (this may take a few minutes)...

Summary:
  Phases completed:  Phase.BUSINESS, Phase.MODELING, Phase.ARCHITECTURE, Phase.DEVELOPMENT
  Features extracted: 12
  Agents generated:  4
  Tasks generated:   8
  Files generated:   15
  Generation time:   45.3s

Phase 2 - Traceability:
  Features tracked:  12
  Tasks tracked:     8
  Code files tracked: 15

Phase 3 - Completeness:
  Total features:     12
  Fully implemented:  10
  Partial:            2
  Not implemented:    0
  Implementation rate: 83.3%
  Completeness score:  87.5/100
  Status: ✅ COMPLETE

✓ Code saved to: ./generated

Next steps:
  1. cd ./generated
  2. Review generated code
  3. Install dependencies (if requirements.txt exists)
  4. Run with docker
```

---

## Phase 1-3 기능

### Phase 1: 계층적 기능 추출

계층적 분석을 사용하여 요구사항에서 2-4배 더 많은 기능을 추출합니다.

**활성화 (기본값):**
```bash
caas generate "할일 관리 시스템 만들기"
```

**비활성화:**
```bash
caas generate "할일 관리 시스템 만들기" --no-hierarchical
```

**출력:** `features_hierarchical.json`

---

### Phase 2: 추적성 매트릭스

양방향 매핑 추적: 기능 ↔ 태스크 ↔ 코드 파일.

**활성화 (기본값):**
```bash
caas generate "REST API 만들기"
```

**비활성화:**
```bash
caas generate "REST API 만들기" --no-traceability
```

**출력:** `traceability_matrix.json`

---

### Phase 3: 완전성 검증

AST 분석 + LLM 검증을 사용하여 구현 완전성을 검증합니다.

**활성화 (기본값):**
```bash
caas generate "블로그 플랫폼 만들기"
```

**비활성화:**
```bash
caas generate "블로그 플랫폼 만들기" --no-completeness
```

**출력:** `completeness_report.json`

---

### 갭 채우기 (실험적)

완전성 검증으로 감지된 누락된 기능을 자동으로 채웁니다.

**활성화:**
```bash
caas generate "API 서버 만들기" --gap-filling
```

**출력:**
```
Gap Filling:
  Features filled:   3
  Files updated:     5
  Status: ✅ SUCCESS
```

---

## 모범 사례

### 1. 상세한 요구사항 작성

**나쁜 예:**
```bash
caas generate "할일 앱 만들기"
```

**좋은 예:**
```bash
caas generate "다음 기능을 가진 할일 관리 시스템 만들기:
- 사용자 인증 (이메일/비밀번호)
- 할일 CRUD 작업 (제목, 설명, 마감일, 우선순위)
- 여러 사용자에게 할일 할당
- 상태, 우선순위, 담당자별 할일 필터링
- FastAPI REST API
- PostgreSQL 데이터베이스
- Docker 배포"
```

---

### 2. 더 나은 결과를 위해 도메인 지정

```bash
# 일반 (느림, 최적화 안됨)
caas generate "금융 분석기 만들기"

# 도메인 지정 (빠름, 최적화됨)
caas generate "금융 분석기 만들기" --domain FINANCE
```

---

### 3. 반복을 위해 Golden Data 사용

첫 번째 생성:
```bash
caas generate "블로그 플랫폼 만들기" --output ./blog-v1
```

`golden_data.json` 검토 후, 정제하고 재생성:
```bash
# golden_data.json을 수동으로 편집
caas generate "블로그 플랫폼 만들기" \
  --golden-data ./blog-v1/golden_data.json \
  --output ./blog-v2
```

---

### 4. 사용 사례에 따라 Phase 기능 제어

**개발/프로토타이핑 (빠름):**
```bash
caas generate "빠른 프로토타입" \
  --no-traceability \
  --no-completeness \
  --no-validation
```

**프로덕션 (포괄적):**
```bash
caas generate "프로덕션 API" \
  --gap-filling \
  --deployment kubernetes
```

---

## 일반적인 사용 사례

### 1. CRUD 백엔드 API

```bash
caas generate "CRUD 작업, 검색, 페이지네이션 기능이 있는 제품 관리 REST API 만들기" \
  --domain TASK_MANAGEMENT \
  --deployment docker
```

---

### 2. AI 에이전트 시스템

```bash
caas generate "티켓 라우팅, 응답 생성, 에스컬레이션 기능이 있는 고객 지원 멀티 에이전트 시스템 만들기" \
  --domain CHATBOT \
  --deployment kubernetes
```

---

### 3. 데이터 처리 파이프라인

```bash
caas generate "API에서 데이터를 추출하고, 비즈니스 규칙으로 변환하고, 웨어하우스에 로드하는 ETL 파이프라인 만들기" \
  --domain DATA_PIPELINE \
  --deployment serverless
```

---

### 4. 풀스택 애플리케이션

```bash
caas generate "다음 기능을 가진 전자상거래 플랫폼 만들기:
- 카테고리별 제품 카탈로그
- 장바구니 및 결제
- 사용자 인증 및 프로필
- 주문 관리
- 관리자 패널
- 결제 통합 (Stripe)
- 이메일 알림
- 검색 및 필터링" \
  --domain ECOMMERCE \
  --gap-filling \
  --output ./ecommerce
```

---

## 문제 해결

### 문제: "caas: command not found"

**해결책:**
```bash
# CLI 의존성 재설치
pip install -e ".[cli]"

# 또는 전체 경로 사용
python -m caas_cli.commands.generate "요구사항"
```

---

### 문제: "OPENAI_API_KEY not set"

**해결책:**
```bash
# .env 파일 확인
cat .env | grep OPENAI_API_KEY

# 또는 임시로 설정
export OPENAI_API_KEY=sk-your-key
caas generate "앱 만들기"
```

---

### 문제: import 오류로 생성 실패

**해결책:**
```bash
# 프레임워크 재설치
cd /path/to/caas
pip install -e . --force-reinstall

# Python 캐시 정리
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

---

### 문제: 생성된 코드에 오류 있음

**해결책:**

1. **자동 수정 활성화 (기본값):**
   ```bash
   caas generate "요구사항"
   ```

2. **갭 채우기 시도:**
   ```bash
   caas generate "요구사항" --gap-filling
   ```

3. **완전성 보고서 검토:**
   ```bash
   cat ./generated/completeness_report.json
   ```

---

### 문제: 느린 생성

**해결책:**

1. **프로토타이핑을 위해 비용이 많이 드는 phase 비활성화:**
   ```bash
   caas generate "프로토타입" \
     --no-traceability \
     --no-completeness
   ```

2. **도메인별로 더 작은 요구사항 사용**

3. **API rate limit 확인**

---

## 고급 사용법

### 커스텀 출력 구조

```bash
caas generate "API 만들기" \
  --output ./my-projects/api-v2 \
  --deployment kubernetes
```

---

### 여러 배포

다른 대상에 대해 생성:

```bash
# Docker 버전
caas generate "서비스 만들기" --deployment docker -o ./service-docker

# Kubernetes 버전
caas generate "서비스 만들기" --deployment kubernetes -o ./service-k8s

# Serverless 버전
caas generate "서비스 만들기" --deployment serverless -o ./service-lambda
```

---

### 스크립팅 및 자동화

배치 생성을 위한 bash 스크립트 생성:

```bash
#!/bin/bash
# generate_all.sh

REQUIREMENTS=(
  "사용자 인증 서비스 만들기"
  "제품 카탈로그 서비스 만들기"
  "주문 관리 서비스 만들기"
)

for req in "${REQUIREMENTS[@]}"; do
  name=$(echo "$req" | sed 's/만들기//' | sed 's/ /-/g')
  echo "Generating: $name"
  caas generate "$req" --output "./services/$name"
done
```

---

## 다른 도구와의 통합

### Git 통합

```bash
# 프로젝트 생성
caas generate "API 만들기" --output ./my-api
cd ./my-api

# git 초기화
git init
git add .
git commit -m "CAAS에 의한 초기 생성"
```

---

### Docker 통합

```bash
# Docker 배포로 생성
caas generate "서비스 만들기" --deployment docker --output ./service

# 빌드 및 실행
cd ./service
docker-compose up -d
```

---

### CI/CD 통합

```yaml
# .github/workflows/generate.yml
name: CAAS로 코드 생성

on:
  workflow_dispatch:
    inputs:
      requirement:
        description: '요구사항 설명'
        required: true

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Python 설정
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: CAAS 설치
        run: pip install -e ".[cli]"

      - name: 코드 생성
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          caas generate "${{ github.event.inputs.requirement }}" \
            --output ./generated

      - name: Artifact 업로드
        uses: actions/upload-artifact@v2
        with:
          name: generated-code
          path: ./generated
```

---

## 다음 단계

CLI로 코드 생성 후:

1. **생성된 코드 검토**: 에이전트, 태스크, 구현 확인
2. **커스터마이징**: 템플릿 수정, 비즈니스 로직 추가
3. **테스트**: 생성된 테스트 실행, 더 많은 테스트 추가
4. **배포**: Docker/Kubernetes 파일을 사용하여 배포
5. **모니터링**: 로깅 및 모니터링 설정

---

## 추가 리소스

- **설치 가이드**: [설치_가이드.md](./설치_가이드.md)
- **빠른 시작**: [빠른_시작_가이드.md](./빠른_시작_가이드.md)
- **아키텍처**: [아키텍처_가이드.md](../3_시스템_문서/아키텍처_가이드.md)
- **개발 방법론**: [개발_방법론.md](../2_개발_방법론/개발_방법론.md)
- **배포**: [배포_가이드.md](../3_시스템_문서/배포_가이드.md)
- **도구 매핑**: [도구_매핑.md](../4_기능_가이드/도구_매핑.md)
- **예제**: `examples/` 디렉토리 확인

---

## CLI vs 다른 인터페이스

| 기능 | CLI | Python SDK | Python API |
|------|-----|------------|------------|
| **API 서버 필요** | ❌ 아니오 | ❌ 아니오 | ❌ 아니오 |
| **대화형** | ❌ 아니오 | ❌ 아니오 | ⚠️ 제한적 |
| **스크립팅/자동화** | ✅ 예 | ✅ 예 | ✅ 예 |
| **프로그래밍 방식 접근** | ⚠️ 제한적 | ✅ 예 | ✅ 예 |
| **타입 안전성** | ❌ 아니오 | ✅ 예 | ✅ 예 |
| **적합한 용도** | 터미널 사용자, CI/CD | 통합, 자동화 | 고급 통합 |

**참고**: CAAS는 Framework-First 아키텍처로, 별도의 UI 애플리케이션은 제공하지 않습니다. UI는 생성되는 프로젝트의 일부로 포함됩니다.

---

## CLI 치트시트

### 자주 사용하는 명령어

```bash
# 기본 생성
caas generate "요구사항"

# 도메인 지정
caas generate "요구사항" --domain CHATBOT

# 출력 디렉토리 지정
caas generate "요구사항" -o ./my-project

# 모든 Phase 포함
caas generate "요구사항" --gap-filling

# 빠른 프로토타입 (Phase 없이)
caas generate "요구사항" --no-traceability --no-completeness

# 커스텀 배포
caas generate "요구사항" --deployment kubernetes

# Golden Data 사용
caas generate "요구사항" -g ./golden.json

# 버전 확인
caas --version

# 도움말
caas --help
caas generate --help
```

---

## 지원

- **GitHub Issues**: https://github.com/aidx/caas/issues
- **문서**: https://github.com/aidx/caas#readme
- **예제**: CLI 사용 패턴은 `examples/` 디렉토리 확인
