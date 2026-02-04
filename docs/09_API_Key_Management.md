# API Key Management for CrewAI Tools

CAAS 프레임워크에 CrewAI 도구와 MCP 서버를 위한 API 키 관리 기능이 추가되었습니다.

## 📋 개요

많은 CrewAI 도구들은 외부 서비스의 API 키가 필요합니다. 이제 CAAS는:
- ✅ API 키 요구사항 자동 감지
- ✅ .env 파일에서 API 키 관리
- ✅ Streamlit UI에서 API 키 설정/확인
- ✅ 생성된 코드에서 API 키 자동 로드
- ✅ 도구별 API 키 상태 표시

## 🚀 주요 기능

### 1. API 키 요구사항 매핑 (`caas_framework/codegen/tool_api_keys.py`)

각 도구가 필요로 하는 API 키 정보를 정의:
- 환경 변수 이름
- 설명
- 필수 여부 (optional/required)
- 회원가입 URL
- 초기화 파라미터 이름 (있는 경우)

```python
from app.codegen.tool_api_keys import (
    get_tool_api_key_requirements,
    is_tool_requires_api_key
)

# 도구가 API 키를 필요로 하는지 확인
if is_tool_requires_api_key("SerperDevTool"):
    # API 키 요구사항 가져오기
    requirements = get_tool_api_key_requirements("SerperDevTool")
    for req in requirements:
        print(f"{req.env_var}: {req.description}")
```

### 2. 환경 변수 관리자 (`caas_framework/utils/env_manager.py`)

.env 파일을 프로그래밍 방식으로 관리:

```python
from app.utils.env_manager import get_env_manager

env_manager = get_env_manager()

# API 키 설정
env_manager.set_value("SERPER_API_KEY", "your-api-key-here")

# API 키 확인
value = env_manager.get_value("SERPER_API_KEY")

# API 키가 설정되었는지 확인
if env_manager.is_key_set("SERPER_API_KEY"):
    print("API key is configured!")

# 모든 환경 변수 가져오기
all_vars = env_manager.get_all_values()

# 여러 키 한번에 설정
env_manager.bulk_set({
    "SERPER_API_KEY": "key1",
    "BRAVE_API_KEY": "key2"
})
```

### 3. CLI 환경 변수 관리

CAAS CLI는 `.env` 파일을 통해 API 키를 관리합니다.

#### 3.1 환경 변수 확인
```bash
caas env --list
```

#### 3.2 특정 키 확인
```bash
caas env --get OPENAI_API_KEY
```

#### 3.3 API 키 설정 도구 위치
- **파일 경로**: `.env`
- **예제**: `.env.example`
- **도구 레지스트리**: `data/tools_registry.json`

## 🔧 지원되는 도구

### Search Tools
| 도구 | 환경 변수 | 필수 여부 |
|------|-----------|-----------|
| SerperDevTool | `SERPER_API_KEY` | Required |
| BraveSearchTool | `BRAVE_API_KEY` | Required |
| TavilySearchTool | `TAVILY_API_KEY` | Required |
| EXASearchTool | `EXA_API_KEY` | Required |

### Web Scraping
| 도구 | 환경 변수 | 필수 여부 |
|------|-----------|-----------|
| FirecrawlScrapeWebsiteTool | `FIRECRAWL_API_KEY` | Required |
| JinaScrapeWebsiteTool | `JINA_API_KEY` | Required |
| SpiderTool | `SPIDER_API_KEY` | Required |

### Communication
| 도구 | 환경 변수 | 필수 여부 |
|------|-----------|-----------|
| TwilioTool | `TWILIO_ACCOUNT_SID`<br>`TWILIO_AUTH_TOKEN`<br>`TWILIO_PHONE_NUMBER` | Required |

### Code Tools
| 도구 | 환경 변수 | 필수 여부 |
|------|-----------|-----------|
| GithubSearchTool | `GITHUB_TOKEN` | Optional |

### AI/ML Tools
| 도구 | 환경 변수 | 필수 여부 |
|------|-----------|-----------|
| HuggingFaceModelTool | `HUGGINGFACE_API_KEY` | Optional |

### Database Tools
| 도구 | 환경 변수 | 필수 여부 |
|------|-----------|-----------|
| MySQLSearchTool | `MYSQL_CONNECTION_STRING` | Required |
| MongoDBVectorSearchTool | `MONGODB_URI` | Required |
| SnowflakeSearchTool | `SNOWFLAKE_ACCOUNT`<br>`SNOWFLAKE_USER`<br>`SNOWFLAKE_PASSWORD` | Required |

### Productivity
| 도구 | 환경 변수 | 필수 여부 |
|------|-----------|-----------|
| GoogleAnalyticsSearchTool | `GOOGLE_ANALYTICS_CREDENTIALS` | Required |
| GoogleCalendarSearchTool | `GOOGLE_CALENDAR_CREDENTIALS` | Required |
| GoogleDocsSearchTool | `GOOGLE_DOCS_CREDENTIALS` | Required |
| GoogleSheetsSearchTool | `GOOGLE_SHEETS_CREDENTIALS` | Required |
| NotionSearchTool | `NOTION_API_KEY` | Required |
| MixpanelSearchTool | `MIXPANEL_API_SECRET` | Required |

### Other Tools
| 도구 | 환경 변수 | 필수 여부 |
|------|-----------|-----------|
| MultiOnTool | `MULTION_API_KEY` | Required |
| ComposioTool | `COMPOSIO_API_KEY` | Required |

## 📝 사용 방법

### 1. .env 파일 직접 편집

`.env` 파일을 직접 수정할 수도 있습니다:

```bash
# .env 파일 편집
nano .env

# API 키 추가
SERPER_API_KEY=your-api-key-here
BRAVE_API_KEY=your-brave-api-key
TAVILY_API_KEY=your-tavily-api-key
```

### 2. CLI 환경 변수 관리

```bash
# 환경 변수 설정
export SERPER_API_KEY=your-api-key-here

# 또는 .env 파일에 추가
echo "SERPER_API_KEY=your-api-key-here" >> .env

# 환경 변수 확인
caas env --list

# 특정 키 확인
caas env --get SERPER_API_KEY
}
success_count, failed_keys = env_manager.bulk_set(keys)
print(f"Successfully set {success_count} keys")
```

## 🔐 보안 고려사항

1. **민감 정보 보호**
   - .env 파일은 `.gitignore`에 포함되어 있습니다
   - Git에 API 키를 커밋하지 마세요
   - `.env.example` 파일만 공유하세요

2. **API 키 마스킹**
   - UI에서 API 키는 기본적으로 마스킹됩니다
   - "Show" 버튼을 눌러야 전체 키를 볼 수 있습니다

3. **백업**
   ```python
   # .env 백업 생성
   env_manager.backup()

   # 백업에서 복원
   env_manager.restore()
   ```

## 🧪 테스트

### API 키 검증 테스트

```python
from app.utils.env_manager import get_env_manager
from app.codegen.tool_api_keys import get_tool_api_key_requirements

env_manager = get_env_manager()

# SerperDevTool 요구사항 확인
requirements = get_tool_api_key_requirements("SerperDevTool")
for req in requirements:
    is_set = env_manager.is_key_set(req.env_var)
    status = "✅" if is_set else "❌"
    print(f"{status} {req.env_var}: {req.description}")
```

### 생성된 코드에서 자동 로드 확인

생성된 `agents.py` 파일에서:
```python
# TOOL_REQUIREMENTS에 API 키 정보가 포함됨
TOOL_REQUIREMENTS = {
    "SerperDevTool": {
        "env_var": "SERPER_API_KEY",
        "param_name": None,
        "optional": False,
    },
    # ...
}

# create_tools 함수가 자동으로 API 키를 확인하고 로드
tools = create_tools(["SerperDevTool"])
```

## 📚 관련 파일

### 핵심 파일
- `caas_framework/codegen/tool_api_keys.py` - API 키 요구사항 정의
- `caas_framework/utils/env_manager.py` - 환경 변수 관리 유틸리티
- `caas_streamlit/pages/9_🔧_Tool_Manager.py` - Streamlit UI
- `.env.example` - 환경 변수 예제

### 템플릿
- `data/templates/agents_with_error_handling.py.j2` - TOOL_REQUIREMENTS 매핑 포함

## 🔄 워크플로우

```
사용자가 프로젝트 생성 요청
    ↓
CAAS가 필요한 도구 분석
    ↓
각 도구의 API 키 요구사항 확인
    ↓
.env 파일에서 API 키 로드
    ↓
생성된 코드에 TOOL_REQUIREMENTS 포함
    ↓
agents.py 실행 시 자동으로 API 키 로드
    ↓
API 키가 없으면 경고 메시지 표시
    ↓
Optional 도구는 스킵, Required 도구는 에러
```

## 🆕 추가된 기능 요약

1. ✅ **API 키 요구사항 자동 감지**
   - 40+ 도구에 대한 API 키 매핑
   - 필수/선택 구분
   - 회원가입 URL 제공

2. ✅ **.env 파일 관리**
   - 프로그래밍 방식으로 읽기/쓰기
   - 백업/복원 기능
   - 벌크 설정 지원

3. ✅ **Streamlit UI 통합**
   - 카테고리별 API 키 설정
   - 실시간 상태 확인
   - 도구별 요구사항 표시

4. ✅ **생성된 코드 자동화**
   - TOOL_REQUIREMENTS 자동 생성
   - API 키 자동 로드
   - 에러 핸들링 개선

5. ✅ **Browse Tools 개선**
   - API 키 상태 배지 (🟢/🔴)
   - 요구사항 명시
   - 사용 예제 개선

## 🎉 결론

이제 CAAS 프레임워크는 CrewAI 도구의 API 키를 효율적으로 관리할 수 있습니다:
- 💡 직관적인 UI로 쉽게 설정
- 🔒 안전한 .env 파일 관리
- 🤖 생성된 코드에서 자동 로드
- ✅ 실시간 상태 확인

API 키 관리가 이제 훨씬 쉬워졌습니다! 🚀
