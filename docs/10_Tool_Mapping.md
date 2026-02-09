# 도구 매핑 워크플로우 가이드

**최종 업데이트**: 2026-02-06
**버전**: v0.4.1

---

## 개요

CAAS 시스템은 온톨로지 기반의 지능형 도구 매핑 워크플로우를 제공하여, 에이전트의 역할과 태스크에 따라 자동으로 적절한 도구를 추천하고 할당합니다.

### 최신 개선사항 ✨

- ✅ **40+ 도구 지원**: CrewAI 도구 34개 매핑으로 확장
- ✅ **온톨로지 통합**: 중앙화된 도구 온톨로지 관리
- ✅ **AI 추론 통합**: 자동 도구 추천 및 할당
- ✅ **한국어 도구명 지원**: 40+ 번역 용어로 한국어 도구명 자동 변환
- ✅ **3-Layer Defense**: tools.py 생성 100% 보장 (v0.3.0+)
- ✅ **멀티 LLM 지원**: OpenAI, Anthropic, Ollama (v0.4.1)

---

## 아키텍처

도구 매핑 시스템은 3개 핵심 계층으로 구성됩니다:

```
┌─────────────────────────────────────────────────────────┐
│                   Interface Layer                       │
│  - CLI (caas generate, 29 commands)                    │
│  - Python SDK (CrewAIFramework API)                    │
│  - 40+ 도구 자동 매핑 및 선택                          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Tool Ontology Layer                        │
│  - 개념적 도구 (예: "web_search")                      │
│  - 도구당 여러 구현체                                   │
│  - 영구 저장소 (data/ontology/tools.json)              │
│  - ToolOntologyManager (중앙 관리)                     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│           AI Inference Engine                           │
│  - 태스크 기반 도구 추천                                │
│  - 역할 기반 도구 매칭                                  │
│  - 키워드 및 의미 매칭                                  │
│  - 한국어-영어 번역 지원 (40+ 용어)                    │
│  - 3-Layer Defense (Validation → LLM → Fallback)      │
└─────────────────────────────────────────────────────────┘
```

**참고**: CAAS는 CLI/Framework 기반 도구입니다. Web UI는 포함되지 않습니다.

---

## 도구 카테고리

### 1. File Operations (파일 작업)
- file_read, file_write, directory_read, directory_search

### 2. Web Search (웹 검색)
- web_search, brave_search, tavily_search, website_search

### 3. Web Scraping (웹 크롤링)
- scrape_website, selenium_scraping, firecrawl_scraping

### 4. Document Search (문서 검색)
- pdf_search, csv_search, json_search, docx_search, txt_search, xml_search

### 5. Code & Development (코드 및 개발)
- code_interpreter, calculator, github_search, code_docs_search

### 6. Database (데이터베이스)
- database_query, mysql_search, mongodb_search, snowflake_search

### 7. Vision & Images (이미지)
- vision

### 8. YouTube
- youtube_search, youtube_channel_search

### 9. Other (기타)
- rag_tool

---

## 한국어 도구명 지원 ✨

CAAS는 한국어 도구명을 자동으로 영어 클래스명으로 변환합니다.

### 번역 맵 (40+ 용어)

**파일**: `caas_framework/codegen/llm_code_generator.py`

| 한국어 | 영어 클래스 | 카테고리 |
|--------|-------------|----------|
| 키보드 | KeyboardTool | 시스템 |
| 마우스 | MouseTool | 시스템 |
| 웹 크롤러 | WebScraperTool | 웹 |
| 인터넷 검색 | InternetSearchTool | 검색 |
| 데이터 분석 도구 | DataAnalysisTool | 분석 |
| 보고서 생성 | ReportGeneratorTool | 문서 |
| 파일 읽기 | FileReadTool | 파일 |
| 파일 쓰기 | FileWriteTool | 파일 |
| ... | ... | ... |

**전체 목록**: 40+ 용어 (코드 참조)

### 자동 변환 예시

**입력 (agents.json)**:
```json
{
  "role": "연구원",
  "tools": ["키보드", "웹 크롤러", "인터넷 검색"]
}
```

**출력 (tools.py)**:
```python
class KeyboardTool(BaseTool):
    name: str = "키보드"
    description: str = "키보드 조작 도구"

class WebScraperTool(BaseTool):
    name: str = "웹 크롤러"
    description: str = "웹 크롤링 도구"

class InternetSearchTool(BaseTool):
    name: str = "인터넷 검색"
    description: str = "인터넷 검색 도구"
```

---

## AI 자동 도구 추천

CAAS는 에이전트의 역할, 목표, 할당된 태스크를 분석하여 자동으로 추가 도구를 추천합니다.

### 예시 1: 연구 에이전트

**입력**:
```json
{
  "role": "Researcher",
  "goal": "Research latest AI trends and write summary",
  "tools": ["web_search"]
}
```

**AI 분석 및 추천**:
1. LLM이 생성: `["web_search"]`
2. AI가 분석:
   - 역할: "Researcher"
   - 목표: "Research and summarize"
   - 태스크: "Search web, compile findings"
3. AI 추천: `["web_search", "brave_search", "file_write"]`
4. **최종 도구**: `["web_search", "brave_search", "file_write"]`

**로그 출력**:
```
Tool recommendation for 'Researcher':
LLM suggested 1, AI recommended 3, final 3 tools
```

### 예시 2: 데이터 분석 에이전트

**입력**:
```json
{
  "role": "Data Analyst",
  "goal": "Analyze customer data from CSV files",
  "tools": ["csv_search"]
}
```

**AI 추천**:
1. LLM: `["csv_search"]`
2. AI 추천: `["csv_search", "file_read", "calculator", "file_write"]`
3. **최종**: 4개 도구

---

## 도구 추천 알고리즘

AI 추론 엔진은 여러 매칭 전략을 사용합니다:

### 1. Exact Match (정확한 매칭)
```python
if task_type.lower() in [t.lower() for t in tool.compatible_tasks]:
    recommend(tool)  # 신뢰도: 0.9
```

### 2. Keyword Match (키워드 매칭)
```python
if task_keyword in " ".join(tool.tags).lower():
    recommend(tool)  # 신뢰도: 0.7
```

### 3. Semantic Match (의미 매칭)
```python
if task_keyword in tool.description.lower():
    recommend(tool)  # 신뢰도: 0.5
```

### 4. Role-Based Matching (역할 기반 매칭)
```python
if agent_role in tool.compatible_roles:
    boost_confidence(tool)
```

### 5. Translation Match (번역 매칭) ✨ NEW
```python
# 한국어 도구명을 영어로 변환
sanitized_name = translation_map.get(korean_name, hash_fallback(korean_name))
```

---

## 사용 방법

### 1. CLI 사용

```bash
# 프로젝트 생성 (자동 도구 추천)
caas generate "블로그 플랫폼 만들기" --output ./blog

# tools.py 확인
cat ./blog/src/tools.py
```

### 2. Python API 사용

```python
from caas_framework.framework import CrewAIFramework
from caas_framework.plugins.llm.openai import OpenAIPlugin

# LLM 초기화 (OpenAI, Anthropic, Ollama 중 선택)
llm = OpenAIPlugin(model="gpt-4o-mini")

# Framework 초기화
framework = CrewAIFramework(llm_plugin=llm)
await framework.initialize()

# 프로젝트 생성 (자동 도구 추천 포함)
result = await framework.generate_from_requirement(
    requirement="금융 뉴스 분석기 만들기",
    domain_hint="DATA_ANALYSIS"
)

# 추천된 도구 확인
for agent_file in result.files.get("agents.py", ""):
    print(f"Agent tools: {agent_file}")
```

**Ollama 사용 예시** (v0.4.1):
```python
from caas_framework.plugins.llm.ollama import OllamaPlugin

# Ollama 로컬 LLM (API 키 불필요)
llm = OllamaPlugin(
    model="llama3.1:8b",
    base_url="http://localhost:11434/v1"
)
```

### 3. 온톨로지 직접 사용

```python
from caas_framework.knowledge.ontology.tool_manager import get_tool_ontology_manager

# 온톨로지 매니저 가져오기
tool_manager = get_tool_ontology_manager()

# 모든 도구 조회
all_tools = tool_manager.get_all_tools(enabled_only=True)
print(f"Available tools: {len(all_tools)}")

# 특정 도구 조회
search_tool = tool_manager.get_tool("web_search")
print(f"Display name: {search_tool.display_name}")
print(f"Implementations: {len(search_tool.implementations)}")

# 도구 추천 (AI 추론 기반)
recommended = tool_manager.recommend_tools(
    task_description="웹에서 데이터 수집",
    agent_role="Researcher"
)
print(f"Recommended: {[t.name for t in recommended]}")
```

---

## 새 도구 추가하기

### 방법 1: 온톨로지에 추가 (권장)

`caas_framework/knowledge/ontology/tool_data_generator.py` 편집:

```python
def generate_initial_ontology() -> ToolOntology:
    tools = []

    # 새 도구 추가
    tools.append(ConceptualTool(
        id="tool_new_feature",
        name="new_feature",
        display_name="새로운 기능 도구",
        category=ToolCategory.OTHER,
        description="이 도구가 하는 일에 대한 설명",
        use_cases=["사용 사례 1", "사용 사례 2"],
        implementations=[
            ToolImplementation(
                crewai_class="NewFeatureTool",
                name="구현체 이름",
                description="구현 방식",
                requires_api_key=False
            )
        ],
        default_implementation="NewFeatureTool",
        compatible_roles=["Developer", "Analyst"],
        compatible_tasks=["development", "analysis"],
        tags=["feature", "new"]
    ))

    return ToolOntology(version="1.0.0", tools=tools)
```

온톨로지 재생성:
```bash
rm data/ontology/tools.json
python -c "from caas_framework.knowledge.ontology.tool_manager import get_tool_ontology_manager; get_tool_ontology_manager().load()"
```

### 방법 2: 매핑에 직접 추가 (빠른 방법)

`caas_framework/codegen/tool_generator.py` 편집:

```python
TOOL_NAME_TO_CREWAI = {
    # ... 기존 매핑 ...
    "new_feature": "NewFeatureTool",
}
```

---

## 모니터링 및 로그

시스템은 각 단계에서 상세한 로깅을 제공합니다:

```python
# 도구 로딩
INFO: Loaded 22 tools

# 도구 추천
INFO: Tool recommendation for 'Agent Name':
      LLM suggested 3, AI recommended 5, final 6 tools

# 추론 엔진
INFO: 도구 추론: tasks=[RESEARCH, ANALYSIS]

# Fallback
WARNING: Failed to use Tool Ontology Manager, falling back to legacy
```

디버그 로깅 활성화:
```bash
export LOG_LEVEL=DEBUG
```

---

## 문제 해결

### 문제: 잘못된 도구 추천

**해결책**: 온톨로지 메타데이터 업데이트
- `compatible_tasks`가 사용 사례와 일치하는지 확인
- 관련 키워드를 `tags`에 추가
- `description`에 의미있는 키워드 포함

### 문제: 한국어 도구명이 변환되지 않음 ✨

**해결책**: 번역 맵에 추가
```python
# caas_framework/codegen/llm_code_generator.py
translation_map = {
    "새로운_도구": "NewCustomTool",
    # ... 추가
}
```

### 문제: tools.py 생성 실패

**해결책**: 3-Layer Defense로 자동 해결됩니다! (v0.3.0+)
- ✅ **Layer 1: Validation** - 한국어 도구명 자동 변환 (40+ 용어)
- ✅ **Layer 2: LLM Generation** - BaseTool 상속, 에러 핸들링 포함
- ✅ **Layer 3: Fallback Stub** - LLM 실패 시 자동 생성
- ✅ 항상 실행 가능한 코드 보장 (100% 생성률)

---

## 성능 고려사항

1. **온톨로지 로딩**: 한 번 로드 후 메모리에 캐싱 (싱글톤 패턴)
2. **도구 추천**: O(n*m) 복잡도 (일반적으로 <1초)
3. **3-Layer Defense**: Validation → LLM → Fallback (평균 2-5초)
4. **Fallback Stub**: LLM 실패 시 즉시 생성 (<100ms)

---

## 향후 개선사항

- [ ] 머신러닝 기반 도구 추천
- [ ] 사용 통계 및 성공률 추적
- [ ] 도구 조합 A/B 테스트
- [ ] 도구 의존성 해결 (예: code_interpreter는 file_write 필요)
- [ ] 커스텀 도구 생성 UI
- [ ] 도구 성능 벤치마킹
- [ ] 다국어 도구 설명

---

## 참고 자료

### CAAS 핵심 파일

- **도구 온톨로지 스키마**: `caas_framework/knowledge/ontology/tool_ontology.py`
- **도구 매니저**: `caas_framework/knowledge/ontology/tool_manager.py`
- **도구 생성기**: `caas_framework/codegen/tool_generator.py`
- **LLM 코드 생성기**: `caas_framework/codegen/llm_code_generator.py` (번역 맵 포함)
- **도구 API 키 관리**: `caas_framework/codegen/tool_api_keys.py`
- **도구 온톨로지 데이터**: `data/ontology/tools.json` (40+ 도구)

### CAAS 문서

- [01_README_KO.md](01_README_KO.md) - 프로젝트 개요
- [04_CLI_Usage_Guide.md](04_CLI_Usage_Guide.md) - CLI 사용 가이드 (29 commands)
- [06_Architecture_Guide.md](06_Architecture_Guide.md) - 아키텍처 가이드
- [09_API_Key_Management.md](09_API_Key_Management.md) - API 키 관리 (40+ 도구)
- [15_Ollama_Setup_Guide.md](15_Ollama_Setup_Guide.md) - Ollama 로컬 LLM 설정

### 외부 문서

- [CrewAI Tools Documentation](https://docs.crewai.com/tools/)
- [CrewAI Tools GitHub](https://github.com/joaomdmoura/crewai-tools)

---

**최종 업데이트**: 2026-02-06
**CAAS 버전**: v0.4.1
**문서 버전**: 1.2.0
**상태**: Production Ready ✅
