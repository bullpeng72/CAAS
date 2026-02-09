# Ollama 로컬 LLM 설정 가이드

CAAS에서 Ollama를 사용하여 로컬에서 LLM을 실행하는 방법을 안내합니다.

## 목차
1. [Ollama란?](#ollama란)
2. [설치 방법](#설치-방법)
3. [모델 선택 및 다운로드](#모델-선택-및-다운로드)
4. [CAAS 설정](#caas-설정)
5. [추천 모델](#추천-모델)
6. [문제 해결](#문제-해결)
7. [성능 최적화](#성능-최적화)

---

## Ollama란?

**Ollama**는 로컬 환경에서 LLM을 쉽게 실행할 수 있게 해주는 오픈소스 도구입니다.

### 주요 특징
- ✅ **로컬 실행**: 인터넷 연결 없이도 LLM 사용 가능
- ✅ **프라이버시**: 데이터가 외부로 전송되지 않음
- ✅ **비용 절감**: API 호출 비용 없음
- ✅ **OpenAI 호환 API**: OpenAI SDK와 호환되는 REST API 제공
- ✅ **다양한 모델**: Llama 3, Mistral, CodeLlama 등 50+ 모델 지원

### 지원 모델 (일부)
- **Llama 3 / 3.1** (8B, 70B, 405B)
- **Mistral / Mixtral** (7B, 8x7B)
- **CodeLlama** (7B, 13B, 34B)
- **Qwen 2.5** (0.5B ~ 72B)
- **Gemma 2** (2B, 9B, 27B)
- **Phi-3** (3.8B, 14B)

---

## 설치 방법

### 1. Ollama 설치

**macOS / Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
- [Ollama 다운로드 페이지](https://ollama.ai/download)에서 Windows 설치 프로그램 다운로드 및 실행

**설치 확인:**
```bash
ollama --version
# 출력 예시: ollama version 0.1.20
```

### 2. Ollama 서버 시작

Ollama는 설치 후 자동으로 백그라운드에서 실행됩니다.

**수동 시작:**
```bash
ollama serve
```

**서버 상태 확인:**
```bash
curl http://localhost:11434/api/tags
```

성공 시 사용 가능한 모델 목록이 JSON으로 반환됩니다.

---

## 모델 선택 및 다운로드

### 1. 모델 선택 가이드

| 모델 | 크기 | 메모리 요구사항 | 용도 | 속도 | 품질 |
|------|------|------------------|------|------|------|
| **llama3.2:3b** | 3B | 4GB | 빠른 실험, 개발 | ⚡⚡⚡ | ⭐⭐ |
| **llama3.1:8b** | 8B | 8GB | 일반적인 작업 | ⚡⚡ | ⭐⭐⭐ |
| **mistral:7b** | 7B | 8GB | 코드 생성 | ⚡⚡ | ⭐⭐⭐ |
| **llama3.1:70b** | 70B | 40GB+ | 고품질 작업 | ⚡ | ⭐⭐⭐⭐ |
| **codellama:13b** | 13B | 16GB | 코드 중심 작업 | ⚡⚡ | ⭐⭐⭐⭐ |

### 2. 모델 다운로드

**추천 모델 (CAAS용):**
```bash
# 빠른 실험용 (3B - 4GB RAM)
ollama pull llama3.2:3b

# 일반 사용 (8B - 8GB RAM)
ollama pull llama3.1:8b

# 고품질 작업 (13B - 16GB RAM)
ollama pull codellama:13b
```

**다운로드 확인:**
```bash
ollama list
# 출력 예시:
# NAME                     ID              SIZE      MODIFIED
# llama3.1:8b             a1b2c3d4        4.7 GB    2 hours ago
```

### 3. 모델 테스트

```bash
# 간단한 테스트
ollama run llama3.1:8b "Hello, how are you?"

# 코드 생성 테스트
ollama run codellama:13b "Write a Python function to calculate fibonacci"
```

---

## CAAS 설정

### 방법 1: 환경 변수 설정

`.env` 파일에 다음 추가:
```bash
# Ollama 설정
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_API_BASE=http://localhost:11434/v1
```

### 방법 2: CLI 인자 사용

```bash
caas generate "할일 관리 시스템" \
  --provider ollama \
  --model llama3.1:8b \
  --output ./generated
```

### 방법 3: 프로그래밍 방식 (Python SDK)

```python
from caas_framework.framework import CrewAIFramework
from caas_framework.config.settings import LLMConfig, LLMProvider

# Ollama 설정
llm_config = LLMConfig(
    provider=LLMProvider.OLLAMA,
    model="llama3.1:8b",
    api_base="http://localhost:11434/v1",
    temperature=0.3,
)

# Framework 초기화
framework = CrewAIFramework(llm_config=llm_config)
await framework.initialize()

# 코드 생성
result = await framework.generate_from_requirement(
    "블로그 관리 시스템을 만들어주세요"
)
print(f"생성 완료: {result.output_dir}")
```

### 방법 4: 설정 파일 사용

`config/llm_config.yaml`:
```yaml
llm:
  provider: ollama
  model: llama3.1:8b
  api_base: http://localhost:11434/v1
  temperature: 0.3
  max_tokens: 4096
```

```bash
caas generate "요구사항" --config config/llm_config.yaml
```

---

## 추천 모델

### CAAS 워크로드별 추천

#### 1. 빠른 프로토타이핑 (개발/테스트)
```bash
ollama pull llama3.2:3b
```
- **장점**: 빠른 응답 속도, 낮은 메모리 사용량
- **단점**: 품질이 다소 낮음
- **권장 사용**: Phase 0-1 (Concretization, Discovery)

#### 2. 균형잡힌 성능 (일반 사용)
```bash
ollama pull llama3.1:8b
```
- **장점**: 적절한 품질과 속도, 8GB RAM으로 실행 가능
- **단점**: 복잡한 작업에서 한계
- **권장 사용**: 전체 Phase (0-5)

#### 3. 코드 생성 중심
```bash
ollama pull codellama:13b
```
- **장점**: 코드 생성 특화, 높은 정확도
- **단점**: 16GB+ RAM 필요
- **권장 사용**: Phase 3-5 (Design, Development, Delivery)

#### 4. 고품질 프로덕션
```bash
ollama pull llama3.1:70b
```
- **장점**: 최고 품질, 복잡한 요구사항 처리
- **단점**: 40GB+ RAM 필요, 느린 속도
- **권장 사용**: 프로덕션 레디 코드 생성

### Multi-Model 설정 (하이브리드)

작은 모델로 빠르게 시작하고, 필요시 큰 모델로 폴백:

```python
from caas_framework.config.settings import LLMConfig, MultiModelConfig, LLMProvider

llm_config = LLMConfig(
    provider=LLMProvider.OLLAMA,
    model="llama3.1:8b",  # 기본 모델
    enable_multi_model=True,
    model_selection_strategy="phase_based",
    enable_model_fallback=True,
    multi_models=[
        # 빠른 모델 (Discovery, QA)
        MultiModelConfig(
            name="llama-3b",
            provider=LLMProvider.OLLAMA,
            model="llama3.2:3b",
            cost_per_1k_tokens=0.0,  # 로컬이므로 무료
            max_tokens=4096,
            suitable_phases=["DISCOVERY", "QUALITY_ASSURANCE"],
            priority=1,
        ),
        # 중간 모델 (일반 작업)
        MultiModelConfig(
            name="llama-8b",
            provider=LLMProvider.OLLAMA,
            model="llama3.1:8b",
            cost_per_1k_tokens=0.0,
            max_tokens=4096,
            suitable_phases=["ARCHITECTURE", "DESIGN"],
            priority=2,
        ),
        # 큰 모델 (코드 생성)
        MultiModelConfig(
            name="codellama-13b",
            provider=LLMProvider.OLLAMA,
            model="codellama:13b",
            cost_per_1k_tokens=0.0,
            max_tokens=4096,
            suitable_phases=["DELIVERY"],
            priority=3,
        ),
    ],
)
```

---

## 문제 해결

### 1. "Failed to connect to Ollama server" 오류

**증상:**
```
RuntimeError: Failed to connect to Ollama server at http://localhost:11434/v1.
Please ensure Ollama is running.
```

**해결 방법:**
```bash
# 1. Ollama 서버 상태 확인
ps aux | grep ollama

# 2. 서버 재시작
ollama serve

# 3. 연결 테스트
curl http://localhost:11434/api/tags
```

### 2. "Model not found" 오류

**증상:**
```
RuntimeError: Model 'llama3.1:8b' not found.
Pull it with: ollama pull llama3.1:8b
```

**해결 방법:**
```bash
# 사용 가능한 모델 확인
ollama list

# 모델 다운로드
ollama pull llama3.1:8b
```

### 3. 메모리 부족 오류

**증상:**
- 시스템이 느려지거나 멈춤
- "Out of memory" 오류

**해결 방법:**

**더 작은 모델 사용:**
```bash
# 70B 대신 8B 사용
ollama pull llama3.1:8b
```

**Quantization 활용:**
```bash
# Q4 양자화 버전 (메모리 50% 절감)
ollama pull llama3.1:8b-q4

# Q8 양자화 버전 (메모리 25% 절감, 품질 유지)
ollama pull llama3.1:8b-q8
```

### 4. 느린 응답 속도

**해결 방법:**

**GPU 가속 확인:**
```bash
# GPU 사용 확인 (NVIDIA)
nvidia-smi

# GPU 사용 확인 (Apple Silicon)
sudo powermetrics --samplers gpu_power -n 1
```

**더 작은 모델 사용:**
```bash
# 70B → 13B → 8B → 3B
ollama pull llama3.2:3b
```

**컨텍스트 윈도우 줄이기:**
```python
llm_config = LLMConfig(
    provider=LLMProvider.OLLAMA,
    model="llama3.1:8b",
    max_tokens=2048,  # 기본값 4096에서 줄임
)
```

### 5. JSON 응답 파싱 오류

Ollama 모델은 JSON 모드 지원이 제한적일 수 있습니다.

**해결 방법:**

**CAAS의 Robust JSON Parsing 사용:**
CAAS는 4-전략 JSON 추출을 사용하므로 대부분 자동 처리됩니다.

**모델 업그레이드:**
```bash
# 더 최신 모델은 JSON 지원이 개선됨
ollama pull llama3.1:8b  # Llama 3.1 권장
```

---

## 성능 최적화

### 1. 하드웨어 요구사항

| 모델 크기 | 최소 RAM | 권장 RAM | GPU | 속도 (tokens/s) |
|-----------|----------|----------|-----|-----------------|
| 3B        | 4GB      | 8GB      | 선택적 | 50-100 |
| 8B        | 8GB      | 16GB     | 권장 | 30-60 |
| 13B       | 16GB     | 32GB     | 권장 | 20-40 |
| 70B       | 40GB     | 64GB     | 필수 | 5-15 |

### 2. GPU 가속

**NVIDIA GPU:**
```bash
# CUDA 사용 자동 감지
ollama serve

# GPU 메모리 확인
nvidia-smi
```

**Apple Silicon (M1/M2/M3):**
```bash
# Metal 자동 사용
ollama serve
```

### 3. 병렬 처리

Ollama는 단일 요청만 처리하므로, CAAS에서 병렬 처리가 제한됩니다.

**해결책: 여러 Ollama 인스턴스 실행**
```bash
# 포트 11434 (기본)
OLLAMA_HOST=127.0.0.1:11434 ollama serve &

# 포트 11435
OLLAMA_HOST=127.0.0.1:11435 ollama serve &

# CAAS 설정에서 라운드로빈
```

### 4. 캐싱 활용

Ollama는 자동으로 모델과 KV 캐시를 관리합니다.

**KV 캐시 크기 조정:**
```bash
# 더 큰 캐시 (메모리 여유 있을 때)
OLLAMA_KV_CACHE_SIZE=4096 ollama serve
```

---

## OpenAI와 병행 사용

비용과 품질을 균형있게 사용하려면 Ollama와 OpenAI를 함께 사용할 수 있습니다.

### 하이브리드 설정 예시

```python
from caas_framework.config.settings import LLMConfig, MultiModelConfig, LLMProvider

llm_config = LLMConfig(
    provider=LLMProvider.OLLAMA,
    model="llama3.1:8b",
    enable_multi_model=True,
    model_selection_strategy="phase_based",
    enable_model_fallback=True,
    multi_models=[
        # Ollama - 빠른 작업 (무료)
        MultiModelConfig(
            name="ollama-8b",
            provider=LLMProvider.OLLAMA,
            model="llama3.1:8b",
            cost_per_1k_tokens=0.0,
            suitable_phases=["DISCOVERY", "QUALITY_ASSURANCE"],
            priority=1,
        ),
        # GPT-4 - 중요 작업 (유료, 고품질)
        MultiModelConfig(
            name="gpt-4",
            provider=LLMProvider.OPENAI,
            model="gpt-4-turbo",
            cost_per_1k_tokens=0.01,
            suitable_phases=["ARCHITECTURE", "DESIGN", "DELIVERY"],
            priority=2,
        ),
    ],
)
```

**장점:**
- ✅ 단순 작업은 Ollama (무료)
- ✅ 복잡한 작업은 GPT-4 (고품질)
- ✅ 비용 최적화

---

## 요약

### Quick Start (5분 안에 시작)

```bash
# 1. Ollama 설치
curl -fsSL https://ollama.ai/install.sh | sh

# 2. 모델 다운로드
ollama pull llama3.1:8b

# 3. .env 설정
cat >> .env << EOF
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_API_BASE=http://localhost:11434/v1
EOF

# 4. CAAS 실행
caas generate "할일 관리 시스템" --output ./generated
```

### 추천 모델 요약

| 사용 사례 | 추천 모델 | 메모리 |
|-----------|-----------|--------|
| 빠른 실험 | llama3.2:3b | 4GB |
| 일반 사용 | llama3.1:8b | 8GB |
| 코드 중심 | codellama:13b | 16GB |
| 프로덕션 | llama3.1:70b | 40GB+ |

---

## 참고 자료

### Ollama 공식 리소스

- [Ollama 공식 문서](https://ollama.ai/docs)
- [Ollama GitHub](https://github.com/ollama/ollama)
- [Ollama 모델 라이브러리](https://ollama.ai/library)
- [Llama 3 모델](https://ollama.ai/library/llama3)
- [CodeLlama 모델](https://ollama.ai/library/codellama)

### CAAS 핵심 파일

**LLM Plugin** (`caas_framework/plugins/llm/`):
- `ollama.py` - Ollama 플러그인 구현
- `factory.py` - LLM 플러그인 팩토리
- `openai.py`, `anthropic.py` - 다른 LLM 플러그인

**Configuration** (`caas_framework/config/`):
- `settings.py` - LLMConfig, LLMProvider, MultiModelConfig
- `unified.py` - 통합 설정 관리

### CAAS 문서

- [01_README_KO.md](01_README_KO.md) - 프로젝트 개요
- [02_Installation_Guide.md](02_Installation_Guide.md) - 설치 가이드 (Ollama 포함)
- [03_Quick_Start_Guide.md](03_Quick_Start_Guide.md) - 빠른 시작 가이드
- [04_CLI_Usage_Guide.md](04_CLI_Usage_Guide.md) - CLI 사용 가이드 (29 commands)
- [05_Expert_Methodology_Guide.md](05_Expert_Methodology_Guide.md) - CAAS 6-Phase 방법론
- [06_Architecture_Guide.md](06_Architecture_Guide.md) - 아키텍처 가이드 (플러그인 시스템)
- [07_Deployment_Guide.md](07_Deployment_Guide.md) - 배포 가이드
- [09_API_Key_Management.md](09_API_Key_Management.md) - API 키 관리 (Ollama는 불필요)
- [14_Code_Analysis_Guide.md](14_Code_Analysis_Guide.md) - 코드 분석 (Ollama 사용 예시 포함)
- [CLAUDE.md](../CLAUDE.md) - 프로젝트 컨텍스트

### 커뮤니티

- [CAAS GitHub Issues](https://github.com/bullpeng72/CAAS/issues) - 문의 및 버그 리포트
- [Ollama Discord](https://discord.gg/ollama) - Ollama 커뮤니티

---

**최종 업데이트**: 2026-02-06
**CAAS 버전**: v0.4.1
**문서 버전**: 1.0.0
**상태**: Production Ready ✅

**Made with ❤️ by bullpeng72**
