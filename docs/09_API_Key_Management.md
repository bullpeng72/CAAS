# API Key Management Guide

CAAS에서 사용하는 CrewAI 도구들의 API 키 관리 가이드입니다.

## 📋 목차

1. [개요](#개요)
2. [빠른 시작](#빠른-시작)
3. [API 키 분류 및 목록](#api-키-분류-및-목록)
4. [검증 및 관리 도구](#검증-및-관리-도구)
5. [설정 방법](#설정-방법)
6. [프로그래밍 방식 사용](#프로그래밍-방식-사용)
7. [보안 및 모범 사례](#보안-및-모범-사례)
8. [문제 해결](#문제-해결)
9. [참고 자료](#참고-자료)

---

## 개요

CAAS 프레임워크는 40개 이상의 CrewAI 도구를 지원하며, 많은 도구들이 외부 서비스의 API 키를 필요로 합니다.

### 주요 기능

- ✅ API 키 요구사항 자동 감지
- ✅ .env 파일에서 API 키 관리
- ✅ CLI 및 UI에서 API 키 설정/확인
- ✅ 생성된 코드에서 API 키 자동 로드
- ✅ 도구별 API 키 상태 표시
- ✅ API 키 검증 스크립트 제공

---

## 빠른 시작

### 1. 현재 상태 확인

```bash
# API 키 검증 실행
python3 scripts/validate_api_keys.py
```

### 2. 필수 API 키 설정

```bash
# .env 파일 편집
nano .env

# 또는
code .env
```

### 3. OpenAI API 키 설정 (필수)

```bash
# .env 파일에 추가
OPENAI_API_KEY=sk-your-actual-openai-key-here
```

### 4. 검증 재실행

```bash
python3 scripts/validate_api_keys.py
```

---

## API 키 분류 및 목록

### ✅ REQUIRED (필수)

CAAS의 기본 기능을 사용하기 위해 **반드시** 필요한 키입니다.

| API Key | 도구 | 설명 | 발급 방법 |
|---------|------|------|----------|
| `OPENAI_API_KEY` | VisionTool, DallETool | OpenAI API (이미지 분석, 생성) | [OpenAI Platform](https://platform.openai.com/api-keys) |

**비용**: $5 무료 크레딧 (신규 계정)

---

### 🔧 CORE (자주 사용)

선택 사항이지만 **자주 사용**되는 기능입니다.

| API Key | 도구 | 설명 | 발급 방법 | 무료 티어 |
|---------|------|------|----------|----------|
| `SERPER_API_KEY` | SerperDevTool | Google 검색 (Serper API) | [Serper.dev](https://serper.dev/api-key) | 2,500 검색/월 |
| `BRAVE_API_KEY` | BraveSearchTool | 프라이버시 중심 Brave 검색 | [Brave Search API](https://brave.com/search/api/) | 2,000 검색/월 |
| `TAVILY_API_KEY` | TavilySearchTool | AI 최적화 검색 | [Tavily](https://tavily.com/) | 1,000 검색/월 |

---

### 📦 OPTIONAL (선택적)

특정 기능을 사용할 때만 필요한 키들입니다.

#### 🌐 Web Scraping Tools

| API Key | 도구 | 설명 | 발급 방법 |
|---------|------|------|----------|
| `FIRECRAWL_API_KEY` | FirecrawlScrapeWebsiteTool | 고급 웹 스크래핑 (JS 렌더링) | [Firecrawl](https://firecrawl.dev/) |
| `JINA_API_KEY` | JinaScrapeWebsiteTool | Jina AI 스크래핑 | [Jina AI](https://jina.ai/) |
| `SPIDER_API_KEY` | SpiderTool | Spider 크롤링 | [Spider](https://spider.cloud/) |

#### 💻 Code & Integration Tools

| API Key | 도구 | 설명 | 발급 방법 |
|---------|------|------|----------|
| `GITHUB_API_KEY` | GithubSearchTool | GitHub 검색 및 통합 | [GitHub Tokens](https://github.com/settings/tokens) |

**무료 티어**: Rate limit 적용

#### 🎥 Media Tools

| API Key | 도구 | 설명 | 발급 방법 |
|---------|------|------|----------|
| `YOUTUBE_API_KEY` | YoutubeChannelSearchTool<br>YoutubeVideoSearchTool | YouTube 데이터 API | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |

**무료 티어**: 10,000 쿼터/일

#### 💬 Communication Tools

| API Key | 도구 | 설명 | 상태 |
|---------|------|------|------|
| `SLACK_API_KEY` | SlackSearchTool | Slack 워크스페이스 검색 | ⚠️ CrewAI에서 사용 불가 |
| `TWILIO_ACCOUNT_SID`<br>`TWILIO_AUTH_TOKEN`<br>`TWILIO_PHONE_NUMBER` | TwilioTool | SMS/전화 발송 | [Twilio](https://www.twilio.com/) |

#### 🗄️ Database Tools

| API Key | 도구 | 설명 |
|---------|------|------|
| `MYSQL_CONNECTION_STRING` | MySQLSearchTool | MySQL 검색 |
| `MONGODB_URI` | MongoDBVectorSearchTool | MongoDB 벡터 검색 |
| `SNOWFLAKE_ACCOUNT`<br>`SNOWFLAKE_USER`<br>`SNOWFLAKE_PASSWORD` | SnowflakeSearchTool | Snowflake 검색 |

#### 📊 Productivity & Analytics

| API Key | 도구 | 설명 |
|---------|------|------|
| `GOOGLE_ANALYTICS_CREDENTIALS` | GoogleAnalyticsSearchTool | Google Analytics 데이터 |
| `GOOGLE_CALENDAR_CREDENTIALS` | GoogleCalendarSearchTool | Google Calendar |
| `GOOGLE_DOCS_CREDENTIALS` | GoogleDocsSearchTool | Google Docs |
| `GOOGLE_SHEETS_CREDENTIALS` | GoogleSheetsSearchTool | Google Sheets |
| `NOTION_API_KEY` | NotionSearchTool | Notion 검색 |
| `MIXPANEL_API_SECRET` | MixpanelSearchTool | Mixpanel 분석 |

#### 🤖 AI/ML Tools

| API Key | 도구 | 설명 |
|---------|------|------|
| `HUGGINGFACE_API_KEY` | HuggingFaceModelTool | Hugging Face 모델 (선택) |
| `STABILITY_API_KEY` | StableDiffusionTool | Stable Diffusion 이미지 생성 |

#### 🔧 Other Tools

| API Key | 도구 | 설명 |
|---------|------|------|
| `MULTION_API_KEY` | MultiOnTool | MultiOn 자동화 |
| `COMPOSIO_API_KEY` | ComposioTool | Composio 통합 |
| `EXA_API_KEY` | EXASearchTool | EXA 검색 |

---

### 🆓 API Key가 필요 없는 도구

다음 도구들은 API 키 없이 바로 사용할 수 있습니다:

#### 📁 File Tools
- `FileReadTool` - 파일 읽기
- `FileWriterTool` - 파일 쓰기
- `DirectoryReadTool` - 디렉토리 목록
- `DirectorySearchTool` - 디렉토리 검색

#### 📄 Document Tools
- `PDFSearchTool` - PDF 검색
- `DOCXSearchTool` - DOCX 검색
- `CSVSearchTool` - CSV 검색
- `JSONSearchTool` - JSON 검색
- `XMLSearchTool` - XML 검색
- `TXTSearchTool` - TXT 검색
- `MDXSearchTool` - MDX 검색

#### 🌐 Basic Web Tools
- `WebsiteSearchTool` - 웹사이트 검색
- `ScrapeWebsiteTool` - 기본 웹 스크래핑
- `SeleniumScrapingTool` - Selenium 스크래핑

#### 💻 Code Tools
- `CodeInterpreterTool` - 코드 해석
- `CodeDocsSearchTool` - 코드 문서 검색

---

## 검증 및 관리 도구

### 1. API Key 검증 스크립트

**파일**: `/scripts/validate_api_keys.py`

#### 기능
- ✅ .env 파일에서 자동으로 API 키 로드
- ✅ 8개 주요 API 키 실제 검증 (API 호출 테스트)
- ✅ 상세한 검증 리포트 생성
- ✅ 필수/선택 키 구분
- ✅ 도구별 영향 분석

#### 사용법

```bash
# 전체 검증 실행
python3 scripts/validate_api_keys.py

# 출력 예시:
# ======================================================================
# 🔍 CAAS API Key Validation
# ======================================================================
#
# 📦 OPENAI_API_KEY
#    Description: OpenAI API for vision and image generation
#    Tools: VisionTool, DallETool
#    Required: Yes
#    Status: ✅ Valid (Model: gpt-4o-mini)
#
# 📦 SERPER_API_KEY
#    Description: Google search via Serper API
#    Tools: SerperDevTool
#    Required: No
#    Status: ✅ Valid
# ...
```

#### 검증 로직

각 API 키별로 다른 검증 방법 사용:

- **OpenAI**: `gpt-4o-mini` 모델로 간단한 chat 요청
- **Serper**: Google 검색 테스트 요청
- **Brave**: Brave Search API 테스트 요청
- **Tavily**: Tavily Search API 테스트 요청
- **GitHub**: GitHub API user 정보 요청
- **YouTube**: YouTube Search API 테스트 요청
- **Firecrawl**: 키 형식 검증 (실제 크롤링 요청은 비용 발생)

### 2. CLI 환경 변수 관리

#### 환경 변수 확인

```bash
# 모든 환경 변수 나열
caas env --list

# 특정 키 확인
caas env --get OPENAI_API_KEY

# 특정 키 확인 (마스킹)
caas env --get SERPER_API_KEY --masked
```

#### 환경 변수 설정

```bash
# 직접 export (현재 세션에만 적용)
export OPENAI_API_KEY=sk-your-key-here

# .env 파일에 추가 (영구 적용)
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

### 3. Tool Ontology 기반 요구사항 조회

CAAS는 Tool Ontology (`data/ontology/tools.json`)를 통해 각 도구의 API 키 요구사항을 동적으로 관리합니다.

```python
from caas_framework.knowledge.ontology.tool_manager import get_tool_ontology_manager

# Tool Ontology Manager 가져오기
manager = get_tool_ontology_manager()

# API 키 정보를 포함한 도구 목록
tools = manager.get_tools_for_api()

for tool in tools:
    print(f"\n{tool['display_name']}")
    for impl in tool['implementations']:
        if impl['requires_api_key']:
            print(f"  - API Key: {impl['api_key_env']}")
```

---

## 설정 방법

### 방법 1: .env 파일 직접 편집 (권장)

#### 1단계: .env 파일 열기

```bash
# 텍스트 에디터로 열기
nano .env

# 또는 VSCode
code .env

# 또는 vim
vim .env
```

#### 2단계: API 키 입력

```bash
# =============================================================================
# CAAS - CrewAI Agent Auto-generation System
# Environment Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# LLM API Keys
# -----------------------------------------------------------------------------
OPENAI_API_KEY=sk-your-actual-openai-key-here

# -----------------------------------------------------------------------------
# CrewAI Tool API Keys
# -----------------------------------------------------------------------------

# 🔍 Web Search Tools
SERPER_API_KEY=your-serper-key-here
BRAVE_API_KEY=your-brave-key-here
TAVILY_API_KEY=your-tavily-key-here

# 🌐 Web Scraping Tools
FIRECRAWL_API_KEY=your-firecrawl-key-here

# 💻 Code & Integration Tools
GITHUB_API_KEY=your-github-token-here

# 🎥 Media Tools
YOUTUBE_API_KEY=your-youtube-key-here

# 💬 Communication Tools
SLACK_API_KEY=your-slack-key-here
```

#### 3단계: 저장 및 검증

```bash
# 저장 후 검증
python3 scripts/validate_api_keys.py
```

### 방법 2: 환경 변수 직접 설정

#### Bash/Zsh

```bash
# ~/.bashrc 또는 ~/.zshrc에 추가
export OPENAI_API_KEY=sk-your-key-here
export SERPER_API_KEY=your-serper-key-here

# 적용
source ~/.bashrc  # 또는 source ~/.zshrc
```

#### Windows PowerShell

```powershell
# 환경 변수 설정
$env:OPENAI_API_KEY = "sk-your-key-here"

# 영구 설정
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-your-key-here", "User")
```

### 방법 3: .env.example 복사

```bash
# .env.example을 .env로 복사
cp .env.example .env

# .env 편집
nano .env
```

---

## 프로그래밍 방식 사용

개발자를 위한 프로그래밍 방식 API 키 관리 방법입니다.

### 1. Tool API Keys 모듈

**파일**: `caas_framework/codegen/tool_api_keys.py`

#### API 키 요구사항 확인

```python
from caas_framework.codegen.tool_api_keys import (
    get_tool_api_key_requirements,
    is_tool_requires_api_key
)

# 도구가 API 키를 필요로 하는지 확인
if is_tool_requires_api_key("SerperDevTool"):
    print("SerperDevTool requires API key")

# API 키 요구사항 가져오기
requirements = get_tool_api_key_requirements("SerperDevTool")
for req in requirements:
    print(f"Environment Variable: {req.env_var}")
    print(f"Description: {req.description}")
    print(f"Required: {req.optional == False}")
    print(f"Signup URL: {req.signup_url}")
```

### 2. Environment Manager

**파일**: `caas_framework/utils/env_manager.py`

#### 기본 사용법

```python
from caas_framework.utils.env_manager import get_env_manager

# Environment Manager 인스턴스 가져오기
env_manager = get_env_manager()

# API 키 설정
env_manager.set_value("SERPER_API_KEY", "your-api-key-here")

# API 키 확인
value = env_manager.get_value("SERPER_API_KEY")
print(f"SERPER_API_KEY: {value}")

# API 키가 설정되었는지 확인
if env_manager.is_key_set("SERPER_API_KEY"):
    print("✅ SERPER_API_KEY is configured!")
else:
    print("❌ SERPER_API_KEY is not configured")

# 모든 환경 변수 가져오기
all_vars = env_manager.get_all_values()
for key, value in all_vars.items():
    print(f"{key}: {value}")
```

#### 벌크 설정

```python
# 여러 키 한번에 설정
keys_to_set = {
    "SERPER_API_KEY": "key1",
    "BRAVE_API_KEY": "key2",
    "TAVILY_API_KEY": "key3"
}

success_count, failed_keys = env_manager.bulk_set(keys_to_set)
print(f"✅ Successfully set {success_count} keys")
if failed_keys:
    print(f"❌ Failed keys: {', '.join(failed_keys)}")
```

#### 백업 및 복원

```python
# .env 파일 백업
backup_path = env_manager.backup()
print(f"Backup created at: {backup_path}")

# 백업에서 복원
env_manager.restore()
print("Restored from backup")
```

### 3. Tool Ontology Manager

**파일**: `caas_framework/knowledge/ontology/tool_manager.py`

```python
from caas_framework.knowledge.ontology.tool_manager import get_tool_ontology_manager

# Manager 인스턴스
manager = get_tool_ontology_manager()

# 모든 도구 가져오기 (활성화된 것만)
enabled_tools = manager.get_all_tools(enabled_only=True)

# API 키 요구사항이 있는 도구만 필터링
tools_with_api_keys = [
    tool for tool in enabled_tools
    if any(impl.requires_api_key for impl in tool.implementations)
]

for tool in tools_with_api_keys:
    print(f"\n{tool.display_name} ({tool.name})")
    for impl in tool.implementations:
        if impl.requires_api_key:
            print(f"  - {impl.name}: {impl.api_key_env}")
```

### 4. 생성된 코드에서 자동 로드

CAAS가 생성한 `agents.py` 파일에는 `TOOL_REQUIREMENTS` 매핑이 자동으로 포함됩니다:

```python
# agents.py (CAAS가 자동 생성)

import os
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# API 키 요구사항 매핑
TOOL_REQUIREMENTS = {
    "SerperDevTool": {
        "env_var": "SERPER_API_KEY",
        "param_name": None,
        "optional": False,
    },
    "BraveSearchTool": {
        "env_var": "BRAVE_API_KEY",
        "param_name": None,
        "optional": False,
    },
    # ...
}

def create_tools(tool_names: list) -> list:
    """Create tools from tool names with API key validation"""
    tools = []

    for tool_name in tool_names:
        # API 키 요구사항 확인
        if tool_name in TOOL_REQUIREMENTS:
            req = TOOL_REQUIREMENTS[tool_name]
            api_key = os.getenv(req["env_var"])

            if not api_key:
                if req["optional"]:
                    print(f"⚠️ {tool_name}: {req['env_var']} not set (optional)")
                    continue
                else:
                    raise ValueError(
                        f"❌ {tool_name} requires {req['env_var']} to be set"
                    )

        # 도구 초기화
        tool_class = globals()[tool_name]
        tools.append(tool_class())

    return tools
```

### 5. API 키 검증 테스트

```python
from caas_framework.utils.env_manager import get_env_manager
from caas_framework.codegen.tool_api_keys import get_tool_api_key_requirements

env_manager = get_env_manager()

# 모든 도구의 API 키 상태 확인
tool_names = ["SerperDevTool", "BraveSearchTool", "TavilySearchTool"]

for tool_name in tool_names:
    print(f"\n{tool_name}:")
    requirements = get_tool_api_key_requirements(tool_name)

    for req in requirements:
        is_set = env_manager.is_key_set(req.env_var)
        status = "✅" if is_set else "❌"
        print(f"  {status} {req.env_var}: {req.description}")

        if not is_set and not req.optional:
            print(f"     ⚠️ REQUIRED - Get your key at: {req.signup_url}")
```

---

## 보안 및 모범 사례

### 1. 민감 정보 보호

#### .gitignore 설정

`.env` 파일은 반드시 `.gitignore`에 포함되어야 합니다:

```bash
# .gitignore
.env
.env.local
.env.*.local
```

#### 공유할 때

```bash
# ✅ 공유 가능 (.env.example)
OPENAI_API_KEY=your-openai-api-key-here
SERPER_API_KEY=your-serper-api-key-here

# ❌ 절대 공유 금지 (.env)
OPENAI_API_KEY=sk-proj-abc123...
SERPER_API_KEY=9f8e7d6c5b4a3...
```

### 2. API 키 마스킹

```python
def mask_api_key(key: str, show_chars: int = 4) -> str:
    """API 키를 마스킹하여 표시"""
    if not key or len(key) <= show_chars * 2:
        return "***"

    return f"{key[:show_chars]}...{key[-show_chars:]}"

# 사용 예시
api_key = "sk-proj-4m_9ItxDyqLmtJkyXpiR..."
print(mask_api_key(api_key))  # sk-p...E7IA
```

### 3. 환경별 설정

```bash
# 개발 환경
.env.development

# 프로덕션 환경
.env.production

# 테스트 환경
.env.test
```

```python
import os
from dotenv import load_dotenv

# 환경에 따라 다른 .env 파일 로드
env = os.getenv("APP_ENV", "development")
load_dotenv(f".env.{env}")
```

### 4. API 키 갱신 주기

| 서비스 | 권장 갱신 주기 |
|--------|--------------|
| OpenAI | 90일 |
| GitHub | 180일 |
| 기타 API | 90-180일 |

### 5. 최소 권한 원칙

API 키를 생성할 때 필요한 최소한의 권한만 부여하세요:

```bash
# ✅ 좋은 예: 읽기 전용 권한
GITHUB_API_KEY=ghp_read_only_...

# ❌ 나쁜 예: 모든 권한
GITHUB_API_KEY=ghp_full_access_...
```

### 6. 백업 전략

```python
from caas_framework.utils.env_manager import get_env_manager

env_manager = get_env_manager()

# 정기 백업
env_manager.backup()

# 백업 파일: .env.backup.YYYYMMDD_HHMMSS
```

---

## 문제 해결

### 문제 1: API 키가 유효하지 않다고 나옴

#### 증상
```
❌ OPENAI_API_KEY: Invalid API key
```

#### 해결 방법

1. **API 키 확인**
   ```bash
   # .env 파일 확인
   cat .env | grep OPENAI_API_KEY

   # 앞뒤 공백 확인
   python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print(repr(os.getenv('OPENAI_API_KEY')))"
   ```

2. **새 API 키 발급**
   - https://platform.openai.com/api-keys
   - 기존 키 삭제 후 새로 생성
   - .env 파일에 업데이트

3. **API 키 형식 확인**
   - OpenAI: `sk-proj-...` (최신) 또는 `sk-...` (레거시)
   - Serper: 32자 hex 문자열
   - GitHub: `ghp_...` (personal access token)

### 문제 2: 환경 변수가 로드되지 않음

#### 증상
```python
os.getenv("OPENAI_API_KEY")  # None 반환
```

#### 해결 방법

1. **python-dotenv 설치 확인**
   ```bash
   pip install python-dotenv
   ```

2. **load_dotenv() 호출 확인**
   ```python
   from dotenv import load_dotenv

   # .env 파일 로드
   load_dotenv()

   # 또는 명시적 경로
   load_dotenv(".env")
   ```

3. **.env 파일 위치 확인**
   ```bash
   # 현재 디렉토리에 .env가 있는지 확인
   ls -la .env

   # 프로젝트 루트로 이동
   cd /path/to/CAAS
   ```

### 문제 3: 검증 스크립트 실행 오류

#### 증상
```bash
ModuleNotFoundError: No module named 'openai'
```

#### 해결 방법

```bash
# 필요한 패키지 설치
pip install python-dotenv requests openai

# 또는 requirements.txt 사용
pip install -r requirements.txt

# 스크립트 재실행
python3 scripts/validate_api_keys.py
```

### 문제 4: API 쿼터 초과

#### 증상
```
⚠️ API key valid but quota exceeded
```

#### 해결 방법

1. **OpenAI**
   - https://platform.openai.com/account/billing
   - 결제 수단 추가 또는 크레딧 충전

2. **Serper**
   - https://serper.dev/dashboard
   - 무료 플랜: 2,500 검색/월
   - 유료 플랜으로 업그레이드

3. **대안 도구 사용**
   ```python
   # Serper 대신 Brave Search 사용
   tools = ["BraveSearchTool"]  # 2,000 무료 검색/월

   # 또는 Tavily 사용
   tools = ["TavilySearchTool"]  # 1,000 무료 검색/월
   ```

### 문제 5: 생성된 코드에서 API 키 로드 실패

#### 증상
```python
ValueError: ❌ SerperDevTool requires SERPER_API_KEY to be set
```

#### 해결 방법

1. **생성된 코드 디렉토리에 .env 복사**
   ```bash
   # 생성된 프로젝트 디렉토리로 이동
   cd generated/my_project

   # 프로젝트 루트의 .env를 복사
   cp ../../.env .
   ```

2. **절대 경로로 .env 로드**
   ```python
   from pathlib import Path
   from dotenv import load_dotenv

   # 프로젝트 루트의 .env 로드
   project_root = Path(__file__).parent.parent.parent
   load_dotenv(project_root / ".env")
   ```

3. **환경 변수 직접 설정**
   ```bash
   export SERPER_API_KEY=your-key-here
   python main.py
   ```

### 문제 6: 특정 도구만 API 키 오류

#### 증상
```
✅ SerperDevTool works
❌ BraveSearchTool: Invalid API key
```

#### 해결 방법

1. **도구별 API 키 확인**
   ```bash
   python3 scripts/validate_api_keys.py
   ```

2. **개별 도구 테스트**
   ```python
   from crewai_tools import BraveSearchTool
   import os

   # API 키 확인
   api_key = os.getenv("BRAVE_API_KEY")
   print(f"BRAVE_API_KEY: {api_key[:10]}...")

   # 도구 초기화 테스트
   try:
       tool = BraveSearchTool()
       result = tool._run("test")
       print("✅ BraveSearchTool works")
   except Exception as e:
       print(f"❌ Error: {e}")
   ```

---

## 참고 자료

### 공식 문서

- [CrewAI Tools Documentation](https://docs.crewai.com/tools/)
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- [Serper API Documentation](https://serper.dev/docs)
- [Brave Search API Documentation](https://brave.com/search/api/)
- [Tavily API Documentation](https://docs.tavily.com/)

### CAAS 관련 파일

#### 핵심 코드

- `caas_framework/codegen/tool_api_keys.py` - API 키 요구사항 정의
- `caas_framework/utils/env_manager.py` - 환경 변수 관리 유틸리티
- `caas_framework/knowledge/ontology/tool_manager.py` - Tool Ontology 관리
- `caas_framework/codegen/tool_generator.py` - 도구 코드 생성

#### 데이터 파일

- `data/ontology/tools.json` - Tool Ontology (40+ 도구)
- `data/tools_registry.json` - 도구 레지스트리
- `.env.example` - 환경 변수 예제

#### 스크립트

- `scripts/validate_api_keys.py` - API 키 검증 스크립트 (409줄)

#### 템플릿

- `data/templates/agents_with_error_handling.py.j2` - TOOL_REQUIREMENTS 매핑 포함

### 추가 문서

- [01_README_KO.md](01_README_KO.md) - CAAS 프로젝트 개요
- [03_Quick_Start_Guide.md](03_Quick_Start_Guide.md) - 빠른 시작 가이드
- [06_Architecture_Guide.md](06_Architecture_Guide.md) - 아키텍처 가이드
- [CLAUDE.md](../CLAUDE.md) - 프로젝트 컨텍스트

### 외부 리소스

#### API 키 발급

| 서비스 | URL |
|--------|-----|
| OpenAI | https://platform.openai.com/api-keys |
| Serper | https://serper.dev/api-key |
| Brave Search | https://brave.com/search/api/ |
| Tavily | https://tavily.com/ |
| Firecrawl | https://firecrawl.dev/ |
| GitHub | https://github.com/settings/tokens |
| YouTube | https://console.cloud.google.com/apis/credentials |

#### 커뮤니티

- [CAAS GitHub Issues](https://github.com/bullpeng72/CAAS/issues)
- [CrewAI Discord](https://discord.gg/crewai)

---

## 워크플로우 다이어그램

```
┌─────────────────────────────────────┐
│ 사용자가 프로젝트 생성 요청          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ CAAS가 필요한 도구 분석              │
│ (Requirement Analyst + Agent Designer)│
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 각 도구의 API 키 요구사항 확인       │
│ (tool_api_keys.py + tools.json)     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ .env 파일에서 API 키 로드            │
│ (env_manager.py)                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 생성된 코드에 TOOL_REQUIREMENTS 포함 │
│ (agents.py.j2 템플릿)               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ agents.py 실행 시 자동으로 API 키 로드│
│ (create_tools 함수)                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ API 키가 없으면?                     │
│ - Optional: 경고 메시지 + 스킵       │
│ - Required: 에러 발생 + 중단         │
└─────────────────────────────────────┘
```

---

## 버전 히스토리

### v0.4.1 (2026-02-06)
- ✅ 코드 품질 개선 (중복 코드 제거, 구조화된 로깅)
- ✅ 커스텀 예외 체계 추가 (17개 예외 클래스)
- ✅ 테스트 커버리지 확대 (160 tests)
- ✅ 문서 업데이트 (버전 정보 통합)

### v0.4.0 (2026-02-05)
- ✅ API 키 검증 스크립트 추가 (`validate_api_keys.py`)
- ✅ 8개 주요 API 실제 검증 지원
- ✅ .env 파일 구조 개선 (REQUIRED/CORE/OPTIONAL 분류)
- ✅ 통합 가이드 문서 작성

### v0.3.0 (2026-02-02)
- ✅ Tool Ontology 기반 API 키 관리
- ✅ Environment Manager 추가 (`env_manager.py`)
- ✅ 40+ 도구 API 키 매핑 완성

### v0.2.0 (2025-12-XX)
- ✅ 기본 API 키 관리 기능
- ✅ CLI 환경 변수 명령어

---

**Last Updated**: 2026-02-06
**CAAS Version**: 0.4.1
**Author**: bullpeng72

---

## 요약

### 필수 액션 체크리스트

- [ ] OpenAI API 키 발급 및 설정 (필수)
- [ ] Serper API 키 발급 및 설정 (권장)
- [ ] .env 파일 생성 및 편집
- [ ] `python3 scripts/validate_api_keys.py` 실행
- [ ] 필요한 추가 API 키 발급

### 빠른 참조

```bash
# API 키 검증
python3 scripts/validate_api_keys.py

# 환경 변수 확인
caas env --list

# .env 편집
nano .env

# 도구 목록 확인
python3 -c "from caas_framework.knowledge.ontology.tool_manager import get_tool_ontology_manager; m = get_tool_ontology_manager(); [print(t.name) for t in m.get_all_tools()]"
```

이제 CAAS의 모든 API 키 관리 기능을 활용할 수 있습니다! 🚀
