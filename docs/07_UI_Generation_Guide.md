# UI Generation Guide (Streamlit & React)

**버전**: 1.0.0
**작성일**: 2026-02-10
**대상**: CAAS v0.4.1+

---

## 📋 목차

1. [개요](#개요)
2. [자동 UI 감지](#자동-ui-감지)
3. [수동 UI 생성](#수동-ui-생성)
4. [Streamlit UI 생성](#streamlit-ui-생성)
5. [React UI 생성](#react-ui-생성)
6. [한국어 UI 지원](#한국어-ui-지원)
7. [트러블슈팅](#트러블슈팅)

---

## 개요

CAAS는 **v0.4.1부터** UI 자동 생성 기능을 지원합니다. 요구사항에서 UI 관련 키워드를 자동으로 감지하고, Streamlit 또는 React 기반 프론트엔드 코드를 생성합니다.

### 지원 프레임워크

| 프레임워크 | 타입 | 난이도 | 배포 용이성 |
|-----------|------|--------|------------|
| **Streamlit** | Python 기반 | ⭐️ 쉬움 | ⭐️⭐️⭐️ 매우 높음 |
| **React** | JavaScript 기반 | ⭐️⭐️⭐️ 어려움 | ⭐️⭐️ 중간 |

**권장**: 빠른 프로토타입이나 데이터 중심 앱은 **Streamlit**, 복잡한 인터랙션은 **React**

---

## 자동 UI 감지

CAAS는 다음 3가지 방법으로 UI 생성 필요성을 자동으로 감지합니다:

### 1️⃣ UI 컴포넌트 감지

Golden Data의 `ui_components` 필드가 있으면 자동으로 UI 생성:

```json
{
  "ui_components": [
    {
      "component_type": "form",
      "page_name": "메인 페이지",
      "description": "키워드 입력 폼"
    },
    {
      "component_type": "table",
      "page_name": "결과 페이지",
      "description": "검색 결과 테이블"
    }
  ]
}
```

### 2️⃣ 실행 명령어 감지

Golden Data의 `commands.run`에서 `streamlit` 또는 `react` 키워드 감지:

```json
{
  "commands": {
    "run": "streamlit run main.py"
  }
}
```

### 3️⃣ Feature 키워드 감지

Feature 이름/설명에서 UI 관련 키워드 감지:

```json
{
  "features": [
    {
      "name": "Streamlit UI for Keyword Input",
      "description": "Provide a user interface using Streamlit"
    }
  ]
}
```

**감지되는 키워드**: `ui`, `streamlit`, `react`, `frontend`, `interface`, `dashboard`, `form`, `button`

---

## 수동 UI 생성

자동 감지가 작동하지 않거나 명시적으로 제어하고 싶은 경우 CLI 플래그를 사용합니다.

### CLI 옵션

```bash
caas generate "요구사항" --enable-frontend --frontend-framework streamlit
```

**파라미터**:
- `--enable-frontend`: UI 생성 활성화
- `--frontend-framework <streamlit|react>`: 프레임워크 선택 (기본값: streamlit)

### 예시

#### Streamlit 강제 생성
```bash
caas generate "블로그 관리 시스템" \
  --enable-frontend \
  --frontend-framework streamlit \
  --output ./blog-system
```

#### React 강제 생성
```bash
caas generate "실시간 대시보드" \
  --enable-frontend \
  --frontend-framework react \
  --output ./dashboard
```

---

## Streamlit UI 생성

### 생성되는 파일

```
generated/
├── main.py              # Streamlit 앱 진입점
├── src/
│   ├── agents.py        # CrewAI 에이전트
│   ├── tasks.py         # CrewAI 태스크
│   └── crew.py          # Crew 구성
├── requirements.txt     # streamlit 포함
└── README.md            # 실행 가이드
```

### 생성된 코드 예시

```python
# main.py (Streamlit)
import streamlit as st
from src.crew import create_crew

st.title("키워드 검색 요약 시스템")

# 입력 폼
with st.form("keyword_form"):
    keyword = st.text_input("검색 키워드 입력:", placeholder="예: AI 기술 트렌드")
    submitted = st.form_submit_button("검색")

if submitted and keyword:
    with st.spinner("검색 중..."):
        crew = create_crew()
        result = crew.kickoff(inputs={"keyword": keyword})

    st.success("검색 완료!")
    st.markdown("### 요약 보고서")
    st.write(result)
```

### 실행 방법

```bash
cd generated
pip install -r requirements.txt
streamlit run main.py
```

### 배포 (Streamlit Cloud)

1. GitHub 리포지토리 생성
2. [https://streamlit.io/cloud](https://streamlit.io/cloud) 접속
3. "New app" → 리포지토리 선택
4. `main.py` 지정 → Deploy

---

## React UI 생성

### 생성되는 파일

```
generated/
├── frontend/            # React 앱
│   ├── src/
│   │   ├── App.tsx      # 메인 컴포넌트
│   │   ├── components/  # UI 컴포넌트
│   │   └── services/    # API 클라이언트
│   ├── package.json
│   └── tsconfig.json
├── backend/             # FastAPI 백엔드
│   ├── main.py          # API 서버
│   ├── src/
│   │   ├── agents.py
│   │   └── tasks.py
│   └── requirements.txt
└── docker-compose.yml   # 통합 실행
```

### 생성된 코드 예시

**Frontend (React + TypeScript)**:
```tsx
// frontend/src/App.tsx
import React, { useState } from 'react';
import { searchKeyword } from './services/api';

function App() {
  const [keyword, setKeyword] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    try {
      const data = await searchKeyword(keyword);
      setResult(data.report);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h1>키워드 검색 요약 시스템</h1>
      <input
        type="text"
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        placeholder="검색 키워드 입력"
      />
      <button onClick={handleSearch} disabled={loading}>
        {loading ? '검색 중...' : '검색'}
      </button>
      {result && <div className="result">{result}</div>}
    </div>
  );
}
```

**Backend (FastAPI)**:
```python
# backend/main.py
from fastapi import FastAPI
from src.crew import create_crew

app = FastAPI()

@app.post("/api/search")
async def search(keyword: str):
    crew = create_crew()
    result = crew.kickoff(inputs={"keyword": keyword})
    return {"report": str(result)}
```

### 실행 방법

**개발 모드**:
```bash
# Terminal 1: Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm install
npm start  # http://localhost:3000
```

**프로덕션 (Docker)**:
```bash
docker-compose up --build
```

---

## 한국어 UI 지원

CAAS는 요구사항에서 한국어를 자동 감지하고 UI 텍스트를 한국어로 생성합니다.

### 자동 감지 조건

1. **한글 문자 감지**: Feature 이름/설명에 한글이 포함됨
2. **명시적 키워드**: "한국어", "in Korean" 등
3. **Golden Data 언어 설정**: `code_style.language: "ko"`

### 한국어 UI 예시

```python
# main.py (한국어 Streamlit)
import streamlit as st

st.title("📊 키워드 검색 요약 시스템")

st.markdown("""
이 시스템은 입력한 키워드로 인터넷 검색을 수행하고,
결과를 요약하여 한국어 보고서를 생성합니다.
""")

with st.form("search_form"):
    keyword = st.text_input(
        "검색 키워드:",
        placeholder="예: 인공지능 최신 동향",
        help="검색하고 싶은 주제를 입력하세요"
    )

    col1, col2 = st.columns(2)
    with col1:
        search_depth = st.selectbox("검색 깊이:", ["기본", "상세", "전문가"])
    with col2:
        result_count = st.number_input("결과 개수:", min_value=5, max_value=50, value=10)

    submitted = st.form_submit_button("🔍 검색 시작")

if submitted and keyword:
    with st.spinner("검색 및 분석 중입니다..."):
        # CrewAI 실행 로직
        pass

    st.success("✅ 검색이 완료되었습니다!")

    # 결과 표시
    st.markdown("### 📄 요약 보고서")
    with st.expander("상세 보기", expanded=True):
        st.write(result)

    # 다운로드 버튼
    st.download_button(
        label="📥 보고서 다운로드",
        data=result,
        file_name=f"보고서_{keyword}.txt",
        mime="text/plain"
    )
```

### 에러 메시지 한국어화

```python
# src/crew.py
try:
    result = crew.kickoff(inputs=user_inputs)
except Exception as e:
    st.error(f"❌ 오류 발생: {str(e)}")
    st.info("💡 다른 키워드로 다시 시도해 주세요.")
```

---

## 트러블슈팅

### 문제 1: UI가 생성되지 않음

**증상**: `main.py`가 CLI 기반 코드로 생성됨

**해결 방법**:
```bash
# 1. 명시적으로 UI 생성 플래그 사용
caas generate "요구사항" --enable-frontend

# 2. 요구사항에 UI 키워드 명시
caas generate "Streamlit UI로 키워드 입력받는 시스템" --output ./app
```

### 문제 2: 한국어 출력이 안 됨

**증상**: UI 텍스트가 영어로 생성됨

**해결 방법**:
```bash
# 요구사항에 한국어 명시
caas generate "한국어로 출력하는 검색 시스템, Streamlit UI 제공" --output ./app
```

또는 Golden Data에 언어 설정 추가:
```json
{
  "code_style": {
    "language": "ko"
  }
}
```

### 문제 3: Streamlit vs React 선택이 잘못됨

**증상**: React를 원했는데 Streamlit이 생성됨

**해결 방법**:
```bash
# 명시적으로 프레임워크 지정
caas generate "대시보드 시스템" \
  --enable-frontend \
  --frontend-framework react \
  --output ./dashboard
```

### 문제 4: 생성된 코드 커스터마이징

**생성 후 수동 수정 가이드**:

1. **Streamlit 레이아웃 변경**:
   ```python
   # main.py 수정
   col1, col2, col3 = st.columns([1, 2, 1])  # 컬럼 비율 조정

   with st.sidebar:  # 사이드바 추가
       st.header("설정")
       theme = st.selectbox("테마:", ["라이트", "다크"])
   ```

2. **스타일링 추가**:
   ```python
   # Streamlit CSS
   st.markdown("""
   <style>
   .stButton button {
       background-color: #4CAF50;
       color: white;
   }
   </style>
   """, unsafe_allow_html=True)
   ```

3. **React 컴포넌트 추가**:
   ```bash
   cd frontend/src/components
   # 새 컴포넌트 생성
   ```

---

## 다음 단계

- [Deployment Guide](07_Deployment_Guide.md) - UI 앱 배포 방법
- [CLI Usage Guide](04_CLI_Usage_Guide.md) - 전체 CLI 옵션
- [Quick Start Guide](03_Quick_Start_Guide.md) - 빠른 시작

---

## 관련 리소스

- [Streamlit Documentation](https://docs.streamlit.io/)
- [React Documentation](https://react.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

**Last Updated**: 2026-02-10
**Version**: 1.0.0 (CAAS v0.4.1+)
