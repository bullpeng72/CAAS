"""
YAML Helper

YAML 파싱, 검증, 포맷팅을 위한 유틸리티
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from caas_framework.utils.file_utils import FileUtils
from caas_framework.utils.logger import get_logger
from caas_framework.utils.security import YAMLSecurityError, validate_yaml_size

logger = get_logger("utils.yaml_helper")


class YAMLHelper:
    """YAML 처리 유틸리티"""

    @staticmethod
    def safe_load(
        yaml_content: str, validate_size: bool = True, max_size_mb: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        안전한 YAML 로드

        Args:
            yaml_content: YAML 문자열
            validate_size: 크기 검증 여부
            max_size_mb: 최대 크기 (MB)

        Returns:
            파싱된 Dict 또는 None

        Raises:
            YAMLSecurityError: 크기 초과
            yaml.YAMLError: 파싱 오류
        """
        if not yaml_content or not yaml_content.strip():
            logger.warning("YAML 내용이 비어있음")
            return None

        # 크기 검증
        if validate_size:
            try:
                validate_yaml_size(yaml_content, max_size_mb=max_size_mb)
            except YAMLSecurityError as e:
                logger.error(f"YAML 크기 검증 실패: {e}")
                raise

        try:
            data = yaml.safe_load(yaml_content)

            if data is None:
                logger.warning("YAML이 비어있음 (null)")
                return None

            if isinstance(data, dict) and not data:
                logger.warning("YAML이 빈 딕셔너리")
                return None

            logger.debug(f"YAML 로드 성공: {len(str(data))} bytes")
            return data

        except yaml.YAMLError as e:
            logger.error(f"YAML 파싱 오류: {e}")
            raise

    @staticmethod
    def safe_load_file(
        file_path: Path, validate_size: bool = True, max_size_mb: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        파일에서 안전한 YAML 로드

        Args:
            file_path: 파일 경로
            validate_size: 크기 검증 여부
            max_size_mb: 최대 크기 (MB)

        Returns:
            파싱된 Dict 또는 None
        """
        # Note: FileUtils doesn't support validate_size parameter
        # So we still need custom logic for size validation
        if not file_path.exists():
            logger.error(f"파일이 존재하지 않음: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                yaml_content = f.read()

            logger.info(f"YAML 파일 읽기: {file_path}")
            return YAMLHelper.safe_load(yaml_content, validate_size, max_size_mb)

        except Exception as e:
            logger.error(f"YAML 파일 로드 실패: {e}")
            raise

    @staticmethod
    def format_dump(
        data: Any,
        indent: int = 2,
        sort_keys: bool = False,
        default_flow_style: bool = False,
        allow_unicode: bool = True,
    ) -> str:
        """
        YAML 포맷팅 (일관된 스타일)

        Args:
            data: 직렬화할 데이터
            indent: 들여쓰기 크기
            sort_keys: 키 정렬 여부
            default_flow_style: Flow 스타일 사용 여부
            allow_unicode: 유니코드 허용 여부

        Returns:
            포맷팅된 YAML 문자열
        """
        return FileUtils.format_yaml(
            data,
            indent=indent,
            sort_keys=sort_keys,
            default_flow_style=default_flow_style,
            allow_unicode=allow_unicode,
        )

    @staticmethod
    def safe_dump_file(data: Any, file_path: Path, **kwargs) -> bool:
        """
        파일에 안전하게 YAML 저장

        Args:
            data: 저장할 데이터
            file_path: 파일 경로
            **kwargs: format_dump에 전달할 추가 인자

        Returns:
            성공 여부
        """
        return FileUtils.safe_dump_file(data, file_path, file_type="yaml", **kwargs)

    @staticmethod
    def validate_structure(
        data: Dict[str, Any],
        required_keys: Optional[List[str]] = None,
        optional_keys: Optional[List[str]] = None,
    ) -> tuple[bool, List[str]]:
        """
        YAML 데이터 구조 검증

        Args:
            data: 검증할 데이터
            required_keys: 필수 키 목록
            optional_keys: 선택 키 목록

        Returns:
            (valid, errors): 검증 결과 및 에러 목록
        """
        return FileUtils.validate_structure(data, required_keys, optional_keys)

    @staticmethod
    def merge_yaml(
        base: Dict[str, Any], override: Dict[str, Any], deep: bool = True
    ) -> Dict[str, Any]:
        """
        YAML 딕셔너리 병합

        Args:
            base: 기본 딕셔너리
            override: 덮어쓸 딕셔너리
            deep: 깊은 병합 여부

        Returns:
            병합된 딕셔너리
        """
        if not deep:
            # 얕은 병합
            result = base.copy()
            result.update(override)
            return result

        # 깊은 병합
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                # 재귀적 병합
                result[key] = YAMLHelper.merge_yaml(result[key], value, deep=True)
            else:
                result[key] = value

        return result

    @staticmethod
    def extract_errors(yaml_error: yaml.YAMLError) -> Dict[str, Any]:
        """
        YAML 에러에서 정보 추출

        Args:
            yaml_error: YAML 에러 객체

        Returns:
            에러 정보 딕셔너리
        """
        error_info = {
            "message": str(yaml_error),
            "line": None,
            "column": None,
            "context": None,
        }

        # problem_mark에서 위치 정보 추출
        if hasattr(yaml_error, "problem_mark"):
            mark = yaml_error.problem_mark
            error_info["line"] = mark.line + 1  # 1-based
            error_info["column"] = mark.column + 1

        # context 추출
        if hasattr(yaml_error, "problem"):
            error_info["context"] = yaml_error.problem

        return error_info


# 편의 함수들
def load_yaml(yaml_content: str) -> Optional[Dict[str, Any]]:
    """YAML 로드 (단축 함수)"""
    return YAMLHelper.safe_load(yaml_content)


def dump_yaml(data: Any, **kwargs) -> str:
    """YAML 덤프 (단축 함수)"""
    return YAMLHelper.format_dump(data, **kwargs)


def load_yaml_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """YAML 파일 로드 (단축 함수)"""
    return YAMLHelper.safe_load_file(file_path)


def dump_yaml_file(data: Any, file_path: Path, **kwargs) -> bool:
    """YAML 파일 저장 (단축 함수)"""
    return YAMLHelper.safe_dump_file(data, file_path, **kwargs)
