# CAAS CLI 사용 가이드

CAAS 명령줄 인터페이스(CLI) 완전 가이드입니다.

---

## 개요

CAAS CLI는 자연어 요구사항으로부터 멀티 에이전트 시스템을 생성할 수 있는 터미널 기반 인터페이스를 제공합니다. 단순한 CRUD 애플리케이션부터, CrewAI를 활용한 복잡한 멀티 에이전트 시스템, 게임 전략 AI까지 다양한 프로젝트를 생성할 수 있습니다.

**주요 기능:**
- 명령줄에서 완전한 CrewAI 프로젝트 생성
- 직접 프레임워크 사용 (API 서버 불필요)
- CAAS 6-Phase 워크플로우 실행
- 17개 이상의 다양한 도메인 지원
- 유연한 출력 및 품질 제어

---

## 설치

### 사전 준비사항

- Python 3.11+
- Git
- OpenAI 또는 Anthropic API 키

### CLI 설치

```bash
# 리포지토리 클론
git clone https://github.com/bullpeng72/CAAS.git
cd caas

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# CLI 지원 포함 설치
pip install -e ".[cli]"

# 설치 확인
caas --help
```

---

## 기본 사용법

### generate 명령

프로젝트 생성을 위한 메인 명령입니다.

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

CAAS CLI는 **20개 메인 명령어**와 다수의 서브명령어를 제공합니다.

### Setup & Configuration (설정 및 구성)

- **`caas init`**: 대화형 설정 마법사
- **`caas config`**: 설정 관리 (list, set, get)
- **`caas env`**: 환경 변수 관리 (list, set, unset)

---

### Requirement Refinement (요구사항 정제)

- **`caas analyze-gaps`**: 요구사항의 부족한 부분을 분석
- **`caas expand`**: 요구사항 자동 확장
- **`caas questions`**: 갭을 해결하기 위한 대화형 질문 생성

---

### Code Generation (코드 생성)

- **`caas generate`**: 전체 워크플로우를 실행하여 프로젝트 생성
- **`caas generate-code`**: 기존 설계 파일로부터 빠르게 코드만 생성
- **`caas codegen`**: 특정 컴포넌트(agents, tasks 등)만 재생성
- **`caas generate-phase`**: 특정 6-Phase만 실행

---

### Validation & Fixing (검증 및 수정)

- **`caas validate`**: 생성된 설계 검증 (6개 타입)
- **`caas fix`**: 3-Level Auto-Fixing으로 설계 자동 수정
- **`caas traceability`**: 요구사항-코드 간 추적성 매트릭스 생성

---

### Testing (테스트)

- **`caas test`**: 생성된 테스트 실행

---

### Management (관리)

- **`caas plugins`**: 플러그인 관리
- **`caas session`**: 프로젝트 작업 세션 관리
- **`caas workflow`**: 생성 워크플로우 제어
- **`caas status`**: 프로젝트 상태 확인
- **`caas download`**: 산출물 다운로드
- **`caas list`**: 생성된 프로젝트 목록 조회

---

## 명령 옵션

### 핵심 옵션

| 옵션 | 설명 | 기본값 |
|-----|------|--------|
| `--domain, -d` | 도메인 힌트 (17+개 지원) | 자동 감지 |
| `--output, -o` | 출력 디렉토리 | `./generated` |
| `--deployment` | 배포 대상 (docker, kubernetes, serverless) | `docker` |
| `--golden-data, -g` | 기존 Golden Data JSON 파일 | None |

### 품질 옵션

| 옵션 | 설명 | 기본값 |
|-----|------|--------|
| `--no-traceability` | 추적성 매트릭스 생성 비활성화 | 활성화됨 |
| `--no-completeness` | 완전성 검증 비활성화 | 활성화됨 |
| `--gap-filling` | 누락된 기능에 대한 자동 갭 채우기 활성화 | 비활성화됨 |
| `--no-validation` | 검증 비활성화 | 활성화됨 |
| `--no-auto-fix` | 자동 수정 비활성화 | 활성화됨 |

### 일반 옵션

| 옵션 | 설명 | 기본값 |
|---|---|---|
| `--verbosity` | 출력 상세 수준 (quiet, minimal, normal, verbose, debug) | `normal` |

---

## 지원 도메인

CAAS는 최적화된 생성을 위해 17개 이상의 도메인 타입을 지원합니다.

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
| **`GAMING`** | **Mixed** | **게임 서버, 게임 AI, 매치메이킹** |
| `DOCUMENT_MANAGEMENT` | CRUD | 문서 저장, 버전 관리 |
| `MONITORING` | Agent | 시스템 모니터링, 알림 |

---

## 사용 예시

### 예시 1: 간단한 CRUD 앱

```bash
caas generate "사용자가 할일을 생성, 편집, 삭제할 수 있는 할일 목록 애플리케이션 만들기" \
  --domain TASK_MANAGEMENT
```
**출력**: FastAPI 백엔드, SQLAlchemy 모델, Docker 배포 파일 등

### 예시 2: AI 에이전트 시스템

```bash
caas generate "뉴스를 수집하고, 감성을 분석하고, 보고서를 생성하는 금융 뉴스 분석기 만들기" \
  --domain DATA_ANALYSIS \
  --output ./fin-analyzer
```
**출력**: 뉴스 수집, 감성 분석, 보고서 생성 역할을 하는 CrewAI 멀티 에이전트 시스템

### 예시 3: 게임 전략 AI (고급)

```bash
caas generate "4:4 물고기 전투 게임을 위한 AI 에이전트를 만들어줘. 각 물고기는 고유한 스킬과 패시브를 가지고 있어. AI는 상대방의 물고기 종류를 추론(Assert)하고, 주어진 상황에서 최적의 행동(Act)을 결정해야 해." \
  --domain GAMING \
  --output ./fish-battle-ai
```
**출력**: `Pick`, `Assert`, `Act`와 같은 게임 단계별 메소드를 포함하는 복잡한 상태 기반 `AI` 클래스. 내부에 승리 전략, 적 추론 로직, 스킬 사용 판단 로직 등이 포함될 수 있습니다.

---

## 출력 구조

생성된 프로젝트의 기본 구조입니다. (전략에 따라 달라질 수 있습니다)

```
./generated/
├── src/
│   ├── agents.py            # CrewAI 에이전트 정의
│   ├── tasks.py             # 태스크 정의
│   ├── tools.py             # 커스텀 도구
│   └── crew.py              # Crew 설정
├── main.py                  # 진입점
├── requirements.txt         # 의존성
├── Dockerfile               # 컨테이너 정의
├── docker-compose.yml       # 멀티 서비스 오케스트레이션
├── README.md                # 프로젝트 문서
└── tests/                   # 생성된 테스트
    └── test_crew.py
```

---

## 모범 사례

1.  **상세한 요구사항 작성**: 생성하고자 하는 시스템의 기능, 데이터, 로직을 구체적으로 설명할수록 결과물의 품질이 높아집니다.
2.  **도메인 지정**: `--domain` 옵션을 사용하여 생성하려는 프로젝트의 종류를 명시하면, CAAS가 더 최적화된 전략과 템플릿을 사용합니다.
3.  **반복적 정제**: `generate` → `analyze-gaps` → `questions` → `expand` → `generate` 순서로 요구사항을 점진적으로 구체화하며 프로젝트를 완성도를 높여가세요.

---

## CLI 치트시트

```bash
# 기본 생성
caas generate "요구사항"

# 도메인 지정 및 출력 디렉토리 설정
caas generate "요구사항" --domain CHATBOT -o ./my-project

# Golden Data 사용
caas generate "요구사항" -g ./golden.json

# 빠른 프로토타입 (품질 검증 없이)
caas generate "프로토타입" --no-validation --no-traceability

# 상세 로그와 함께 실행
caas generate "디버깅할 요구사항" --verbosity debug

# 버전 확인
caas --version

# 도움말
caas --help
caas generate --help
```

---

## 지원

- **GitHub Issues**: https://github.com/bullpeng72/CAAS/issues
- **문서**: `docs/README_KO.md`
- **예제**: `tests/test_e2e_` 디렉토리 확인
