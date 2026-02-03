"""
LLM Response Parser

LLM 응답을 파싱하고 구조화된 데이터로 변환합니다.
"""

import json
import re
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from caas_framework.utils.logger import get_logger

from caas_framework.utils.json_helper import JSONHelper

logger = get_logger(name="caas_framework.llm.response_parser")

T = TypeVar("T", bound=BaseModel)


class ResponseParser:
    """LLM 응답 파싱 유틸리티"""

    @staticmethod
    def extract_code_block(
        content: str, language: Optional[str] = None, fallback: Optional[str] = None
    ) -> Optional[str]:
        """
        Markdown 코드 블록 추출

        Args:
            content: LLM 응답 문자열
            language: 추출할 언어 (None이면 모든 언어)
            fallback: 추출 실패 시 반환할 값

        Returns:
            추출된 코드 또는 fallback

        Example:
            ```python
            code = extract_code_block(response, language="python")
            ```
        """
        if not content:
            logger.warning("내용이 비어있음")
            return fallback

        content = content.strip()

        # 언어별 패턴
        if language:
            pattern = rf"```{language}\s*\n(.*?)```"
        else:
            # 모든 언어
            pattern = r"```(?:\w+)?\s*\n(.*?)```"

        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

        if matches:
            # 첫 번째 매치 반환
            code = matches[0].strip()
            logger.debug(f"코드 블록 추출 성공: {len(code)} bytes")
            return code

        # 패턴 매칭 실패 시, 코드 블록 없이 직접 코드인 경우
        logger.warning(f"코드 블록을 찾을 수 없음 (language={language})")
        return fallback

    @staticmethod
    def extract_all_code_blocks(
        content: str, language: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        모든 코드 블록 추출

        Args:
            content: LLM 응답 문자열
            language: 필터링할 언어 (None이면 모든 언어)

        Returns:
            코드 블록 리스트 [{"language": "python", "code": "..."}, ...]
        """
        if not content:
            return []

        # 언어와 코드 모두 캡처
        pattern = r"```(\w+)?\s*\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)

        blocks = []
        for lang, code in matches:
            lang = lang.strip() if lang else "unknown"
            code = code.strip()

            # 언어 필터링
            if language and lang.lower() != language.lower():
                continue

            blocks.append({"language": lang, "code": code})

        logger.debug(f"코드 블록 {len(blocks)}개 추출됨")
        return blocks

    @staticmethod
    def extract_json_from_response(
        content: str, fallback: Optional[Any] = None, strict: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        LLM 응답에서 JSON 추출 (JSONHelper 래퍼)

        Args:
            content: LLM 응답 문자열
            fallback: 추출 실패 시 반환할 값
            strict: 엄격 모드 (실패 시 예외 발생)

        Returns:
            파싱된 Dict 또는 fallback

        Raises:
            ValueError: strict=True이고 파싱 실패 시
        """
        result = JSONHelper.extract_from_markdown(content, fallback)

        if result is None and strict:
            raise ValueError(f"JSON 추출 실패: {content[:100]}...")

        return result

    @staticmethod
    def extract_list_from_response(content: str, pattern: Optional[str] = None) -> List[str]:
        """
        LLM 응답에서 리스트 항목 추출

        Args:
            content: LLM 응답 문자열
            pattern: 추출 패턴 (None이면 기본 패턴 사용)

        Returns:
            추출된 항목 리스트

        Example:
            ```python
            # "- Item 1\n- Item 2" -> ["Item 1", "Item 2"]
            items = extract_list_from_response(response)
            ```
        """
        if not content:
            return []

        if pattern is None:
            # 기본 패턴: Markdown 리스트 (-, *, 1., 2. 등)
            patterns = [
                r"^[\s]*[-*]\s+(.+)$",  # - Item 또는 * Item
                r"^[\s]*\d+\.\s+(.+)$",  # 1. Item
            ]
        else:
            patterns = [pattern]

        items = []
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            for pat in patterns:
                match = re.match(pat, line, re.MULTILINE)
                if match:
                    items.append(match.group(1).strip())
                    break

        logger.debug(f"리스트 항목 {len(items)}개 추출됨")
        return items

    @staticmethod
    def extract_key_value_pairs(content: str, separator: str = ":") -> Dict[str, str]:
        """
        LLM 응답에서 키-값 쌍 추출

        Args:
            content: LLM 응답 문자열
            separator: 키와 값 구분자

        Returns:
            키-값 딕셔너리

        Example:
            ```python
            # "Name: John\nAge: 30" -> {"Name": "John", "Age": "30"}
            pairs = extract_key_value_pairs(response)
            ```
        """
        if not content:
            return {}

        pairs = {}
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if not line or separator not in line:
                continue

            # 첫 번째 구분자로만 분할
            parts = line.split(separator, 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()

                # Markdown 강조 제거 (**, __, ` 등)
                key = re.sub(r"[*_`]", "", key)
                value = re.sub(r"[*_`]", "", value)

                pairs[key] = value

        logger.debug(f"키-값 쌍 {len(pairs)}개 추출됨")
        return pairs

    @staticmethod
    def parse_to_model(
        content: str, model_class: Type[T], extract_json: bool = True, strict: bool = True
    ) -> Optional[T]:
        """
        LLM 응답을 Pydantic 모델로 파싱

        Args:
            content: LLM 응답 문자열
            model_class: 대상 Pydantic 모델 클래스
            extract_json: JSON 추출 시도 여부
            strict: 엄격 모드 (검증 실패 시 예외 발생)

        Returns:
            모델 인스턴스 또는 None

        Raises:
            ValidationError: strict=True이고 검증 실패 시
        """
        if extract_json:
            # JSON 추출
            data = ResponseParser.extract_json_from_response(content, fallback={})
        else:
            # 직접 JSON 파싱
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}")
                if strict:
                    raise
                return None

        # Pydantic 모델로 변환
        try:
            model = model_class(**data)
            logger.debug(f"모델 파싱 성공: {model_class.__name__}")
            return model
        except ValidationError as e:
            logger.error(f"모델 검증 실패: {e}")
            if strict:
                raise
            return None

    @staticmethod
    def clean_response(
        content: str,
        remove_markdown: bool = False,
        remove_code_blocks: bool = False,
        strip_whitespace: bool = True,
    ) -> str:
        """
        LLM 응답 정제

        Args:
            content: LLM 응답 문자열
            remove_markdown: Markdown 포맷 제거 여부
            remove_code_blocks: 코드 블록 제거 여부
            strip_whitespace: 앞뒤 공백 제거 여부

        Returns:
            정제된 문자열
        """
        if not content:
            return content

        result = content

        # 코드 블록 제거
        if remove_code_blocks:
            result = re.sub(r"```.*?```", "", result, flags=re.DOTALL)

        # Markdown 포맷 제거
        if remove_markdown:
            # 헤더
            result = re.sub(r"#+\s+", "", result)
            # 강조 (**, __, *)
            result = re.sub(r"\*\*(.+?)\*\*", r"\1", result)
            result = re.sub(r"__(.+?)__", r"\1", result)
            result = re.sub(r"\*(.+?)\*", r"\1", result)
            result = re.sub(r"_(.+?)_", r"\1", result)
            # 링크
            result = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", result)
            # 인라인 코드
            result = re.sub(r"`(.+?)`", r"\1", result)

        # 앞뒤 공백 제거
        if strip_whitespace:
            result = result.strip()

        return result

    @staticmethod
    def validate_response(
        content: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        required_keywords: Optional[List[str]] = None,
        forbidden_keywords: Optional[List[str]] = None,
    ) -> tuple[bool, List[str]]:
        """
        LLM 응답 검증

        Args:
            content: LLM 응답 문자열
            min_length: 최소 길이
            max_length: 최대 길이
            required_keywords: 필수 키워드 리스트
            forbidden_keywords: 금지 키워드 리스트

        Returns:
            (검증 성공 여부, 에러 메시지 리스트)
        """
        errors = []

        if not content:
            errors.append("응답이 비어있음")
            return False, errors

        # 길이 검증
        if min_length and len(content) < min_length:
            errors.append(f"응답이 너무 짧음 (최소 {min_length}자)")

        if max_length and len(content) > max_length:
            errors.append(f"응답이 너무 김 (최대 {max_length}자)")

        # 필수 키워드 검증
        if required_keywords:
            for keyword in required_keywords:
                if keyword.lower() not in content.lower():
                    errors.append(f"필수 키워드 누락: '{keyword}'")

        # 금지 키워드 검증
        if forbidden_keywords:
            for keyword in forbidden_keywords:
                if keyword.lower() in content.lower():
                    errors.append(f"금지된 키워드 발견: '{keyword}'")

        valid = len(errors) == 0
        return valid, errors

    @staticmethod
    def retry_parse(
        content: str,
        parser_func: Callable[[str], Any],
        max_retries: int = 3,
        fallback: Optional[Any] = None,
    ) -> Any:
        """
        파싱 재시도 (에러 처리 포함)

        Args:
            content: LLM 응답 문자열
            parser_func: 파싱 함수
            max_retries: 최대 재시도 횟수
            fallback: 실패 시 반환할 값

        Returns:
            파싱 결과 또는 fallback
        """
        for attempt in range(max_retries):
            try:
                result = parser_func(content)
                logger.debug(f"파싱 성공 (시도 {attempt + 1})")
                return result
            except Exception as e:
                logger.warning(f"파싱 실패 (시도 {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    # 재시도 전 전처리
                    content = ResponseParser.clean_response(content)
                else:
                    # 최종 실패
                    logger.error(f"파싱 최종 실패: {e}")

        return fallback


class StreamingResponseParser:
    """
    스트리밍 LLM 응답 파싱

    실시간으로 응답을 받으면서 파싱합니다.
    """

    def __init__(self, buffer_size: int = 1000):
        """
        스트리밍 파서 초기화

        Args:
            buffer_size: 버퍼 크기 (바이트)
        """
        self.buffer = ""
        self.buffer_size = buffer_size
        self.complete_blocks: List[str] = []

    def add_chunk(self, chunk: str) -> List[str]:
        """
        청크 추가 및 완성된 블록 추출

        Args:
            chunk: 새로운 텍스트 청크

        Returns:
            완성된 블록 리스트
        """
        self.buffer += chunk
        new_blocks = []

        # 완성된 코드 블록 추출
        while "```" in self.buffer:
            # 시작과 끝 찾기
            start_idx = self.buffer.find("```")
            end_idx = self.buffer.find("```", start_idx + 3)

            if end_idx == -1:
                # 아직 블록이 완성되지 않음
                break

            # 블록 추출
            block = self.buffer[start_idx : end_idx + 3]
            new_blocks.append(block)
            self.complete_blocks.append(block)

            # 버퍼에서 제거
            self.buffer = self.buffer[end_idx + 3 :]

        # 버퍼 크기 제한
        if len(self.buffer) > self.buffer_size:
            # 오래된 내용 제거
            self.buffer = self.buffer[-self.buffer_size :]

        return new_blocks

    def get_complete_blocks(self) -> List[str]:
        """완성된 블록 리스트 반환"""
        return self.complete_blocks

    def get_buffer(self) -> str:
        """현재 버퍼 내용 반환"""
        return self.buffer

    def reset(self):
        """상태 리셋"""
        self.buffer = ""
        self.complete_blocks = []


# 편의 함수들
def extract_code(content: str, language: str = "python") -> Optional[str]:
    """코드 블록 추출 (단축 함수)"""
    return ResponseParser.extract_code_block(content, language)


def extract_json(content: str) -> Optional[Dict[str, Any]]:
    """JSON 추출 (단축 함수)"""
    return ResponseParser.extract_json_from_response(content)


def parse_to_model(content: str, model_class: Type[T]) -> Optional[T]:
    """모델 파싱 (단축 함수)"""
    return ResponseParser.parse_to_model(content, model_class)


def extract_list(content: str) -> List[str]:
    """리스트 추출 (단축 함수)"""
    return ResponseParser.extract_list_from_response(content)


def clean_response(content: str, remove_markdown: bool = True) -> str:
    """응답 정제 (단축 함수)"""
    return ResponseParser.clean_response(content, remove_markdown=remove_markdown)
