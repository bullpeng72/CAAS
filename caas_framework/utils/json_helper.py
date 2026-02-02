"""
JSON Helper

JSON 파싱, 추출, 검증을 위한 유틸리티
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from caas_framework.utils.file_utils import FileUtils
from caas_framework.utils.logger import get_logger

logger = get_logger("utils.json_helper")


class JSONHelper:
    """JSON 처리 유틸리티"""

    @staticmethod
    def extract_from_markdown(
        content: str, fallback: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Markdown 코드 블록에서 JSON 추출

        LLM 응답에서 ```json ... ``` 형식의 JSON을 추출합니다.

        Args:
            content: Markdown 문자열
            fallback: 추출 실패 시 반환할 값

        Returns:
            파싱된 Dict 또는 fallback
        """
        if not content:
            logger.warning("내용이 비어있음")
            return fallback

        content = content.strip()

        # 패턴 1: ```json ... ```
        if "```json" in content:
            try:
                extracted = content.split("```json")[1].split("```")[0].strip()
                logger.debug("JSON 코드 블록 추출 성공 (json)")
                return JSONHelper.safe_parse(extracted, fallback)
            except (IndexError, ValueError) as e:
                logger.warning(f"JSON 블록 추출 실패: {e}")

        # 패턴 2: ``` ... ``` (일반 코드 블록)
        if "```" in content:
            try:
                extracted = content.split("```")[1].split("```")[0].strip()
                logger.debug("JSON 코드 블록 추출 성공 (일반)")
                return JSONHelper.safe_parse(extracted, fallback)
            except (IndexError, ValueError) as e:
                logger.warning(f"코드 블록 추출 실패: {e}")

        # 패턴 3: 직접 JSON (코드 블록 없음)
        return JSONHelper.safe_parse(content, fallback)

    @staticmethod
    def safe_parse(json_str: str, fallback: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """
        안전한 JSON 파싱

        Args:
            json_str: JSON 문자열
            fallback: 파싱 실패 시 반환할 값

        Returns:
            파싱된 Dict 또는 fallback
        """
        if not json_str or not json_str.strip():
            logger.warning("JSON 문자열이 비어있음")
            return fallback

        try:
            data = json.loads(json_str)
            logger.debug(f"JSON 파싱 성공: {len(json_str)} bytes")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            logger.debug(f"실패한 JSON 내용: {json_str[:200]}...")
            return fallback

    @staticmethod
    def safe_load_file(file_path: Path) -> Optional[Dict[str, Any]]:
        """
        파일에서 안전한 JSON 로드

        Args:
            file_path: 파일 경로

        Returns:
            파싱된 Dict 또는 None
        """
        return FileUtils.safe_load_file(file_path, file_type="json")

    @staticmethod
    def format_dump(
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
        return FileUtils.format_json(data, indent, ensure_ascii, sort_keys)

    @staticmethod
    def safe_dump_file(data: Any, file_path: Path, **kwargs) -> bool:
        """
        파일에 안전하게 JSON 저장

        Args:
            data: 저장할 데이터
            file_path: 파일 경로
            **kwargs: format_dump에 전달할 추가 인자

        Returns:
            성공 여부
        """
        return FileUtils.safe_dump_file(data, file_path, file_type="json", **kwargs)

    @staticmethod
    def sanitize_response(content: str) -> str:
        """
        LLM 응답 정제 (JSON 추출 전 전처리)

        Args:
            content: LLM 응답 문자열

        Returns:
            정제된 문자열
        """
        if not content:
            return content

        # 앞뒤 공백 제거
        content = content.strip()

        # 일반적인 LLM 응답 패턴 제거
        # 예: "Here's the JSON:" 같은 설명 텍스트
        patterns = [
            r"^Here['\s]s the JSON:?\s*",
            r"^The JSON is:?\s*",
            r"^Response:?\s*",
            r"^Output:?\s*",
        ]

        for pattern in patterns:
            content = re.sub(pattern, "", content, flags=re.IGNORECASE)

        return content.strip()

    @staticmethod
    def validate_structure(
        data: Dict[str, Any],
        required_keys: Optional[List[str]] = None,
        optional_keys: Optional[List[str]] = None,
    ) -> tuple[bool, List[str]]:
        """
        JSON 데이터 구조 검증

        Args:
            data: 검증할 데이터
            required_keys: 필수 키 목록
            optional_keys: 선택 키 목록

        Returns:
            (valid, errors): 검증 결과 및 에러 목록
        """
        return FileUtils.validate_structure(data, required_keys, optional_keys)

    @staticmethod
    def sanitize_id(raw_id: str) -> str:
        """
        ID 문자열 정규화 (snake_case)

        Args:
            raw_id: 원본 ID

        Returns:
            정규화된 ID
        """
        if not raw_id:
            return ""

        # 소문자 변환
        sanitized = raw_id.lower()

        # 공백과 하이픈을 언더스코어로
        sanitized = sanitized.replace(" ", "_").replace("-", "_")

        # 특수문자 제거 (알파벳, 숫자, 언더스코어만 허용)
        sanitized = re.sub(r"[^a-z0-9_]", "", sanitized)

        # 연속된 언더스코어를 하나로
        sanitized = re.sub(r"__+", "_", sanitized)

        # 앞뒤 언더스코어 제거
        sanitized = sanitized.strip("_")

        # 빈 문자열 처리
        if not sanitized:
            logger.warning(f"ID 정규화 결과가 비어있음: {raw_id}")
            return "unnamed"

        # 숫자로 시작하는 경우 처리
        if sanitized[0].isdigit():
            sanitized = "id_" + sanitized

        logger.debug(f"ID 정규화: {raw_id} -> {sanitized}")
        return sanitized


# 편의 함수들
def extract_json(content: str, fallback: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Markdown에서 JSON 추출 (단축 함수)"""
    return JSONHelper.extract_from_markdown(content, fallback)


def parse_json(json_str: str, fallback: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """JSON 파싱 (단축 함수)"""
    return JSONHelper.safe_parse(json_str, fallback)


def dump_json(data: Any, **kwargs) -> str:
    """JSON 덤프 (단축 함수)"""
    return JSONHelper.format_dump(data, **kwargs)


def sanitize_id(raw_id: str) -> str:
    """ID 정규화 (단축 함수)"""
    return JSONHelper.sanitize_id(raw_id)
