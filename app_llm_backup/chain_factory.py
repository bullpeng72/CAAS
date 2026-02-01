"""
LLM Chain Factory

LangChain 체인 생성을 위한 팩토리 클래스
"""

from typing import Optional, Type, Any, Dict
from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.utils.logger import get_logger, LoggerMixin

logger = get_logger("llm.chain_factory")

# LangChain 선택적 import
LANGCHAIN_AVAILABLE = False
ChatPromptTemplate = None
JsonOutputParser = None

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    logger.warning(
        f"LangChain Core를 사용할 수 없습니다: {e}. "
        "설치하려면: pip install langchain-core"
    )


def check_langchain():
    """LangChain 가용성 체크"""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError(
            "langchain이 설치되지 않았습니다. "
            "pip install langchain-core langchain-openai"
        )


class BaseChainFactory(LoggerMixin, ABC):
    """
    LLM Chain 생성 기본 클래스

    공통 기능:
    - LLM 초기화
    - Prompt 템플릿 설정
    - Output Parser 설정 (Function Calling 지원)
    - Chain 조립

    하위 클래스는 다음을 구현해야 합니다:
    - get_system_prompt() -> str
    - get_user_prompt() -> str
    - get_output_model() -> Type[BaseModel]
    """

    def __init__(self, llm_config: Optional[Any] = None, use_function_calling: bool = True):
        """
        Chain 초기화

        Args:
            llm_config: LLM 설정 (LLMConfig 객체)
            use_function_calling: Function Calling 사용 여부 (기본: True)
                - True: LLM의 with_structured_output() 사용 (더 안정적)
                - False: JsonOutputParser 사용 (기존 방식)
        """
        check_langchain()

        self.use_function_calling = use_function_calling

        # LLM 초기화
        from app.llm.client import get_langchain_llm
        self.llm = get_langchain_llm(**(llm_config.model_dump() if llm_config else {}))

        # Prompt 템플릿 생성
        system_prompt = self.get_system_prompt()
        user_prompt = self.get_user_prompt()

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt),
        ])

        # Output 모델 가져오기
        output_model = self.get_output_model()

        # Chain 조립 (Function Calling 여부에 따라)
        if use_function_calling and hasattr(self.llm, 'with_structured_output'):
            # Function Calling 사용: with_structured_output으로 직접 Pydantic 모델 반환
            structured_llm = self.llm.with_structured_output(output_model)
            self.chain = self.prompt | structured_llm
            self.log_info(f"Chain 초기화 완료 (Function Calling 사용): {self.__class__.__name__}")
        else:
            # 기존 방식: JsonOutputParser 사용
            self.parser = JsonOutputParser(pydantic_object=output_model)
            self.chain = self.prompt | self.llm | self.parser
            self.log_info(f"Chain 초기화 완료 (JsonOutputParser 사용): {self.__class__.__name__}")

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        시스템 프롬프트 반환 (추상 메서드)

        Returns:
            시스템 프롬프트 문자열
        """
        raise NotImplementedError("Subclasses must implement get_system_prompt()")

    @abstractmethod
    def get_user_prompt(self) -> str:
        """
        사용자 프롬프트 반환 (추상 메서드)

        Returns:
            사용자 프롬프트 문자열
        """
        raise NotImplementedError("Subclasses must implement get_user_prompt()")

    @abstractmethod
    def get_output_model(self) -> Type[BaseModel]:
        """
        출력 모델 반환 (추상 메서드)

        Returns:
            Pydantic 모델 클래스
        """
        raise NotImplementedError("Subclasses must implement get_output_model()")

    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Chain 실행

        Args:
            inputs: 입력 변수 딕셔너리

        Returns:
            파싱된 출력 (dict)
        """
        self.log_debug(f"Chain 실행 시작: {list(inputs.keys())}")

        try:
            result = self.chain.invoke(inputs)

            # Function Calling 사용 시 Pydantic 모델이 반환되므로 dict로 변환
            if self.use_function_calling and isinstance(result, BaseModel):
                result = result.model_dump()

            self.log_info("Chain 실행 완료")
            return result

        except Exception as e:
            self.log_error(f"Chain 실행 실패: {e}", exc_info=True)
            raise

    def batch(self, inputs_list: list) -> list:
        """
        여러 입력에 대해 배치 실행

        Args:
            inputs_list: 입력 딕셔너리 리스트

        Returns:
            결과 리스트
        """
        self.log_info(f"배치 실행 시작: {len(inputs_list)}개 입력")

        try:
            results = self.chain.batch(inputs_list)

            # Function Calling 사용 시 Pydantic 모델이 반환되므로 dict로 변환
            if self.use_function_calling:
                results = [
                    r.model_dump() if isinstance(r, BaseModel) else r
                    for r in results
                ]

            self.log_info("배치 실행 완료")
            return results

        except Exception as e:
            self.log_error(f"배치 실행 실패: {e}", exc_info=True)
            raise


class SimpleChainFactory:
    """
    간단한 Chain 생성을 위한 헬퍼 클래스 (non-abstract)
    """

    @staticmethod
    def create_chain(
        system_prompt: str,
        user_prompt: str,
        output_model: Type[BaseModel],
        llm_config: Optional[Any] = None,
        use_function_calling: bool = True
    ):
        """
        Chain 생성 (일회성)

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            output_model: 출력 Pydantic 모델
            llm_config: LLM 설정
            use_function_calling: Function Calling 사용 여부 (기본: True)

        Returns:
            조립된 Chain
        """
        check_langchain()

        from app.llm.client import get_langchain_llm

        llm = get_langchain_llm(**(llm_config.model_dump() if llm_config else {}))

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt),
        ])

        # Function Calling 지원
        if use_function_calling and hasattr(llm, 'with_structured_output'):
            structured_llm = llm.with_structured_output(output_model)
            chain = prompt | structured_llm
            logger.info("Simple Chain 생성 완료 (Function Calling 사용)")
        else:
            parser = JsonOutputParser(pydantic_object=output_model)
            chain = prompt | llm | parser
            logger.info("Simple Chain 생성 완료 (JsonOutputParser 사용)")

        return chain

    @staticmethod
    def create_string_chain(
        system_prompt: str,
        user_prompt: str,
        llm_config: Optional[Any] = None
    ):
        """
        문자열 출력 Chain 생성

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            llm_config: LLM 설정

        Returns:
            조립된 Chain (문자열 출력)
        """
        check_langchain()

        from app.llm.client import get_langchain_llm
        from langchain_core.output_parsers import StrOutputParser

        llm = get_langchain_llm(**(llm_config.model_dump() if llm_config else {}))

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt),
        ])

        parser = StrOutputParser()

        chain = prompt | llm | parser

        logger.info("String Chain 생성 완료")
        return chain


# 편의 함수
def create_json_chain(
    system_prompt: str,
    user_prompt: str,
    output_model: Type[BaseModel],
    llm_config: Optional[Any] = None,
    use_function_calling: bool = True
):
    """JSON 출력 Chain 생성 (단축 함수)"""
    return SimpleChainFactory.create_chain(
        system_prompt, user_prompt, output_model, llm_config, use_function_calling
    )


def create_text_chain(
    system_prompt: str,
    user_prompt: str,
    llm_config: Optional[Any] = None
):
    """텍스트 출력 Chain 생성 (단축 함수)"""
    return SimpleChainFactory.create_string_chain(
        system_prompt, user_prompt, llm_config
    )
