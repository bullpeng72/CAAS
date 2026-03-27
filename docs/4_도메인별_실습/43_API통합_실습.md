# API 통합 시스템 실습

## 🎯 학습 목표
- [ ] API_INTEGRATION 도메인 프로젝트 생성
- [ ] 외부 API 연동 시스템 실행
- [ ] OAuth 인증 및 Rate Limiting 이해
- [ ] Webhook 처리 기능 추가

⏱️ **예상 시간**: 30분

---

## 1. 프로젝트 생성 (5분)

### 요구사항
```
외부 결제 API 통합 시스템을 만들어줘.
결제 처리, 환불, 결제 내역 조회, Webhook 수신 기능이 필요해.
```

### 실행
```bash
caas generate "결제 API 통합 시스템. 결제 처리, 환불, 내역 조회, Webhook 수신" \
  --domain api_integration \
  --output ./payment-integration \
  --enable-frontend \
  --frontend-framework streamlit
```

> **참고**: `--enable-frontend` 플래그는 선택적입니다. CAAS는 요구사항에서 "결제", "대시보드", "관리" 등의 키워드를 자동으로 감지하여 프론트엔드를 생성합니다.

### 생성 결과 (2-3분)
```
✅ Generation complete!
- Files: 9 (main.py, agents.py, tasks.py, tools.py, app.py, ...)
- Code Quality: 8.7/10.0
- Security: 10.0/10.0
- Features: 4
```

---

## 2. 코드 실행 (5분)

### 설치
```bash
cd payment-integration
pip install -r requirements.txt
cp .env.example .env
# .env 파일에 API 키 설정
```

**.env 설정**:
```bash
OPENAI_API_KEY=sk-...
PAYMENT_API_KEY=pk_test_...        # Stripe API Key (예시)
PAYMENT_SECRET_KEY=sk_test_...
WEBHOOK_SECRET=whsec_...
```

### CLI 실행
```bash
python main.py
```

**출력**:
```
## Welcome to Payment Integration Crew

요청: 결제 처리
- 금액: ₩50,000
- 카드: **** **** **** 1234
- 고객: customer@example.com

🤖 Agent 1 (인증) starting...
✅ Task: API 인증 완료
- 토큰 생성: Bearer eyJhbGciOiJIUzI1NiIs...
- 만료 시간: 3600초

🤖 Agent 2 (결제 처리) starting...
✅ Task: 결제 요청 전송
- API: POST /v1/charges
- 상태: 200 OK
- 응답 시간: 1.2초

🤖 Agent 3 (데이터 변환) starting...
✅ Task: 응답 데이터 매핑
- 외부 ID: ch_3abc123def
- 내부 ID: PAY-2024-001

🤖 Agent 4 (저장) starting...
✅ Task: 데이터베이스 저장 완료

📊 최종 결과:
결제 성공!
- 결제 ID: PAY-2024-001
- 금액: ₩50,000
- 상태: success
- 영수증: https://receipt.example.com/abc123
```

### Streamlit UI 실행
```bash
streamlit run app.py
```

**브라우저 접속**: http://localhost:8501

**UI 기능**:
- 결제 테스트 (카드 번호 입력)
- 결제 내역 조회
- 환불 처리
- Webhook 로그 확인

---

## 3. 생성된 파일 분석 (10분)

### agents.py
```python
# 4개 Agent 생성됨
agent_1: API 인증 담당자 (OAuth2Tool, APIKeyManagerTool)
agent_2: API 호출 담당자 (HTTPClientTool, RetryHandlerTool)
agent_3: 데이터 변환 담당자 (JSONMapperTool, ValidationTool)
agent_4: 저장 담당자 (DatabaseTool, LoggingTool)
```

### tasks.py
```python
# 6개 Task
task_1: OAuth 토큰 발급 (또는 API Key 사용)
task_2: 결제 API 호출 (POST /v1/charges)
task_3: 응답 데이터 검증 및 변환
task_4: 데이터베이스 저장
task_5: 에러 핸들링 (재시도 로직)
task_6: Webhook 수신 및 처리
```

### tools.py
```python
class OAuth2Tool(BaseTool):
    """OAuth 2.0 인증 도구"""
    def _run(self, client_id: str, client_secret: str):
        import requests

        # 토큰 발급
        response = requests.post(
            "https://api.payment.com/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret
            }
        )

        if response.status_code == 200:
            token_data = response.json()
            return {
                "access_token": token_data["access_token"],
                "expires_in": token_data["expires_in"],
                "token_type": token_data["token_type"]
            }
        else:
            raise Exception(f"OAuth failed: {response.text}")

class HTTPClientTool(BaseTool):
    """HTTP 클라이언트 도구 (Rate Limiting 포함)"""
    def _run(self, method: str, url: str, headers: dict, data: dict):
        import requests
        import time
        from ratelimit import limits, sleep_and_retry

        # Rate Limiting: 초당 10회 제한
        @sleep_and_retry
        @limits(calls=10, period=1)
        def call_api():
            return requests.request(method, url, headers=headers, json=data)

        # 재시도 로직 (3회)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = call_api()
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff

class JSONMapperTool(BaseTool):
    """JSON 데이터 변환 도구"""
    def _run(self, source_data: dict, mapping_rules: dict):
        """
        Example mapping_rules:
        {
            "id": "payment_id",
            "amount": "total_amount",
            "status": "payment_status"
        }
        """
        mapped_data = {}

        for source_key, target_key in mapping_rules.items():
            if source_key in source_data:
                mapped_data[target_key] = source_data[source_key]

        return mapped_data

class WebhookHandlerTool(BaseTool):
    """Webhook 수신 처리 도구"""
    def _run(self, webhook_data: dict, signature: str, secret: str):
        import hmac
        import hashlib

        # 서명 검증 (보안)
        expected_signature = hmac.new(
            secret.encode(),
            webhook_data.encode(),
            hashlib.sha256
        ).hexdigest()

        if signature != expected_signature:
            raise ValueError("Invalid webhook signature")

        # 이벤트 타입별 처리
        event_type = webhook_data.get("type")

        if event_type == "charge.succeeded":
            # 결제 성공 처리
            return {"action": "update_status", "status": "completed"}
        elif event_type == "charge.refunded":
            # 환불 처리
            return {"action": "process_refund", "amount": webhook_data["amount"]}

        return {"action": "log", "message": f"Unknown event: {event_type}"}
```

### 데이터베이스 스키마
```sql
-- payments
CREATE TABLE payments (
    id INTEGER PRIMARY KEY,
    external_id TEXT NOT NULL,  -- 외부 API의 ID
    amount INTEGER,
    currency TEXT DEFAULT 'KRW',
    status TEXT,  -- pending, success, failed, refunded
    customer_email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- webhook_logs
CREATE TABLE webhook_logs (
    id INTEGER PRIMARY KEY,
    event_type TEXT,
    payload JSON,
    signature TEXT,
    processed BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. 기능 추가 실습 (10분)

### 시나리오: "환불 자동 승인" 기능 추가

**Step 1: Golden Data 수정**
```bash
vim ./payment-integration/golden_data.json
```

```json
{
  "features": [
    ...기존 features,
    {
      "id": "f5",
      "name": "환불 자동 승인",
      "description": "특정 조건 충족 시 환불 자동 승인 (금액 ≤ ₩10,000)",
      "priority": "MEDIUM",
      "inputs": ["payment_id", "refund_amount"],
      "outputs": ["approval_status", "refund_id"]
    }
  ]
}
```

**Step 2: Tools 재생성 (Phase 5: Delivery)**
```bash
caas generate-phase --phase 5 \
  --input ./payment-integration \
  --requirement "기존 요구사항 + 환불 자동 승인" \
  --output ./payment-integration
```

**결과**: `tools.py`에 `RefundApprovalTool` 자동 추가

**Step 3: Tool 구현 확인**
```python
# tools.py
class RefundApprovalTool(BaseTool):
    """환불 자동 승인 도구"""
    def _run(self, payment_id: str, refund_amount: int):
        # 결제 정보 조회
        payment = db.query(Payment).filter(Payment.id == payment_id).first()

        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        # 자동 승인 조건 체크
        auto_approve = (
            refund_amount <= 10000 and  # ₩10,000 이하
            payment.status == "success" and
            (datetime.now() - payment.created_at).days <= 30  # 30일 이내
        )

        if auto_approve:
            # API 호출 (환불 처리)
            refund_result = self._call_refund_api(payment.external_id, refund_amount)

            return {
                "approval_status": "auto_approved",
                "refund_id": refund_result["id"],
                "message": "환불이 자동으로 승인되었습니다."
            }
        else:
            return {
                "approval_status": "manual_review",
                "message": "수동 검토가 필요합니다."
            }

    def _call_refund_api(self, external_id: str, amount: int):
        import requests

        response = requests.post(
            f"https://api.payment.com/v1/refunds",
            headers={"Authorization": f"Bearer {os.getenv('PAYMENT_API_KEY')}"},
            json={"charge": external_id, "amount": amount}
        )

        return response.json()
```

**Step 4: Agent에 Tool 할당**
```python
# agents.py
agent_5 = Agent(
    role="환불 승인 담당자",
    goal="환불 요청 자동 승인 여부 판단",
    tools=[RefundApprovalTool()],
    backstory="규정에 따라 환불을 신속하게 처리하는 전문가",
)
```

**Step 5: Task 추가**
```python
# tasks.py
task_refund_approval = Task(
    description="환불 요청 {payment_id}, 금액 {refund_amount} 자동 승인 여부 판단",
    expected_output="승인 상태 (auto_approved/manual_review), 환불 ID",
    agent=agent_5,
    context=[]  # 독립 실행
)
```

**Step 6: 테스트**
```bash
python main.py --refund PAY-2024-001 --amount 5000
```

**출력**:
```
🤖 Agent 5 (환불 승인) starting...
✅ Task: 환불 자동 승인 완료
- 결제 ID: PAY-2024-001
- 환불 금액: ₩5,000
- 승인 상태: auto_approved ✅
- 환불 ID: rf_3xyz789abc
```

---

## 5. 커스터마이징 (선택)

### Webhook 서버 추가
```python
# webhook_server.py
from flask import Flask, request, jsonify
import hmac
import hashlib
import os

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    # 서명 검증
    signature = request.headers.get("Stripe-Signature")
    payload = request.data.decode("utf-8")

    secret = os.getenv("WEBHOOK_SECRET")
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    if signature != expected_signature:
        return jsonify({"error": "Invalid signature"}), 401

    # 이벤트 처리
    event = request.json
    event_type = event["type"]

    if event_type == "charge.succeeded":
        # CrewAI로 처리 위임
        crew.kickoff(inputs={"event": event})

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(port=5000)
```

**실행**:
```bash
python webhook_server.py
# ngrok으로 외부 노출
ngrok http 5000
```

### 에러 핸들링 강화
```python
# tools.py - HTTPClientTool 확장
class HTTPClientTool(BaseTool):
    def _run(self, method: str, url: str, **kwargs):
        max_retries = 3
        retry_delay = [1, 2, 4]  # Exponential backoff

        for attempt in range(max_retries):
            try:
                response = requests.request(method, url, **kwargs)

                # HTTP 상태 코드별 처리
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise Exception("Unauthorized - check API key")
                elif response.status_code == 429:
                    # Rate limit 초과 - 재시도
                    time.sleep(retry_delay[attempt])
                    continue
                elif response.status_code >= 500:
                    # 서버 오류 - 재시도
                    time.sleep(retry_delay[attempt])
                    continue
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    raise
                time.sleep(retry_delay[attempt])

            except requests.exceptions.ConnectionError:
                if attempt == max_retries - 1:
                    raise Exception("Connection failed - check network")
                time.sleep(retry_delay[attempt])

        raise Exception(f"Failed after {max_retries} retries")
```

### 로깅 및 모니터링
```python
# tools.py
import logging
from pythonjsonlogger import jsonlogger

# JSON 로깅 설정
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class HTTPClientTool(BaseTool):
    def _run(self, method: str, url: str, **kwargs):
        # 요청 로깅
        logger.info("API Request", extra={
            "method": method,
            "url": url,
            "timestamp": datetime.now().isoformat()
        })

        start_time = time.time()
        response = requests.request(method, url, **kwargs)
        elapsed = time.time() - start_time

        # 응답 로깅
        logger.info("API Response", extra={
            "status_code": response.status_code,
            "elapsed": elapsed,
            "url": url
        })

        return response.json()
```

---

## 6. 보안 강화 (중요)

### API Key 암호화 저장
```python
# config/security.py
from cryptography.fernet import Fernet
import os

class SecretManager:
    def __init__(self):
        # 암호화 키 (환경 변수에서 로드)
        self.cipher = Fernet(os.getenv("ENCRYPTION_KEY").encode())

    def encrypt(self, plain_text: str) -> str:
        return self.cipher.encrypt(plain_text.encode()).decode()

    def decrypt(self, encrypted_text: str) -> str:
        return self.cipher.decrypt(encrypted_text.encode()).decode()

# 사용 예시
manager = SecretManager()
encrypted_key = manager.encrypt(os.getenv("PAYMENT_API_KEY"))
# DB에 encrypted_key 저장

# 사용 시 복호화
api_key = manager.decrypt(encrypted_key)
```

### Rate Limiting 구현
```python
# tools.py
from functools import wraps
import time

class RateLimiter:
    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()

            # 오래된 호출 제거
            self.calls = [c for c in self.calls if now - c < self.period]

            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                time.sleep(sleep_time)

            self.calls.append(time.time())
            return func(*args, **kwargs)

        return wrapper

# 사용 예시
@RateLimiter(max_calls=10, period=60)  # 분당 10회
def call_payment_api():
    ...
```

---

## 📚 관련 문서
- **[14_도구(Tools)_개발_가이드.md](../2_개발_실무_가이드/14_도구(Tools)_개발_가이드.md)** - API Tool 개발 패턴
- **[15_코드_품질_가이드.md](../2_개발_실무_가이드/15_코드_품질_가이드.md)** - 보안 스캔
- **[22_트러블슈팅_가이드.md](../2_개발_실무_가이드/22_트러블슈팅_가이드.md)** - API 오류 해결

---

**작성일**: 2026-02-14
**버전**: v0.6.6
**난이도**: ⭐⭐ 중급
