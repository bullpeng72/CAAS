"""
Data Transformer

데이터 변환, 정규화, 매핑을 위한 유틸리티
"""

from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from caas_framework.utils.json_helper import sanitize_id
from caas_framework.utils.logger import get_logger

logger = get_logger("utils.data_transformer")

T = TypeVar("T", bound=BaseModel)


class DataTransformer:
    """데이터 변환 유틸리티"""

    @staticmethod
    def dict_to_model(
        data: Dict[str, Any], model_class: Type[T], strict: bool = True
    ) -> Optional[T]:
        """
        Dict를 Pydantic 모델로 변환

        Args:
            data: 변환할 딕셔너리
            model_class: 대상 Pydantic 모델 클래스
            strict: 엄격 모드 (검증 실패 시 예외 발생)

        Returns:
            모델 인스턴스 또는 None (strict=False일 때)

        Raises:
            ValidationError: strict=True이고 검증 실패 시
        """
        try:
            model = model_class(**data)
            logger.debug(f"Dict → {model_class.__name__} 변환 성공")
            return model

        except ValidationError as e:
            logger.error(f"Dict → {model_class.__name__} 변환 실패: {e}")
            if strict:
                raise
            return None

    @staticmethod
    def model_to_dict(
        model: BaseModel,
        exclude_none: bool = False,
        exclude_unset: bool = False,
        by_alias: bool = False,
    ) -> Dict[str, Any]:
        """
        Pydantic 모델을 Dict로 변환

        Args:
            model: 변환할 Pydantic 모델
            exclude_none: None 값 제외 여부
            exclude_unset: 설정되지 않은 값 제외 여부
            by_alias: alias 사용 여부

        Returns:
            딕셔너리
        """
        try:
            data = model.model_dump(
                exclude_none=exclude_none,
                exclude_unset=exclude_unset,
                by_alias=by_alias,
            )
            logger.debug(f"{model.__class__.__name__} → Dict 변환 성공")
            return data

        except Exception as e:
            logger.error(f"{model.__class__.__name__} → Dict 변환 실패: {e}")
            raise

    @staticmethod
    def models_to_dicts(models: List[BaseModel], **kwargs) -> List[Dict[str, Any]]:
        """
        Pydantic 모델 리스트를 Dict 리스트로 변환

        Args:
            models: 모델 리스트
            **kwargs: model_to_dict에 전달할 추가 인자

        Returns:
            딕셔너리 리스트
        """
        return [DataTransformer.model_to_dict(m, **kwargs) for m in models]

    @staticmethod
    def normalize_id(
        raw_id: str, prefix: Optional[str] = None, suffix: Optional[str] = None
    ) -> str:
        """
        ID 정규화 (snake_case + 접두사/접미사)

        Args:
            raw_id: 원본 ID
            prefix: 접두사 (예: "agent_")
            suffix: 접미사 (예: "_v1")

        Returns:
            정규화된 ID
        """
        # 기본 정규화
        normalized = sanitize_id(raw_id)

        # 접두사 추가
        if prefix:
            normalized = f"{prefix}{normalized}"

        # 접미사 추가
        if suffix:
            normalized = f"{normalized}{suffix}"

        return normalized

    @staticmethod
    def merge_dicts(
        base: Dict[str, Any],
        override: Dict[str, Any],
        deep: bool = True,
        list_strategy: str = "override",
    ) -> Dict[str, Any]:
        """
        딕셔너리 병합

        Args:
            base: 기본 딕셔너리
            override: 덮어쓸 딕셔너리
            deep: 깊은 병합 여부
            list_strategy: 리스트 병합 전략 ("override", "extend", "keep")

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
            if key not in result:
                # 새 키
                result[key] = value

            elif isinstance(result[key], dict) and isinstance(value, dict):
                # 중첩된 딕셔너리 - 재귀적 병합
                result[key] = DataTransformer.merge_dicts(
                    result[key], value, deep=True, list_strategy=list_strategy
                )

            elif isinstance(result[key], list) and isinstance(value, list):
                # 리스트 병합
                if list_strategy == "override":
                    result[key] = value
                elif list_strategy == "extend":
                    result[key] = result[key] + value
                elif list_strategy == "keep":
                    # 기존 값 유지
                    pass

            else:
                # 단순 값 - 덮어쓰기
                result[key] = value

        return result

    @staticmethod
    def extract_fields(
        data: Dict[str, Any], fields: List[str], strict: bool = False
    ) -> Dict[str, Any]:
        """
        딕셔너리에서 특정 필드만 추출

        Args:
            data: 원본 딕셔너리
            fields: 추출할 필드 목록
            strict: 엄격 모드 (필드 없을 시 KeyError)

        Returns:
            추출된 필드만 포함하는 딕셔너리

        Raises:
            KeyError: strict=True이고 필드가 없을 시
        """
        result = {}

        for field in fields:
            if field in data:
                result[field] = data[field]
            elif strict:
                raise KeyError(f"필드 '{field}'가 존재하지 않음")

        return result

    @staticmethod
    def rename_fields(data: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        딕셔너리 필드 이름 변경

        Args:
            data: 원본 딕셔너리
            mapping: {old_name: new_name} 매핑

        Returns:
            필드명이 변경된 딕셔너리
        """
        result = {}

        for key, value in data.items():
            new_key = mapping.get(key, key)
            result[new_key] = value

        return result

    @staticmethod
    def transform_values(
        data: Dict[str, Any], transformers: Dict[str, callable]
    ) -> Dict[str, Any]:
        """
        딕셔너리 값 변환

        Args:
            data: 원본 딕셔너리
            transformers: {field: transform_func} 매핑

        Returns:
            값이 변환된 딕셔너리
        """
        result = data.copy()

        for field, transform_func in transformers.items():
            if field in result:
                try:
                    result[field] = transform_func(result[field])
                except Exception as e:
                    logger.warning(f"필드 '{field}' 변환 실패: {e}")

        return result

    @staticmethod
    def flatten_dict(
        data: Dict[str, Any], separator: str = ".", prefix: str = ""
    ) -> Dict[str, Any]:
        """
        중첩된 딕셔너리를 평탄화

        Args:
            data: 중첩된 딕셔너리
            separator: 키 구분자
            prefix: 접두사

        Returns:
            평탄화된 딕셔너리

        Example:
            {"a": {"b": 1}} -> {"a.b": 1}
        """
        result = {}

        for key, value in data.items():
            new_key = f"{prefix}{separator}{key}" if prefix else key

            if isinstance(value, dict):
                # 재귀적 평탄화
                result.update(DataTransformer.flatten_dict(value, separator, new_key))
            else:
                result[new_key] = value

        return result

    @staticmethod
    def unflatten_dict(data: Dict[str, Any], separator: str = ".") -> Dict[str, Any]:
        """
        평탄화된 딕셔너리를 중첩 구조로 복원

        Args:
            data: 평탄화된 딕셔너리
            separator: 키 구분자

        Returns:
            중첩된 딕셔너리

        Example:
            {"a.b": 1} -> {"a": {"b": 1}}
        """
        result = {}

        for key, value in data.items():
            parts = key.split(separator)
            current = result

            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            current[parts[-1]] = value

        return result

    @staticmethod
    def filter_dict(data: Dict[str, Any], predicate: callable) -> Dict[str, Any]:
        """
        조건에 맞는 항목만 필터링

        Args:
            data: 원본 딕셔너리
            predicate: (key, value) -> bool 함수

        Returns:
            필터링된 딕셔너리
        """
        return {key: value for key, value in data.items() if predicate(key, value)}

    @staticmethod
    def clean_dict(
        data: Dict[str, Any],
        remove_none: bool = True,
        remove_empty: bool = True,
        remove_whitespace: bool = False,
    ) -> Dict[str, Any]:
        """
        딕셔너리 정제 (None, 빈 값 제거)

        Args:
            data: 원본 딕셔너리
            remove_none: None 값 제거
            remove_empty: 빈 문자열/리스트/딕셔너리 제거
            remove_whitespace: 공백만 있는 문자열 제거

        Returns:
            정제된 딕셔너리
        """
        result = {}

        for key, value in data.items():
            # None 체크
            if remove_none and value is None:
                continue

            # 빈 값 체크
            if remove_empty:
                if isinstance(value, (str, list, dict)) and not value:
                    continue

            # 공백 체크
            if remove_whitespace and isinstance(value, str) and not value.strip():
                continue

            # 중첩된 딕셔너리 재귀 처리
            if isinstance(value, dict):
                value = DataTransformer.clean_dict(
                    value, remove_none, remove_empty, remove_whitespace
                )

            result[key] = value

        return result


# 편의 함수들
def to_model(data: Dict[str, Any], model_class: Type[T]) -> Optional[T]:
    """Dict → Pydantic 모델 (단축 함수)"""
    return DataTransformer.dict_to_model(data, model_class, strict=False)


def to_dict(model: BaseModel, exclude_none: bool = True) -> Dict[str, Any]:
    """Pydantic 모델 → Dict (단축 함수)"""
    return DataTransformer.model_to_dict(model, exclude_none=exclude_none)


def normalize_id(raw_id: str, prefix: Optional[str] = None) -> str:
    """ID 정규화 (단축 함수)"""
    return DataTransformer.normalize_id(raw_id, prefix=prefix)


def merge_dicts(base: Dict, override: Dict, deep: bool = True) -> Dict:
    """딕셔너리 병합 (단축 함수)"""
    return DataTransformer.merge_dicts(base, override, deep=deep)


def clean_dict(data: Dict, remove_none: bool = True) -> Dict:
    """딕셔너리 정제 (단축 함수)"""
    return DataTransformer.clean_dict(data, remove_none=remove_none)
