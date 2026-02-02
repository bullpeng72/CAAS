# 배포 가이드

**버전**: 1.0.0
**작성일**: 2026년 02월 02일
**작성자**: CAAS

---

## 1. 배포 개요

### 1.1 목적
본 문서는 시스템의 배포 절차와 운영 가이드를 제공합니다.

### 1.2 배포 환경

- **개발**: 로컬 개발 환경
- **스테이징**: 테스트 서버
- **프로덕션**: 운영 서버

---

## 2. 사전 요구사항

### 2.1 시스템 요구사항

- Python 3.10+
- 4GB+ RAM
- 20GB+ Disk

### 2.2 필수 도구

- Docker (선택)
- Git
- pip/poetry

---

## 3. 배포 절차

### 3.1 코드 배포

```bash
# 1. 저장소 클론
git clone <repository>
cd <project>

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일 수정

# 4. 실행
python main.py
```

### 3.2 Docker 배포

```bash
# 빌드
docker-compose build

# 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

---

## 4. 환경 변수

| 변수명 | 설명 | 필수 | 기본값 |
|--------|------|------|--------|
| OPENAI_API_KEY | OpenAI API 키 | ✅ | - |
| LOG_LEVEL | 로그 레벨 | ❌ | INFO |
| DATABASE_URL | DB 연결 문자열 | ❌ | sqlite:/// |

---

## 5. 모니터링

### 5.1 로그

- 위치: `./logs/`
- 로테이션: 일일
- 보관: 7일

### 5.2 Health Check

```bash
curl http://localhost:8000/health
```

---

## 6. 트러블슈팅

### 6.1 일반적인 문제

**API 키 오류**:
- `.env` 파일 확인
- 키 유효성 검증

**포트 충돌**:
- 다른 포트 사용
- 기존 프로세스 종료

---

**문서 이력**

| 버전 | 일자 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 1.0.0 | 2026-02-02 | 초안 작성 | CAAS |

---

*본 문서는 CAAS (CrewAI Agent Auto-generation System)에 의해 자동 생성되었습니다.*