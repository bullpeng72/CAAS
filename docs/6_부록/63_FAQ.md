# FAQ (자주 묻는 질문)

## 🎯 이 문서의 목적
- CAAS 사용 중 자주 묻는 질문 정리
- 카테고리별 분류 (설치, 생성, 품질, 성능, 트러블슈팅)
- 빠른 해결책 제공

⏱️ **사용 방법**: 카테고리별로 탐색 또는 Ctrl+F로 검색

---

## 📦 설치 및 설정

### Q1. CAAS 설치 방법은?

**A**:
```bash
# PyPI에서 설치 (권장)
pip install caas

# 또는 소스 코드에서 설치
git clone https://github.com/bullpeng72/CAAS.git
cd CAAS
pip install -e .
```

**관련 문서**: [01_CAAS_소개_및_설치.md](../1_시작하기/01_CAAS_소개_및_설치.md)

---

### Q2. 어떤 LLM 공급자를 사용할 수 있나요?

**A**: 3가지 공급자 지원.
- **OpenAI** (기본, 가장 안정적)
- **Anthropic** (Claude 모델)
- **Ollama** (로컬 실행, 무료)

**설정**:
```bash
# OpenAI (기본)
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Ollama
export OLLAMA_API_BASE="http://localhost:11434/v1"
caas config --set llm_provider ollama
```

---

### Q3. API 키가 없으면 사용할 수 없나요?

**A**: **Ollama 사용 시 무료**로 로컬에서 실행 가능.
```bash
# Ollama 설치
curl -fsSL https://ollama.ai/install.sh | sh

# 모델 다운로드
ollama pull llama3:70b

# CAAS 설정
caas config --set llm_provider ollama
caas generate "할일 관리" --output ./todo
```

**단점**: 생성 시간 2배 증가 (5분 → 10분), 코드 품질 약간 낮음 (8.5 → 8.0)
**장점**: 비용 $0, 데이터 프라이버시 보장

---

### Q4. Python 버전 요구사항은?

**A**: **Python 3.11 이상** 필수.
```bash
python --version
# Python 3.11.0 이상이어야 함
```

**업그레이드**:
```bash
# pyenv 사용
pyenv install 3.11.0
pyenv global 3.11.0
```

---

## 🚀 프로젝트 생성

### Q5. 어떤 도메인이 가장 잘 지원되나요?

**A**: **Top 3 도메인** (98%+ 구현률):
1. **CONVERSATIONAL_AI** (98.7%) - 챗봇, 대화형 AI
2. **DATA_ANALYSIS** (98.3%) - 데이터 분석, 시각화
3. **CONTENT_CREATION** (98.7%) - 콘텐츠 자동 생성

**권장**: 처음 사용 시 이 3개 도메인 중 하나로 시작.

**관련 문서**: [60_프레임워크_데이터구조.md](./60_프레임워크_데이터구조.md)

---

### Q6. 생성 시간이 얼마나 걸리나요?

**A**: 프로젝트 복잡도에 따라 다름.
- **단순 프로젝트** (3-5 features): 2-4분
- **중간 프로젝트** (6-10 features): 5-8분
- **복잡한 프로젝트** (11-20 features): 10-15분

**최적화 방법**:
```bash
# 분산 병렬 실행 활성화 (-30% 시간)
caas generate "..." --distributed --workers 4

# Haiku 모델 사용 (단순 작업)
caas generate "..." --model haiku  # 2-3분

# 캐싱 활성화
caas config --set llm_cache true
```

**관련 문서**: [53_성능_최적화_가이드.md](../5_엔터프라이즈_기능/53_성능_최적화_가이드.md)

---

### Q7. UI를 포함해서 생성할 수 있나요?

**A**: **Streamlit** 또는 **Gradio** UI 자동 생성 가능.
```bash
# Streamlit UI 포함
caas generate "할일 관리" --ui streamlit --output ./todo

# 실행
cd todo
streamlit run app.py
```

**생성 파일**: `app.py` (Streamlit 앱 코드)

---

### Q8. 생성된 코드를 바로 실행할 수 있나요?

**A**: **예**, 프로덕션 레디 코드 생성.
```bash
cd ./generated
pip install -r requirements.txt
cp .env.example .env
# .env에 OPENAI_API_KEY 설정

# CLI 실행
python main.py

# Streamlit UI 실행
streamlit run app.py
```

**품질**: 평균 코드 품질 8.5/10.0, 보안 스캔 통과

---

### Q9. 특정 Phase만 재실행할 수 있나요?

**A**: **예**, Phase별 재생성 가능.
```bash
# Phase 5만 재생성 (코드만)
caas generate-phase --phase 5 "할일 관리" \
  --output ./todo \
  --force

# Phase 2 재생성 (Architecture만)
caas generate-phase --phase 2 "할일 관리" \
  --output ./todo \
  --force
```

**주의**: `--force` 플래그 사용 시 기존 파일 덮어씀. 체크포인트 저장 권장.

---

## ✅ 코드 품질 및 QA

### Q10. 생성된 코드의 품질 기준은?

**A**: **5가지 메트릭** 평가.
| 항목 | 기준 | 설명 |
|------|------|------|
| Code Quality | ≥8.5/10.0 | Docstring, Type Hints, Complexity 종합 |
| Test Coverage | ≥80% | 단위 테스트 커버리지 |
| Security | 0 Critical | OWASP Top 10 검사 |
| Traceability | 100% | Feature → Component 매핑 |
| Completeness | 100% | Feature → Agent/Task 매핑 |

**검증**:
```bash
caas qa report --project ./todo --output qa_report.html
```

**관련 문서**: [15_코드_품질_가이드.md](../2_개발_실무_가이드/15_코드_품질_가이드.md)

---

### Q11. 코드 품질이 낮으면 어떻게 하나요?

**A**: **자동 수정** 기능 사용.
```bash
# Level 3 (LLM 기반) 자동 수정
caas fix --level 3 --project ./todo --apply --backup

# 결과:
# Code Quality: 7.2 → 8.6 (개선)
# Docstring: 3개 추가
# Type Hints: 7개 추가
# Complexity: 6.2 → 4.1 (감소)
```

**관련 문서**: [22_트러블슈팅_가이드.md](../2_개발_실무_가이드/22_트러블슈팅_가이드.md)

---

### Q12. 보안 취약점은 어떻게 확인하나요?

**A**: **보안 스캔** 자동 실행.
```bash
# OWASP Top 10 검사
caas qa security --project ./todo --output security_report.json

# 결과:
# CRITICAL: 0
# HIGH: 1 (SQL Injection)
# MEDIUM: 2 (Hardcoded Secret)

# 자동 수정
caas fix --level 3 --project ./todo --apply --backup
```

**관련 문서**: [51_QA_자동화_가이드.md](../5_엔터프라이즈_기능/51_QA_자동화_가이드.md)

---

## 💰 성능 및 비용

### Q13. LLM 비용이 얼마나 드나요?

**A**: 프로젝트당 평균 **$0.50** (OpenAI Sonnet 기준).
- **Haiku**: $0.20 (60% 절감)
- **Sonnet**: $0.50 (기본값)
- **Opus**: $2.00 (복잡한 프로젝트)
- **Ollama**: $0.00 (무료, 로컬)

**비용 절감 방법**:
```bash
# 1. Haiku 모델 사용 (단순 작업)
caas generate "..." --model haiku  # -60% 비용

# 2. 캐싱 활성화
caas config --set llm_cache true  # 동일 요구사항 재사용 시 무료

# 3. Ollama 사용 (무료)
caas config --set llm_provider ollama  # $0
```

**관련 문서**: [53_성능_최적화_가이드.md](../5_엔터프라이즈_기능/53_성능_최적화_가이드.md)

---

### Q14. 생성 시간을 더 단축할 수 있나요?

**A**: **3가지 최적화 방법**.
```bash
# 1. 분산 병렬 실행 (-30% 시간)
caas generate "..." --distributed --workers 4

# 2. 캐싱 활성화 (-90% 시간, 동일 요구사항)
caas config --set llm_cache true

# 3. Haiku 모델 (-40% 시간)
caas generate "..." --model haiku
```

**효과**: 10분 → 4분 (60% 단축)

---

### Q15. 대규모 프로젝트 (100+ features)도 처리 가능한가요?

**A**: **예**, 스트리밍 모드 사용.
```bash
# 100개 features → 청크 단위 처리
caas generate "대규모 시스템 (100 features)" \
  --output ./large-system \
  --streaming \
  --chunk-size 100
```

**효과**: 메모리 사용량 3 GB → 800 MB (-73%)

---

## 🔧 트러블슈팅

### Q16. "Traceability 83%" 오류가 발생해요.

**A**: Feature가 Architecture에 누락됨.
```bash
# 문제 진단
caas traceability \
  --golden-data ./todo/golden_data.json \
  --agents ./todo/agents.json \
  --tasks ./todo/tasks.json

# 출력:
# Feature f4 (할일 공유) → ❌ No mapping

# 해결:
# 1. Golden Data 수정 (Feature f4 제거 또는 단순화)
# 2. Architecture 재생성
caas generate-phase --phase 2 "..." --output ./todo --force
```

**관련 문서**: [22_트러블슈팅_가이드.md#phase-2-오류](../2_개발_실무_가이드/22_트러블슈팅_가이드.md)

---

### Q17. "Completeness 67%" 오류가 발생해요.

**A**: Feature가 Agent/Task로 구현되지 않음.
```bash
# 문제 진단
caas analyze-completeness \
  --project ./todo \
  --golden-data ./todo/golden_data.json \
  --detailed

# 출력:
# Feature f3 (우선순위 분석) → ❌ Not implemented

# 해결:
# 1. Phase 3 재생성 (Agent/Task 설계)
caas generate-phase --phase 3 "..." --output ./todo --force

# 2. Phase 5 재생성 (코드 생성)
caas generate-phase --phase 5 "..." --output ./todo --force
```

---

### Q18. 생성된 코드 실행 시 에러가 발생해요.

**A**: **런타임 에러 자동 수정** 사용.
```bash
# 에러 로그 저장
python main.py 2> error.log

# 자동 수정
caas fix-runtime-error \
  --project ./todo \
  --error-log error.log \
  --apply \
  --backup

# 재실행
python main.py  # ✅ 정상 실행
```

**지원 에러**: ImportError, NameError, TypeError, AttributeError, KeyError, ValueError, IndexError, FileNotFoundError (8개)

**관련 문서**: [22_트러블슈팅_가이드.md#phase-5-오류](../2_개발_실무_가이드/22_트러블슈팅_가이드.md)

---

### Q19. "Quality Gate 무한 대기" 문제는 해결되었나요?

**A**: **예**, v0.4.1에서 완전 해결.
- **원인**: 메트릭 누락 시 None 반환 → 계산 오류
- **해결** (v0.4.1):
  1. AutoMetricsCollector 통합 (자동 메트릭 수집)
  2. 메트릭 기본값 사용 (None → 0.0)
  3. LLM Judge 타임아웃 (60초)
- **결과**: 무한 대기 발생률 **10-20% → 0%** ✅

**사용**:
```python
# v0.4.1부터 안전하게 사용 가능
collaboration = ExpertAgentCollaboration(
    strict_quality_gates=True  # 무한 대기 없음 ✅
)
```

**관련**: CLAUDE.md v0.4.1 섹션

---

### Q20. 한국어 출력이 제대로 안 되요.

**A**: **v0.6.4에서 한국어 출력 강화** 완료.
- Agent role, goal, backstory 한국어 100% 보장
- Task description/expected_output 한국어 출력
- 코드 주석 및 docstring 한국어 생성

**확인**:
```bash
cat agents.json
# {
#   "role": "데이터 분석가",  ✅ 한국어
#   "goal": "데이터 분석 및 시각화",  ✅ 한국어
#   ...
# }
```

---

## 🏢 엔터프라이즈 기능

### Q21. Checkpoint 기능은 언제 사용하나요?

**A**: **Human Approval Checkpoint** (v0.6.2) - PM 승인 워크플로우

**사용 시나리오**:

1. **Phase 완료 후 PM 승인**
   ```bash
   # 7개 체크포인트 목록 확인
   caas checkpoint list

   # CP-3 (Architecture) 승인
   caas checkpoint approve \
     --project todo-system \
     --checkpoint-id CP-3 \
     --reviewer "김PM" \
     --comment "아키텍처 설계 검토 완료. 승인합니다."
   ```

2. **체크포인트 상태 추적**
   ```bash
   # 프로젝트의 모든 체크포인트 상태 확인
   # (status 명령어는 현재 구현 예정)

   # 결과 예시:
   # CP-1 (Phase 0: Concretization): ✅ APPROVED (검토자: 이PM)
   # CP-2 (Phase 1: Discovery): ✅ APPROVED (검토자: 김PM)
   # CP-3 (Phase 2: Architecture): ⏳ PENDING
   # ...
   ```

3. **팀 협업 워크플로우**
   - PM이 각 Phase 완료 시점에서 산출물 검토
   - 체크포인트 승인 전까지 다음 Phase 진행 불가
   - 승인 이력 및 코멘트 추적

**참고**:
- **Version Control Checkpoint** (save/restore/diff/export)은 v0.7.0+에서 계획 중
- 현재는 Human Approval Checkpoint만 지원 (approve, list 명령어)

**관련 문서**: [52_Checkpoint_활용법.md](../5_엔터프라이즈_기능/52_Checkpoint_활용법.md)

---

### Q22. TDD 자동화는 어떻게 사용하나요?

**A**: **Golden Data 기반 테스트 자동 생성**.
```bash
# 1. 테스트 자동 생성
caas tdd generate-tests ./todo/golden_data.json \
  --output-dir ./tests

# 결과: tests/ 디렉토리에 41개 테스트 생성

# 2. 테스트 실행
pytest tests/ -v

# 3. 코드 분석 (테스트 통과 확인 후)
caas tdd analyze-code ./todo --detailed

# 4. 완전한 TDD 워크플로우 실행
caas tdd workflow ./todo ./todo/golden_data.json
```

**관련 문서**: [50_TDD_자동화_가이드.md](../5_엔터프라이즈_기능/50_TDD_자동화_가이드.md)

---

### Q23. QA 자동화를 CI/CD에 통합할 수 있나요?

**A**: **예**, GitHub Actions/Jenkins 통합 가능.
```yaml
# .github/workflows/qa.yml
name: QA Validation

on: [push, pull_request]

jobs:
  qa:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install CAAS
        run: pip install caas
      - name: QA Validation
        run: |
          caas qa report --project . --output qa_report.html
      - name: Upload Report
        uses: actions/upload-artifact@v2
        with:
          name: qa-report
          path: qa_report.html
```

**관련 문서**: [51_QA_자동화_가이드.md#ci-cd-통합](../5_엔터프라이즈_기능/51_QA_자동화_가이드.md)

---

### Q24. 성능 프로파일링은 어떻게 하나요?

**A**: Python 내장 프로파일링 도구 사용.

**방법 1: cProfile 사용**
```bash
# CLI 명령어 프로파일링
python -m cProfile -o profile.stats -m caas_cli.cli generate "할일 관리" --output ./todo

# 프로파일 결과 분석
python -m pstats profile.stats
# > sort cumtime
# > stats 20
```

**방법 2: 성능 테스트 명령어**
```bash
# QA 성능 테스트 실행
caas qa performance --project ./todo --output perf_report.json

# 결과: 메모리 사용량, CPU 메트릭, 부하 테스트 결과
```

**참고**: `--profile` 플래그는 현재 지원되지 않음. Python 표준 프로파일링 도구 사용 권장.

**관련 문서**: [53_성능_최적화_가이드.md](../5_엔터프라이즈_기능/53_성능_최적화_가이드.md)

---

## 📚 일반 질문

### Q25. CAAS와 AutoGPT의 차이는?

**A**: **3가지 핵심 차이**.
| 항목 | CAAS | AutoGPT |
|------|------|---------|
| **목적** | 멀티 에이전트 **시스템 코드** 생성 | 일반 작업 자동화 |
| **출력** | 프로덕션 레디 Python 코드 (agents.py, tasks.py, tools.py) | 작업 결과 (텍스트, 파일) |
| **품질 보증** | Quality Gate, Traceability 100%, Code Quality 8.5+ | 없음 |
| **도메인** | 17개 도메인 전문화 | 범용 |
| **프레임워크** | CrewAI 멀티 에이전트 | LangChain |

**요약**: CAAS는 **코드 생성 전문 도구**, AutoGPT는 **작업 자동화 도구**.

---

### Q26. 라이브러리로 사용할 수 있나요?

**A**: **예**, Python SDK 제공.
```python
from caas_framework.framework import CrewAIFramework

# 초기화
framework = CrewAIFramework()
await framework.initialize()

# 코드 생성
result = await framework.generate_from_requirement(
    requirement="할일 관리 시스템",
    output_dir=Path("./todo")
)

print(f"✅ {len(result.files)}개 파일 생성!")
print(f"Code Quality: {result.code_quality}/10.0")
```

**용도**: Streamlit 앱, FastAPI 백엔드, React + Python, VSCode Extension 등

**관련 문서**: [01_CAAS_소개_및_설치.md#라이브러리-사용](../1_시작하기/01_CAAS_소개_및_설치.md)

---

### Q27. 오픈소스인가요?

**A**: **예**, GitHub에 공개.
- **저장소**: https://github.com/bullpeng72/CAAS
- **라이선스**: MIT (상업적 사용 가능)
- **버전**: v0.6.6 (2026-03-27 기준)

**기여 방법**:
```bash
git clone https://github.com/bullpeng72/CAAS.git
cd CAAS
# 기능 추가/버그 수정 후 PR 제출
```

---

### Q28. 어떤 문서를 먼저 읽어야 하나요?

**A**: **학습 경로** 추천.

**초보자** (처음 사용):
1. [01_CAAS_소개_및_설치.md](../1_시작하기/01_CAAS_소개_및_설치.md) - 설치
2. [02_5분_빠른_시작.md](../1_시작하기/02_5분_빠른_시작.md) - 첫 프로젝트 생성
3. [40_할일관리_실습.md](../4_도메인별_실습/40_할일관리_실습.md) - 실습
4. [22_트러블슈팅_가이드.md](../2_개발_실무_가이드/22_트러블슈팅_가이드.md) - 오류 해결

**중급자** (실무 적용):
1. [10_CAAS_6Phase_개발_프로세스.md](../2_개발_실무_가이드/10_CAAS_6Phase_개발_프로세스.md) - 방법론 이해
2. [12_Golden_Data_활용법.md](../2_개발_실무_가이드/12_Golden_Data_활용법.md) - Golden Data 편집
3. [13_Agent_Task_설계_가이드.md](../2_개발_실무_가이드/13_Agent_Task_설계_가이드.md) - 설계 패턴
4. [15_코드_품질_가이드.md](../2_개발_실무_가이드/15_코드_품질_가이드.md) - 품질 기준

**고급자** (엔터프라이즈):
1. [50_TDD_자동화_가이드.md](../5_엔터프라이즈_기능/50_TDD_자동화_가이드.md) - TDD 자동화
2. [51_QA_자동화_가이드.md](../5_엔터프라이즈_기능/51_QA_자동화_가이드.md) - QA 자동화
3. [52_Checkpoint_활용법.md](../5_엔터프라이즈_기능/52_Checkpoint_활용법.md) - 체크포인트
4. [53_성능_최적화_가이드.md](../5_엔터프라이즈_기능/53_성능_최적화_가이드.md) - 성능 최적화

---

### Q29. 피드백은 어디에 남기나요?

**A**: **2가지 방법**.
1. **GitHub Issues**: https://github.com/bullpeng72/CAAS/issues
2. **GitHub Discussions**: https://github.com/bullpeng72/CAAS/discussions

---

### Q30. 향후 로드맵은?

**A**: **v0.6.0+ 계획** (CAAS-E).
- [ ] 웹 UI (대시보드)
- [ ] 실시간 협업 (멀티 유저)
- [ ] 더 많은 도메인 지원 (20+)
- [ ] 자동 배포 (Docker, Kubernetes)
- [ ] 성능 개선 (생성 시간 2분 이하)

**최신 정보**: GitHub Releases 참조

---

## 📚 관련 문서 색인

- **시작하기**
  - [01_CAAS_소개_및_설치.md](../1_시작하기/01_CAAS_소개_및_설치.md)
  - [02_5분_빠른_시작.md](../1_시작하기/02_5분_빠른_시작.md)

- **개발 실무**
  - [10_CAAS_6Phase_개발_프로세스.md](../2_개발_실무_가이드/10_CAAS_6Phase_개발_프로세스.md)
  - [22_트러블슈팅_가이드.md](../2_개발_실무_가이드/22_트러블슈팅_가이드.md)

- **엔터프라이즈**
  - [50_TDD_자동화_가이드.md](../5_엔터프라이즈_기능/50_TDD_자동화_가이드.md)
  - [51_QA_자동화_가이드.md](../5_엔터프라이즈_기능/51_QA_자동화_가이드.md)

- **부록**
  - [60_프레임워크_데이터구조.md](./60_프레임워크_데이터구조.md)
  - [61_API_레퍼런스.md](./61_API_레퍼런스.md)
  - [62_용어집.md](./62_용어집.md)

---

**작성일**: 2026-02-14
**버전**: v0.6.6
**대상**: 전체 사용자
**업데이트**: 자주 묻는 질문 추가 시 지속 업데이트
