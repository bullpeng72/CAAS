"""
Cost Tracker

LLM API 사용량 및 비용 추적
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import BaseModel, Field
from collections import defaultdict
from enum import Enum

from app.utils.logger import get_logger

logger = get_logger("cost_tracker")


# ========== Models ==========

class LLMProvider(str, Enum):
    """LLM 제공자"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    CUSTOM = "custom"


class ModelPricing(BaseModel):
    """모델 가격 정보"""
    provider: LLMProvider
    model_name: str
    input_price_per_1k: float  # Input tokens per 1K
    output_price_per_1k: float  # Output tokens per 1K
    currency: str = "USD"


class UsageRecord(BaseModel):
    """사용량 기록"""
    record_id: str
    session_id: str
    timestamp: datetime

    # LLM Info
    provider: LLMProvider
    model_name: str

    # Token Usage
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    # Cost
    input_cost: float
    output_cost: float
    total_cost: float

    # Metadata
    operation: Optional[str] = None  # e.g., "requirement_analysis", "agent_design"
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default={})


class CostSummary(BaseModel):
    """비용 요약"""
    session_id: Optional[str] = None
    start_date: datetime
    end_date: datetime

    # Totals
    total_requests: int
    total_tokens: int
    total_cost: float

    # By Provider
    by_provider: Dict[str, Dict[str, Any]]

    # By Model
    by_model: Dict[str, Dict[str, Any]]

    # By Operation
    by_operation: Dict[str, Dict[str, Any]]


class BudgetAlert(BaseModel):
    """예산 알림"""
    alert_id: str
    timestamp: datetime
    session_id: Optional[str] = None
    user_id: Optional[str] = None

    budget_type: str  # "session", "user", "daily", "monthly"
    budget_limit: float
    current_usage: float
    percentage: float

    message: str


# ========== Default Pricing ==========

DEFAULT_PRICING = {
    # OpenAI GPT-4
    "gpt-4": ModelPricing(
        provider=LLMProvider.OPENAI,
        model_name="gpt-4",
        input_price_per_1k=0.03,
        output_price_per_1k=0.06,
    ),
    "gpt-4-turbo": ModelPricing(
        provider=LLMProvider.OPENAI,
        model_name="gpt-4-turbo",
        input_price_per_1k=0.01,
        output_price_per_1k=0.03,
    ),
    # OpenAI GPT-3.5
    "gpt-3.5-turbo": ModelPricing(
        provider=LLMProvider.OPENAI,
        model_name="gpt-3.5-turbo",
        input_price_per_1k=0.0015,
        output_price_per_1k=0.002,
    ),
    # Anthropic Claude
    "claude-3-opus": ModelPricing(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-3-opus",
        input_price_per_1k=0.015,
        output_price_per_1k=0.075,
    ),
    "claude-3-sonnet": ModelPricing(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-3-sonnet",
        input_price_per_1k=0.003,
        output_price_per_1k=0.015,
    ),
    "claude-3-haiku": ModelPricing(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-3-haiku",
        input_price_per_1k=0.00025,
        output_price_per_1k=0.00125,
    ),
}


# ========== Cost Tracker ==========

class CostTracker:
    """
    LLM API 비용 추적기

    - 토큰 사용량 추적
    - 비용 계산
    - 예산 알림
    - 사용량 리포트
    """

    def __init__(
        self,
        storage_dir: str = ".caas/costs",
        pricing: Optional[Dict[str, ModelPricing]] = None,
    ):
        """
        Args:
            storage_dir: 비용 데이터 저장 디렉토리
            pricing: 모델 가격 정보 (기본값: DEFAULT_PRICING)
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.pricing = pricing or DEFAULT_PRICING
        self.logger = logger

        # In-memory cache
        self.usage_records: Dict[str, List[UsageRecord]] = defaultdict(list)
        self.budget_limits: Dict[str, Dict[str, float]] = defaultdict(dict)

    def track_usage(
        self,
        session_id: str,
        provider: LLMProvider,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        operation: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageRecord:
        """
        사용량 추적

        Args:
            session_id: 세션 ID
            provider: LLM 제공자
            model_name: 모델 이름
            prompt_tokens: 프롬프트 토큰 수
            completion_tokens: 완성 토큰 수
            operation: 작업 이름
            user_id: 사용자 ID
            metadata: 추가 메타데이터

        Returns:
            UsageRecord: 사용량 기록
        """
        # 가격 정보 조회
        pricing = self.get_pricing(model_name)

        # 비용 계산
        input_cost = (prompt_tokens / 1000) * pricing.input_price_per_1k
        output_cost = (completion_tokens / 1000) * pricing.output_price_per_1k
        total_cost = input_cost + output_cost

        # 기록 생성
        record = UsageRecord(
            record_id=f"{session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            session_id=session_id,
            timestamp=datetime.utcnow(),
            provider=provider,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            operation=operation,
            user_id=user_id,
            metadata=metadata or {},
        )

        # 캐시에 추가
        self.usage_records[session_id].append(record)

        # 파일로 저장
        self._save_record(record)

        # 예산 체크
        self._check_budget(record)

        self.logger.info(
            f"Usage tracked: {model_name} - "
            f"{prompt_tokens + completion_tokens} tokens - "
            f"${total_cost:.4f}"
        )

        return record

    def get_pricing(self, model_name: str) -> ModelPricing:
        """모델 가격 정보 조회"""
        if model_name in self.pricing:
            return self.pricing[model_name]

        # 기본 가격 (알 수 없는 모델)
        self.logger.warning(f"Unknown model pricing: {model_name}, using default")
        return ModelPricing(
            provider=LLMProvider.CUSTOM,
            model_name=model_name,
            input_price_per_1k=0.001,
            output_price_per_1k=0.002,
        )

    def set_pricing(self, model_name: str, pricing: ModelPricing):
        """모델 가격 정보 설정"""
        self.pricing[model_name] = pricing
        self.logger.info(f"Pricing set for {model_name}")

    def get_usage_records(
        self,
        session_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[UsageRecord]:
        """
        사용량 기록 조회

        Args:
            session_id: 세션 ID (None이면 전체)
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            List[UsageRecord]: 사용량 기록 목록
        """
        records = []

        if session_id:
            # 특정 세션
            records = self.usage_records.get(session_id, [])
        else:
            # 전체 세션
            for session_records in self.usage_records.values():
                records.extend(session_records)

        # 날짜 필터링
        if start_date or end_date:
            filtered = []
            for record in records:
                if start_date and record.timestamp < start_date:
                    continue
                if end_date and record.timestamp > end_date:
                    continue
                filtered.append(record)
            records = filtered

        return records

    def get_summary(
        self,
        session_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> CostSummary:
        """
        비용 요약 조회

        Args:
            session_id: 세션 ID
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            CostSummary: 비용 요약
        """
        records = self.get_usage_records(session_id, start_date, end_date)

        if not records:
            return CostSummary(
                session_id=session_id,
                start_date=start_date or datetime.utcnow(),
                end_date=end_date or datetime.utcnow(),
                total_requests=0,
                total_tokens=0,
                total_cost=0.0,
                by_provider={},
                by_model={},
                by_operation={},
            )

        # 집계
        by_provider = defaultdict(lambda: {"requests": 0, "tokens": 0, "cost": 0.0})
        by_model = defaultdict(lambda: {"requests": 0, "tokens": 0, "cost": 0.0})
        by_operation = defaultdict(lambda: {"requests": 0, "tokens": 0, "cost": 0.0})

        total_requests = len(records)
        total_tokens = 0
        total_cost = 0.0

        for record in records:
            # Totals
            total_tokens += record.total_tokens
            total_cost += record.total_cost

            # By Provider
            by_provider[record.provider.value]["requests"] += 1
            by_provider[record.provider.value]["tokens"] += record.total_tokens
            by_provider[record.provider.value]["cost"] += record.total_cost

            # By Model
            by_model[record.model_name]["requests"] += 1
            by_model[record.model_name]["tokens"] += record.total_tokens
            by_model[record.model_name]["cost"] += record.total_cost

            # By Operation
            if record.operation:
                by_operation[record.operation]["requests"] += 1
                by_operation[record.operation]["tokens"] += record.total_tokens
                by_operation[record.operation]["cost"] += record.total_cost

        return CostSummary(
            session_id=session_id,
            start_date=start_date or records[0].timestamp,
            end_date=end_date or records[-1].timestamp,
            total_requests=total_requests,
            total_tokens=total_tokens,
            total_cost=total_cost,
            by_provider=dict(by_provider),
            by_model=dict(by_model),
            by_operation=dict(by_operation),
        )

    def set_budget_limit(
        self,
        budget_type: str,
        limit: float,
        identifier: Optional[str] = None,
    ):
        """
        예산 한도 설정

        Args:
            budget_type: 예산 유형 ("session", "user", "daily", "monthly")
            limit: 한도 금액
            identifier: 식별자 (session_id, user_id 등)
        """
        key = identifier or "default"
        self.budget_limits[budget_type][key] = limit
        self.logger.info(f"Budget limit set: {budget_type}/{key} = ${limit}")

    def get_budget_usage(
        self,
        budget_type: str,
        identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        예산 사용량 조회

        Returns:
            Dict: {"limit": float, "usage": float, "remaining": float, "percentage": float}
        """
        key = identifier or "default"
        limit = self.budget_limits.get(budget_type, {}).get(key, 0.0)

        if limit == 0.0:
            return {
                "limit": 0.0,
                "usage": 0.0,
                "remaining": 0.0,
                "percentage": 0.0,
            }

        # 사용량 계산
        if budget_type == "session":
            usage = self.get_summary(session_id=identifier).total_cost
        elif budget_type == "daily":
            start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            usage = self.get_summary(start_date=start).total_cost
        elif budget_type == "monthly":
            start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            usage = self.get_summary(start_date=start).total_cost
        else:
            usage = 0.0

        return {
            "limit": limit,
            "usage": usage,
            "remaining": max(0, limit - usage),
            "percentage": (usage / limit * 100) if limit > 0 else 0.0,
        }

    def _check_budget(self, record: UsageRecord):
        """예산 체크 및 알림 생성"""
        # Session budget
        if "session" in self.budget_limits:
            key = record.session_id
            if key in self.budget_limits["session"]:
                usage_info = self.get_budget_usage("session", key)
                if usage_info["percentage"] >= 80:
                    self._create_budget_alert(
                        "session",
                        key,
                        usage_info,
                        record.user_id,
                    )

        # Daily budget
        if "daily" in self.budget_limits:
            usage_info = self.get_budget_usage("daily")
            if usage_info["percentage"] >= 80:
                self._create_budget_alert(
                    "daily",
                    None,
                    usage_info,
                    record.user_id,
                )

    def _create_budget_alert(
        self,
        budget_type: str,
        identifier: Optional[str],
        usage_info: Dict[str, Any],
        user_id: Optional[str] = None,
    ):
        """예산 알림 생성"""
        alert = BudgetAlert(
            alert_id=f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            timestamp=datetime.utcnow(),
            session_id=identifier if budget_type == "session" else None,
            user_id=user_id,
            budget_type=budget_type,
            budget_limit=usage_info["limit"],
            current_usage=usage_info["usage"],
            percentage=usage_info["percentage"],
            message=f"Budget alert: {budget_type} usage at {usage_info['percentage']:.1f}% "
                   f"(${usage_info['usage']:.2f} / ${usage_info['limit']:.2f})",
        )

        self.logger.warning(alert.message)

        # 알림 저장
        alert_file = self.storage_dir / "alerts" / f"{alert.alert_id}.json"
        alert_file.parent.mkdir(exist_ok=True)
        with open(alert_file, "w") as f:
            json.dump(alert.model_dump(mode="json"), f, indent=2, default=str)

    def _save_record(self, record: UsageRecord):
        """사용량 기록을 파일로 저장"""
        # 날짜별로 디렉토리 생성
        date_dir = self.storage_dir / record.timestamp.strftime("%Y%m%d")
        date_dir.mkdir(exist_ok=True)

        # 파일로 저장
        record_file = date_dir / f"{record.record_id}.json"
        with open(record_file, "w") as f:
            json.dump(record.model_dump(mode="json"), f, indent=2, default=str)

    def load_records_from_disk(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        """디스크에서 기록 로드"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()

        loaded_count = 0

        # 날짜 범위 순회
        current_date = start_date
        while current_date <= end_date:
            date_dir = self.storage_dir / current_date.strftime("%Y%m%d")

            if date_dir.exists():
                for record_file in date_dir.glob("*.json"):
                    try:
                        with open(record_file, "r") as f:
                            data = json.load(f)
                        record = UsageRecord(**data)
                        self.usage_records[record.session_id].append(record)
                        loaded_count += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to load record {record_file}: {e}")

            current_date += timedelta(days=1)

        self.logger.info(f"Loaded {loaded_count} usage records from disk")

    def export_summary_csv(
        self,
        output_file: str,
        session_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        """CSV로 요약 내보내기"""
        import csv

        records = self.get_usage_records(session_id, start_date, end_date)

        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "Session ID", "Provider", "Model",
                "Prompt Tokens", "Completion Tokens", "Total Tokens",
                "Input Cost", "Output Cost", "Total Cost",
                "Operation", "User ID"
            ])

            for record in records:
                writer.writerow([
                    record.timestamp.isoformat(),
                    record.session_id,
                    record.provider.value,
                    record.model_name,
                    record.prompt_tokens,
                    record.completion_tokens,
                    record.total_tokens,
                    f"{record.input_cost:.4f}",
                    f"{record.output_cost:.4f}",
                    f"{record.total_cost:.4f}",
                    record.operation or "",
                    record.user_id or "",
                ])

        self.logger.info(f"Summary exported to {output_file}")


# ========== Global Cost Tracker Instance ==========

_global_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """전역 Cost Tracker 인스턴스 반환"""
    global _global_cost_tracker
    if _global_cost_tracker is None:
        _global_cost_tracker = CostTracker()
    return _global_cost_tracker
