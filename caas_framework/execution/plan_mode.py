"""
Plan Mode - User Review Before Code Generation

Allows users to review and approve specifications before generating code.
This prevents wasted effort from incorrect requirements.
"""

from enum import Enum

# Type checking imports
from typing import TYPE_CHECKING, Any, Dict

from caas_framework.utils.logger import get_logger

logger = get_logger(__name__)


if TYPE_CHECKING:
    pass


class ApprovalDecision(Enum):
    """User approval decision"""

    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"


class PlanMode:
    """
    Plan Mode orchestrator

    Provides approval gates at critical points:
    1. After Phase 0 (Concretization) - Review requirements
    2. After Phase 3 (Design) - Review agents and tasks
    3. Before Phase 5 (Code Generation) - Final approval
    """

    def __init__(self, auto_approve: bool = False) -> None:
        """
        Initialize Plan Mode.

        Args:
            auto_approve: If True, skip user prompts (for testing)
        """
        self.auto_approve: bool = auto_approve

    def review_concretized_requirements(self, concretized: Any) -> ApprovalDecision:
        """
        Review concretized requirements (after Phase 0).

        Args:
            concretized: ConcretizedRequirement object

        Returns:
            ApprovalDecision
        """
        if self.auto_approve:
            return ApprovalDecision.APPROVE

        logger.info("\n" + "=" * 70)
        logger.info("PHASE 0 COMPLETE: Requirements Concretization")
        logger.info("=" * 70)
        # Display project info
        logger.info(f"\n📋 Project: {concretized.project_name}")
        logger.info(f"📝 Description: {concretized.description}")
        # Display features
        if concretized.features:
            logger.info(f"\n✨ Features ({len(concretized.features)}):")
            for i, feature in enumerate(concretized.features[:10], 1):  # Limit to 10
                priority_emoji = (
                    "🔴"
                    if feature.priority == "high"
                    else "🟡"
                    if feature.priority == "medium"
                    else "⚪"
                )
                logger.info(f"  {i}. [{priority_emoji} {feature.priority}] {feature.name}")
                if len(feature.description) <= 80:
                    logger.info(f"     {feature.description}")
        # Display data models
        if concretized.data_models:
            logger.info(f"\n💾 Data Models ({len(concretized.data_models)}):")
            for i, model in enumerate(concretized.data_models[:5], 1):
                logger.info(f"  {i}. {model.entity_name}: {len(model.attributes)} attributes")
        # Display boundaries if available
        if hasattr(concretized, "boundaries") and concretized.boundaries:
            logger.info("\n🔒 Security Boundaries:")
            if concretized.boundaries.never_allowed:
                print(
                    f"  ❌ Never Allowed: {len(concretized.boundaries.never_allowed)} restrictions"
                )
            if concretized.boundaries.ask_first:
                print(
                    f"  ⚠️ Ask First: {len(concretized.boundaries.ask_first)} operations"
                )

        # Get approval
        logger.info("\n" + "=" * 70)
        choice = input("Review this specification? (approve/edit/reject): ").lower()

        if choice in ["a", "approve", "yes", "y"]:
            return ApprovalDecision.APPROVE
        elif choice in ["e", "edit"]:
            return ApprovalDecision.EDIT
        else:
            return ApprovalDecision.REJECT

    def review_design(self, design: Dict[str, Any]) -> ApprovalDecision:
        """
        Review agent and task design (after Phase 3).

        Args:
            design: Design output with agents and tasks

        Returns:
            ApprovalDecision
        """
        if self.auto_approve:
            return ApprovalDecision.APPROVE

        logger.info("\n" + "=" * 70)
        logger.info("PHASE 3 COMPLETE: Agent & Task Design")
        logger.info("=" * 70)
        agents = design.get("agents", [])
        tasks = design.get("tasks", [])

        # Display agents
        if agents:
            logger.info(f"\n🤖 Agents ({len(agents)}):")
            for i, agent in enumerate(agents, 1):
                agent_id = agent.get("id", f"agent_{i}")
                role = agent.get("role", "Unknown")
                goal = agent.get("goal", "")
                tools = agent.get("tools", [])

                logger.info(f"  {i}. {agent_id}")
                logger.info(f"     Role: {role}")
                if len(goal) <= 80:
                    logger.info(f"     Goal: {goal}")
                if tools:
                    logger.info(f"     Tools: {', '.join(tools[:5])}")
        # Display tasks
        if tasks:
            logger.info(f"\n📋 Tasks ({len(tasks)}):")
            for i, task in enumerate(tasks, 1):
                task_id = task.get("id", f"task_{i}")
                desc = task.get("description", "")
                agent_id = task.get("agent", "")

                logger.info(f"  {i}. {task_id} (assigned to: {agent_id})")
                if len(desc) <= 80:
                    logger.info(f"     {desc}")
        # Get approval
        logger.info("\n" + "=" * 70)
        choice = input(
            "Proceed to code generation? (approve/reject/redesign): "
        ).lower()

        if choice in ["a", "approve", "yes", "y"]:
            return ApprovalDecision.APPROVE
        elif choice in ["r", "redesign", "edit"]:
            return ApprovalDecision.EDIT
        else:
            return ApprovalDecision.REJECT

    def review_final_code(self, generated_code: Dict[str, str]) -> ApprovalDecision:
        """
        Review generated code (after Phase 5).

        Args:
            generated_code: Dict of filename -> code content

        Returns:
            ApprovalDecision
        """
        if self.auto_approve:
            return ApprovalDecision.APPROVE

        logger.info("\n" + "=" * 70)
        logger.info("CODE GENERATION COMPLETE")
        logger.info("=" * 70)
        # Display file list
        logger.info(f"\n📄 Generated Files ({len(generated_code)}):")
        for i, (filename, content) in enumerate(generated_code.items(), 1):
            lines = content.count("\n") + 1
            size_kb = len(content) / 1024
            logger.info(f"  {i}. {filename} ({lines} lines, {size_kb:.1f} KB)")
        # Show preview of main.py
        if "main.py" in generated_code:
            logger.info("\n📝 Preview of main.py:")
            logger.info("-" * 70)
            preview_lines = generated_code["main.py"].split("\n")[:30]
            logger.info("\n".join(preview_lines))
            if len(generated_code["main.py"].split("\n")) > 30:
                logger.info("... (truncated)")
            logger.info("-" * 70)
        # Get approval
        logger.info("\n" + "=" * 70)
        choice = input("Save generated code? (yes/no): ").lower()

        if choice in ["y", "yes", "approve"]:
            return ApprovalDecision.APPROVE
        else:
            return ApprovalDecision.REJECT

    def display_diff(self, before: str, after: str):
        """
        Display differences between before and after (for edits).

        Args:
            before: Original content
            after: Modified content
        """
        logger.info("\n📊 Changes:")
        logger.info("-" * 70)
        # Simple line-by-line diff
        before_lines = before.split("\n")
        after_lines = after.split("\n")

        for i, (b_line, a_line) in enumerate(zip(before_lines, after_lines), 1):
            if b_line != a_line:
                logger.info(f"Line {i}:")
                logger.info(f"  - {b_line}")
                logger.info(f"  + {a_line}")
        logger.info("-" * 70)