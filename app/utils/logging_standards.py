"""
Logging Standards

표준화된 로그 메시지 포맷 및 구조화된 로깅
"""

import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
from collections import defaultdict
import functools

from app.utils.logger import get_logger

logger = get_logger("utils.logging_standards")


class LogCategory(Enum):
    """로그 카테고리"""
    SYSTEM = "system"           # 시스템 이벤트
    USER_ACTION = "user_action" # 사용자 액션
    DATA = "data"               # 데이터 처리
    API = "api"                 # API 호출
    WORKFLOW = "workflow"       # 워크플로우
    SECURITY = "security"       # 보안
    PERFORMANCE = "performance" # 성능
    ERROR = "error"             # 에러


class LogEmoji:
    """로그 레벨별 이모지"""
    DEBUG = "🔍"
    INFO = "ℹ️"
    WARNING = "⚠️"
    ERROR = "❌"
    CRITICAL = "🔥"
    SUCCESS = "✅"
    START = "🚀"
    END = "🏁"
    PROGRESS = "⏳"
    SECURITY = "🔒"
    PERFORMANCE = "⚡"
    DATA = "📊"
    API = "🌐"
    USER = "👤"


class StandardLogger:
    """
    표준화된 로깅 인터페이스

    일관된 로그 메시지 포맷을 제공합니다.
    """

    def __init__(self, name: str, category: Optional[LogCategory] = None):
        """
        표준 로거 초기화

        Args:
            name: 로거 이름
            category: 로그 카테고리
        """
        self.logger = get_logger(name)
        self.category = category or LogCategory.SYSTEM
        self.context: Dict[str, Any] = {}

    def set_context(self, **kwargs):
        """
        로그 컨텍스트 설정

        Args:
            **kwargs: 컨텍스트 키-값 쌍
        """
        self.context.update(kwargs)

    def clear_context(self):
        """컨텍스트 초기화"""
        self.context = {}

    def _format_message(
        self,
        message: str,
        emoji: str = "",
        category: Optional[LogCategory] = None,
        **extra_context
    ) -> str:
        """
        메시지 포맷팅

        Args:
            message: 원본 메시지
            emoji: 이모지
            category: 카테고리
            **extra_context: 추가 컨텍스트

        Returns:
            포맷팅된 메시지
        """
        # 카테고리
        cat = category or self.category
        cat_tag = f"[{cat.value.upper()}]"

        # 컨텍스트 병합
        full_context = {**self.context, **extra_context}

        # 컨텍스트 문자열
        if full_context:
            context_str = " | ".join(f"{k}={v}" for k, v in full_context.items())
            context_part = f" ({context_str})"
        else:
            context_part = ""

        # 최종 메시지
        return f"{emoji} {cat_tag} {message}{context_part}"

    def debug(self, message: str, **context):
        """디버그 로그"""
        formatted = self._format_message(message, LogEmoji.DEBUG, **context)
        self.logger.debug(formatted)

    def info(self, message: str, **context):
        """정보 로그"""
        formatted = self._format_message(message, LogEmoji.INFO, **context)
        self.logger.info(formatted)

    def warning(self, message: str, **context):
        """경고 로그"""
        formatted = self._format_message(message, LogEmoji.WARNING, **context)
        self.logger.warning(formatted)

    def error(self, message: str, exc_info: bool = False, **context):
        """에러 로그"""
        formatted = self._format_message(message, LogEmoji.ERROR, **context)
        self.logger.error(formatted, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False, **context):
        """치명적 에러 로그"""
        formatted = self._format_message(message, LogEmoji.CRITICAL, **context)
        self.logger.critical(formatted, exc_info=exc_info)

    def success(self, message: str, **context):
        """성공 로그"""
        formatted = self._format_message(message, LogEmoji.SUCCESS, **context)
        self.logger.info(formatted)

    def start(self, operation: str, **context):
        """작업 시작 로그"""
        formatted = self._format_message(f"{operation} 시작", LogEmoji.START, **context)
        self.logger.info(formatted)

    def end(self, operation: str, **context):
        """작업 종료 로그"""
        formatted = self._format_message(f"{operation} 완료", LogEmoji.END, **context)
        self.logger.info(formatted)

    def progress(self, message: str, **context):
        """진행 상황 로그"""
        formatted = self._format_message(message, LogEmoji.PROGRESS, **context)
        self.logger.info(formatted)

    def security(self, message: str, **context):
        """보안 관련 로그"""
        formatted = self._format_message(
            message, LogEmoji.SECURITY, category=LogCategory.SECURITY, **context
        )
        self.logger.warning(formatted)

    def performance(self, message: str, duration_ms: Optional[float] = None, **context):
        """성능 관련 로그"""
        if duration_ms is not None:
            context["duration_ms"] = f"{duration_ms:.2f}"

        formatted = self._format_message(
            message, LogEmoji.PERFORMANCE, category=LogCategory.PERFORMANCE, **context
        )
        self.logger.info(formatted)

    def data(self, message: str, **context):
        """데이터 처리 로그"""
        formatted = self._format_message(
            message, LogEmoji.DATA, category=LogCategory.DATA, **context
        )
        self.logger.info(formatted)

    def api(self, message: str, **context):
        """API 호출 로그"""
        formatted = self._format_message(
            message, LogEmoji.API, category=LogCategory.API, **context
        )
        self.logger.info(formatted)

    def user_action(self, message: str, **context):
        """사용자 액션 로그"""
        formatted = self._format_message(
            message, LogEmoji.USER, category=LogCategory.USER_ACTION, **context
        )
        self.logger.info(formatted)


class LogCollector:
    """
    로그 수집기

    메모리에 로그를 수집하고 분석합니다.
    """

    def __init__(self, max_logs: int = 1000):
        """
        로그 수집기 초기화

        Args:
            max_logs: 최대 저장 로그 수
        """
        self.max_logs = max_logs
        self.logs: List[Dict[str, Any]] = []
        self.stats = defaultdict(int)

    def add_log(
        self,
        level: str,
        message: str,
        category: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        로그 추가

        Args:
            level: 로그 레벨
            message: 메시지
            category: 카테고리
            context: 컨텍스트
        """
        log_entry = {
            "timestamp": datetime.now(),
            "level": level,
            "message": message,
            "category": category,
            "context": context or {}
        }

        self.logs.append(log_entry)

        # 통계 업데이트
        self.stats[f"level_{level}"] += 1
        if category:
            self.stats[f"category_{category}"] += 1

        # 크기 제한
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]

    def get_logs(
        self,
        level: Optional[str] = None,
        category: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        로그 조회

        Args:
            level: 필터링할 레벨
            category: 필터링할 카테고리
            limit: 조회할 최대 개수

        Returns:
            로그 항목 리스트
        """
        filtered = self.logs

        # 레벨 필터
        if level:
            filtered = [log for log in filtered if log["level"] == level]

        # 카테고리 필터
        if category:
            filtered = [log for log in filtered if log["category"] == category]

        # 제한
        if limit:
            filtered = filtered[-limit:]

        return filtered

    def get_stats(self) -> Dict[str, Any]:
        """
        통계 조회

        Returns:
            통계 정보
        """
        return {
            "total_logs": len(self.logs),
            "by_level": {
                level.replace("level_", ""): count
                for level, count in self.stats.items()
                if level.startswith("level_")
            },
            "by_category": {
                cat.replace("category_", ""): count
                for cat, count in self.stats.items()
                if cat.startswith("category_")
            }
        }

    def clear(self):
        """수집된 로그 초기화"""
        self.logs = []
        self.stats = defaultdict(int)


class LogFilter(logging.Filter):
    """
    커스텀 로그 필터

    특정 조건에 맞는 로그만 통과시킵니다.
    """

    def __init__(
        self,
        min_level: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None
    ):
        """
        로그 필터 초기화

        Args:
            min_level: 최소 레벨
            keywords: 포함해야 할 키워드
            exclude_keywords: 제외할 키워드
        """
        super().__init__()
        self.min_level = min_level
        self.keywords = keywords or []
        self.exclude_keywords = exclude_keywords or []

    def filter(self, record: logging.LogRecord) -> bool:
        """
        로그 레코드 필터링

        Args:
            record: 로그 레코드

        Returns:
            통과 여부
        """
        # 레벨 필터
        if self.min_level:
            min_level_num = getattr(logging, self.min_level.upper())
            if record.levelno < min_level_num:
                return False

        message = record.getMessage()

        # 키워드 필터
        if self.keywords:
            if not any(kw in message for kw in self.keywords):
                return False

        # 제외 키워드 필터
        if self.exclude_keywords:
            if any(kw in message for kw in self.exclude_keywords):
                return False

        return True


def log_execution(
    logger_name: Optional[str] = None,
    log_args: bool = False,
    log_result: bool = False,
    log_duration: bool = True
):
    """
    함수 실행 로깅 데코레이터

    Args:
        logger_name: 로거 이름 (None이면 함수 모듈명 사용)
        log_args: 인자 로깅 여부
        log_result: 결과 로깅 여부
        log_duration: 실행 시간 로깅 여부

    Example:
        ```python
        @log_execution(log_duration=True)
        def process_data(data):
            # 처리 로직
            pass
        ```
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 로거 설정
            if logger_name:
                func_logger = get_logger(logger_name)
            else:
                func_logger = get_logger(func.__module__)

            # 시작 로그
            func_name = func.__name__
            log_parts = [f"🚀 [{func_name}] 시작"]

            if log_args and (args or kwargs):
                log_parts.append(f"args={args}, kwargs={kwargs}")

            func_logger.info(" | ".join(log_parts))

            # 실행
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)

                # 성공 로그
                end_time = datetime.now()
                duration_ms = (end_time - start_time).total_seconds() * 1000

                success_parts = [f"✅ [{func_name}] 완료"]

                if log_duration:
                    success_parts.append(f"duration={duration_ms:.2f}ms")

                if log_result:
                    success_parts.append(f"result={result}")

                func_logger.info(" | ".join(success_parts))

                return result

            except Exception as e:
                # 에러 로그
                end_time = datetime.now()
                duration_ms = (end_time - start_time).total_seconds() * 1000

                func_logger.error(
                    f"❌ [{func_name}] 실패 | error={type(e).__name__}: {e} | duration={duration_ms:.2f}ms",
                    exc_info=True
                )
                raise

        return wrapper
    return decorator


class StructuredLogger:
    """
    구조화된 로깅

    JSON 형태로 로그를 기록합니다.
    """

    def __init__(self, name: str):
        """
        구조화된 로거 초기화

        Args:
            name: 로거 이름
        """
        self.logger = get_logger(name)
        self.base_context: Dict[str, Any] = {}

    def set_base_context(self, **kwargs):
        """기본 컨텍스트 설정"""
        self.base_context.update(kwargs)

    def log(
        self,
        level: str,
        event: str,
        message: str,
        **context
    ):
        """
        구조화된 로그 기록

        Args:
            level: 로그 레벨
            event: 이벤트 이름
            message: 메시지
            **context: 추가 컨텍스트
        """
        import json

        # 컨텍스트 병합
        full_context = {
            **self.base_context,
            **context,
            "event": event,
            "timestamp": datetime.now().isoformat()
        }

        # JSON 형태로 로그
        log_data = {
            "message": message,
            "context": full_context
        }

        log_message = json.dumps(log_data, ensure_ascii=False)

        # 레벨에 따라 로깅
        log_func = getattr(self.logger, level.lower())
        log_func(log_message)


# 싱글톤 로그 수집기
_global_log_collector = None


def get_log_collector() -> LogCollector:
    """글로벌 로그 수집기 반환"""
    global _global_log_collector
    if _global_log_collector is None:
        _global_log_collector = LogCollector()
    return _global_log_collector


# 편의 함수들
def get_standard_logger(name: str, category: Optional[LogCategory] = None) -> StandardLogger:
    """표준 로거 생성 (편의 함수)"""
    return StandardLogger(name, category)


def create_log_filter(
    min_level: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    exclude_keywords: Optional[List[str]] = None
) -> LogFilter:
    """로그 필터 생성 (편의 함수)"""
    return LogFilter(min_level, keywords, exclude_keywords)
