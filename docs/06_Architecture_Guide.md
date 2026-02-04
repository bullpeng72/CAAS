# CAAS 아키텍처 가이드

CAAS (CrewAI Agent Auto-generation System)의 전체 아키텍처를 설명하는 가이드입니다.

**최종 업데이트**: 2026-02-04

---

## 목차

- [시스템 개요](#시스템-개요)
- [아키텍처 다이어그램](#아키텍처-다이어그램)
- [모듈 구조](#모듈-구조)
- [데이터 플로우](#데이터-플로우)
- [CAAS 6-Phase 프로세스](#bmad-6-phase-프로세스)
- [디자인 패턴](#디자인-패턴)
- [보안 아키텍처](#보안-아키텍처)
- [확장성 및 성능](#확장성-및-성능)

---

## 시스템 개요

CAAS는 자연어 요구사항을 입력받아 **CrewAI 기반 멀티에이전트 시스템** 또는 **FastAPI CRUD 백엔드**를 자동으로 설계하고 생성하는 **프레임워크 중심 플랫폼**입니다.

### 핵심 특징

- **Framework-First 아키텍처**: CLI, SDK, Python API를 통한 접근
- **이중 코드 생성 전략**:
  - **AGENT_BASED**: CrewAI 멀티에이전트 시스템 (CONTENT_CREATION, DATA_ANALYSIS 등)
  - **CRUD_BASED**: FastAPI + SQLAlchemy 백엔드 (TASK_MANAGEMENT 등)
- **CAAS 6-Phase 방법론**: 요구사항 분석부터 코드 생성, 품질 보증까지의 체계적인 워크플로우
- **Expert Agent Collaboration**: 6명의 전문가 에이전트 협업 (v0.4.0에서 CodeAnalysisAgent 추가)
- **도메인 기반 분류**: 13개 주요 도메인 자동 분류 및 최적 전략 선택
- **온톨로지 기반 추론**: 도메인 지식을 활용한 지능적 역할/도구 매핑
- **이중 그래프 백엔드**: Neo4j (프로덕션) 또는 임베디드 (개발)
- **템플릿 + LLM 하이브리드 생성**: Jinja2 템플릿 + LLM 기반 코드 생성
- **개발 산출물 자동 생성**: 10가지 타입의 개발 문서 자동 생성
- **보안 우선 설계**: Path Traversal, YAML Bomb, Injection 방어

### 프로덕션 규모

- **코드량**: 28,000+ 라인 (caas_framework/) - v0.4.0에서 증가
- **CLI 명령**: 29개 메인 명령 (v0.4.0: analyze-completeness, fix-runtime-error 등 추가)
- **Expert Agents**: 6개 (v0.4.0에서 CodeAnalysisAgent 추가)
- **도구 지원**: 40+ CrewAI 도구
- **Validator**: 6개 타입
- **산출물**: 10가지 자동 문서

---

## 아키텍처 다이어그램

### 고수준 아키텍처 (Framework-First)

```
┌─────────────────────────────────────────────────────────────┐
│                   Interface Layer                           │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │   CLI (29개)   │  │  Python SDK    │  │  Python API  │  │
│  │  caas_cli/     │  │  caas_sdk/     │  │ (Direct Use) │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│                   Core Framework Layer                      │
│                    caas_framework/                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  6-Phase Engine (methodology/)                                 │   │
│  │  (6-Phase Workflow Orchestrator)                     │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Code Generation (codegen/)                          │   │
│  │  (LLM, Template, CRUD, Test Generators)              │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Validation & Fixing (validation/, fixing/)          │   │
│  │  (6 Validators, 3-Level Auto-Fix)                    │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Expert Agents (agents/)                             │   │
│  │  (Requirement Analyst, System Architect, etc.)       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│                    Service Layer (plugins/)                 │
│  (LLM, Graph DB, Vector DB Plugins)                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│                     Data Layer (data/)                      │
│  (Templates, Ontologies, Golden Examples)                 │
└─────────────────────────────────────────────────────────────┘
```

### 실제 디렉토리 구조

```
caas/
├── caas_framework/      # 핵심 프레임워크
│   ├── agents/          # Expert Agents (6명)
│   ├── methodology/     # CAAS 6-Phase 엔진 (v0.3.0+)
│   ├── codegen/         # 코드 생성
│   ├── config/          # 설정 관리
│   ├── fixing/          # 3-level 자동 수정
│   ├── knowledge/       # 온톨로지 관리
│   ├── models/          # 데이터 모델
│   ├── plugins/         # 플러그인 시스템
│   ├── refinement/      # 요구사항 정제
│   ├── reporting/       # 진행 리포팅
│   ├── session/         # 세션 관리
│   ├── testing/         # TDD 통합
│   ├── utils/           # 유틸리티
│   ├── validation/      # Validators (6개)
│   └── workflow/        # 워크플로우 오케스트레이션
│
├── caas_cli/            # CLI 인터페이스 (20+ 명령어)
├── caas_sdk/            # Python SDK
│
├── data/                # 데이터 및 리소스
│   ├── templates/       # Jinja2 템플릿 (20+)
│   ├── ontology/        # 온톨로지 파일 (도구, 패턴 등)
│   └── golden_examples/ # Golden 예제
│
├── tests/               # 테스트 스위트 (100+ tests, E2E 예제 포함)
├── scripts/             # 유틸리티 스크립트 (auto_deploy, validate_env)
├── docs/                # 문서 (한국어)
└── config.yaml          # 메인 설정
```

**참고**:
- ❌ `caas_api/` 또는 `caas_streamlit/` 디렉토리는 없습니다. REST API나 Streamlit UI는 CAAS 자체가 아닌, CAAS에 의해 **생성되는 프로젝트**에 포함될 수 있습니다.

---

## 모듈 구조

### 1. caas_framework/ - 핵심 프레임워크

#### 1.1 CAAS 6-Phase Engine (`methodology/`)
- **역할**: CAAS 6-Phase 워크플로우 전체를 조율하는 오케스트레이터 (v0.3.0+).
- **주요 파일**: `engine.py`

#### 1.2 Code Generation (`codegen/`)
- **역할**: 도메인 전략(AGENT_BASED, CRUD_BASED)에 따라 코드를 생성.
- **주요 기능**: LLM 기반 생성, Jinja2 템플릿 기반 생성, `tools.py` 생성을 위한 3-Layer Defense 메커니즘.

**3-Layer Defense (`tools.py` 생성)**:
1.  **Validation**: 한국어 도구명 영어로 변환 등 입력값 검증.
2.  **LLM Generation**: LLM을 통해 코드 생성 시도.
3.  **Fallback**: LLM 생성 실패 시, 실행 가능한 stub 코드를 포함한 `tools.py` 파일을 생성하여 100% 생성을 보장.

#### 1.3 Validation & Fixing (`validation/`, `fixing/`)
- **역할**: 생성된 설계 및 코드의 품질을 검증하고 자동으로 수정.
- **주요 기능**: 6가지 검증기(Ontology, Golden Data, Dependency 등) 및 3단계 자동 수정(Template, Rule, LLM).

#### 1.4 Expert Agents (`agents/`)
- **역할**: 6명의 전문가(요구사항 분석가, 아키텍트, 설계자, 개발자, QA, 코드 분석가)가 협업하여 고품질 산출물 생성.

#### 1.5 Refinement (`refinement/`)
- **역할**: 불완전한 요구사항을 구체화.
- **주요 기능**: 갭 분석(Gap Analysis), 자동 확장(Auto-Expansion), 대화형 질문 생성.

---

## 데이터 플로우

```
사용자 요구사항 (자연어)
    ↓
┌───────────────────────────────┐
│  Phase 0-1: 분석 및 구조화      │
└──────────┬────────────────────┘
           ↓
     Golden Data (구조화된 요구사항)
           ↓
┌───────────────────────────────┐
│  Phase 2-3: 설계 및 추적성 확보  │
└──────────┬────────────────────┘
           ↓
   Agents, Tasks, Traceability Matrix
           ↓
┌───────────────────────────────┐
│  Phase 4: 완전성 검증 및 보완   │
└──────────┬────────────────────┘
           ↓
   Completeness Report, Gap Filling
           ↓
┌───────────────────────────────┐
│  Phase 5: 코드 생성             │
└──────────┬────────────────────┘
           ↓
   Generated Code (src/, tests/, 등)
           ↓
┌───────────────────────────────┐
│  Phase 6: 품질 보증 및 수정     │
└──────────┬────────────────────┘
           ↓
   최종 코드 + 검증 리포트
```

---

## CAAS 6-Phase 프로세스

- **Phase 0 (Concretization)**: 자연어 요구사항을 구조화된 `Golden Data`로 변환.
- **Phase 1 (Discovery)**: 도메인을 분석하고 핵심 기능(Feature) 추출.
- **Phase 2 (Architecture)**: 시스템 아키텍처 설계 및 **Traceability Matrix** 구축.
- **Phase 3 (Design)**: CrewAI 에이전트 및 태스크 상세 설계.
- **Phase 4 (Development)**: **Completeness Validation** 수행 후 코드 스펙 생성, 필요시 **Gap Filling**.
- **Phase 5 (Delivery)**: 프로덕션 코드, 테스트, 문서 등 최종 산출물 생성.
- **Phase 6 (Assurance)**: 6가지 검증기 및 3단계 자동 수정을 통한 품질 보증.

---

## 디자인 패턴

- **Plugin Architecture**: LLM, DB 등을 플러그인 형태로 쉽게 교체 및 확장.
- **Factory Pattern**: 도메인 전략에 따라 Agent, Task, Code Generator 등 다른 객체 생성.
- **Strategy Pattern**: `AGENT_BASED`, `CRUD_BASED` 등 도메인에 맞는 코드 생성 전략을 동적으로 선택.
- **Observer Pattern**: `ProgressReporter`를 통해 워크플로우의 각 단계를 모니터링하고 사용자에게 진행 상황 알림.
- **Template Method Pattern**: `SixPhaseEngine`의 `run` 메서드에서 전체 워크플로우의 뼈대를 정의하고, 각 단계의 구체적인 구현은 서브 클래스나 다른 모듈에 위임.

---

## 보안 아키텍처

- **Input Validation**: Path Traversal, YAML Bomb 등 악의적인 입력 방어.
- **Code Generation Security**: 생성되는 코드에 대해 SQL Injection, `eval()` 사용 등 잠재적 보안 취약점 방지 로직 포함.
- **API Key Management**: `.env` 파일을 통한 안전한 API 키 관리 및 코드 내 노출 방지.

---

## 확장성 및 성능

- **확장성**: 플러그인 시스템과 모듈식 아키텍처를 통해 새로운 LLM, DB, 검증기, 코드 생성기 등을 쉽게 추가 가능.
- **성능 최적화**: LLM 응답 캐싱, 비동기 처리(Async/Await), 지연 로딩(Lazy Loading) 등을 통해 성능 최적화.
- **모니터링**: `ExecutionMonitor`를 통해 각 단계의 실행 시간, LLM 토큰 사용량, 비용 등을 추적하여 성능 병목 및 비용 분석.

### v0.4.0 성능 개선사항 ⚡

#### 1. Quality Gate 강화 (P0) 🚨
- **변경**: `strict_quality_gates` 기본값 False → **True**
- **효과**: Quality Gate 실패 시 워크플로우 즉시 중단, 품질 보증 100% 실효성 확보
- **파일**: `caas_framework/agents/collaboration.py:593`

#### 2. AutoMetricsCollector (P1-2) 🤖
- **기능**: 코드에서 품질 메트릭 자동 추출 (수동 입력 불필요)
- **메트릭**: Code Quality (AST), Test Coverage (휴리스틱), Security Score (패턴 스캔), Complexity Score (순환 복잡도)
- **효과**: 메트릭 수집 시간 **100% 절감** (5-10분 → 0초)
- **파일**: `caas_framework/quality/metrics_collector.py` (NEW)

#### 3. LightweightLLMJudge (P1-3) ⚡
- **기능**: Claude Haiku 모델 사용으로 빠른 평가
- **효과**: LLM Judge 평가 시간 **70% 단축** (3초 → 1초)
- **최적화**: 간결 프롬프트 (100-200 토큰 vs 500-800 토큰), max_tokens 1000 (vs 2000)
- **파일**: `caas_framework/validation/llm_judge.py` (ENHANCED)

#### 4. 병렬 실행 확장 (P2-4) 🚀
- **기능**: QA + Code Analysis 병렬 실행 추가
- **실행 계획**: [Discovery+Architecture] → [Design] → [Delivery] → **[QA+CodeAnalysis]**
- **효과**: 전체 워크플로우 시간 **30% 단축** (5-10분 → 3.5-7분)
- **파일**: `caas_framework/agents/collaboration.py` (ENHANCED)

#### 종합 성능 개선

| 지표 | 개선 전 | 개선 후 | 개선율 |
|------|---------|---------|--------|
| Quality Gate 실효성 | 50% | 100% | **+100%** |
| 메트릭 수집 시간 | 5-10분 | 0초 | **-100%** |
| LLM Judge 평가 | 3초 | 1초 | **-70%** |
| 전체 워크플로우 | 5-10분 | 3.5-7분 | **-30%** |

---

## 참고 자료

- **개발 방법론**: [개발_방법론.md](../2_개발_방법론/개발_방법론.md)
- **배포 가이드**: [배포_가이드.md](./배포_가이드.md)
- **CLI 사용 가이드**: [CLI_사용_가이드.md](../1_시작하기/CLI_사용_가이드.md)

---

**최종 업데이트**: 2026-02-03
**버전**: 0.2.0
