"""
LLM Helper

LLM 호출을 위한 통합 유틸리티
"""

from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
from fastapi import HTTPException

from app.config import settings
from app.utils.config import get_api_key
from app.utils.json_helper import JSONHelper
from app.utils.logger import get_logger

logger = get_logger("utils.llm_helper")


class LLMHelper:
    """LLM 호출 통합 유틸리티"""

    @staticmethod
    async def call_openai_json(
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        model: Optional[str] = None,
        ensure_json_instruction: bool = True
    ) -> Dict[str, Any]:
        """
        OpenAI API를 호출하고 JSON 응답을 반환합니다.

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            temperature: 온도 (0.0 ~ 2.0)
            max_tokens: 최대 토큰 수
            model: 모델 이름 (None이면 설정에서 가져옴)
            ensure_json_instruction: JSON 응답 지시 추가 여부

        Returns:
            파싱된 JSON 응답

        Raises:
            HTTPException: API 키 미설정 또는 API 오류
        """
        # API 키 확인
        api_key = get_api_key("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY가 설정되지 않음")
            raise HTTPException(
                status_code=500,
                detail="OPENAI_API_KEY not configured"
            )

        # 모델 선택
        if model is None:
            model = settings.llm.default_llm_model

        # JSON 응답 지시 추가
        system = system_prompt
        if ensure_json_instruction:
            system += "\n\nIMPORTANT: You must respond with valid JSON only. Do not include any explanatory text outside the JSON structure."

        logger.info(f"LLM 호출 시작: model={model}, temp={temperature}, max_tokens={max_tokens}")
        logger.debug(f"System prompt: {system_prompt[:100]}...")
        logger.debug(f"User prompt: {user_prompt[:100]}...")

        try:
            # OpenAI API 호출
            client = AsyncOpenAI(api_key=api_key)
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens
            )

            # 응답 추출
            result_text = response.choices[0].message.content
            logger.debug(f"LLM 응답: {len(result_text)} chars")

            # JSON 파싱
            result_json = JSONHelper.extract_from_markdown(result_text)

            if result_json is None:
                logger.error("JSON 파싱 실패")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to parse LLM response as JSON"
                )

            logger.info("LLM 호출 성공")
            return result_json

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"LLM 호출 오류: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"LLM API error: {str(e)}"
            )

    @staticmethod
    async def call_openai_text(
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        model: Optional[str] = None
    ) -> str:
        """
        OpenAI API를 호출하고 텍스트 응답을 반환합니다.

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            temperature: 온도 (0.0 ~ 2.0)
            max_tokens: 최대 토큰 수
            model: 모델 이름 (None이면 설정에서 가져옴)

        Returns:
            텍스트 응답

        Raises:
            HTTPException: API 키 미설정 또는 API 오류
        """
        # API 키 확인
        api_key = get_api_key("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY가 설정되지 않음")
            raise HTTPException(
                status_code=500,
                detail="OPENAI_API_KEY not configured"
            )

        # 모델 선택
        if model is None:
            model = settings.llm.default_llm_model

        logger.info(f"LLM 텍스트 호출 시작: model={model}")

        try:
            # OpenAI API 호출
            client = AsyncOpenAI(api_key=api_key)
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            # 응답 추출
            result_text = response.choices[0].message.content
            logger.info(f"LLM 텍스트 응답: {len(result_text)} chars")
            return result_text

        except Exception as e:
            logger.error(f"LLM 호출 오류: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"LLM API error: {str(e)}"
            )


# 편의 함수
async def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    **kwargs
) -> Dict[str, Any]:
    """통합 LLM JSON 호출 (단축 함수)"""
    return await LLMHelper.call_openai_json(system_prompt, user_prompt, **kwargs)


async def call_llm_text(
    system_prompt: str,
    user_prompt: str,
    **kwargs
) -> str:
    """통합 LLM 텍스트 호출 (단축 함수)"""
    return await LLMHelper.call_openai_text(system_prompt, user_prompt, **kwargs)
