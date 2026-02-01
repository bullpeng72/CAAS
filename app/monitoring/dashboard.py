"""
Quality Metrics Dashboard

BMAD 파이프라인의 실행 상태와 품질 메트릭을 시각화하는 대시보드
"""

import streamlit as st
from typing import Dict, Any
import pandas as pd

from app.monitoring.execution_monitor import (
    get_monitor,
    ExecutionEventType,
)
from app.utils.logger import get_logger

logger = get_logger("dashboard")


class QualityMetricsDashboard:
    """
    품질 메트릭 대시보드

    Streamlit 기반으로 실시간 실행 상태와 품질 메트릭을 시각화합니다.
    """

    def __init__(self):
        self.monitor = get_monitor()

    def render(self):
        """대시보드를 렌더링합니다"""
        st.set_page_config(
            page_title="CAAS Quality Dashboard",
            page_icon="📊",
            layout="wide",
        )

        st.title("📊 CAAS Quality Metrics Dashboard")
        st.markdown("**CrewAI-as-a-Service** - Real-time Pipeline Monitoring")

        # 사이드바: 세션 선택
        with st.sidebar:
            st.header("🔍 Sessions")
            sessions = self.monitor.get_all_sessions()

            if not sessions:
                st.info("No active sessions")
                return

            # 세션 목록
            session_options = [
                f"{s['session_id']} - {s['pipeline_name']} ({s['status']})"
                for s in sessions
            ]
            selected_idx = st.selectbox(
                "Select Session",
                range(len(session_options)),
                format_func=lambda i: session_options[i],
            )
            selected_session = sessions[selected_idx]
            session_id = selected_session["session_id"]

            # 자동 새로고침
            auto_refresh = st.checkbox("Auto-refresh (5s)", value=True)
            if auto_refresh:
                st.rerun()

        # 메인 영역
        self._render_session_overview(selected_session)

        col1, col2 = st.columns(2)

        with col1:
            self._render_phase_progress(session_id, selected_session)
            self._render_quality_metrics(selected_session)

        with col2:
            self._render_component_stats(selected_session)
            self._render_errors_warnings(session_id)

        self._render_event_timeline(session_id)

    def _render_session_overview(self, session: Dict[str, Any]):
        """세션 개요를 렌더링합니다"""
        st.header("📋 Session Overview")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            status_emoji = {
                "pending": "⏳",
                "running": "🟢",
                "completed": "✅",
                "failed": "❌",
            }
            emoji = status_emoji.get(session["status"], "❓")
            st.metric("Status", f"{emoji} {session['status'].upper()}")

        with col2:
            st.metric("Current Phase", session["current_phase"] or "N/A")

        with col3:
            st.metric("Duration", f"{session['duration_seconds']}s")

        with col4:
            st.metric("Total Events", session["total_events"])

        # 에러/경고 표시
        if session["error_count"] > 0 or session["warning_count"] > 0:
            col1, col2 = st.columns(2)
            with col1:
                if session["error_count"] > 0:
                    st.error(f"🚨 {session['error_count']} Errors")
            with col2:
                if session["warning_count"] > 0:
                    st.warning(f"⚠️ {session['warning_count']} Warnings")

    def _render_phase_progress(self, session_id: str, session: Dict[str, Any]):
        """Phase 진행 상황을 렌더링합니다"""
        st.subheader("🔄 Phase Progress")

        phase_stats = session.get("phase_stats", {})

        if not phase_stats:
            st.info("No phase data available")
            return

        # Phase별 실행 시간
        phases = list(phase_stats.keys())
        durations = [phase_stats[p]["duration_ms"] / 1000 for p in phases]

        # 바 차트
        df = pd.DataFrame({
            "Phase": phases,
            "Duration (s)": durations,
        })
        st.bar_chart(df.set_index("Phase"))

        # Phase 상세 정보
        for phase, stats in phase_stats.items():
            with st.expander(f"📌 {phase}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Execution Count", stats["count"])
                with col2:
                    st.metric("Total Duration", f"{stats['duration_ms'] / 1000:.2f}s")

    def _render_quality_metrics(self, session: Dict[str, Any]):
        """품질 메트릭을 렌더링합니다"""
        st.subheader("📈 Quality Metrics")

        metrics = session.get("metrics", {})

        if not metrics:
            st.info("No quality metrics available")
            return

        # 품질 점수 표시
        quality_keys = [
            "completeness_score",
            "clarity_score",
            "consistency_score",
            "feasibility_score",
            "confidence_score",
            "overall_quality",
        ]

        cols = st.columns(3)
        idx = 0
        for key in quality_keys:
            if key in metrics:
                with cols[idx % 3]:
                    score = metrics[key]
                    # 색상 결정
                    if score >= 0.8:
                        color = "🟢"
                    elif score >= 0.6:
                        color = "🟡"
                    else:
                        color = "🔴"

                    label = key.replace("_", " ").title()
                    st.metric(label, f"{color} {score:.2%}")
                    idx += 1

        # 기타 메트릭
        other_metrics = {k: v for k, v in metrics.items() if k not in quality_keys}
        if other_metrics:
            with st.expander("Other Metrics"):
                st.json(other_metrics)

    def _render_component_stats(self, session: Dict[str, Any]):
        """컴포넌트 통계를 렌더링합니다"""
        st.subheader("🤖 Agent & Task Stats")

        component_stats = session.get("component_stats", {})

        if not component_stats:
            st.info("No component data available")
            return

        # 컴포넌트 실행 시간 Top 5
        sorted_components = sorted(
            component_stats.items(),
            key=lambda x: x[1]["duration_ms"],
            reverse=True,
        )[:5]

        st.markdown("**⏱️ Top 5 by Duration**")
        for component, stats in sorted_components:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.text(component)
            with col2:
                status = stats.get("status", "unknown")
                status_emoji = {
                    "completed": "✅",
                    "failed": "❌",
                    "running": "🔄",
                }
                st.text(status_emoji.get(status, "❓"))
            with col3:
                st.text(f"{stats['duration_ms'] / 1000:.2f}s")

        # 모든 컴포넌트 상세
        with st.expander("All Components"):
            for component, stats in component_stats.items():
                st.markdown(f"**{component}**")
                st.text(f"  Status: {stats.get('status', 'N/A')}")
                st.text(f"  Duration: {stats['duration_ms'] / 1000:.2f}s")
                st.divider()

    def _render_errors_warnings(self, session_id: str):
        """에러와 경고를 렌더링합니다"""
        st.subheader("🚨 Errors & Warnings")

        # 에러 이벤트
        error_events = self.monitor.get_recent_events(
            session_id=session_id,
            limit=20,
            event_types=[ExecutionEventType.ERROR, ExecutionEventType.WARNING],
        )

        if not error_events:
            st.success("✅ No errors or warnings")
            return

        for event in reversed(error_events):  # 최신 순
            if event.event_type == ExecutionEventType.ERROR:
                with st.expander(f"🔴 ERROR - {event.component or event.phase or 'Unknown'}"):
                    st.text(f"Time: {event.timestamp.strftime('%H:%M:%S')}")
                    st.text(f"Message: {event.message or 'N/A'}")
                    if event.error:
                        st.code(event.error, language="text")
            else:
                with st.expander(f"🟡 WARNING - {event.component or event.phase or 'Unknown'}"):
                    st.text(f"Time: {event.timestamp.strftime('%H:%M:%S')}")
                    st.text(f"Message: {event.message or 'N/A'}")

    def _render_event_timeline(self, session_id: str):
        """이벤트 타임라인을 렌더링합니다"""
        st.header("📅 Event Timeline")

        recent_events = self.monitor.get_recent_events(session_id=session_id, limit=50)

        if not recent_events:
            st.info("No events available")
            return

        # 이벤트 타입 필터
        event_types = st.multiselect(
            "Filter by Event Type",
            options=[e.value for e in ExecutionEventType],
            default=[
                ExecutionEventType.PHASE_START.value,
                ExecutionEventType.PHASE_END.value,
                ExecutionEventType.ERROR.value,
            ],
        )

        # 필터링
        filtered_events = [
            e for e in recent_events
            if e.event_type.value in event_types
        ]

        # 테이블 형식으로 표시
        event_data = []
        for event in reversed(filtered_events):  # 최신 순
            event_data.append({
                "Time": event.timestamp.strftime("%H:%M:%S"),
                "Type": event.event_type.value,
                "Phase": event.phase or "-",
                "Component": event.component or "-",
                "Status": event.status.value if event.status else "-",
                "Duration (s)": f"{event.duration_ms / 1000:.2f}" if event.duration_ms else "-",
                "Message": event.message or "-",
            })

        if event_data:
            df = pd.DataFrame(event_data)
            st.dataframe(df, width='stretch', hide_index=True)
        else:
            st.info("No events match the filter")


def run_dashboard():
    """대시보드를 실행합니다"""
    dashboard = QualityMetricsDashboard()
    dashboard.render()


if __name__ == "__main__":
    run_dashboard()
