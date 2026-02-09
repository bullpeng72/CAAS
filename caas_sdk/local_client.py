"""
CAAS Local SDK Client

Synchronous wrapper around CAAS_API for local execution (no REST API required).
Provides a simple, batteries-included interface for Python applications.
"""

import asyncio
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from caas_framework.utils.logger import get_logger

logger = get_logger()


class CAASLocalClient:
    """
    CAAS Local SDK Client

    Synchronous wrapper around the async CAAS_API for local execution.
    No REST API server required - directly uses the CAAS framework.

    Examples:
        # Basic usage
        from caas_sdk.local_client import CAASLocalClient

        client = CAASLocalClient(api_key="sk-...")
        result = client.generate("Create a blog system")

        logger.info(f"Generated {len(result['files'])} files")
        for filename in result['files']:
            logger.info(f"  - {filename}")
        # Advanced usage with configuration
        client = CAASLocalClient(
            api_key="sk-...",
            config={
                "enable_plan_mode": True,
                "output_dir": "./my_project",
                "verbosity": "verbose"
            }
        )

        result = client.generate("Create a blog system")

        # Generate from design
        result = client.generate_from_design(
            agents=[
                {"id": "writer", "role": "Content Writer", ...},
                {"id": "editor", "role": "Content Editor", ...}
            ],
            tasks=[
                {"description": "Write article", "agent": "writer", ...},
                {"description": "Edit article", "agent": "editor", ...}
            ]
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        event_callback: Optional[Callable] = None,
    ):
        """
        Initialize CAAS Local Client.

        Args:
            api_key: LLM API key (OpenAI, etc.)
            config: Configuration dictionary (maps to GenerationConfig)
            event_callback: Optional callback for framework events

        Configuration Options:
            - llm_provider: "openai" (default)
            - llm_model: "gpt-4" (default)
            - llm_temperature: 0.7 (default)
            - enable_plan_mode: False (default)
            - enable_feedback_loop: True (default)
            - enable_validation: True (default)
            - max_retries: 3 (default)
            - max_feedback_loops: 3 (default)
            - output_dir: "./generated" (default)
            - overwrite_existing: False (default)
            - verbosity: "normal" (default) - options: quiet, minimal, normal, verbose, debug
        """
        from caas_framework.api.caas_api import CAAS_API, GenerationConfig

        # Merge config with API key
        full_config = config or {}
        if api_key:
            full_config["llm_api_key"] = api_key

        # Create GenerationConfig
        self.config = GenerationConfig(**full_config)

        # Create API instance
        self.api = CAAS_API(self.config)

        # Setup event callback
        if event_callback:
            self._setup_event_callback(event_callback)

        # Create event loop for sync execution
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        logger.info("CAAS Local Client initialized")

    def generate(
        self, requirement: str, golden_data: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Generate code from natural language requirement (synchronous).

        Args:
            requirement: Natural language requirement (e.g., "Create a blog system")
            golden_data: Optional pre-generated Golden Data

        Returns:
            Generation result dictionary:
            {
                "success": bool,
                "files": {"main.py": "...", "agents.py": "...", ...},
                "metadata": {
                    "duration": 45.2,
                    "phases_completed": ["discovery", "architecture", ...],
                    "feedback_loops_executed": 2,
                    "agents_used": ["RequirementAnalyst", "SystemArchitect", ...]
                },
                "errors": [],
                "warnings": []
            }

        Examples:
            client = CAASLocalClient(api_key="sk-...")

            # Simple generation
            result = client.generate("Create a blog system with user auth")

            if result['success']:
                logger.info(f"Generated {len(result['files'])} files")
                for filename, content in result['files'].items():
                    logger.info(f"  {filename}: {len(content)} bytes")
            else:
                logger.error(f"Generation failed: {result['errors']}")
        """
        logger.info(f"Generating code for: {requirement[:100]}...")

        # Run async API call in event loop
        result = self.loop.run_until_complete(
            self.api.generate(requirement, golden_data)
        )

        # Convert GenerationResult to dict
        return self._result_to_dict(result)

    def generate_from_design(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        workflow_type: str = "sequential",
    ) -> Dict[str, Any]:
        """
        Generate code from agent/task design (synchronous).

        Skips Discovery and Design phases, directly generates code.

        Args:
            agents: List of agent definitions
            tasks: List of task definitions
            workflow_type: "sequential" or "hierarchical"

        Returns:
            Generation result dictionary (same format as generate())

        Examples:
            client = CAASLocalClient(api_key="sk-...")

            result = client.generate_from_design(
                agents=[
                    {
                        "id": "writer",
                        "role": "Content Writer",
                        "goal": "Write high-quality blog posts",
                        "backstory": "Expert content creator...",
                        "tools": ["web_search", "file_writer"]
                    },
                    {
                        "id": "editor",
                        "role": "Content Editor",
                        "goal": "Edit and improve content",
                        "backstory": "Experienced editor...",
                        "tools": ["file_reader", "file_writer"]
                    }
                ],
                tasks=[
                    {
                        "description": "Write a blog post about AI",
                        "agent": "writer",
                        "expected_output": "A well-written blog post"
                    },
                    {
                        "description": "Edit the blog post",
                        "agent": "editor",
                        "expected_output": "Edited and polished content"
                    }
                ],
                workflow_type="sequential"
            )

            logger.info(result['files']['main.py'])
        """
        logger.info(
            f"Generating code from design: {len(agents)} agents, {len(tasks)} tasks"
        )

        # Run async API call
        result = self.loop.run_until_complete(
            self.api.generate_from_design(agents, tasks, workflow_type)
        )

        return self._result_to_dict(result)

    def subscribe_event(self, event_type: str, callback: Callable[[Any], None]):
        """
        Subscribe to framework events.

        Args:
            event_type: Event type (e.g., "phase_start", "phase_complete")
            callback: Callback function

        Examples:
            def on_phase_start(event):
                logger.info(f"Starting phase: {event.phase}")
            client = CAASLocalClient(api_key="sk-...")
            client.subscribe_event("phase_start", on_phase_start)

            result = client.generate("Create a blog system")
        """
        self.api.subscribe_event(event_type, callback)

    def unsubscribe_event(self, event_type: str, callback: Callable[[Any], None]):
        """
        Unsubscribe from framework events.

        Args:
            event_type: Event type
            callback: Callback function
        """
        self.api.unsubscribe_event(event_type, callback)

    def save_files(
        self, files: Dict[str, str], output_dir: str, overwrite: bool = False
    ):
        """
        Save generated files to disk.

        Args:
            files: Dictionary of filename -> content
            output_dir: Output directory path
            overwrite: Whether to overwrite existing files

        Examples:
            result = client.generate("Create a blog system")

            if result['success']:
                client.save_files(
                    result['files'],
                    output_dir="./my_blog_project",
                    overwrite=False
                )
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Saving {len(files)} files to {output_dir}")

        for filename, content in files.items():
            file_path = output_path / filename

            # Check overwrite
            if file_path.exists() and not overwrite:
                logger.warning(f"File exists, skipping: {filename}")
                continue

            # Write file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

            logger.debug(f"Saved: {filename}")

        logger.info(f"All files saved to {output_dir}")

    # ===========================================
    # Private helper methods
    # ===========================================

    def _setup_event_callback(self, callback: Callable):
        """Setup event callback for all event types"""
        event_types = [
            "phase_start",
            "phase_complete",
            "agent_start",
            "agent_complete",
            "validation_start",
            "validation_complete",
        ]

        for event_type in event_types:
            self.api.subscribe_event(event_type, callback)

    def _result_to_dict(self, result: Any) -> Dict[str, Any]:
        """
        Convert GenerationResult to dictionary.

        Args:
            result: GenerationResult

        Returns:
            Dictionary representation
        """
        return {
            "success": result.success,
            "files": result.files,
            "metadata": result.metadata,
            "errors": result.errors,
            "warnings": result.warnings,
        }

    def close(self):
        """Close event loop (cleanup)"""
        if self.loop and not self.loop.is_closed():
            self.loop.close()
        logger.info("CAAS Local Client closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Convenience function for quick usage
def generate(
    requirement: str,
    api_key: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Quick generation function (convenience wrapper).

    Args:
        requirement: Natural language requirement
        api_key: LLM API key
        config: Optional configuration

    Returns:
        Generation result dictionary

    Examples:
        from caas_sdk.local_client import generate

        result = generate(
            "Create a blog system",
            api_key="sk-..."
        )

        logger.info(result['files'].keys())
    """
    with CAASLocalClient(api_key=api_key, config=config) as client:
        return client.generate(requirement)
