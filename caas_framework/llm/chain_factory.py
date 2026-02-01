"""
LLM Chain Factory

Factory classes for creating LangChain chains.
"""

import logging
from typing import Optional, Type, Any, Dict
from abc import ABC, abstractmethod

from pydantic import BaseModel

logger = logging.getLogger("caas_framework.llm.chain_factory")

# LangChain optional import
LANGCHAIN_AVAILABLE = False
ChatPromptTemplate = None
JsonOutputParser = None

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    logger.warning(
        f"LangChain Core not available: {e}. "
        "Install with: pip install langchain-core"
    )


def check_langchain():
    """Check LangChain availability"""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError(
            "langchain not installed. "
            "pip install langchain-core langchain-openai"
        )


class BaseChainFactory(ABC):
    """
    Base class for LLM Chain creation

    Common functionality:
    - LLM initialization
    - Prompt template setup
    - Output Parser setup (Function Calling support)
    - Chain assembly

    Subclasses must implement:
    - get_system_prompt() -> str
    - get_user_prompt() -> str
    - get_output_model() -> Type[BaseModel]
    """

    def __init__(self, llm_config: Optional[Any] = None, use_function_calling: bool = True):
        """
        Initialize Chain

        Args:
            llm_config: LLM configuration (LLMConfig object)
            use_function_calling: Whether to use Function Calling (default: True)
                - True: Use LLM's with_structured_output() (more stable)
                - False: Use JsonOutputParser (legacy)
        """
        check_langchain()

        self.use_function_calling = use_function_calling
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")

        # Initialize LLM
        from caas_framework.llm.client import get_langchain_llm
        self.llm = get_langchain_llm(**(llm_config.model_dump() if llm_config else {}))

        # Create prompt template
        system_prompt = self.get_system_prompt()
        user_prompt = self.get_user_prompt()

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt),
        ])

        # Get output model
        output_model = self.get_output_model()

        # Assemble chain (depending on Function Calling)
        if use_function_calling and hasattr(self.llm, 'with_structured_output'):
            # Use Function Calling: with_structured_output returns Pydantic model directly
            structured_llm = self.llm.with_structured_output(output_model)
            self.chain = self.prompt | structured_llm
            self.logger.info(f"Chain initialized (Function Calling): {self.__class__.__name__}")
        else:
            # Legacy: Use JsonOutputParser
            self.parser = JsonOutputParser(pydantic_object=output_model)
            self.chain = self.prompt | self.llm | self.parser
            self.logger.info(f"Chain initialized (JsonOutputParser): {self.__class__.__name__}")

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Return system prompt (abstract method)

        Returns:
            System prompt string
        """
        raise NotImplementedError("Subclasses must implement get_system_prompt()")

    @abstractmethod
    def get_user_prompt(self) -> str:
        """
        Return user prompt (abstract method)

        Returns:
            User prompt string
        """
        raise NotImplementedError("Subclasses must implement get_user_prompt()")

    @abstractmethod
    def get_output_model(self) -> Type[BaseModel]:
        """
        Return output model (abstract method)

        Returns:
            Pydantic model class
        """
        raise NotImplementedError("Subclasses must implement get_output_model()")

    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute chain

        Args:
            inputs: Input variable dictionary

        Returns:
            Parsed output (dict)
        """
        self.logger.debug(f"Chain execution started: {list(inputs.keys())}")

        try:
            result = self.chain.invoke(inputs)

            # Convert Pydantic model to dict when using Function Calling
            if self.use_function_calling and isinstance(result, BaseModel):
                result = result.model_dump()

            self.logger.info("Chain execution completed")
            return result

        except Exception as e:
            self.logger.error(f"Chain execution failed: {e}", exc_info=True)
            raise

    def batch(self, inputs_list: list) -> list:
        """
        Batch execution for multiple inputs

        Args:
            inputs_list: List of input dictionaries

        Returns:
            List of results
        """
        self.logger.info(f"Batch execution started: {len(inputs_list)} inputs")

        try:
            results = self.chain.batch(inputs_list)

            # Convert Pydantic models to dicts when using Function Calling
            if self.use_function_calling:
                results = [
                    r.model_dump() if isinstance(r, BaseModel) else r
                    for r in results
                ]

            self.logger.info("Batch execution completed")
            return results

        except Exception as e:
            self.logger.error(f"Batch execution failed: {e}", exc_info=True)
            raise


class SimpleChainFactory:
    """
    Helper class for simple Chain creation (non-abstract)
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
        Create chain (one-time)

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            output_model: Output Pydantic model
            llm_config: LLM configuration
            use_function_calling: Whether to use Function Calling (default: True)

        Returns:
            Assembled Chain
        """
        check_langchain()

        from caas_framework.llm.client import get_langchain_llm

        llm = get_langchain_llm(**(llm_config.model_dump() if llm_config else {}))

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt),
        ])

        # Function Calling support
        if use_function_calling and hasattr(llm, 'with_structured_output'):
            structured_llm = llm.with_structured_output(output_model)
            chain = prompt | structured_llm
            logger.info("Simple Chain created (Function Calling)")
        else:
            parser = JsonOutputParser(pydantic_object=output_model)
            chain = prompt | llm | parser
            logger.info("Simple Chain created (JsonOutputParser)")

        return chain

    @staticmethod
    def create_string_chain(
        system_prompt: str,
        user_prompt: str,
        llm_config: Optional[Any] = None
    ):
        """
        Create string output Chain

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            llm_config: LLM configuration

        Returns:
            Assembled Chain (string output)
        """
        check_langchain()

        from caas_framework.llm.client import get_langchain_llm
        from langchain_core.output_parsers import StrOutputParser

        llm = get_langchain_llm(**(llm_config.model_dump() if llm_config else {}))

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt),
        ])

        parser = StrOutputParser()

        chain = prompt | llm | parser

        logger.info("String Chain created")
        return chain


# Convenience functions
def create_json_chain(
    system_prompt: str,
    user_prompt: str,
    output_model: Type[BaseModel],
    llm_config: Optional[Any] = None,
    use_function_calling: bool = True
):
    """Create JSON output Chain (shortcut)"""
    return SimpleChainFactory.create_chain(
        system_prompt, user_prompt, output_model, llm_config, use_function_calling
    )


def create_text_chain(
    system_prompt: str,
    user_prompt: str,
    llm_config: Optional[Any] = None
):
    """Create text output Chain (shortcut)"""
    return SimpleChainFactory.create_string_chain(
        system_prompt, user_prompt, llm_config
    )
