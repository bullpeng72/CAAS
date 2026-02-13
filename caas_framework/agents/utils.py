"""
Agent Utilities

Common utilities for expert agents to eliminate duplication:
- Prompt templates and builders
- Output parsers and validators
- Error handlers and retry logic
- Common validation schemas
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar

from caas_framework.config.settings import LLMConstants
from caas_framework.models.specifications import ConcretizedRequirement
from caas_framework.utils import PromptBuilder, ResponseParser

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AgentPromptTemplates:
    """
    Standard prompt templates for expert agents.

    Consolidates common prompt patterns to reduce duplication.
    """

    @staticmethod
    def build_analysis_prompt(
        requirement: str,
        agent_role: str,
        golden_data: Optional[ConcretizedRequirement] = None,
        context: Optional[Dict[str, Any]] = None,
        previous_outputs: Optional[Dict[str, Any]] = None,
        output_format: Dict[str, Any] = None,
        guidelines: Optional[List[str]] = None,
    ) -> str:
        """
        Build standard analysis prompt.

        Used by: RequirementAnalyst, SystemArchitect, AgentDesigner

        Args:
            requirement: User requirement text
            agent_role: Role of the agent (e.g., "Expert Requirements Analyst")
            golden_data: Optional Golden Data reference
            context: Additional context
            previous_outputs: Previous phase outputs
            output_format: Expected output schema
            guidelines: List of guidelines

        Returns:
            Complete prompt string
        """
        # ✅ v0.5.0: 한국어 출력 강제 (P0 수정)
        builder = PromptBuilder(
            f"analyze the following requirement as {agent_role}"
        ).add_task(f"""You are an {agent_role}.

**CRITICAL: Output all text values in Korean (한국어).**
- Keep JSON keys in English
- Write all values (descriptions, names, comments) in Korean
- Exception: Technical terms, code, and identifiers can remain in English""")

        # Add requirement
        builder.add_input(requirement=requirement)

        # Add golden data if available
        if golden_data:
            builder.add_golden_data(
                golden_data,
                fields=["domain", "project_name", "features", "data_models"],
            )

        # Add previous outputs
        if previous_outputs:
            builder.add_previous_outputs(previous_outputs)

        # Add context
        if context:
            builder.add_context("Additional Context", context)

        # Add output format
        if output_format:
            builder.add_output_format(output_format, "Provide analysis in JSON format:")

        # Add guidelines
        if guidelines:
            builder.add_guidelines(guidelines)

        return builder.build()

    @staticmethod
    def build_refinement_prompt(
        agent_role: str,
        output_type: str,
        current_output: Dict[str, Any],
        issues_summary: str,
        iteration: int,
        golden_data_context: Optional[str] = None,
        guidelines: Optional[List[str]] = None,
    ) -> str:
        """
        Build standard refinement prompt.

        Used by: All agents via RefinementExecutor

        Args:
            agent_role: Role description
            output_type: Type of output being refined
            current_output: Current output to refine
            issues_summary: Formatted validation issues
            iteration: Refinement iteration number
            golden_data_context: Optional Golden Data context
            guidelines: Refinement guidelines

        Returns:
            Refinement prompt string
        """
        prompt_parts = [
            f"# Task: Refine {output_type} (Iteration {iteration})",
            f"You are an {agent_role} refining your previous output based on validation feedback.",
            "",
            "## Current Output",
            f"```json\n{json.dumps(current_output, indent=2)}\n```",
            "",
            "## Validation Issues",
            issues_summary,
            "",
        ]

        if golden_data_context:
            prompt_parts.extend([
                "## Golden Data Context",
                golden_data_context,
                "",
            ])

        prompt_parts.extend([
            "## Guidelines",
        ])

        if guidelines:
            prompt_parts.extend([f"- {g}" for g in guidelines])
        else:
            prompt_parts.extend([
                "- Address each validation issue specifically",
                "- Maintain consistency with Golden Data (if provided)",
                "- Preserve correct parts of the original output",
                "- Only change what needs to be fixed",
            ])

        prompt_parts.extend([
            "",
            "## Output",
            f"Provide refined {output_type} in the same JSON format as the current output.",
        ])

        return "\n".join(prompt_parts)


class AgentOutputParser:
    """
    Standard output parsers for agent responses.

    Consolidates parsing logic to reduce duplication.
    ✅ v0.4.3 (Bug #3): Enhanced with LLM response parsing support
    """

    @staticmethod
    def parse_json_safe(output: Any, default: Optional[Dict] = None) -> Dict:
        """
        Safe JSON parsing with LLM response support.

        ✅ v0.4.3 (Bug #3): Replaces old parse_json_safe with enhanced
        LLM response handling using LLMResponseParser.

        Handles:
        - LLMResponse objects
        - Raw JSON strings
        - Markdown-wrapped JSON
        - Malformed JSON with automatic repair

        Args:
            output: LLM response (any type)
            default: Default value if parsing fails

        Returns:
            Parsed dictionary or default

        Example:
            >>> from caas_framework.agents.utils import AgentOutputParser
            >>> result = AgentOutputParser.parse_json_safe(llm_response)
        """
        from caas_framework.utils.json_parser import LLMResponseParser
        return LLMResponseParser.parse_json_safe(output, default=default)

    @staticmethod
    async def parse_llm_json(
        response: str,
        expected_fields: List[str],
        fallback_factory: Callable[[], Dict[str, Any]],
        agent_name: str = "Agent",
    ) -> Dict[str, Any]:
        """
        Parse LLM JSON response with fallback.

        Args:
            response: Raw LLM response
            expected_fields: Required field names
            fallback_factory: Factory to create fallback response
            agent_name: Agent name for logging

        Returns:
            Parsed JSON dict
        """
        try:
            result = ResponseParser.parse_structured_response(
                response,
                expected_fields=expected_fields,
                fallback_factory=fallback_factory,
            )

            # Validate expected fields
            missing = [f for f in expected_fields if f not in result]
            if missing:
                logger.warning(
                    f"[{agent_name}] Missing expected fields: {missing}, using fallback"
                )
                return fallback_factory()

            return result

        except Exception as e:
            logger.error(f"[{agent_name}] Failed to parse LLM response: {e}")
            return fallback_factory()

    @staticmethod
    def validate_output_schema(
        output: Dict[str, Any],
        required_fields: List[str],
        agent_name: str = "Agent",
    ) -> bool:
        """
        Validate output against schema.

        Args:
            output: Output dictionary to validate
            required_fields: Required field names
            agent_name: Agent name for logging

        Returns:
            True if valid, False otherwise
        """
        missing = [f for f in required_fields if f not in output]
        if missing:
            logger.error(
                f"[{agent_name}] Output validation failed. Missing fields: {missing}"
            )
            return False
        return True


class AgentErrorHandler:
    """
    Standard error handling for agents.

    Consolidates error handling patterns.
    """

    @staticmethod
    async def with_retry(
        func: Callable,
        max_retries: int = 3,
        agent_name: str = "Agent",
        operation: str = "operation",
    ) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Async function to execute
            max_retries: Maximum retry attempts
            agent_name: Agent name for logging
            operation: Operation description

        Returns:
            Function result

        Raises:
            Exception if all retries fail
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                last_error = e
                logger.warning(
                    f"[{agent_name}] {operation} failed (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    # Exponential backoff (not actually waiting, just logging)
                    logger.info(f"[{agent_name}] Retrying {operation}...")
                    continue
                else:
                    logger.error(f"[{agent_name}] {operation} failed after {max_retries} attempts")
                    raise last_error

    @staticmethod
    def log_agent_error(
        agent_name: str,
        phase: str,
        operation: str,
        error: Exception,
    ) -> None:
        """
        Log agent error with consistent format.

        Args:
            agent_name: Agent name
            phase: Phase name
            operation: Operation that failed
            error: Exception object
        """
        logger.error(
            f"[{agent_name}] [{phase}] {operation} failed: {type(error).__name__}: {error}"
        )


class AgentValidators:
    """
    Common validation schemas and validators.
    """

    # Standard validation schemas for agent outputs
    REQUIREMENT_ANALYSIS_SCHEMA = {
        "functional_requirements": list,
        "non_functional_requirements": dict,
        "constraints": list,
        "success_criteria": list,
    }

    ARCHITECTURE_SCHEMA = {
        "components": list,
        "data_flow": dict,
        "integration_points": list,
        "technology_stack": dict,
    }

    AGENT_DESIGN_SCHEMA = {
        "agents": list,
        "tasks": list,
        "workflow_type": str,
        "agent_collaboration_pattern": str,
    }

    CODE_GENERATION_SCHEMA = {
        "files": dict,
    }

    QA_REPORT_SCHEMA = {
        "qa_report": dict,
        "compliance_check": dict,
        "test_results": dict,
        "recommendations": list,
    }

    @staticmethod
    def validate_by_schema(
        output: Dict[str, Any],
        schema: Dict[str, type],
        agent_name: str = "Agent",
    ) -> bool:
        """
        Validate output against type schema.

        Args:
            output: Output to validate
            schema: Schema dict mapping field -> expected type
            agent_name: Agent name for logging

        Returns:
            True if valid, False otherwise
        """
        for field, expected_type in schema.items():
            if field not in output:
                logger.error(f"[{agent_name}] Missing required field: {field}")
                return False

            if not isinstance(output[field], expected_type):
                logger.error(
                    f"[{agent_name}] Field '{field}' has wrong type. "
                    f"Expected {expected_type}, got {type(output[field])}"
                )
                return False

        return True
