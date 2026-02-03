"""
LLM Helper Utilities

Utilities for standardized LLM invocation patterns.
Consolidates duplicate LLM calling code from across the framework.
"""

import logging
from typing import Any, Optional

from caas_framework.utils.logger import get_logger

# Get logger
logger = get_logger()


class LLMHelper:
    """Helper class for LLM invocation operations"""

    @staticmethod
    def invoke_with_message(
        llm_client: Any, prompt: str, temperature: Optional[float] = None
    ) -> str:
        """
        Invoke LLM with a prompt using standard message format.

        Consolidates the pattern:
        ```python
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content
        ```

        Args:
            llm_client: LLM client instance (supports langchain interface)
            prompt: Prompt text to send to LLM
            temperature: Optional temperature setting

        Returns:
            Response content as string

        Raises:
            Exception: If LLM invocation fails
        """
        try:
            from langchain_core.messages import HumanMessage

            # Prepare message
            message = HumanMessage(content=prompt)

            # Invoke with optional temperature
            if temperature is not None:
                response = llm_client.invoke([message], temperature=temperature)
            else:
                response = llm_client.invoke([message])

            # Extract content
            if hasattr(response, "content"):
                return response.content
            else:
                # Fallback: convert to string
                return str(response)

        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            raise

    @staticmethod
    def safe_invoke_with_message(
        llm_client: Any,
        prompt: str,
        default_value: str = "",
        temperature: Optional[float] = None,
        context: str = "LLM call",
    ) -> str:
        """
        Safely invoke LLM with error handling and logging.

        Args:
            llm_client: LLM client instance
            prompt: Prompt text to send to LLM
            default_value: Value to return on error
            temperature: Optional temperature setting
            context: Context description for logging

        Returns:
            Response content or default_value on error
        """
        try:
            return LLMHelper.invoke_with_message(llm_client, prompt, temperature)
        except Exception as e:
            logger.warning(f"{context} failed: {e}")
            return default_value
