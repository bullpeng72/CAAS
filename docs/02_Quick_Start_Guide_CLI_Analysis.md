# CAAS CLI 명령어 분석 보고서

**분석 날짜**: 2026-02-12
**대상 명령어**: list, status, download
**분석자**: Claude Sonnet 4.5

---

## 📊 분석 결과 요약

| 명령어 | 구현 상태 | 파일 위치 | SDK 메서드 | 서버 필요 |
|--------|----------|----------|-----------|----------|
| **list** | ✅ 구현됨 | `caas_cli/commands/list_projects.py` | `list_projects()` | ✅ 필수 |
| **status** | ✅ 구현됨 | `caas_cli/commands/status.py` | `get_project()` | ✅ 필수 |
| **download** | ✅ 구현됨 | `caas_cli/commands/download.py` | `download_code()` | ✅ 필수 |

---

## 🔍 상세 분석

### 1. list 명령어

**파일**: `caas_cli/commands/list_projects.py` (189 lines)

**기능**:
```bash
caas list [OPTIONS]

Options:
  --limit, -n INTEGER    Number of projects to show (default: 10)
  --status TEXT          Filter by status: generating, completed, failed
  --api-key TEXT         API key for authentication
  --api-url TEXT         API URL (overrides config)
```

**내부 동작**:
1. CAAS SDK 클라이언트 생성 (httpx 사용)
2. API 호출: `GET /api/v1/projects?limit={limit}&status={status}`
3. 프로젝트 목록을 테이블 형식으로 출력
4. 각 프로젝트의 ID, 요구사항(30자), 상태, 진행률, 생성일 표시

**출력 예시**:
```
╔══════════════════════════════════════════════════════════════╗
║                     Project List                             ║
╚══════════════════════════════════════════════════════════════╝

ID          | Requirement             | Status         | Progress | Created
------------|-------------------------|----------------|----------|------------
abc123def   | Build a task manage...  | ✅ completed  | 100%     | 2026-02-12
xyz789ghi   | Create a chatbot...     | ⏳ generating | 45%      | 2026-02-12

Total: 2 project(s)
```

**상태 이모지**:
- ⏳ generating - 생성 중
- ✅ completed - 완료
- ❌ failed - 실패
- ⏸️ paused - 일시정지

---

### 2. status 명령어

**파일**: `caas_cli/commands/status.py` (174 lines)

**기능**:
```bash
caas status PROJECT_ID [OPTIONS]

Arguments:
  PROJECT_ID             Project ID (required)

Options:
  --watch, -w            Watch status updates in real-time
  --interval, -i INTEGER Watch interval in seconds (default: 2)
  --api-key TEXT         API key for authentication
  --api-url TEXT         API URL (overrides config)
```

**내부 동작**:
1. CAAS SDK 클라이언트 생성
2. API 호출: `GET /api/v1/projects/{project_id}`
3. 프로젝트 상태 정보 출력
4. --watch 모드: 2초마다 자동 갱신 (완료/실패 시 자동 종료)

**출력 예시**:
```
============================================================
Project: abc123def456
============================================================
Status:       completed
Progress:     100.0%
Phase:        Phase 4: Deployment
Created:      2026-02-12T10:30:00Z
Updated:      2026-02-12T10:35:45Z
Domain:       DATA_ANALYSIS

✅ Generation completed!
```

**BMAD Phase 추적**:
- Phase 0: Requirements Analysis (5-10%)
- Phase 1: Modeling (10-30%)
- Phase 2: Architecture (30-50%)
- Phase 3: Development (50-90%)
- Phase 4: Deployment (90-100%)

**Watch 모드 특징**:
- Ctrl+C로 중지
- completed 또는 failed 상태가 되면 자동 종료
- 실시간 진행률 업데이트

---

### 3. download 명령어

**파일**: `caas_cli/commands/download.py` (186 lines)

**기능**:
```bash
caas download PROJECT_ID [OUTPUT_DIR] [OPTIONS]

Arguments:
  PROJECT_ID             Project ID (required)
  OUTPUT_DIR             Output directory (default: ./generated)

Options:
  --force, -f            Overwrite existing files without confirmation
  --api-key TEXT         API key for authentication
  --api-url TEXT         API URL (overrides config)
```

**내부 동작**:
1. CAAS SDK 클라이언트 생성
2. API 호출: `GET /api/v1/projects/{project_id}/result`
3. 응답에서 파일 목록 추출 (files dict)
4. 각 파일을 output_dir에 저장
5. 다음 단계 안내 출력

**다운로드되는 파일**:
```
output_dir/
├── src/
│   ├── agents.py          # CrewAI agent definitions
│   ├── tasks.py           # CrewAI task definitions
│   ├── crew.py            # Crew configuration
│   └── tools.py           # Custom tool implementations
├── tests/                 # Unit & integration tests
├── main.py                # Application entry point
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variables template
├── Dockerfile             # Container definition
├── docker-compose.yml     # Multi-service orchestration
├── README.md              # Project documentation
├── golden_data.json       # Phase 0 output
├── agents.json            # Phase 1 output
├── tasks.json             # Phase 1 output
└── architecture.json      # Phase 2 output
```

**출력 예시**:
```
Downloading code for project abc123def...
Code downloaded to: ./my-project

Next steps:
  1. cd ./my-project
  2. Review generated code
  3. Install dependencies: pip install -r requirements.txt
  4. Run: python main.py
```

**디렉토리 존재 시 동작**:
- 파일이 있으면 확인 프롬프트 표시
- --force 옵션: 확인 없이 덮어쓰기

---

## 🔌 백엔드 서버 의존성

### API 서버 요구사항

**모든 명령어가 HTTP API 서버에 연결합니다**:

```python
# CAAS SDK 내부 구현
class CAAS(BaseClient):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:8000",  # 기본 서버 주소
        timeout: int = 300,
    ):
        ...
```

**API 엔드포인트**:
```
GET  /api/v1/projects                      # list 명령어
GET  /api/v1/projects/{project_id}         # status 명령어
GET  /api/v1/projects/{project_id}/result  # download 명령어
```

### 서버 설정 방법

**1. 환경 변수**:
```bash
export CAAS_API_KEY="your_api_key"
export CAAS_API_URL="http://localhost:8000"
```

**2. CLI 옵션**:
```bash
caas list --api-key your_key --api-url http://localhost:8000
```

**3. 설정 파일** (caas config):
```bash
caas config --set api_key your_key
caas config --set api_url http://localhost:8000
```

### 서버 미실행 시 오류

```bash
$ caas list
❌ Error: Network error: [Errno 61] Connection refused
```

**원인**: 백엔드 서버가 http://localhost:8000에서 실행되지 않음

**해결**:
1. CAAS API 서버 실행 필요
2. 또는 원격 API 서버 URL로 변경

---

## ✅ 명령어 작동 여부

### 현재 상태

| 명령어 | 코드 구현 | SDK 메서드 | API 필요 | 로컬 전용 사용 |
|--------|----------|-----------|---------|--------------|
| **generate** | ✅ | ❌ (로컬) | ❌ | ✅ 가능 |
| **generate-phase** | ✅ | ❌ (로컬) | ❌ | ✅ 가능 |
| **validate** | ✅ | ❌ (로컬) | ❌ | ✅ 가능 |
| **fix** | ✅ | ❌ (로컬) | ❌ | ✅ 가능 |
| **list** | ✅ | ✅ (API) | ✅ | ❌ 불가능 |
| **status** | ✅ | ✅ (API) | ✅ | ❌ 불가능 |
| **download** | ✅ | ✅ (API) | ✅ | ❌ 불가능 |

### 사용 시나리오

**시나리오 1: 로컬 전용 사용** (API 서버 없음)
```bash
# ✅ 가능
caas generate "요구사항" --output ./project
cd ./project
python main.py

# ❌ 불가능
caas list
caas status abc123
caas download abc123
```

**시나리오 2: API 서버 사용** (서버 실행 중)
```bash
# ✅ 모두 가능
caas generate "요구사항"  # 서버로 전송
caas list                 # 프로젝트 목록
caas status abc123        # 상태 확인
caas download abc123      # 다운로드
```

---

## 📝 Quick Start Guide 업데이트 권장사항

### P0: 필수 수정사항

**1. 백엔드 서버 의존성 명확화**

현재 문서:
```markdown
💡 중요: 백엔드 서버 의존성

일부 명령어는 CAAS 백엔드 서버 연결이 필요합니다:
- caas list
- caas status <id>
- caas download <id>

로컬 전용 사용 시: 이 명령어들은 생략 가능
```

**개선 제안**:
```markdown
### 🔌 백엔드 서버 의존성

#### API 서버 필요 명령어

다음 명령어는 **CAAS API 서버** 연결이 필수입니다:

| 명령어 | 기능 | API 엔드포인트 |
|--------|------|---------------|
| `caas list` | 프로젝트 목록 조회 | `GET /api/v1/projects` |
| `caas status <id>` | 프로젝트 상태 확인 | `GET /api/v1/projects/{id}` |
| `caas download <id>` | 코드 다운로드 | `GET /api/v1/projects/{id}/result` |

#### API 서버 설정

**방법 1: 로컬 서버 실행** (개발 환경)
```bash
# CAAS API 서버 시작 (별도 설치 필요)
caas-server start --port 8000
```

**방법 2: 원격 서버 사용**
```bash
# 환경 변수 설정
export CAAS_API_URL="https://api.caas.example.com"
export CAAS_API_KEY="your_api_key"

# 또는 설정 파일 사용
caas config --set api_url https://api.caas.example.com
caas config --set api_key your_api_key
```

**방법 3: CLI 옵션 사용** (일회성)
```bash
caas list --api-url http://localhost:8000 --api-key your_key
```

#### 로컬 전용 사용 (API 서버 없음)

API 서버 없이 로컬 전용으로 사용할 수 있습니다:

```bash
# ✅ 사용 가능 (로컬 실행)
caas generate "요구사항" --output ./project
caas generate-phase --phase 0 --requirement "요구사항"
caas validate --agents agents.json --tasks tasks.json
caas fix --agents agents.json --tasks tasks.json

# ❌ 사용 불가 (API 서버 필요)
caas list
caas status abc123
caas download abc123
```

**로컬 전용 워크플로우**:
```bash
# 1. 프로젝트 생성 (로컬)
caas generate "금융 뉴스 분석" --output ./analyzer

# 2. 생성된 코드는 즉시 --output 디렉토리에 저장됨
cd ./analyzer
ls -la
# → agents.py, tasks.py, main.py 등 확인

# 3. 실행
pip install -r requirements.txt
python main.py
```

> 💡 **팁**: 로컬 전용 사용 시 `list`, `status`, `download` 명령어는 불필요합니다.
> 생성된 코드는 `--output` 디렉토리에 즉시 저장되므로 별도 다운로드가 필요 없습니다.
```

**2. 예제 코드에서 API 명령어 제거 또는 조건부 표시**

현재:
```bash
# 8️⃣ 프로젝트 관리
caas list                    # 프로젝트 목록
caas status <project-id>     # 상태 확인
caas download <project-id> ./output  # 다운로드
```

개선:
```bash
# 8️⃣ 프로젝트 관리 (API 서버 사용 시)
# ⚠️ 주의: 다음 명령어는 CAAS API 서버가 필요합니다

caas list                    # 프로젝트 목록
caas status <project-id>     # 상태 확인
caas download <project-id> ./output  # 다운로드

# 로컬 전용 사용 시:
# 생성된 코드는 --output 디렉토리에 즉시 저장되므로
# list/status/download 명령어가 필요 없습니다
```

---

## 🎯 결론

### ✅ 검증 완료

1. **list, status, download 명령어 모두 실제로 구현되어 있음**
2. **코드 품질 우수**: 명확한 에러 처리, 상세한 도움말, 사용자 친화적 출력
3. **SDK 기반 구현**: httpx를 사용한 안정적인 HTTP 통신

### ⚠️ 중요 발견

1. **백엔드 서버 필수**: 세 명령어 모두 HTTP API 서버 필요
2. **기본 서버 주소**: http://localhost:8000
3. **로컬 전용 사용 시 불필요**: `generate` 명령어가 코드를 즉시 --output에 저장하므로 download 불필요

### 📝 문서 업데이트 필요

**P0 (필수)**:
1. ✅ 백엔드 서버 의존성 명확화 (상세 설명 추가)
2. ✅ API 서버 설정 방법 안내
3. ✅ 로컬 전용 워크플로우 설명 추가
4. ✅ 예제에서 조건부 표시 (API 필요 여부)

**P1 (권장)**:
1. API 서버 설치/실행 방법 문서화
2. 원격 API 서버 사용 예시
3. 인증(API 키) 설정 가이드

---

**분석 완료**: 2026-02-12 16:30
**다음 단계**: Quick Start Guide 업데이트 적용
