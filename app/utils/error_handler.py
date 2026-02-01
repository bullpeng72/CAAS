"""
Error Handler - 에러 처리 통합

Context manager를 통한 일관된 에러 처리
"""

import streamlit as st
from typing import Optional, Callable, Any, Type, List
from contextlib import contextmanager
import traceback
import yaml
from pydantic import ValidationError

from caas_framework.utils.logger import get_logger

logger = get_logger("utils.error_handler")


class ErrorSeverity:
    """에러 심각도"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorHandler:
    """
    통합 에러 핸들러

    Context manager로 에러 처리를 자동화합니다.
    """

    def __init__(
        self,
        operation_name: str,
        show_ui_error: bool = True,
        log_error: bool = True,
        raise_on_error: bool = False,
        fallback_value: Optional[Any] = None,
        severity: str = ErrorSeverity.ERROR
    ):
        """
        에러 핸들러 초기화

        Args:
            operation_name: 작업 이름 (로깅 및 UI 표시용)
            show_ui_error: UI에 에러 표시 여부
            log_error: 로그에 에러 기록 여부
            raise_on_error: 에러 발생 시 예외 재발생 여부
            fallback_value: 에러 발생 시 반환할 대체 값
            severity: 에러 심각도 (info, warning, error, critical)
        """
        self.operation_name = operation_name
        self.show_ui_error = show_ui_error
        self.log_error = log_error
        self.raise_on_error = raise_on_error
        self.fallback_value = fallback_value
        self.severity = severity
        self.exception: Optional[Exception] = None
        self.traceback_str: Optional[str] = None

    def __enter__(self):
        """Context manager 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료 (에러 처리)"""
        if exc_type is None:
            # 에러 없음
            return True

        # 에러 저장
        self.exception = exc_val
        self.traceback_str = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))

        # 로깅
        if self.log_error:
            logger.error(
                f"❌ [{self.operation_name}] 오류: {exc_val}",
                exc_info=(exc_type, exc_val, exc_tb)
            )

        # UI 표시
        if self.show_ui_error:
            self._display_error(exc_type, exc_val)

        # 예외 재발생 여부
        if self.raise_on_error:
            return False  # 예외를 상위로 전파

        return True  # 예외를 억제

    def _display_error(self, exc_type: Type[Exception], exc_val: Exception):
        """UI에 에러 표시"""
        # 에러 타입별 처리
        if exc_type == yaml.YAMLError:
            self._display_yaml_error(exc_val)
        elif exc_type == ValidationError:
            self._display_validation_error(exc_val)
        elif exc_type in [FileNotFoundError, PermissionError, IOError]:
            self._display_file_error(exc_val)
        else:
            self._display_generic_error(exc_val)

    def _display_yaml_error(self, error: yaml.YAMLError):
        """YAML 에러 표시"""

        st.error(f"**{self.operation_name} 실패: YAML 파싱 오류**")

        # 에러 정보 추출
        error_info = {
            "message": str(error),
            "line": None,
            "column": None,
        }

        if hasattr(error, "problem_mark"):
            mark = error.problem_mark
            error_info["line"] = mark.line + 1
            error_info["column"] = mark.column + 1

        st.markdown(f"**오류 내용:** {error_info['message']}")

        if error_info["line"]:
            st.markdown(f"**위치:** 라인 {error_info['line']}, 컬럼 {error_info['column']}")

        # 해결 제안
        st.markdown("**💡 해결 방법:**")
        st.markdown("- YAML 구문이 올바른지 확인하세요")
        st.markdown("- 들여쓰기는 스페이스를 사용하고 탭을 사용하지 마세요")
        st.markdown("- 특수문자가 포함된 경우 따옴표로 감싸세요")

    def _display_validation_error(self, error: ValidationError):
        """Pydantic 검증 에러 표시"""
        st.error(f"**{self.operation_name} 실패: 데이터 검증 오류**")

        errors = error.errors()
        st.markdown(f"**{len(errors)}개의 검증 오류 발견:**")

        for idx, err in enumerate(errors[:5], 1):  # 최대 5개만 표시
            location = " → ".join(str(x) for x in err["loc"])
            message = err["msg"]
            err_type = err["type"]

            with st.expander(f"오류 {idx}: {location}", expanded=True):
                st.markdown(f"**타입:** `{err_type}`")
                st.markdown(f"**메시지:** {message}")

        if len(errors) > 5:
            st.warning(f"⚠️ {len(errors) - 5}개의 추가 오류가 있습니다.")

    def _display_file_error(self, error: Exception):
        """파일 시스템 에러 표시"""
        st.error(f"**{self.operation_name} 실패: 파일 시스템 오류**")

        st.markdown(f"**오류 내용:** {str(error)}")

        # 에러 타입별 제안
        if isinstance(error, FileNotFoundError):
            st.markdown("**💡 해결 방법:**")
            st.markdown("- 파일 경로가 올바른지 확인하세요")
            st.markdown("- 파일이 존재하는지 확인하세요")
        elif isinstance(error, PermissionError):
            st.markdown("**💡 해결 방법:**")
            st.markdown("- 파일 접근 권한을 확인하세요")
            st.markdown("- 관리자 권한으로 실행해보세요")
        elif isinstance(error, IOError):
            st.markdown("**💡 해결 방법:**")
            st.markdown("- 디스크 공간이 충분한지 확인하세요")
            st.markdown("- 파일이 다른 프로그램에서 사용 중인지 확인하세요")

    def _display_generic_error(self, error: Exception):
        """일반 에러 표시"""
        error_func = {
            ErrorSeverity.INFO: st.info,
            ErrorSeverity.WARNING: st.warning,
            ErrorSeverity.ERROR: st.error,
            ErrorSeverity.CRITICAL: st.error
        }.get(self.severity, st.error)

        error_func(f"**{self.operation_name} 실패**")

        st.markdown(f"**오류 타입:** `{type(error).__name__}`")
        st.markdown(f"**오류 내용:** {str(error)}")

        # 트레이스백 표시 (접을 수 있음)
        if self.traceback_str and self.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            with st.expander("🐛 상세 오류 정보 (개발자용)"):
                st.code(self.traceback_str, language="python")

    def get_result(self) -> Any:
        """
        에러 발생 시 fallback 값 반환

        Returns:
            fallback_value
        """
        return self.fallback_value

    def has_error(self) -> bool:
        """
        에러 발생 여부 확인

        Returns:
            에러 발생 여부
        """
        return self.exception is not None


# Context manager 편의 함수들

@contextmanager
def handle_operation(
    operation_name: str,
    show_ui_error: bool = True,
    log_error: bool = True,
    raise_on_error: bool = False,
    fallback_value: Optional[Any] = None,
    severity: str = ErrorSeverity.ERROR
):
    """
    작업 에러 처리 context manager

    Args:
        operation_name: 작업 이름
        show_ui_error: UI에 에러 표시 여부
        log_error: 로그에 에러 기록 여부
        raise_on_error: 에러 발생 시 예외 재발생 여부
        fallback_value: 에러 발생 시 반환할 대체 값
        severity: 에러 심각도

    Example:
        ```python
        with handle_operation("데이터 저장"):
            save_data(data)
        ```
    """
    handler = ErrorHandler(
        operation_name,
        show_ui_error,
        log_error,
        raise_on_error,
        fallback_value,
        severity
    )

    with handler:
        yield handler


@contextmanager
def handle_validation(operation_name: str = "데이터 검증"):
    """
    검증 에러 처리 context manager (특화)

    Args:
        operation_name: 작업 이름

    Example:
        ```python
        with handle_validation("스펙 검증"):
            spec = SpecModel(**data)
        ```
    """
    with handle_operation(
        operation_name,
        show_ui_error=True,
        log_error=True,
        raise_on_error=False
    ) as handler:
        yield handler


@contextmanager
def handle_file_operation(operation_name: str = "파일 작업"):
    """
    파일 작업 에러 처리 context manager (특화)

    Args:
        operation_name: 작업 이름

    Example:
        ```python
        with handle_file_operation("파일 읽기"):
            with open(file_path) as f:
                data = f.read()
        ```
    """
    with handle_operation(
        operation_name,
        show_ui_error=True,
        log_error=True,
        raise_on_error=False
    ) as handler:
        yield handler


@contextmanager
def handle_api_call(operation_name: str = "API 호출"):
    """
    API 호출 에러 처리 context manager (특화)

    Args:
        operation_name: 작업 이름

    Example:
        ```python
        with handle_api_call("LLM 요청"):
            response = llm.invoke(prompt)
        ```
    """
    with handle_operation(
        operation_name,
        show_ui_error=True,
        log_error=True,
        raise_on_error=False,
        severity=ErrorSeverity.WARNING
    ) as handler:
        yield handler


def safe_execute(
    func: Callable,
    operation_name: str,
    fallback_value: Optional[Any] = None,
    show_ui_error: bool = True,
    *args,
    **kwargs
) -> Any:
    """
    안전한 함수 실행 (에러 처리 포함)

    Args:
        func: 실행할 함수
        operation_name: 작업 이름
        fallback_value: 에러 발생 시 반환 값
        show_ui_error: UI 에러 표시 여부
        *args: 함수 인자
        **kwargs: 함수 키워드 인자

    Returns:
        함수 실행 결과 또는 fallback_value

    Example:
        ```python
        result = safe_execute(
            parse_yaml,
            "YAML 파싱",
            fallback_value={},
            yaml_string
        )
        ```
    """
    with handle_operation(
        operation_name,
        show_ui_error=show_ui_error,
        fallback_value=fallback_value
    ) as handler:
        result = func(*args, **kwargs)
        return result

    # 에러 발생 시
    return handler.get_result()


class BatchErrorHandler:
    """
    배치 작업 에러 핸들러

    여러 작업을 수행하면서 에러를 수집합니다.
    """

    def __init__(self, operation_name: str):
        """
        배치 에러 핸들러 초기화

        Args:
            operation_name: 작업 이름
        """
        self.operation_name = operation_name
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[str] = []
        self.successes: int = 0

    def add_error(self, item: str, error: Exception):
        """
        에러 추가

        Args:
            item: 실패한 항목 이름
            error: 발생한 예외
        """
        self.errors.append({
            "item": item,
            "error_type": type(error).__name__,
            "error_message": str(error)
        })

        logger.error(f"❌ [{self.operation_name}] {item} 실패: {error}")

    def add_warning(self, message: str):
        """
        경고 추가

        Args:
            message: 경고 메시지
        """
        self.warnings.append(message)
        logger.warning(f"⚠️ [{self.operation_name}] {message}")

    def add_success(self):
        """성공 카운트 증가"""
        self.successes += 1

    def has_errors(self) -> bool:
        """에러 존재 여부"""
        return len(self.errors) > 0

    def display_summary(self):
        """배치 작업 결과 요약 표시"""
        total = self.successes + len(self.errors)

        if total == 0:
            st.info("처리할 항목이 없습니다.")
            return

        # 요약 메트릭
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("성공", self.successes, delta=None)

        with col2:
            st.metric("실패", len(self.errors), delta=None, delta_color="inverse")

        with col3:
            success_rate = (self.successes / total * 100) if total > 0 else 0
            st.metric("성공률", f"{success_rate:.1f}%")

        # 경고 표시
        if self.warnings:
            with st.expander(f"⚠️ 경고 ({len(self.warnings)}개)"):
                for warning in self.warnings:
                    st.warning(warning)

        # 에러 표시
        if self.errors:
            with st.expander(f"❌ 오류 ({len(self.errors)}개)", expanded=True):
                for error in self.errors:
                    st.error(
                        f"**{error['item']}**: {error['error_type']} - {error['error_message']}"
                    )


# 편의 함수
def with_error_handling(operation_name: str):
    """
    데코레이터: 함수에 에러 처리 추가

    Args:
        operation_name: 작업 이름

    Example:
        ```python
        @with_error_handling("데이터 처리")
        def process_data(data):
            # 처리 로직
            pass
        ```
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with handle_operation(operation_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator
