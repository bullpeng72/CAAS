"""
CAAS Logging Utility

애플리케이션 전체에서 사용하는 로깅 설정을 관리합니다.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Rich는 선택적 의존성
try:
    from rich.console import Console
    from rich.logging import RichHandler
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


def setup_logger(
    name: str = "caas",
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """
    로거를 설정하고 반환합니다.
    
    Args:
        name: 로거 이름
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 로그 파일 경로 (선택사항)
    
    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
    # 설정 로드 (순환 import 방지)
    try:
        from app.utils.config import get_settings
        settings = get_settings()
        log_level = level or settings.app.log_level
        is_dev = settings.app.is_development
    except Exception:
        log_level = level or "INFO"
        is_dev = True
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # 기존 핸들러 제거
    logger.handlers.clear()

    # 부모 로거로의 전파 방지 (중복 로그 방지)
    logger.propagate = False
    
    # 핸들러 설정
    if RICH_AVAILABLE:
        # Rich 핸들러 (콘솔 출력)
        handler = RichHandler(
            console=console,
            show_time=True,
            show_path=is_dev,
            rich_tracebacks=True,
            tracebacks_show_locals=is_dev,
        )
        formatter = logging.Formatter("%(message)s", datefmt="[%X]")
    else:
        # 기본 스트림 핸들러
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    handler.setLevel(getattr(logging, log_level.upper()))
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # 파일 핸들러 (선택사항)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    지정된 이름의 로거를 반환합니다.
    
    Args:
        name: 로거 이름 (일반적으로 모듈명)
    
    Returns:
        logging.Logger: 로거 인스턴스
    """
    return setup_logger(f"caas.{name}")


class LoggerMixin:
    """로거를 제공하는 믹스인 클래스"""

    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger

    # 편의 메서드들 (표준 로깅 패턴)
    def log_debug(self, message: str, **context):
        """디버그 로그"""
        self.logger.debug(f"🔍 {message}" + (f" | {context}" if context else ""))

    def log_info(self, message: str, **context):
        """정보 로그"""
        self.logger.info(f"ℹ️ {message}" + (f" | {context}" if context else ""))

    def log_warning(self, message: str, **context):
        """경고 로그"""
        self.logger.warning(f"⚠️ {message}" + (f" | {context}" if context else ""))

    def log_error(self, message: str, exc_info: bool = False, **context):
        """에러 로그"""
        self.logger.error(f"❌ {message}" + (f" | {context}" if context else ""), exc_info=exc_info)

    def log_success(self, message: str, **context):
        """성공 로그"""
        self.logger.info(f"✅ {message}" + (f" | {context}" if context else ""))


class StandardLoggerMixin:
    """
    표준화된 로거를 제공하는 믹스인 클래스

    logging_standards 모듈의 StandardLogger를 사용합니다.
    """

    @property
    def std_logger(self):
        """표준 로거 반환 (지연 초기화)"""
        if not hasattr(self, "_std_logger"):
            # 순환 import 방지를 위해 지연 import
            from app.utils.logging_standards import StandardLogger, LogCategory

            # 클래스 이름에서 카테고리 추론
            class_name = self.__class__.__name__.lower()
            if "workflow" in class_name:
                category = LogCategory.WORKFLOW
            elif "api" in class_name or "client" in class_name:
                category = LogCategory.API
            elif "data" in class_name or "transformer" in class_name:
                category = LogCategory.DATA
            elif "error" in class_name or "exception" in class_name:
                category = LogCategory.ERROR
            elif "security" in class_name or "validator" in class_name:
                category = LogCategory.SECURITY
            else:
                category = LogCategory.SYSTEM

            self._std_logger = StandardLogger(self.__class__.__name__, category)

        return self._std_logger


# 기본 로거 인스턴스 (지연 초기화)
_default_logger = None

def get_default_logger() -> logging.Logger:
    """기본 로거 반환 (지연 초기화)"""
    global _default_logger
    if _default_logger is None:
        _default_logger = setup_logger()
    return _default_logger

# 하위 호환성을 위한 기본 로거
logger = get_default_logger()
