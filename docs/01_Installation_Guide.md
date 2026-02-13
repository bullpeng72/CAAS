# CAAS 설치 가이드

CAAS (CrewAI Agent Auto-generation System) 완전 설치 가이드입니다.

---

## 시스템 요구사항

- **Python**: 3.11 이상
- **Git**: 리포지토리 클론용
- **LLM Provider** (최소 하나 필수):
  - OpenAI API 키, 또는
  - Anthropic API 키, 또는
  - Ollama (로컬 LLM, API 키 불필요) ✨ NEW
- **선택사항**: Neo4j (지식 그래프 시각화용)

---

## 설치 방법

### 방법 1: PyPI 설치 (권장)

일반 사용자에게 권장하는 방법입니다.

```bash
pip install caas
```

**설치 확인:**
```bash
# CLI 확인
caas --version

# Python 라이브러리 확인
python -c "from caas_framework import CrewAIFramework; print('OK')"
```

**포함 내용:**
- ✅ `caas_framework` - 코어 프레임워크
- ✅ `caas_cli` - CLI 도구 (필수)
- ✅ `caas_sdk` - Python SDK
- ✅ `data/` - 템플릿, 온톨로지
- ✅ `scripts/` - 자동화 스크립트

### 방법 2: 개발 설치

개발 목적이거나 소스 코드를 수정하려는 경우 사용합니다.

#### 1단계: 리포지토리 클론

```bash
git clone https://github.com/bullpeng72/CAAS.git
cd caas
```

#### 2단계: 가상 환경 생성

```bash
# 가상 환경 생성
python3 -m venv venv

# 활성화 (Linux/macOS)
source venv/bin/activate

# 활성화 (Windows)
virtualenv\Scripts\activate
```

#### 3단계: CAAS 프레임워크 설치

`setup.py` 파일을 사용하여 선택적 의존성과 함께 설치됩니다.

**기본 설치 (통합 패키지):**
```bash
pip install -e .
```
> 💡 **참고**: CAAS는 CLI와 Framework가 포함된 통합 패키지입니다. CLI 사용과 라이브러리 사용 모두 가능합니다.

**개발용 (테스트 도구 포함):**
```bash
pip install -e ".[dev]"
```

#### 4단계: 환경 변수 설정

예제 환경 파일을 복사합니다:
```bash
cp .env.example .env
```

`.env` 파일을 편집하여 LLM Provider를 설정합니다:
```env
# 필수: 최소 하나의 LLM 제공자 선택

# 옵션 1: OpenAI
OPENAI_API_KEY=sk-your-openai-key-here

# 옵션 2: Anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# 옵션 3: Ollama (로컬 LLM, API 키 불필요) ✨ NEW
OLLAMA_API_BASE=http://localhost:11434/v1

# 선택: Neo4j 지식 그래프용
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

> 💡 **Ollama 사용**: Ollama를 사용하면 API 키 없이 로컬에서 LLM을 실행할 수 있습니다. 자세한 내용은 [09_Ollama_Setup_Guide.md](09_Ollama_Setup_Guide.md)를 참조하세요.

#### 5단계: 설치 확인

```bash
# CLI 확인
caas --help

# 프레임워크 기능 확인
python -c "from caas_framework.framework import CrewAIFramework; print('✓ Framework ready')"
```

---

## CAAS 사용하기

CAAS는 CLI와 Python 라이브러리로 모두 사용할 수 있습니다.

### 옵션 1: CLI 사용 (필수 포함)

**CLI는 기본 설치에 포함됩니다:**
```bash
# 프로젝트 생성
caas generate "할일 관리 시스템 만들기"

# 전체 자동화 워크플로우
caas auto-deploy "블로그 시스템" --target docker

# 상태 확인
caas status

# 프로젝트 목록
caas list
```

### 옵션 2: Python 라이브러리 사용

**Streamlit 앱 개발:**
```python
import streamlit as st
from caas_framework.framework import CrewAIFramework

st.title("CAAS Agent Generator")
requirement = st.text_area("요구사항:")

if st.button("생성"):
    framework = CrewAIFramework()
    await framework.initialize()
    result = await framework.generate_from_requirement(requirement)
    st.success(f"{len(result.files)}개 파일 생성!")
```

**FastAPI 백엔드 개발:**
```python
from fastapi import FastAPI
from caas_framework.framework import CrewAIFramework

app = FastAPI()

@app.post("/generate")
async def generate(requirement: str):
    framework = CrewAIFramework()
    await framework.initialize()
    result = await framework.generate_from_requirement(requirement)
    return {"files": len(result.files), "success": True}
```

**중요**: CLI는 `caas_framework`를 직접 사용하며 FastAPI 서버 실행이 **필요하지 않습니다**.

---

> 💡 **참고**: CAAS는 CLI 기반 도구로, 별도의 웹 UI나 API 서버를 포함하지 않습니다. CAAS를 통해 생성된 프로젝트에는 필요에 따라 Streamlit UI나 FastAPI 백엔드가 포함될 수 있습니다.

---

## 선택적 구성요소

### Neo4j (지식 그래프)

지식 그래프 시각화 및 패턴 저장용:

**Docker 사용:**
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

**접속**: http://localhost:7474

**.env에서 설정:**
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### Ollama (로컬 LLM 실행) ✨ NEW

API 키 없이 로컬에서 LLM을 실행:

**설치 및 설정:**
```bash
# 1. Ollama 설치 (macOS)
brew install ollama

# 2. Ollama 서비스 시작
ollama serve

# 3. 모델 다운로드 (예: llama3)
ollama pull llama3

# 4. .env 설정
echo "OLLAMA_API_BASE=http://localhost:11434/v1" >> .env
```

**자세한 내용**: [09_Ollama_Setup_Guide.md](09_Ollama_Setup_Guide.md)

### Redis (선택 - 다중 서버 설정)

분산 배포 시에만 필요:

```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

---

## 검증 단계

### 1. 프레임워크 import 테스트

```bash
python -c "from caas_framework.framework import CrewAIFramework; print('✓ Framework imported successfully')"
```

### 2. CLI 테스트 (설치한 경우)

```bash
caas --version
caas --help
```

### 3. 생성 테스트 (빠른 테스트)

`test_generation.py` 생성:
```python
import asyncio
from caas_framework.framework import CrewAIFramework

async def test():
    framework = CrewAIFramework(llm_provider="openai")
    await framework.initialize()

    result = await framework.generate_from_requirement(
        requirement="간단한 할일 앱 만들기",
        domain="TASK_MANAGEMENT"
    )

    print(f"✓ Generation {'successful' if result.success else 'failed'}")
    print(f"  Agents: {len(result.agent_specs)}")
    print(f"  Tasks: {len(result.task_specs)}")

    await framework.close()

asyncio.run(test())
```

실행:
```bash
python test_generation.py
```

---

## 문제 해결

### 문제: ModuleNotFoundError: No module named 'caas_framework'

**해결책:**
```bash
# 개발 모드로 재설치
cd /path/to/caas
pip install -e . --force-reinstall
```

---

### 문제: "OPENAI_API_KEY not found" 또는 LLM Provider 오류

**해결책:**

**옵션 1: API 키 사용 (OpenAI/Anthropic)**
1. 프로젝트 루트에 `.env` 파일이 있는지 확인
2. API 키 설정 확인: `cat .env | grep API_KEY`
3. 터미널/셸을 재시작하여 환경 다시 로드

**옵션 2: Ollama 사용 (API 키 불필요)** ✨ NEW
1. Ollama 설치 및 실행: `ollama serve`
2. `.env`에 추가: `OLLAMA_API_BASE=http://localhost:11434/v1`
3. 자세한 내용: [09_Ollama_Setup_Guide.md](09_Ollama_Setup_Guide.md)

---

### 문제: SDK 사용 시 "Connection refused"

**해결책:**
- `caas_sdk`는 생성된 프로젝트의 FastAPI 서버가 실행되어야 할 수 있습니다.
- 생성된 프로젝트의 백엔드 서버 시작: `uvicorn backend.main:app --reload`
- 서버 실행 확인: `curl http://localhost:8000/health`

---

### 문제: CLI 명령을 찾을 수 없음

**해결책:**
```bash
# CAAS 재설치 (CLI 포함)
pip install -e . --force-reinstall

# entry point 등록 확인
which caas
```

---

### 문제: 생성된 Streamlit 앱 import 오류

**해결책:**
```bash
# 생성된 프로젝트의 requirements.txt에 streamlit이 포함되어 있는지 확인
pip install streamlit
```

---

### 문제: "Port 8000 already in use"

**해결책:**
```bash
# 옵션 1: 포트 8000을 사용하는 프로세스 종료
lsof -ti:8000 | xargs kill -9

# 옵션 2: 다른 포트 사용 (생성된 앱 실행 시)
uvicorn backend.main:app --port 8001
```

---

### 문제: Neo4j 연결 실패

**참고**: Neo4j는 선택사항입니다. 없어도 프레임워크는 동작합니다.

**해결:**
1. Neo4j 실행 확인: `docker ps | grep neo4j`
2. 연결 테스트: `cypher-shell -u neo4j -p password`
3. `.env`의 인증 정보 확인

---

## CAAS 업데이트

### PyPI에서 (권장)

```bash
pip install --upgrade caas
```

### 소스에서 (개발 모드)

```bash
cd /path/to/caas
git pull origin CAAS

# 의존성 재설치
pip install -e ".[dev]" --force-reinstall

# 캐시 파일 정리
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

---

## 제거

```bash
# CAAS 제거 (Framework + CLI + SDK)
pip uninstall caas

# 가상 환경 제거
deactivate
rm -rf venv

# 설정 제거
rm -rf .caas/
```

---

## 아키텍처 개요

CAAS는 모듈식 아키텍처를 가지고 있습니다:

```
caas_framework/     - 핵심 프레임워크 (UI 독립적)
    ├── agents/     - 6개 전문 에이전트 (v0.4.0+)
    │   ├── utils.py           - 공통 유틸리티 (v0.4.1+)
    │   └── code_gen_helpers.py - 코드 생성 헬퍼 (v0.4.1+)
    ├── methodology/ - CAAS 6-Phase 엔진 (v0.3.0+)
    ├── codegen/    - 코드 생성
    ├── knowledge/  - 온톨로지 & 지식 그래프
    ├── plugins/
    │   └── llm/
    │       └── utils.py       - LLM 공통 유틸리티 (v0.4.1+)
    ├── exceptions.py - 커스텀 예외 체계 (v0.4.1+)
    └── ...

caas_cli/           - CLI 인터페이스 (28개 명령어)
caas_sdk/           - Python SDK
data/               - 템플릿, 온톨로지, 예제
docs/               - 한국어 + 영어 문서 (15개)
tests/              - 테스트 스위트 (160+ tests, v0.4.1: +60개)
```

**핵심 설계**:
- `caas_framework`가 핵심이며, UI-독립적으로 완전히 기능합니다.
- CLI와 SDK는 프레임워크를 감싸는 얇은 래퍼(wrapper)입니다.
- CLI는 프레임워크를 직접 사용하며, 별도의 API 서버가 필요하지 않습니다.
- Framework-First 아키텍처로 향후 다양한 인터페이스 추가 가능

---

## 설치 결정 트리

**사용 사례별 설치 선택:**

| 사용 사례 | 설치 명령 | 구성요소 |
|----------|----------|---------|
| **일반 사용자 (권장)** | `pip install caas` | Framework + CLI + SDK |
| **개발 모드 (소스 수정)** | `pip install -e "."` | Framework + CLI + SDK |
| **CAAS 프레임워크 개발** | `pip install -e ".[dev]"` | 전체 + 테스트 도구 |

---

## 다음 단계

설치 후:

1. **빠른 시작**: [03_Quick_Start_Guide.md](03_Quick_Start_Guide.md)에서 5분 튜토리얼 확인
2. **CLI 가이드**: [04_CLI_Usage_Guide.md](04_CLI_Usage_Guide.md)에서 CLI 28개 명령어 확인
3. **아키텍처**: [06_Architecture_Guide.md](06_Architecture_Guide.md)에서 시스템 설계 확인
4. **개발 방법론**: [05_Expert_Methodology_Guide.md](05_Expert_Methodology_Guide.md)에서 CAAS 6-Phase Methodology 확인
5. **Ollama 설정**: [09_Ollama_Setup_Guide.md](09_Ollama_Setup_Guide.md)에서 로컬 LLM 설정 확인 ✨ NEW

---

## 지원

- **GitHub Issues**: https://github.com/bullpeng72/CAAS/issues
- **문서**: [01_README_KO.md](01_README_KO.md) - 전체 문서 색인
- **테스트**: `tests/` 디렉토리에서 E2E 예제 확인

---

**다음 단계**: [03_Quick_Start_Guide.md](03_Quick_Start_Guide.md)에서 첫 프로젝트를 만들어보세요!
