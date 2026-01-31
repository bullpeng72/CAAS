"""
BMAD Engine with Monitoring

Phase 3.2 통합: 모니터링이 통합된 BMAD Engine wrapper
"""

import time
from typing import Optional
from datetime import datetime

from app.core.bmad.engine import BMADEngine, BMADContext
from app.monitoring.performance_profiler import get_profiler
from app.monitoring.cost_tracker import get_cost_tracker
from app.monitoring.usage_analytics import get_usage_analytics, EventType
from app.utils.logger import get_logger

logger = get_logger("bmad.engine_monitored")


class MonitoredBMADEngine(BMADEngine):
    """
    모니터링이 통합된 BMAD Engine

    기존 BMADEngine을 상속하여 각 phase에서 다음을 자동으로 수행:
    - 성능 프로파일링 (CPU, 메모리, 시간)
    - 비용 추적 (LLM API 호출)
    - 사용 분석 (이벤트 추적, 도메인/템플릿 통계)
    """

    def __init__(self):
        super().__init__()

        # Monitoring instances
        self.profiler = get_profiler()
        self.cost_tracker = get_cost_tracker()
        self.analytics = get_usage_analytics()

        self.logger = logger

    def execute_discovery(self, context: BMADContext, enable_sharding: bool = True) -> BMADContext:
        """Discovery 단계 실행 with monitoring"""
        session_id = context.session_id
        start_time = time.time()

        # Track phase start
        self.analytics.track_event(
            event_type=EventType.PHASE_START,
            session_id=session_id,
            user_id=context.user_id,
            domain=context.domain,
            phase="discovery",
        )

        try:
            # Profile performance
            with self.profiler.profile("discovery_phase", session_id=session_id):
                # Execute original method
                context = super().execute_discovery(context, enable_sharding)

            # Track successful completion
            duration_ms = (time.time() - start_time) * 1000
            self.analytics.track_event(
                event_type=EventType.PHASE_END,
                session_id=session_id,
                user_id=context.user_id,
                domain=context.domain,
                phase="discovery",
                duration_ms=duration_ms,
            )

            return context

        except Exception as e:
            # Track failure
            duration_ms = (time.time() - start_time) * 1000
            self.analytics.track_event(
                event_type=EventType.ERROR,
                session_id=session_id,
                user_id=context.user_id,
                phase="discovery",
                duration_ms=duration_ms,
                metadata={"error": str(e)},
            )
            raise

    def execute_architecture(self, context: BMADContext) -> BMADContext:
        """Architecture 단계 실행 with monitoring"""
        session_id = context.session_id
        start_time = time.time()

        self.analytics.track_event(
            event_type=EventType.PHASE_START,
            session_id=session_id,
            user_id=context.user_id,
            domain=context.domain,
            phase="architecture",
        )

        try:
            with self.profiler.profile("architecture_phase", session_id=session_id):
                context = super().execute_architecture(context)

            duration_ms = (time.time() - start_time) * 1000
            self.analytics.track_event(
                event_type=EventType.PHASE_END,
                session_id=session_id,
                user_id=context.user_id,
                domain=context.domain,
                phase="architecture",
                duration_ms=duration_ms,
            )

            return context

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.analytics.track_event(
                event_type=EventType.ERROR,
                session_id=session_id,
                user_id=context.user_id,
                phase="architecture",
                duration_ms=duration_ms,
                metadata={"error": str(e)},
            )
            raise

    def execute_design(self, context: BMADContext) -> BMADContext:
        """Design 단계 실행 with monitoring"""
        session_id = context.session_id
        start_time = time.time()

        self.analytics.track_event(
            event_type=EventType.PHASE_START,
            session_id=session_id,
            user_id=context.user_id,
            domain=context.domain,
            phase="design",
        )

        try:
            with self.profiler.profile("design_phase", session_id=session_id):
                context = super().execute_design(context)

            duration_ms = (time.time() - start_time) * 1000
            self.analytics.track_event(
                event_type=EventType.PHASE_END,
                session_id=session_id,
                user_id=context.user_id,
                domain=context.domain,
                phase="design",
                duration_ms=duration_ms,
            )

            return context

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.analytics.track_event(
                event_type=EventType.ERROR,
                session_id=session_id,
                user_id=context.user_id,
                phase="design",
                duration_ms=duration_ms,
                metadata={"error": str(e)},
            )
            raise

    def execute_development(
        self,
        context: BMADContext,
        enable_reflection: bool = True,
        enable_traceability: bool = True,
        quality_threshold: float = 0.7,
        max_reflection_iterations: int = 3
    ) -> BMADContext:
        """Development 단계 실행 with monitoring"""
        session_id = context.session_id
        start_time = time.time()

        self.analytics.track_event(
            event_type=EventType.PHASE_START,
            session_id=session_id,
            user_id=context.user_id,
            domain=context.domain,
            phase="development",
        )

        try:
            with self.profiler.profile("development_phase", session_id=session_id):
                context = super().execute_development(
                    context,
                    enable_reflection,
                    enable_traceability,
                    quality_threshold,
                    max_reflection_iterations
                )

            duration_ms = (time.time() - start_time) * 1000
            self.analytics.track_event(
                event_type=EventType.PHASE_END,
                session_id=session_id,
                user_id=context.user_id,
                domain=context.domain,
                phase="development",
                duration_ms=duration_ms,
            )

            return context

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.analytics.track_event(
                event_type=EventType.ERROR,
                session_id=session_id,
                user_id=context.user_id,
                phase="development",
                duration_ms=duration_ms,
                metadata={"error": str(e)},
            )
            raise

    def execute_delivery(self, context: BMADContext) -> BMADContext:
        """Delivery 단계 실행 with monitoring"""
        session_id = context.session_id
        start_time = time.time()

        self.analytics.track_event(
            event_type=EventType.PHASE_START,
            session_id=session_id,
            user_id=context.user_id,
            domain=context.domain,
            phase="delivery",
        )

        try:
            with self.profiler.profile("delivery_phase", session_id=session_id):
                context = super().execute_delivery(context)

            duration_ms = (time.time() - start_time) * 1000
            self.analytics.track_event(
                event_type=EventType.PHASE_END,
                session_id=session_id,
                user_id=context.user_id,
                domain=context.domain,
                phase="delivery",
                duration_ms=duration_ms,
            )

            # Track final success
            self.analytics.track_event(
                event_type=EventType.SUCCESS,
                session_id=session_id,
                user_id=context.user_id,
                domain=context.domain,
                duration_ms=(time.time() - context.created_at.timestamp()) * 1000,
            )

            return context

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.analytics.track_event(
                event_type=EventType.ERROR,
                session_id=session_id,
                user_id=context.user_id,
                phase="delivery",
                duration_ms=duration_ms,
                metadata={"error": str(e)},
            )
            raise

    def run_full_pipeline(
        self,
        project_name: str,
        requirement: str,
        enable_adaptive: bool = True,
        user_id: Optional[str] = None,
    ) -> BMADContext:
        """전체 파이프라인 실행 with monitoring"""
        # Create context with session_id
        context = self.create_context(project_name, requirement)
        context.user_id = user_id

        session_id = context.session_id
        start_time = time.time()

        # Track session start
        self.analytics.track_event(
            event_type=EventType.SESSION_START,
            session_id=session_id,
            user_id=user_id,
            domain=context.domain,
        )

        try:
            # Execute pipeline (will call monitored execute_* methods)
            context = super().run_full_pipeline(project_name, requirement, enable_adaptive)

            # Track session end
            duration_ms = (time.time() - start_time) * 1000
            self.analytics.track_event(
                event_type=EventType.SESSION_END,
                session_id=session_id,
                user_id=user_id,
                domain=context.domain,
                duration_ms=duration_ms,
            )

            # Generate monitoring report
            self._generate_monitoring_report(context)

            return context

        except Exception as e:
            # Track session failure
            duration_ms = (time.time() - start_time) * 1000
            self.analytics.track_event(
                event_type=EventType.ERROR,
                session_id=session_id,
                user_id=user_id,
                duration_ms=duration_ms,
                metadata={"error": str(e), "phase": "full_pipeline"},
            )
            raise

    def _generate_monitoring_report(self, context: BMADContext):
        """모니터링 리포트 생성 및 출력"""
        session_id = context.session_id

        # Performance report
        perf_report = self.profiler.generate_report(session_id)
        if perf_report:
            self.logger.info("=" * 60)
            self.logger.info("Performance Report")
            self.logger.info("=" * 60)
            self.logger.info(f"Total Duration: {perf_report.total_duration_ms:.2f}ms")
            self.logger.info(f"Bottlenecks: {len(perf_report.bottlenecks)}")
            for bottleneck in perf_report.bottlenecks[:3]:  # Top 3
                self.logger.info(
                    f"  - {bottleneck.name}: {bottleneck.duration_ms:.2f}ms "
                    f"({bottleneck.percentage:.1f}%)"
                )

        # Cost report
        cost_summary = self.cost_tracker.get_summary(session_id=session_id)
        self.logger.info("=" * 60)
        self.logger.info("Cost Report")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Cost: ${cost_summary.total_cost:.4f}")
        self.logger.info(f"Total Tokens: {cost_summary.total_tokens:,}")
        self.logger.info(f"Total Requests: {cost_summary.total_requests}")

        # Session analytics
        session_analytics = self.analytics.get_session_analytics(session_id)
        if session_analytics:
            self.logger.info("=" * 60)
            self.logger.info("Session Analytics")
            self.logger.info("=" * 60)
            self.logger.info(f"Phases Completed: {len(session_analytics.phases_completed)}")
            self.logger.info(f"Quality Gates Passed: {session_analytics.quality_gates_passed}")
            self.logger.info(f"Success: {session_analytics.success}")


# Global instance for easy import
_monitored_engine: Optional[MonitoredBMADEngine] = None


def get_monitored_engine() -> MonitoredBMADEngine:
    """모니터링 통합 BMAD Engine 인스턴스 반환"""
    global _monitored_engine
    if _monitored_engine is None:
        _monitored_engine = MonitoredBMADEngine()
    return _monitored_engine
