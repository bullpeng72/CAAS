"""
File Utilities

파일 I/O 및 직렬화를 위한 공통 유틸리티
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from caas_framework.utils.logger import get_logger

logger = get_logger("utils.file_utils")


class FileUtils:
    """파일 처리 유틸리티 (JSON, YAML 공통)"""

    @staticmethod
    def safe_load_file(
        file_path: Path, file_type: str = "auto"
    ) -> Optional[Dict[str, Any]]:
        """
        파일에서 안전하게 데이터 로드

        Args:
            file_path: 파일 경로
            file_type: 파일 타입 ("json", "yaml", "auto")

        Returns:
            파싱된 Dict 또는 None
        """
        if not file_path.exists():
            logger.error(f"파일이 존재하지 않음: {file_path}")
            return None

        # 파일 타입 자동 감지
        if file_type == "auto":
            suffix = file_path.suffix.lower()
            if suffix in [".json"]:
                file_type = "json"
            elif suffix in [".yaml", ".yml"]:
                file_type = "yaml"
            else:
                logger.error(f"알 수 없는 파일 타입: {suffix}")
                return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if file_type == "json":
                    data = json.load(f)
                elif file_type == "yaml":
                    data = yaml.safe_load(f)
                else:
                    logger.error(f"지원하지 않는 파일 타입: {file_type}")
                    return None

            logger.info(f"{file_type.upper()} 파일 로드 성공: {file_path}")
            return data

        except Exception as e:
            logger.error(f"파일 로드 실패: {e}")
            return None

    @staticmethod
    def safe_dump_file(
        data: Any, file_path: Path, file_type: str = "auto", **kwargs
    ) -> bool:
        """
        파일에 안전하게 데이터 저장

        Args:
            data: 저장할 데이터
            file_path: 파일 경로
            file_type: 파일 타입 ("json", "yaml", "auto")
            **kwargs: format_dump에 전달할 추가 인자

        Returns:
            성공 여부
        """
        # 파일 타입 자동 감지
        if file_type == "auto":
            suffix = file_path.suffix.lower()
            if suffix in [".json"]:
                file_type = "json"
            elif suffix in [".yaml", ".yml"]:
                file_type = "yaml"
            else:
                logger.error(f"알 수 없는 파일 타입: {suffix}")
                return False

        try:
            # 디렉토리 생성
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 데이터 포맷팅
            if file_type == "json":
                content = FileUtils.format_json(data, **kwargs)
            elif file_type == "yaml":
                content = FileUtils.format_yaml(data, **kwargs)
            else:
                logger.error(f"지원하지 않는 파일 타입: {file_type}")
                return False

            # 파일 쓰기
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"{file_type.upper()} 파일 저장 성공: {file_path}")
            return True

        except Exception as e:
            logger.error(f"파일 저장 실패: {e}")
            return False

    @staticmethod
    def format_json(
        data: Any, indent: int = 2, ensure_ascii: bool = False, sort_keys: bool = False
    ) -> str:
        """
        JSON 포맷팅 (일관된 스타일)

        Args:
            data: 직렬화할 데이터
            indent: 들여쓰기 크기
            ensure_ascii: ASCII 전용 여부
            sort_keys: 키 정렬 여부

        Returns:
            포맷팅된 JSON 문자열
        """
        try:
            json_str = json.dumps(
                data,
                indent=indent,
                ensure_ascii=ensure_ascii,
                sort_keys=sort_keys,
            )

            logger.debug(f"JSON 포맷팅 완료: {len(json_str)} bytes")
            return json_str

        except Exception as e:
            logger.error(f"JSON 포맷팅 실패: {e}")
            raise

    @staticmethod
    def format_yaml(
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
        try:
            yaml_str = yaml.dump(
                data,
                indent=indent,
                sort_keys=sort_keys,
                default_flow_style=default_flow_style,
                allow_unicode=allow_unicode,
            )

            logger.debug(f"YAML 포맷팅 완료: {len(yaml_str)} bytes")
            return yaml_str

        except Exception as e:
            logger.error(f"YAML 포맷팅 실패: {e}")
            raise

    @staticmethod
    def validate_structure(
        data: Dict[str, Any],
        required_keys: Optional[List[str]] = None,
        optional_keys: Optional[List[str]] = None,
    ) -> tuple[bool, List[str]]:
        """
        데이터 구조 검증

        Args:
            data: 검증할 데이터
            required_keys: 필수 키 목록
            optional_keys: 선택 키 목록

        Returns:
            (valid, errors): 검증 결과 및 에러 목록
        """
        errors = []

        if not isinstance(data, dict):
            errors.append("데이터가 딕셔너리가 아님")
            return False, errors

        # 필수 키 확인
        if required_keys:
            for key in required_keys:
                if key not in data:
                    errors.append(f"필수 키 누락: {key}")

        # 허용되지 않은 키 확인 (strict mode)
        if required_keys is not None and optional_keys is not None:
            allowed_keys = set(required_keys) | set(optional_keys)
            for key in data.keys():
                if key not in allowed_keys:
                    errors.append(f"허용되지 않은 키: {key}")

        valid = len(errors) == 0
        return valid, errors


# 편의 함수들
def load_file(file_path: Path, file_type: str = "auto") -> Optional[Dict[str, Any]]:
    """파일 로드 (단축 함수)"""
    return FileUtils.safe_load_file(file_path, file_type)


def save_file(data: Any, file_path: Path, file_type: str = "auto", **kwargs) -> bool:
    """파일 저장 (단축 함수)"""
    return FileUtils.safe_dump_file(data, file_path, file_type, **kwargs)


def format_data(data: Any, format_type: str = "json", **kwargs) -> str:
    """데이터 포맷팅 (단축 함수)"""
    if format_type == "json":
        return FileUtils.format_json(data, **kwargs)
    elif format_type == "yaml":
        return FileUtils.format_yaml(data, **kwargs)
    else:
        raise ValueError(f"지원하지 않는 포맷: {format_type}")


def validate_data_structure(
    data: Dict[str, Any],
    required_keys: Optional[List[str]] = None,
    optional_keys: Optional[List[str]] = None,
) -> tuple[bool, List[str]]:
    """데이터 구조 검증 (단축 함수)"""
    return FileUtils.validate_structure(data, required_keys, optional_keys)
