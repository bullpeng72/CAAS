# 생성된 프로젝트 Frontend-Backend 통합 가이드

CAAS로 생성된 프로젝트의 frontend와 backend를 연결하여 완전한 애플리케이션을 만드는 방법입니다.

**최종 업데이트**: 2026-02-06

---

## 📋 목차

1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [통합 방법](#통합-방법)
4. [실제 예제](#실제-예제)
5. [문제 해결](#문제-해결)
6. [Best Practices](#best-practices)

---

## 🎯 개요

CAAS는 **프레임워크**로, 생성된 프로젝트 코드에 Frontend(Streamlit/React)와 Backend(FastAPI)가 포함됩니다. 이 가이드는 생성된 프로젝트 내에서 Frontend와 Backend를 성공적으로 연결하는 방법을 설명합니다.

**참고**: CAAS 자체는 UI 애플리케이션을 제공하지 않습니다. CLI 또는 Python API로 프로젝트를 생성하면, 생성된 프로젝트 폴더 내에 Frontend/Backend 코드가 포함됩니다.

### 핵심 구성요소 (생성된 프로젝트 내부)

CAAS로 프로젝트를 생성하면 다음과 같은 구조가 생성됩니다:

```
생성된 프로젝트/
├── frontend/               # Streamlit 또는 React UI
│   ├── app.py             # Streamlit 메인
│   └── api_client.py      # Backend API 호출
├── backend/               # FastAPI CRUD API
│   ├── main.py            # FastAPI 앱
│   ├── models.py          # SQLAlchemy 모델
│   └── api.py             # API 엔드포인트
├── agents/                # CrewAI 에이전트 (Agent-based 전략)
│   ├── agents.py
│   ├── tasks.py
│   └── tools.py
└── docker-compose.yml     # 전체 스택 실행

통합 아키텍처:
┌─────────────────────┐         HTTP/REST        ┌─────────────────────┐
│                     │ ◄────────────────────────► │                     │
│   Streamlit/React   │      API Requests         │   FastAPI Backend   │
│     Frontend        │      (JSON)               │     (CRUD API)      │
│                     │                           │                     │
│   Port: 8501/3000   │                           │   Port: 8000        │
└─────────────────────┘                           └─────────────────────┘
         ▲                                                  ▲
         │                                                  │
         │                                                  │
    User Browser                                   SQLite/PostgreSQL
```

---

## 🏗️ 아키텍처

### 1. Backend (FastAPI)

**역할**:
- RESTful API 엔드포인트 제공
- 비즈니스 로직 처리
- 데이터 저장/조회
- CORS 설정으로 frontend 접근 허용

**필수 구성**:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS 설정 (Frontend 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 또는 특정 frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Frontend (Streamlit/React)

**역할**:
- 사용자 인터페이스 제공
- Backend API 호출
- 데이터 시각화
- 사용자 입력 처리

**필수 구성**:
```python
import streamlit as st
import requests

# Backend URL 설정
BACKEND_URL = "http://localhost:8000"

# API 호출
response = requests.get(f"{BACKEND_URL}/api/todos")
```

### 3. 통신 프로토콜

**HTTP/REST**:
- Method: GET, POST, PUT, DELETE
- Format: JSON
- Headers: Content-Type: application/json
- CORS: 크로스 오리진 허용 필요

---

## 🔧 통합 방법

### 방법 1: 직접 통합

#### Step 1: Backend 준비

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS 설정 - 중요!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/items")
async def list_items():
    return [{"id": 1, "name": "Item 1"}]
```

#### Step 2: Frontend 생성

CAAS CLI 사용:
```bash
caas generate "할일 관리 시스템 만들기" \
  --domain TASK_MANAGEMENT \
  --output ./todo_app
```

#### Step 3: 실행

```bash
# Terminal 1: Backend
cd todo_app/backend
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend (CLI로 사용)
cd todo_app
# CLI로 생성된 프로젝트는 실행 스크립트 포함
python main.py
```

---

## 💡 실제 예제

### 완전한 Todo 애플리케이션

#### 📁 프로젝트 구조

```
todo_app/
├── backend/
│   ├── main.py              # FastAPI CRUD API
│   ├── models.py            # SQLAlchemy 모델
│   ├── database.py          # DB 설정
│   ├── requirements.txt
│   └── README.md
├── src/
│   ├── agents.py            # CrewAI 에이전트
│   ├── tasks.py             # 태스크 정의
│   ├── tools.py             # 커스텀 도구 (✨ 2026-01-31 개선)
│   └── crew.py              # Crew 구성
├── main.py                  # 진입점
└── README.md
```

#### 🚀 실행 방법

```bash
# 1. 프로젝트 생성
caas generate "할일 관리 CRUD API 만들기" --output ./todo_app

# 2. Backend 실행 (CRUD_BASED인 경우)
cd todo_app/backend
pip install -r requirements.txt
uvicorn main:app --reload

# 3. API 문서 확인
open http://localhost:8000/docs
```

#### 📡 API 엔드포인트

Backend가 제공하는 API:

```
GET    /health              - Health check
GET    /api/todos           - List all todos
POST   /api/todos           - Create new todo
GET    /api/todos/{id}      - Get specific todo
PUT    /api/todos/{id}      - Update todo
DELETE /api/todos/{id}      - Delete todo
```

### 코드 예제

#### Backend (FastAPI)

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터 저장소
todos = []

class TodoCreate(BaseModel):
    title: str
    description: str = ""

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/api/todos")
async def list_todos():
    return todos

@app.post("/api/todos")
async def create_todo(todo: TodoCreate):
    new_todo = {
        "id": len(todos) + 1,
        "title": todo.title,
        "description": todo.description,
        "completed": False
    }
    todos.append(new_todo)
    return new_todo
```

#### tools.py (2026-01-31 개선) ✨

CAAS가 생성하는 `tools.py`는 이제 3단계 방어 메커니즘으로 보호됩니다:

```python
from crewai.tools import BaseTool
from typing import Any
import logging

logger = logging.getLogger(__name__)

class APICallTool(BaseTool):
    """할일 API를 호출하는 도구"""
    name: str = "api_call"
    description: str = "Backend API를 호출하여 데이터 조작"

    def _run(self, endpoint: str, method: str = "GET") -> Any:
        """API 호출 실행"""
        try:
            import requests
            url = f"http://localhost:8000{endpoint}"

            if method == "GET":
                response = requests.get(url)
            elif method == "POST":
                response = requests.post(url, json={})

            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"API call failed: {e}")
            return {"error": str(e)}
```

**개선사항**:
- ✅ 항상 BaseTool 상속
- ✅ 에러 처리 포함
- ✅ 로깅 추가
- ✅ Fallback stub (LLM 실패 시 자동 생성)

---

## 🔍 문제 해결

### 문제 1: CORS 오류

**증상**:
```
Access to XMLHttpRequest blocked by CORS policy
```

**원인**: Backend에서 CORS 설정이 안 되어 있음

**해결**:
```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 문제 2: Backend 연결 실패

**증상**:
```python
requests.exceptions.ConnectionError: Connection refused
```

**원인**: Backend가 실행되지 않음

**해결**:
```bash
# Backend 실행 확인
curl http://localhost:8000/health

# 실행되지 않았으면
cd backend
uvicorn main:app --reload
```

### 문제 3: tools.py 생성 실패 (2026-01-31 수정됨) ✨

**이전 증상**:
```
FileNotFoundError: tools.py not found
완전성 검증: 0% 구현율
```

**해결**: 이제 자동으로 해결됩니다!
- ✅ LLM 실패 시 Fallback stub 자동 생성
- ✅ 한국어 도구명 자동 영어 변환
- ✅ 항상 실행 가능한 tools.py 보장

```python
# 자동 생성되는 Fallback stub 예시
class CustomToolStub(BaseTool):
    name: str = "custom_tool"
    description: str = "자동 생성된 Fallback 도구"

    def _run(self, input_data: str) -> Any:
        logger.warning(f"{self.name} called but not fully implemented")
        return {"status": "stub", "message": "구현 필요"}
```

### 문제 4: Port 충돌

**증상**:
```
OSError: [Errno 48] Address already in use
```

**원인**: 포트가 이미 사용 중

**해결**:
```bash
# 사용 중인 프로세스 찾기
lsof -i :8000  # Backend port

# 프로세스 종료
kill -9 <PID>

# 또는 다른 포트 사용
uvicorn main:app --port 8001
```

---

## ✅ Best Practices

### 1. 환경 변수 사용

```python
# backend/config.py
import os

BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
```

### 2. 에러 처리

```python
def call_api(url: str):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        logger.error("Request timeout")
        return None
    except requests.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        return None
```

### 3. Health Check

```python
# Backend
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
```

### 4. API 클라이언트 클래스

```python
# api_client.py
import requests

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def get(self, path: str):
        response = requests.get(f"{self.base_url}{path}")
        response.raise_for_status()
        return response.json()

    def post(self, path: str, data: dict):
        response = requests.post(
            f"{self.base_url}{path}",
            json=data
        )
        response.raise_for_status()
        return response.json()

# 사용
client = APIClient("http://localhost:8000")
todos = client.get("/api/todos")
```

---

## 🧪 통합 테스트

### 자동화된 테스트

```python
# test_integration.py
import requests
import pytest

BACKEND_URL = "http://localhost:8000"

def test_health():
    response = requests.get(f"{BACKEND_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_todo():
    response = requests.post(
        f"{BACKEND_URL}/api/todos",
        json={"title": "Test", "description": "Test todo"}
    )
    assert response.status_code == 200
    todo = response.json()
    assert todo["title"] == "Test"
    return todo["id"]

def test_list_todos():
    response = requests.get(f"{BACKEND_URL}/api/todos")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### 실행

```bash
# 통합 테스트 실행
pytest test_integration.py -v
```

---

## 🎯 요약

### ✅ 성공적인 통합을 위한 체크리스트

- [ ] Backend에 CORS 설정 추가
- [ ] Backend API 엔드포인트 구현
- [ ] Health check 엔드포인트 구현
- [ ] 에러 처리 추가
- [ ] 포트 충돌 확인 (Backend: 8000)
- [ ] tools.py 생성 확인 (2026-01-31 자동 생성)
- [ ] 통합 테스트 작성 및 실행
- [ ] 문서화 (README, API docs)

### 💡 핵심 포인트

1. **CORS 설정 필수**: Backend에서 반드시 CORS 허용
2. **Health Check**: Backend 연결 상태 확인
3. **에러 처리**: 네트워크 오류, 타임아웃 처리
4. **tools.py 자동 생성**: 2026-01-31 개선으로 항상 생성 보장
5. **통합 테스트**: 자동화된 테스트로 검증

---

## 📚 참고 자료

### 공식 문서
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Requests 라이브러리](https://requests.readthedocs.io/)
- [CrewAI 문서](https://docs.crewai.com/)

### CAAS 문서
- [CAAS 아키텍처 가이드](06_Architecture_Guide.md) - 시스템 구조
- [배포 가이드](07_Deployment_Guide.md) - 프로덕션 배포
- [빠른 시작 가이드](03_Quick_Start_Guide.md) - 첫 프로젝트 생성
- [CLI 사용 가이드](04_CLI_Usage_Guide.md) - CLI 명령어
- [전문가 방법론 가이드](05_Expert_Methodology_Guide.md) - 개발 방법론
- [Ollama 설정 가이드](15_Ollama_Setup_Guide.md) - 로컬 LLM 설정 ✨ NEW

---

**최종 업데이트**: 2026-02-06
**버전**: 1.1.0 (tools.py 생성 개선 반영)
**상태**: Production Ready ✅
