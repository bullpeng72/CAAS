# CAAS 배포 가이드

CAAS (CrewAI Agent Auto-generation System) 프로덕션 배포를 위한 완전 가이드입니다.

---

## 목차

- [배포 방식 선택](#배포-방식-선택)
- [로컬 개발 환경](#로컬-개발-환경)
- [프로덕션 배포](#프로덕션-배포)
- [Docker 배포](#docker-배포)
- [환경 변수 설정](#환경-변수-설정)
- [보안 고려사항](#보안-고려사항)
- [생성된 프로젝트 배포](#생성된-프로젝트-배포)
- [문제 해결](#문제-해결)

---

## CAAS 설치

### PyPI 설치 (권장)

일반 사용자에게 권장하는 방법입니다.

```bash
pip install caas
```

**포함 내용:**
- ✅ `caas_framework` - 코어 프레임워크 (UI-독립적)
- ✅ `caas_cli` - CLI 도구 (필수 포함)
- ✅ `caas_sdk` - Python SDK
- ✅ `data/` - 템플릿, 온톨로지
- ✅ `scripts/` - 자동화 스크립트

**사용 방법:**

```bash
# CLI 사용
caas generate "할일 관리 시스템" --output ./generated

# 라이브러리 사용
python -c "from caas_framework import CrewAIFramework; print('OK')"
```

### 소스 설치

개발 목적이거나 최신 버전을 사용하려는 경우:

```bash
git clone https://github.com/bullpeng72/CAAS.git
cd caas
pip install -e .
```

---

## 배포 방식 선택

CAAS는 두 가지 그래프 백엔드를 지원합니다:

| 방식 | 적합한 용도 | 장점 | 단점 |
|-----|-----------|-----|-----|
| **임베디드 그래프** | 개발, 테스트, 데모, 소규모 | - 설치 불필요<br>- 즉시 시작 가능<br>- 별도 서버 불필요 | - 성능 제한 (~1000 노드)<br>- JSON 파일 기반 |
| **Neo4j** | 프로덕션, 대규모 | - 높은 성능<br>- 무제한 확장<br>- 고급 쿼리 지원 | - 설치 필요<br>- 추가 리소스 필요 |

### 권장사항

- **개발/테스트**: 임베디드 그래프 사용
- **프로덕션**: Neo4j 사용 (특히 패턴 라이브러리가 큰 경우)
- **데모/POC**: 임베디드 그래프 사용

---

## 로컬 개발 환경

### 방법 1: PyPI 설치 (권장)

가장 빠르고 간단한 시작 방법입니다.

```bash
# CAAS 설치
pip install caas

# 설치 확인
caas --version
```

### 방법 2: 소스 설치 (개발용)

소스 코드를 수정하거나 최신 개발 버전을 사용하려는 경우:

#### 1. 저장소 클론

```bash
git clone https://github.com/bullpeng72/CAAS.git
cd caas
```

#### 2. 가상 환경 생성

**pip 사용:**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

**conda 사용:**
```bash
conda env create -f environment.yml
conda activate caas
```

#### 3. 의존성 설치

```bash
# 기본 설치
pip install -e .

# 개발 의존성 포함
pip install -e ".[dev]"
```

#### 5. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일 편집:
```env
# LLM API 키 (하나 이상 필수)
# 옵션 1: OpenAI
OPENAI_API_KEY=sk-your-openai-api-key

# 옵션 2: Anthropic
# ANTHROPIC_API_KEY=sk-ant-your-api-key

# 옵션 3: Ollama (로컬 LLM, API 키 불필요) ✨ NEW
# OLLAMA_API_BASE=http://localhost:11434/v1
# LLM_PROVIDER=ollama
# LLM_MODEL=llama3

# 그래프 백엔드 설정 (임베디드 사용)
GRAPH_BACKEND=embedded
EMBEDDED_GRAPH_STORAGE=./data/embedded_graph.json

# 애플리케이션 설정
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO

# 출력 디렉토리
OUTPUT_DIR=./generated
TEMPLATE_DIR=./data/templates
```

#### 6. 임베디드 그래프 초기화

```bash
python scripts/seed_embedded_patterns.py
```

출력 예시:
```
✅ 임베디드 그래프 초기화 완료
📊 20개 패턴 로드됨
💾 저장 위치: ./data/embedded_graph.json
```

#### 7. 애플리케이션 실행

```bash
# CLI 사용
caas generate "할일 관리 시스템 만들기"

# 또는 Python API
python your_script.py  # SixPhaseEngine 사용
```

---

### 방법 2: Neo4j 사용

프로덕션 환경이나 대규모 패턴 라이브러리가 필요한 경우.

#### 1-4. 위 임베디드 방식의 1-4단계 동일

#### 5. Neo4j 설치 및 실행

**Docker 사용 (권장):**
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your-secure-password \
  -v neo4j_data:/data \
  -v neo4j_logs:/logs \
  neo4j:5-community
```

**로컬 설치:**
- [Neo4j 다운로드](https://neo4j.com/download/)
- 설치 후 Neo4j Desktop 또는 서비스로 실행

#### 6. Neo4j 스키마 및 데이터 초기화

```bash
# 스키마 생성
python scripts/setup_neo4j.py

# 초기 패턴 데이터 삽입
python scripts/seed_patterns.py
```

#### 7. 환경 변수 설정 (Neo4j 모드)

`.env` 파일 편집:
```env
# LLM API 키 (하나 이상 필수)
# 옵션 1: OpenAI
OPENAI_API_KEY=sk-your-openai-api-key

# 옵션 2: Anthropic
# ANTHROPIC_API_KEY=sk-ant-your-api-key

# 옵션 3: Ollama (로컬 LLM, API 키 불필요) ✨ NEW
# OLLAMA_API_BASE=http://localhost:11434/v1
# LLM_PROVIDER=ollama
# LLM_MODEL=llama3

# Neo4j 설정
GRAPH_BACKEND=neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password

# 애플리케이션 설정
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO
```

---

## 프로덕션 배포

### 사전 준비

1. **서버 요구사항**
   - CPU: 2코어 이상
   - RAM: 4GB 이상 (Neo4j 사용 시 8GB 권장)
   - 디스크: 10GB 이상
   - OS: Ubuntu 20.04+ / RHEL 8+ / Debian 11+

2. **네트워크**
   - 포트 7474, 7687 (Neo4j, 선택사항)
   - CAAS는 CLI/Python API로 작동하므로 별도 포트 불필요

### 배포 단계

#### 1. 서버 설정

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Python 3.11 설치
sudo apt install python3.11 python3.11-venv python3.11-dev -y

# Git 설치
sudo apt install git -y
```

#### 2. 애플리케이션 배포

```bash
# 배포 디렉토리 생성
sudo mkdir -p /opt/caas
sudo chown $USER:$USER /opt/caas
cd /opt/caas

# 저장소 클론
git clone https://github.com/bullpeng72/CAAS.git .

# 가상 환경 생성
python3.11 -m venv venv
source venv/bin/activate

# 의존성 설치 (프로덕션만)
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. 환경 변수 설정

```bash
# .env 파일 생성
cat > .env << 'EOF'
# LLM API Keys (하나 이상 필수)
# 옵션 1: OpenAI
OPENAI_API_KEY=sk-your-production-api-key

# 옵션 2: Anthropic
ANTHROPIC_API_KEY=sk-ant-your-production-api-key

# 옵션 3: Ollama (로컬 LLM, API 키 불필요) ✨ NEW
# OLLAMA_API_BASE=http://localhost:11434/v1
# LLM_PROVIDER=ollama
# LLM_MODEL=llama3

# Graph Backend
GRAPH_BACKEND=neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=secure-production-password

# Application Settings
APP_ENV=production
DEBUG=false
LOG_LEVEL=WARNING

# Output Directories
OUTPUT_DIR=/opt/caas/generated
TEMPLATE_DIR=/opt/caas/data/templates
EOF

# 권한 설정 (보안)
chmod 600 .env
```

#### 4. Neo4j 설치 (프로덕션)

**Docker 사용:**
```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Neo4j 컨테이너 실행
docker run -d \
  --name neo4j-prod \
  --restart unless-stopped \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/secure-production-password \
  -e NEO4J_dbms_memory_heap_initial__size=1G \
  -e NEO4J_dbms_memory_heap_max__size=2G \
  -v /opt/caas/data/neo4j:/data \
  -v /opt/caas/logs/neo4j:/logs \
  neo4j:5-community
```

#### 5. 데이터 초기화

```bash
source venv/bin/activate
python scripts/setup_neo4j.py
python scripts/seed_patterns.py
```

#### 6. 배포 완료 및 검증

CAAS는 CLI/Python API로 작동하므로 별도의 웹 서버나 systemd 서비스가 필요하지 않습니다.

```bash
# 설치 확인
source venv/bin/activate
caas --version

# 테스트 실행
caas generate "간단한 할일 앱" --output /opt/caas/test-output

# CLI 접근성 확인
which caas
```

**참고**:
- CAAS 자체는 웹 서버가 아니므로 Nginx나 systemd 설정이 불필요합니다
- 생성된 프로젝트가 FastAPI 백엔드인 경우, 해당 프로젝트를 배포할 때 Nginx/Gunicorn 설정이 필요합니다 (아래 "생성된 프로젝트 배포" 섹션 참조)
- 정기적인 코드 생성이 필요한 경우 cron job으로 CAAS CLI 명령을 스케줄링할 수 있습니다

---

## Docker 배포

Docker Compose를 사용한 빠른 배포 방법입니다.

### 1. Docker 및 Docker Compose 설치

```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose 설치 (최신 버전)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 환경 변수 설정

`.env` 파일 생성:
```env
# LLM API Keys (하나 이상 필수)
# 옵션 1: OpenAI
OPENAI_API_KEY=sk-your-api-key

# 옵션 2: Anthropic
ANTHROPIC_API_KEY=sk-ant-your-api-key

# 옵션 3: Ollama (로컬 LLM, API 키 불필요) ✨ NEW
# OLLAMA_API_BASE=http://localhost:11434/v1
# LLM_PROVIDER=ollama
# LLM_MODEL=llama3

# Neo4j Settings
NEO4J_PASSWORD=secure-password

# Application Settings
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
```

### 3. Docker Compose 실행

```bash
cd docker
docker-compose up -d
```

### 4. 서비스 확인

```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f caas

# 특정 서비스만 재시작
docker-compose restart caas
```

---

## 환경 변수 설정

### 필수 환경 변수

| 변수명 | 설명 | 예시 |
|-------|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 (옵션 1) | `sk-...` |
| `ANTHROPIC_API_KEY` | Anthropic API 키 (옵션 2) | `sk-ant-...` |
| `OLLAMA_API_BASE` | Ollama API 베이스 URL (옵션 3) ✨ NEW | `http://localhost:11434/v1` |
| `GRAPH_BACKEND` | 그래프 백엔드 선택 | `embedded` 또는 `neo4j` |

**참고**: 최소 하나의 LLM Provider가 필요합니다 (OpenAI, Anthropic, 또는 Ollama).

### LLM 설정

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `LLM_PROVIDER` | `openai` | LLM 제공자 (`openai`, `anthropic`, `ollama`) |
| `LLM_MODEL` | `gpt-4-turbo-preview` | 모델명 (OpenAI: `gpt-4o`, Anthropic: `claude-3-opus`, Ollama: `llama3`) |

### Neo4j 설정 (GRAPH_BACKEND=neo4j)

| 변수명 | 기본값 | 설명 |
|-------|--------|------|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j 연결 URI |
| `NEO4J_USER` | `neo4j` | 사용자명 |
| `NEO4J_PASSWORD` | `password` | 비밀번호 |

---

## 보안 고려사항

### 1. API 키 관리

```bash
# .env 파일 권한 제한
chmod 600 .env

# Git에서 제외
echo ".env" >> .gitignore
```

### 2. 네트워크 보안

```bash
# UFW 사용 (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Neo4j 포트는 로컬만 허용
sudo ufw deny 7474
sudo ufw deny 7687
```

### 3. 최신 개선사항 (2026-01-31) ✨

CAAS의 보안 기능이 향상되었습니다:

- ✅ **tools.py 항상 생성**: Fallback 메커니즘으로 악의적 코드 삽입 방지
- ✅ **도구명 Sanitization**: 한국어 도구명 자동 검증 및 변환
- ✅ **에러 처리 강화**: 모든 LLM 호출에 try-except 및 로깅
- ✅ **BaseTool 검증**: 생성된 도구 코드가 BaseTool 상속 여부 확인

---

## 생성된 프로젝트 배포

CAAS가 생성한 프로젝트를 배포하는 방법입니다.

### 1. CrewAI 프로젝트 배포 (AGENT_BASED)

#### 로컬 실행

```bash
# 생성된 프로젝트로 이동
cd generated/financial_news_analysis

# 의존성 설치
pip install -r requirements.txt

# .env 파일 생성
cat > .env << 'EOF'
# 하나 이상의 LLM Provider 필요
OPENAI_API_KEY=sk-your-api-key
# 또는 Ollama 사용 (API 키 불필요)
# OLLAMA_API_BASE=http://localhost:11434/v1
# LLM_PROVIDER=ollama
# LLM_MODEL=llama3
EOF

# 실행
python main.py
```

#### Docker 배포

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV OPENAI_API_KEY=""
CMD ["python", "main.py"]
```

---

### 2. FastAPI CRUD 백엔드 배포 (CRUD_BASED)

#### 로컬 개발 실행

```bash
cd generated/todo_app

# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행
uvicorn backend.main:app --reload --port 8000
```

#### 프로덕션 배포 (Gunicorn)

```bash
# Gunicorn 설치
pip install gunicorn

# 실행
gunicorn -c gunicorn_config.py backend.main:app
```

`gunicorn_config.py`:
```python
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
```

---

## 문제 해결

### 1. CLI 명령을 찾을 수 없음

**증상:**
```
caas: command not found
```

**해결:**
```bash
# CAAS 재설치
pip install -e .
```

### 2. Neo4j 연결 실패

**증상:**
```
Neo4jError: Unable to connect to bolt://localhost:7687
```

**해결:**
```bash
# Neo4j 상태 확인
docker ps | grep neo4j

# Neo4j 재시작
docker restart neo4j

# 연결 정보 확인
echo $NEO4J_URI
```

### 3. OpenAI API 키 오류

**증상:**
```
ValueError: OPENAI_API_KEY가 설정되지 않았습니다
```

**해결:**
```bash
# .env 파일 확인
cat .env | grep OPENAI_API_KEY

# 환경 변수 재로드
source .env
```

### 4. tools.py 생성 실패 (2026-01-31 수정됨) ✨

**증상:**
```
완전성 검증: 0% 구현율
```

**해결:**
이제 자동으로 해결됩니다:
- ✅ LLM 실패 시 자동 Fallback 생성
- ✅ 한국어 도구명 자동 영어 변환
- ✅ 항상 실행 가능한 tools.py 보장

---

## 성능 최적화

### 1. Neo4j 튜닝

```bash
# docker-compose.yml에서 메모리 증가
environment:
  - NEO4J_dbms_memory_heap_initial__size=2G
  - NEO4J_dbms_memory_heap_max__size=4G
  - NEO4J_dbms_memory_pagecache_size=2G
```

### 2. 생성 성능 향상 (2026-01-31) ✨

최신 개선사항으로 생성 속도 및 품질 향상:
- ⚡ 3단계 방어 메커니즘으로 재시도 감소
- ⚡ 영어-한국어 번역 지원으로 매칭 속도 향상
- ⚡ Fallback stub 즉시 생성으로 대기 시간 제거

---

## 추가 리소스

- 📚 [설치 가이드](02_Installation_Guide.md) - 설치 방법
- ✨ [아키텍처 가이드](06_Architecture_Guide.md) - 시스템 구조 및 최신 개선사항
- 🚀 [빠른 시작 가이드](03_Quick_Start_Guide.md) - 첫 프로젝트 생성
- 📘 [CLI 사용 가이드](04_CLI_Usage_Guide.md) - 28개 CLI 명령어
- 🔧 [Ollama 설정 가이드](15_Ollama_Setup_Guide.md) - 로컬 LLM 설정 ✨ NEW
- [GitHub Issues](https://github.com/bullpeng72/CAAS/issues)

---

**최종 업데이트**: 2026-02-06
**버전**: 1.2.0 (v0.4.1 반영)
