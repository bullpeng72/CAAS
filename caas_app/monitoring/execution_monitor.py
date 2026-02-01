"""
Real-time Execution Monitor

BMAD 파이프라인 실행을 실시간으로 모니터링하고 추적하는 시스템
"""

from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from collections import defaultdict

from caas_framework.utils.logger import get_logger

logger = get_logger("execution_monitor")


class ExecutionEventType(str, Enum):
    """실행 이벤트 타입"""
    PIPELINE_START = "pipeline_start"
    PIPELINE_END = "pipeline_end"
    PHASE_START = "phase_start"
    PHASE_END = "phase_end"
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    TASK_START = "task_start"
    TASK_END = "task_end"
    QUALITY_GATE_CHECK = "quality_gate_check"
    ERROR = "error"
    WARNING = "warning"
    METRIC_UPDATE = "metric_update"


class ExecutionStatus(str, Enum):
    """실행 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionEvent(BaseModel):
    """실행 이벤트"""
    event_type: ExecutionEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    phase: Optional[str] = None
    component: Optional[str] = None  # agent_id, task_id 등
    status: Optional[ExecutionStatus] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None


class ExecutionSession(BaseModel):
    """실행 세션"""
    session_id: str
    pipeline_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_phase: Optional[str] = None
    events: List[ExecutionEvent] = []
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error_count: int = 0
    warning_count: int = 0


class ExecutionMonitor:
    """
    실시간 실행 모니터

    BMAD 파이프라인의 실행을 실시간으로 추적하고 모니터링합니다.
    """

    def __init__(self):
        self.logger = logger
        self.sessions: Dict[str, ExecutionSession] = {}
        self.event_listeners: List[Callable] = []
        self._phase_start_times: Dict[str, datetime] = {}
        self._component_start_times: Dict[str, datetime] = {}

    def create_session(self, session_id: str, pipeline_name: str) -> ExecutionSession:
        """새로운 실행 세션을 생성합니다"""
        session = ExecutionSession(
            session_id=session_id,
            pipeline_name=pipeline_name,
            start_time=datetime.utcnow(),
            status=ExecutionStatus.PENDING,
        )
        self.sessions[session_id] = session
        self.logger.info(f"Session created: {session_id} ({pipeline_name})")

        # PIPELINE_START 이벤트 발행
        self.emit_event(
            session_id=session_id,
            event_type=ExecutionEventType.PIPELINE_START,
            message=f"Pipeline '{pipeline_name}' started",
        )

        return session

    def get_session(self, session_id: str) -> Optional[ExecutionSession]:
        """세션을 조회합니다"""
        return self.sessions.get(session_id)

    def emit_event(
        self,
        session_id: str,
        event_type: ExecutionEventType,
        phase: Optional[str] = None,
        component: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        message: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        """이벤트를 발행합니다"""
        session = self.sessions.get(session_id)
        if not session:
            self.logger.warning(f"Session not found: {session_id}")
            return

        # Duration 계산
        duration_ms = None
        if event_type == ExecutionEventType.PHASE_END:
            key = f"{session_id}:{phase}"
            if key in self._phase_start_times:
                duration = datetime.utcnow() - self._phase_start_times[key]
                duration_ms = duration.total_seconds() * 1000
                del self._phase_start_times[key]

        elif event_type in [ExecutionEventType.AGENT_END, ExecutionEventType.TASK_END]:
            key = f"{session_id}:{component}"
            if key in self._component_start_times:
                duration = datetime.utcnow() - self._component_start_times[key]
                duration_ms = duration.total_seconds() * 1000
                del self._component_start_times[key]

        # 이벤트 생성
        event = ExecutionEvent(
            event_type=event_type,
            phase=phase,
            component=component,
            status=status,
            message=message,
            data=data,
            duration_ms=duration_ms,
            error=error,
        )

        # 세션에 이벤트 추가
        session.events.append(event)

        # 세션 상태 업데이트
        if event_type == ExecutionEventType.PHASE_START:
            session.current_phase = phase
            self._phase_start_times[f"{session_id}:{phase}"] = datetime.utcnow()

        elif event_type == ExecutionEventType.AGENT_START:
            self._component_start_times[f"{session_id}:{component}"] = datetime.utcnow()

        elif event_type == ExecutionEventType.TASK_START:
            self._component_start_times[f"{session_id}:{component}"] = datetime.utcnow()

        elif event_type == ExecutionEventType.ERROR:
            session.error_count += 1

        elif event_type == ExecutionEventType.WARNING:
            session.warning_count += 1

        elif event_type == ExecutionEventType.PIPELINE_END:
            session.end_time = datetime.utcnow()
            session.status = status or ExecutionStatus.COMPLETED

        # 리스너에게 이벤트 전달
        self._notify_listeners(session_id, event)

        # 로깅
        log_msg = f"[{session_id}] {event_type}"
        if phase:
            log_msg += f" | Phase: {phase}"
        if component:
            log_msg += f" | Component: {component}"
        if message:
            log_msg += f" | {message}"

        if event_type == ExecutionEventType.ERROR:
            self.logger.error(log_msg)
        elif event_type == ExecutionEventType.WARNING:
            self.logger.warning(log_msg)
        else:
            self.logger.info(log_msg)

    def update_metrics(
        self,
        session_id: str,
        metrics: Dict[str, Any],
    ):
        """메트릭을 업데이트합니다"""
        session = self.sessions.get(session_id)
        if not session:
            return

        session.metrics.update(metrics)

        # METRIC_UPDATE 이벤트 발행
        self.emit_event(
            session_id=session_id,
            event_type=ExecutionEventType.METRIC_UPDATE,
            data=metrics,
        )

    def register_listener(self, listener: Callable[[str, ExecutionEvent], None]):
        """이벤트 리스너를 등록합니다"""
        self.event_listeners.append(listener)
        self.logger.info(f"Event listener registered: {listener.__name__}")

    def _notify_listeners(self, session_id: str, event: ExecutionEvent):
        """등록된 리스너에게 이벤트를 전달합니다"""
        for listener in self.event_listeners:
            try:
                listener(session_id, event)
            except Exception as e:
                self.logger.error(f"Error in event listener: {e}")

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 요약 정보를 반환합니다"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        # 전체 실행 시간
        if session.end_time:
            duration = (session.end_time - session.start_time).total_seconds()
        else:
            duration = (datetime.utcnow() - session.start_time).total_seconds()

        # Phase별 통계
        phase_stats = defaultdict(lambda: {"count": 0, "duration_ms": 0.0})
        for event in session.events:
            if event.phase and event.duration_ms:
                phase_stats[event.phase]["count"] += 1
                phase_stats[event.phase]["duration_ms"] += event.duration_ms

        # Component별 통계
        component_stats = defaultdict(lambda: {"count": 0, "duration_ms": 0.0, "status": None})
        for event in session.events:
            if event.component:
                if event.event_type in [ExecutionEventType.AGENT_END, ExecutionEventType.TASK_END]:
                    component_stats[event.component]["count"] += 1
                    if event.duration_ms:
                        component_stats[event.component]["duration_ms"] += event.duration_ms
                    component_stats[event.component]["status"] = event.status

        return {
            "session_id": session_id,
            "pipeline_name": session.pipeline_name,
            "status": session.status,
            "current_phase": session.current_phase,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "duration_seconds": round(duration, 2),
            "total_events": len(session.events),
            "error_count": session.error_count,
            "warning_count": session.warning_count,
            "metrics": session.metrics,
            "phase_stats": dict(phase_stats),
            "component_stats": dict(component_stats),
        }

    def get_recent_events(
        self,
        session_id: str,
        limit: int = 10,
        event_types: Optional[List[ExecutionEventType]] = None,
    ) -> List[ExecutionEvent]:
        """최근 이벤트를 조회합니다"""
        session = self.sessions.get(session_id)
        if not session:
            return []

        events = session.events

        # 이벤트 타입 필터링
        if event_types:
            events = [e for e in events if e.event_type in event_types]

        # 최근 N개 반환
        return events[-limit:]

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """모든 세션의 요약 정보를 반환합니다"""
        return [
            self.get_session_summary(session_id)
            for session_id in self.sessions.keys()
        ]

    def clear_completed_sessions(self, keep_recent: int = 10):
        """완료된 세션을 정리합니다 (최근 N개는 유지)"""
        completed_sessions = [
            (sid, s) for sid, s in self.sessions.items()
            if s.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]
        ]

        # 시작 시간 기준 정렬
        completed_sessions.sort(key=lambda x: x[1].start_time, reverse=True)

        # 오래된 세션 삭제
        for session_id, _ in completed_sessions[keep_recent:]:
            del self.sessions[session_id]
            self.logger.info(f"Session cleared: {session_id}")


# 전역 모니터 인스턴스
_global_monitor: Optional[ExecutionMonitor] = None


def get_monitor() -> ExecutionMonitor:
    """전역 모니터 인스턴스를 반환합니다"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = ExecutionMonitor()
    return _global_monitor


# Context Manager for easy monitoring
class MonitoredExecution:
    """
    실행 모니터링을 위한 Context Manager

    Usage:
        with MonitoredExecution(session_id, "discovery", component="requirement_analyst"):
            # Do work
            pass
    """

    def __init__(
        self,
        session_id: str,
        phase: Optional[str] = None,
        component: Optional[str] = None,
        component_type: str = "agent",  # "agent" or "task"
    ):
        self.monitor = get_monitor()
        self.session_id = session_id
        self.phase = phase
        self.component = component
        self.component_type = component_type
        self.error_occurred = False

    def __enter__(self):
        """시작 이벤트 발행"""
        if self.phase and not self.component:
            self.monitor.emit_event(
                session_id=self.session_id,
                event_type=ExecutionEventType.PHASE_START,
                phase=self.phase,
                status=ExecutionStatus.RUNNING,
            )
        elif self.component:
            event_type = (
                ExecutionEventType.AGENT_START
                if self.component_type == "agent"
                else ExecutionEventType.TASK_START
            )
            self.monitor.emit_event(
                session_id=self.session_id,
                event_type=event_type,
                phase=self.phase,
                component=self.component,
                status=ExecutionStatus.RUNNING,
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """종료 이벤트 발행"""
        if exc_type:
            # 에러 발생
            self.error_occurred = True
            self.monitor.emit_event(
                session_id=self.session_id,
                event_type=ExecutionEventType.ERROR,
                phase=self.phase,
                component=self.component,
                status=ExecutionStatus.FAILED,
                error=str(exc_val),
            )

        # 종료 이벤트
        status = ExecutionStatus.FAILED if self.error_occurred else ExecutionStatus.COMPLETED

        if self.phase and not self.component:
            self.monitor.emit_event(
                session_id=self.session_id,
                event_type=ExecutionEventType.PHASE_END,
                phase=self.phase,
                status=status,
            )
        elif self.component:
            event_type = (
                ExecutionEventType.AGENT_END
                if self.component_type == "agent"
                else ExecutionEventType.TASK_END
            )
            self.monitor.emit_event(
                session_id=self.session_id,
                event_type=event_type,
                phase=self.phase,
                component=self.component,
                status=status,
            )

        # 예외를 다시 발생시키지 않음 (False 반환)
        return False
