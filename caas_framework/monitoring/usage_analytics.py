"""
Usage Analytics

사용 패턴 분석 및 인사이트 생성
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from caas_framework.utils.logger import get_logger

logger = get_logger("usage_analytics")


# ========== Models ==========


class EventType(str, Enum):
    """이벤트 타입"""

    SESSION_START = "session_start"
    SESSION_END = "session_end"
    PHASE_START = "phase_start"
    PHASE_END = "phase_end"
    QUALITY_GATE_PASS = "quality_gate_pass"
    QUALITY_GATE_FAIL = "quality_gate_fail"
    REGENERATION = "regeneration"
    ERROR = "error"
    SUCCESS = "success"


class UsageEvent(BaseModel):
    """사용 이벤트"""

    event_id: str
    timestamp: datetime
    event_type: EventType
    session_id: str

    # Context
    user_id: Optional[str] = None
    domain: Optional[str] = None
    phase: Optional[str] = None
    template: Optional[str] = None

    # Metrics
    duration_ms: Optional[float] = None
    tokens_used: Optional[int] = None
    cost: Optional[float] = None

    # Additional data
    metadata: Dict[str, Any] = Field(default={})


class SessionAnalytics(BaseModel):
    """세션 분석 결과"""

    session_id: str
    user_id: Optional[str] = None

    # Time
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[float] = None

    # Phases
    phases_completed: List[str]
    phases_failed: List[str]

    # Quality Gates
    quality_gates_passed: int
    quality_gates_failed: int

    # Regenerations
    regeneration_count: int

    # Resources
    total_tokens: int
    total_cost: float

    # Outcome
    success: bool
    error_count: int


class DomainStats(BaseModel):
    """도메인별 통계"""

    domain: str
    usage_count: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_duration_minutes: float
    total_cost: float


class TemplateStats(BaseModel):
    """템플릿별 통계"""

    template: str
    usage_count: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_tokens: float


class TrendData(BaseModel):
    """트렌드 데이터"""

    date: str  # YYYY-MM-DD
    sessions: int
    successes: int
    failures: int
    total_tokens: int
    total_cost: float


class AnalyticsReport(BaseModel):
    """분석 리포트"""

    generated_at: datetime
    period_start: datetime
    period_end: datetime

    # Overall Stats
    total_sessions: int
    successful_sessions: int
    failed_sessions: int
    success_rate: float

    # Resources
    total_tokens: int
    total_cost: float
    avg_tokens_per_session: float
    avg_cost_per_session: float

    # Quality
    avg_quality_gates_passed: float
    avg_regenerations: float

    # Top Domains
    top_domains: List[DomainStats]

    # Top Templates
    top_templates: List[TemplateStats]

    # Trends
    daily_trends: List[TrendData]

    # Insights
    insights: List[str]


# ========== Usage Analytics ==========


class UsageAnalytics:
    """
    사용 패턴 분석기

    - 이벤트 추적
    - 통계 집계
    - 트렌드 분석
    - 인사이트 생성
    """

    def __init__(self, storage_dir: str = ".caas/analytics"):
        """
        Args:
            storage_dir: 분석 데이터 저장 디렉토리
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logger

        # In-memory cache
        self.events: List[UsageEvent] = []
        self.sessions: Dict[str, SessionAnalytics] = {}

    def track_event(
        self,
        event_type: EventType,
        session_id: str,
        user_id: Optional[str] = None,
        domain: Optional[str] = None,
        phase: Optional[str] = None,
        template: Optional[str] = None,
        duration_ms: Optional[float] = None,
        tokens_used: Optional[int] = None,
        cost: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageEvent:
        """
        이벤트 추적

        Args:
            event_type: 이벤트 타입
            session_id: 세션 ID
            user_id: 사용자 ID
            domain: 도메인
            phase: Phase
            template: 템플릿
            duration_ms: 소요 시간 (밀리초)
            tokens_used: 사용 토큰 수
            cost: 비용
            metadata: 추가 메타데이터

        Returns:
            UsageEvent: 이벤트
        """
        event = UsageEvent(
            event_id=f"event_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            timestamp=datetime.utcnow(),
            event_type=event_type,
            session_id=session_id,
            user_id=user_id,
            domain=domain,
            phase=phase,
            template=template,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            cost=cost,
            metadata=metadata or {},
        )

        # 캐시에 추가
        self.events.append(event)

        # 파일로 저장
        self._save_event(event)

        # 세션 분석 업데이트
        self._update_session_analytics(event)

        self.logger.debug(f"Event tracked: {event_type.value} for {session_id}")
        return event

    def get_session_analytics(self, session_id: str) -> Optional[SessionAnalytics]:
        """세션 분석 조회"""
        return self.sessions.get(session_id)

    def get_domain_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[DomainStats]:
        """
        도메인별 통계 조회

        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            List[DomainStats]: 도메인별 통계
        """
        events = self._filter_events_by_date(start_date, end_date)

        # 도메인별로 집계
        domain_data = defaultdict(
            lambda: {
                "total": 0,
                "success": 0,
                "failure": 0,
                "durations": [],
                "costs": [],
            }
        )

        for event in events:
            if event.domain:
                if event.event_type == EventType.SUCCESS:
                    domain_data[event.domain]["success"] += 1
                    domain_data[event.domain]["total"] += 1
                    if event.duration_ms:
                        domain_data[event.domain]["durations"].append(
                            event.duration_ms / 1000 / 60
                        )
                    if event.cost:
                        domain_data[event.domain]["costs"].append(event.cost)
                elif event.event_type == EventType.ERROR:
                    domain_data[event.domain]["failure"] += 1
                    domain_data[event.domain]["total"] += 1

        # DomainStats 생성
        stats = []
        for domain, data in domain_data.items():
            if data["total"] == 0:
                continue

            stats.append(
                DomainStats(
                    domain=domain,
                    usage_count=data["total"],
                    success_count=data["success"],
                    failure_count=data["failure"],
                    success_rate=data["success"] / data["total"] * 100,
                    avg_duration_minutes=(
                        sum(data["durations"]) / len(data["durations"])
                        if data["durations"]
                        else 0
                    ),
                    total_cost=sum(data["costs"]),
                )
            )

        # 사용 횟수 내림차순 정렬
        stats.sort(key=lambda s: s.usage_count, reverse=True)
        return stats

    def get_template_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[TemplateStats]:
        """
        템플릿별 통계 조회

        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            List[TemplateStats]: 템플릿별 통계
        """
        events = self._filter_events_by_date(start_date, end_date)

        # 템플릿별로 집계
        template_data = defaultdict(
            lambda: {
                "total": 0,
                "success": 0,
                "failure": 0,
                "tokens": [],
            }
        )

        for event in events:
            if event.template:
                if event.event_type == EventType.SUCCESS:
                    template_data[event.template]["success"] += 1
                    template_data[event.template]["total"] += 1
                    if event.tokens_used:
                        template_data[event.template]["tokens"].append(
                            event.tokens_used
                        )
                elif event.event_type == EventType.ERROR:
                    template_data[event.template]["failure"] += 1
                    template_data[event.template]["total"] += 1

        # TemplateStats 생성
        stats = []
        for template, data in template_data.items():
            if data["total"] == 0:
                continue

            stats.append(
                TemplateStats(
                    template=template,
                    usage_count=data["total"],
                    success_count=data["success"],
                    failure_count=data["failure"],
                    success_rate=data["success"] / data["total"] * 100,
                    avg_tokens=sum(data["tokens"]) / len(data["tokens"])
                    if data["tokens"]
                    else 0,
                )
            )

        # 사용 횟수 내림차순 정렬
        stats.sort(key=lambda s: s.usage_count, reverse=True)
        return stats

    def get_daily_trends(
        self,
        days: int = 30,
    ) -> List[TrendData]:
        """
        일별 트렌드 조회

        Args:
            days: 조회할 일수

        Returns:
            List[TrendData]: 일별 트렌드
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        events = self._filter_events_by_date(start_date, end_date)

        # 날짜별로 집계
        daily_data = defaultdict(
            lambda: {
                "sessions": set(),
                "successes": 0,
                "failures": 0,
                "tokens": 0,
                "cost": 0.0,
            }
        )

        for event in events:
            date_key = event.timestamp.strftime("%Y-%m-%d")

            daily_data[date_key]["sessions"].add(event.session_id)

            if event.event_type == EventType.SUCCESS:
                daily_data[date_key]["successes"] += 1
            elif event.event_type == EventType.ERROR:
                daily_data[date_key]["failures"] += 1

            if event.tokens_used:
                daily_data[date_key]["tokens"] += event.tokens_used
            if event.cost:
                daily_data[date_key]["cost"] += event.cost

        # TrendData 생성
        trends = []
        current_date = start_date
        while current_date <= end_date:
            date_key = current_date.strftime("%Y-%m-%d")
            data = daily_data.get(
                date_key,
                {
                    "sessions": set(),
                    "successes": 0,
                    "failures": 0,
                    "tokens": 0,
                    "cost": 0.0,
                },
            )

            trends.append(
                TrendData(
                    date=date_key,
                    sessions=len(data["sessions"]),
                    successes=data["successes"],
                    failures=data["failures"],
                    total_tokens=data["tokens"],
                    total_cost=data["cost"],
                )
            )

            current_date += timedelta(days=1)

        return trends

    def generate_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> AnalyticsReport:
        """
        분석 리포트 생성

        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            AnalyticsReport: 분석 리포트
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        events = self._filter_events_by_date(start_date, end_date)

        # 세션 수집
        session_ids = set(e.session_id for e in events)
        sessions = [self.sessions[sid] for sid in session_ids if sid in self.sessions]

        # Overall stats
        total_sessions = len(sessions)
        successful_sessions = sum(1 for s in sessions if s.success)
        failed_sessions = total_sessions - successful_sessions
        success_rate = (
            (successful_sessions / total_sessions * 100) if total_sessions > 0 else 0
        )

        # Resources
        total_tokens = sum(s.total_tokens for s in sessions)
        total_cost = sum(s.total_cost for s in sessions)
        avg_tokens = total_tokens / total_sessions if total_sessions > 0 else 0
        avg_cost = total_cost / total_sessions if total_sessions > 0 else 0

        # Quality
        avg_quality_gates = (
            sum(s.quality_gates_passed for s in sessions) / total_sessions
            if total_sessions > 0
            else 0
        )
        avg_regenerations = (
            sum(s.regeneration_count for s in sessions) / total_sessions
            if total_sessions > 0
            else 0
        )

        # Top domains & templates
        top_domains = self.get_domain_stats(start_date, end_date)[:10]
        top_templates = self.get_template_stats(start_date, end_date)[:10]

        # Daily trends
        days = (end_date - start_date).days
        daily_trends = self.get_daily_trends(days=max(days, 7))

        # Generate insights
        insights = self._generate_insights(
            sessions,
            top_domains,
            top_templates,
            daily_trends,
        )

        return AnalyticsReport(
            generated_at=datetime.utcnow(),
            period_start=start_date,
            period_end=end_date,
            total_sessions=total_sessions,
            successful_sessions=successful_sessions,
            failed_sessions=failed_sessions,
            success_rate=success_rate,
            total_tokens=total_tokens,
            total_cost=total_cost,
            avg_tokens_per_session=avg_tokens,
            avg_cost_per_session=avg_cost,
            avg_quality_gates_passed=avg_quality_gates,
            avg_regenerations=avg_regenerations,
            top_domains=top_domains,
            top_templates=top_templates,
            daily_trends=daily_trends,
            insights=insights,
        )

    def _update_session_analytics(self, event: UsageEvent):
        """세션 분석 업데이트"""
        session_id = event.session_id

        # 세션이 없으면 생성
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionAnalytics(
                session_id=session_id,
                user_id=event.user_id,
                start_time=event.timestamp,
                phases_completed=[],
                phases_failed=[],
                quality_gates_passed=0,
                quality_gates_failed=0,
                regeneration_count=0,
                total_tokens=0,
                total_cost=0.0,
                success=False,
                error_count=0,
            )

        session = self.sessions[session_id]

        # 이벤트 타입별 처리
        if event.event_type == EventType.PHASE_END:
            if event.phase and event.phase not in session.phases_completed:
                session.phases_completed.append(event.phase)

        elif event.event_type == EventType.QUALITY_GATE_PASS:
            session.quality_gates_passed += 1

        elif event.event_type == EventType.QUALITY_GATE_FAIL:
            session.quality_gates_failed += 1
            if event.phase and event.phase not in session.phases_failed:
                session.phases_failed.append(event.phase)

        elif event.event_type == EventType.REGENERATION:
            session.regeneration_count += 1

        elif event.event_type == EventType.ERROR:
            session.error_count += 1

        elif event.event_type == EventType.SUCCESS:
            session.success = True

        elif event.event_type == EventType.SESSION_END:
            session.end_time = event.timestamp
            if session.start_time:
                duration = (event.timestamp - session.start_time).total_seconds() / 60
                session.duration_minutes = duration

        # 리소스 업데이트
        if event.tokens_used:
            session.total_tokens += event.tokens_used
        if event.cost:
            session.total_cost += event.cost

    def _filter_events_by_date(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> List[UsageEvent]:
        """날짜로 이벤트 필터링"""
        filtered = []

        for event in self.events:
            if start_date and event.timestamp < start_date:
                continue
            if end_date and event.timestamp > end_date:
                continue
            filtered.append(event)

        return filtered

    def _generate_insights(
        self,
        sessions: List[SessionAnalytics],
        top_domains: List[DomainStats],
        top_templates: List[TemplateStats],
        daily_trends: List[TrendData],
    ) -> List[str]:
        """인사이트 생성"""
        insights = []

        if not sessions:
            return ["No data available for the selected period"]

        # Success rate insights
        success_rate = sum(1 for s in sessions if s.success) / len(sessions) * 100
        if success_rate >= 90:
            insights.append(f"✅ Excellent success rate: {success_rate:.1f}%")
        elif success_rate >= 70:
            insights.append(
                f"⚠️ Good success rate: {success_rate:.1f}%, but room for improvement"
            )
        else:
            insights.append(
                f"❌ Low success rate: {success_rate:.1f}%, requires attention"
            )

        # Quality gate insights
        avg_quality_gates = sum(s.quality_gates_passed for s in sessions) / len(
            sessions
        )
        if avg_quality_gates >= 3:
            insights.append(
                f"🏆 High quality: Average {avg_quality_gates:.1f} quality gates passed"
            )

        # Regeneration insights
        avg_regenerations = sum(s.regeneration_count for s in sessions) / len(sessions)
        if avg_regenerations > 1.5:
            insights.append(
                f"🔄 High regeneration rate: {avg_regenerations:.1f} per session - consider improving prompts"
            )

        # Cost insights
        total_cost = sum(s.total_cost for s in sessions)
        avg_cost = total_cost / len(sessions)
        if avg_cost > 1.0:
            insights.append(f"💰 High average cost: ${avg_cost:.2f} per session")

        # Domain insights
        if top_domains:
            most_popular = top_domains[0]
            insights.append(
                f"📊 Most popular domain: '{most_popular.domain}' ({most_popular.usage_count} uses)"
            )

            # Low success rate domains
            low_success_domains = [
                d for d in top_domains if d.success_rate < 50 and d.usage_count >= 3
            ]
            if low_success_domains:
                insights.append(
                    f"⚠️ Domains with low success rate: {', '.join(d.domain for d in low_success_domains[:3])}"
                )

        # Template insights
        if top_templates:
            most_used = top_templates[0]
            insights.append(
                f"📝 Most used template: '{most_used.template}' ({most_used.usage_count} uses)"
            )

        # Trend insights
        if len(daily_trends) >= 7:
            recent_week = daily_trends[-7:]
            prev_week = daily_trends[-14:-7] if len(daily_trends) >= 14 else None

            recent_sessions = sum(t.sessions for t in recent_week)
            if prev_week:
                prev_sessions = sum(t.sessions for t in prev_week)
                if recent_sessions > prev_sessions * 1.2:
                    insights.append(
                        f"📈 Usage trending up: {((recent_sessions - prev_sessions) / prev_sessions * 100):.1f}% increase this week"
                    )
                elif recent_sessions < prev_sessions * 0.8:
                    insights.append(
                        f"📉 Usage trending down: {((prev_sessions - recent_sessions) / prev_sessions * 100):.1f}% decrease this week"
                    )

        return insights

    def _save_event(self, event: UsageEvent):
        """이벤트를 파일로 저장"""
        # 날짜별로 디렉토리 생성
        date_dir = self.storage_dir / event.timestamp.strftime("%Y%m%d")
        date_dir.mkdir(exist_ok=True)

        # 파일로 저장
        event_file = date_dir / f"{event.event_id}.json"
        with open(event_file, "w") as f:
            json.dump(event.model_dump(mode="json"), f, indent=2, default=str)

    def load_events_from_disk(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        """디스크에서 이벤트 로드"""
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
                for event_file in date_dir.glob("*.json"):
                    try:
                        with open(event_file, "r") as f:
                            data = json.load(f)
                        event = UsageEvent(**data)
                        self.events.append(event)
                        self._update_session_analytics(event)
                        loaded_count += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to load event {event_file}: {e}")

            current_date += timedelta(days=1)

        self.logger.info(f"Loaded {loaded_count} events from disk")

    def export_report_json(self, output_file: str, report: AnalyticsReport):
        """리포트를 JSON으로 내보내기"""
        with open(output_file, "w") as f:
            json.dump(report.model_dump(mode="json"), f, indent=2, default=str)
        self.logger.info(f"Report exported to {output_file}")


# ========== Global Analytics Instance ==========

_global_analytics: Optional[UsageAnalytics] = None


def get_usage_analytics() -> UsageAnalytics:
    """전역 Usage Analytics 인스턴스 반환"""
    global _global_analytics
    if _global_analytics is None:
        _global_analytics = UsageAnalytics()
    return _global_analytics
