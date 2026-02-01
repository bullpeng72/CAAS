"""
Performance Profiler

워크플로우 성능 측정 및 병목 지점 식별
"""

import time
import psutil
import os
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from contextlib import contextmanager
from pydantic import BaseModel, Field
from collections import defaultdict

from app.utils.logger import get_logger

logger = get_logger("performance_profiler")


class PerformanceMetrics(BaseModel):
    """성능 메트릭"""
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None

    # CPU & Memory
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    memory_percent: Optional[float] = None

    # Counts
    call_count: int = 1

    # Children
    children: List["PerformanceMetrics"] = Field(default=[])


class BottleneckReport(BaseModel):
    """병목 지점 리포트"""
    name: str
    duration_ms: float
    percentage: float  # 전체 시간 대비 비율
    call_count: int
    avg_duration_ms: float
    suggestion: Optional[str] = None


class ProfileReport(BaseModel):
    """전체 프로파일 리포트"""
    session_id: str
    total_duration_ms: float
    metrics: List[PerformanceMetrics]
    bottlenecks: List[BottleneckReport]
    summary: Dict[str, Any]


class PerformanceProfiler:
    """
    Performance Profiler

    워크플로우 및 함수 실행의 성능을 측정합니다.
    """

    def __init__(self):
        self.logger = logger
        self.metrics_stack: List[PerformanceMetrics] = []
        self.completed_metrics: Dict[str, List[PerformanceMetrics]] = defaultdict(list)
        self.process = psutil.Process(os.getpid())

    @contextmanager
    def profile(self, name: str, session_id: str = "default"):
        """
        프로파일링 컨텍스트 매니저

        Usage:
            with profiler.profile("my_function"):
                # code to profile
                pass
        """
        metric = PerformanceMetrics(
            name=name,
            start_time=datetime.utcnow(),
        )

        # CPU & Memory 측정 시작
        cpu_before = self.process.cpu_percent()
        mem_before = self.process.memory_info().rss / 1024 / 1024  # MB

        # 스택에 추가
        self.metrics_stack.append(metric)

        start = time.time()

        try:
            yield metric
        finally:
            # 종료 시간 및 duration 계산
            end = time.time()
            metric.end_time = datetime.utcnow()
            metric.duration_ms = (end - start) * 1000

            # CPU & Memory 측정 종료
            metric.cpu_percent = self.process.cpu_percent() - cpu_before
            mem_after = self.process.memory_info().rss / 1024 / 1024
            metric.memory_mb = mem_after - mem_before
            metric.memory_percent = self.process.memory_percent()

            # 스택에서 제거
            self.metrics_stack.pop()

            # 부모가 있으면 부모의 children에 추가
            if self.metrics_stack:
                self.metrics_stack[-1].children.append(metric)
            else:
                # 최상위 메트릭
                self.completed_metrics[session_id].append(metric)

            self.logger.debug(f"Profile: {name} took {metric.duration_ms:.2f}ms")

    def get_metrics(self, session_id: str) -> List[PerformanceMetrics]:
        """세션의 메트릭 조회"""
        return self.completed_metrics.get(session_id, [])

    def clear_metrics(self, session_id: str):
        """세션의 메트릭 초기화"""
        if session_id in self.completed_metrics:
            del self.completed_metrics[session_id]

    def generate_report(self, session_id: str) -> Optional[ProfileReport]:
        """
        프로파일 리포트 생성

        Args:
            session_id: 세션 ID

        Returns:
            ProfileReport: 프로파일 리포트
        """
        metrics = self.get_metrics(session_id)
        if not metrics:
            return None

        # 전체 실행 시간
        total_duration = sum(m.duration_ms or 0 for m in metrics)

        # 병목 지점 분석
        bottlenecks = self._analyze_bottlenecks(metrics, total_duration)

        # 요약 정보
        summary = {
            "total_duration_ms": total_duration,
            "total_metrics": len(metrics),
            "slowest_operation": max(metrics, key=lambda m: m.duration_ms or 0).name if metrics else None,
            "avg_duration_ms": total_duration / len(metrics) if metrics else 0,
        }

        return ProfileReport(
            session_id=session_id,
            total_duration_ms=total_duration,
            metrics=metrics,
            bottlenecks=bottlenecks,
            summary=summary,
        )

    def _analyze_bottlenecks(
        self,
        metrics: List[PerformanceMetrics],
        total_duration: float,
        threshold_percent: float = 10.0,
    ) -> List[BottleneckReport]:
        """
        병목 지점 분석

        Args:
            metrics: 메트릭 목록
            total_duration: 전체 실행 시간
            threshold_percent: 병목으로 간주할 비율 (%)

        Returns:
            List[BottleneckReport]: 병목 지점 목록
        """
        # 이름별로 집계
        aggregated = defaultdict(lambda: {"duration": 0.0, "count": 0})

        def collect_metrics(metrics_list):
            for metric in metrics_list:
                if metric.duration_ms:
                    aggregated[metric.name]["duration"] += metric.duration_ms
                    aggregated[metric.name]["count"] += 1
                # 재귀적으로 children도 수집
                if metric.children:
                    collect_metrics(metric.children)

        collect_metrics(metrics)

        # 병목 지점 찾기
        bottlenecks = []
        for name, data in aggregated.items():
            percentage = (data["duration"] / total_duration * 100) if total_duration > 0 else 0

            if percentage >= threshold_percent:
                suggestion = self._suggest_optimization(name, percentage, data["count"])

                bottlenecks.append(BottleneckReport(
                    name=name,
                    duration_ms=data["duration"],
                    percentage=percentage,
                    call_count=data["count"],
                    avg_duration_ms=data["duration"] / data["count"],
                    suggestion=suggestion,
                ))

        # 비율 내림차순 정렬
        bottlenecks.sort(key=lambda b: b.percentage, reverse=True)
        return bottlenecks

    def _suggest_optimization(self, name: str, percentage: float, count: int) -> str:
        """최적화 제안 생성"""
        suggestions = []

        if percentage > 50:
            suggestions.append(f"Major bottleneck ({percentage:.1f}% of total time)")

        if count > 10:
            suggestions.append(f"Called {count} times - consider caching or batching")

        if "llm" in name.lower() or "chain" in name.lower():
            suggestions.append("Consider using a faster model or reducing token count")

        if "database" in name.lower() or "db" in name.lower():
            suggestions.append("Optimize database queries or add indexes")

        if "api" in name.lower():
            suggestions.append("Consider request batching or caching API responses")

        return ". ".join(suggestions) if suggestions else "Monitor for further optimization opportunities"


# ========== Function Profiler Decorator ==========

def profile_function(name: Optional[str] = None, session_id: str = "default"):
    """
    함수 프로파일링 데코레이터

    Usage:
        @profile_function("my_function")
        def my_function():
            pass
    """
    def decorator(func: Callable):
        func_name = name or func.__name__

        def wrapper(*args, **kwargs):
            profiler = get_profiler()
            with profiler.profile(func_name, session_id):
                return func(*args, **kwargs)

        return wrapper
    return decorator


# ========== Memory Profiler ==========

class MemoryProfiler:
    """
    메모리 프로파일러

    메모리 사용량 추적 및 분석
    """

    def __init__(self):
        self.logger = logger
        self.process = psutil.Process(os.getpid())
        self.snapshots: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def take_snapshot(self, session_id: str, label: str = ""):
        """메모리 스냅샷"""
        memory_info = self.process.memory_info()

        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "label": label,
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": self.process.memory_percent(),
        }

        self.snapshots[session_id].append(snapshot)

    def get_snapshots(self, session_id: str) -> List[Dict[str, Any]]:
        """스냅샷 조회"""
        return self.snapshots.get(session_id, [])

    def get_memory_growth(self, session_id: str) -> float:
        """메모리 증가량 (MB)"""
        snapshots = self.get_snapshots(session_id)
        if len(snapshots) < 2:
            return 0.0

        return snapshots[-1]["rss_mb"] - snapshots[0]["rss_mb"]

    def detect_memory_leak(self, session_id: str, threshold_mb: float = 100.0) -> bool:
        """메모리 누수 감지"""
        growth = self.get_memory_growth(session_id)
        return growth > threshold_mb


# ========== Global Profiler Instance ==========

_global_profiler: Optional[PerformanceProfiler] = None
_global_memory_profiler: Optional[MemoryProfiler] = None


def get_profiler() -> PerformanceProfiler:
    """전역 Performance Profiler 반환"""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler()
    return _global_profiler


def get_memory_profiler() -> MemoryProfiler:
    """전역 Memory Profiler 반환"""
    global _global_memory_profiler
    if _global_memory_profiler is None:
        _global_memory_profiler = MemoryProfiler()
    return _global_memory_profiler
