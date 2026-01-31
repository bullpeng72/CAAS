"""
CAAS Secrets Management

API 키 및 민감한 구성의 안전한 처리.
"""

import os
from typing import Optional, Dict
from functools import lru_cache


class SecretManager:
    """
    안전한 비밀 관리.

    os.environ에 비밀을 노출하는 것을 피합니다:
    - 하위 프로세스에서 읽힘
    - 로그에 누출
    - /proc/self/environ을 통한 노출
    """

    _instance = None
    _secrets: Dict[str, str] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def set_secret(self, key: str, value: str) -> None:
        """
        비밀을 안전하게 저장.

        Args:
            key: 비밀 키 이름
            value: 비밀 값
        """
        self._secrets[key] = value

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        비밀을 안전하게 검색.

        Args:
            key: 비밀 키 이름
            default: 찾을 수 없는 경우 기본값

        Returns:
            str: 비밀 값 또는 기본값
        """
        return self._secrets.get(key, default)

    def has_secret(self, key: str) -> bool:
        """비밀이 존재하는지 확인."""
        return key in self._secrets

    def clear_secret(self, key: str) -> None:
        """비밀 제거."""
        if key in self._secrets:
            # 삭제 전 덮어쓰기 (최선의 노력)
            self._secrets[key] = "0" * len(self._secrets[key])
            del self._secrets[key]

    def get_for_subprocess(self, key: str) -> Dict[str, str]:
        """
        필요할 때만 서브프로세스용 비밀을 환경 dict로 가져오기.

        Args:
            key: 비밀 키 이름

        Returns:
            dict: 비밀이 포함된 환경 dict
        """
        value = self.get_secret(key)
        if value:
            return {key: value}
        return {}


@lru_cache()
def get_secret_manager() -> SecretManager:
    """싱글톤 비밀 관리자 가져오기."""
    return SecretManager()


def mask_secret(secret: str, visible_chars: int = 4) -> str:
    """
    안전한 로깅을 위해 비밀 마스킹.

    Args:
        secret: 마스킹할 비밀
        visible_chars: 표시할 문자 수

    Returns:
        str: 마스킹된 비밀 (예: "sk-...xyz")
    """
    if not secret or len(secret) <= visible_chars:
        return "***"

    prefix_len = min(visible_chars, len(secret) // 4)
    suffix_len = min(visible_chars, len(secret) // 4)

    return f"{secret[:prefix_len]}...{secret[-suffix_len:]}"
