"""
Plan Mode - User Review Before Code Generation

Allows users to review and approve specifications before generating code.
This prevents wasted effort from incorrect requirements.
"""

from typing import Any, Dict
from enum import Enum

# Type checking imports
from typing import TYPE_CHECKING
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

    def review_concretized_requirements(
        self,
        concretized: Any
    ) -> ApprovalDecision:
        """
        Review concretized requirements (after Phase 0).

        Args:
            concretized: ConcretizedRequirement object

        Returns:
            ApprovalDecision
        """
        if self.auto_approve:
            return ApprovalDecision.APPROVE

        print("\n" + "=" * 70)
        print("PHASE 0 COMPLETE: Requirements Concretization")
        print("=" * 70)

        # Display project info
        print(f"\n📋 Project: {concretized.project_name}")
        print(f"📝 Description: {concretized.description}")

        # Display features
        if concretized.features:
            print(f"\n✨ Features ({len(concretized.features)}):")
            for i, feature in enumerate(concretized.features[:10], 1):  # Limit to 10
                priority_emoji = "🔴" if feature.priority == "high" else "🟡" if feature.priority == "medium" else "⚪"
                print(f"  {i}. [{priority_emoji} {feature.priority}] {feature.name}")
                if len(feature.description) <= 80:
                    print(f"     {feature.description}")

        # Display data models
        if concretized.data_models:
            print(f"\n💾 Data Models ({len(concretized.data_models)}):")
            for i, model in enumerate(concretized.data_models[:5], 1):
                print(f"  {i}. {model.entity_name}: {len(model.attributes)} attributes")

        # Display boundaries if available
        if hasattr(concretized, 'boundaries') and concretized.boundaries:
            print(f"\n🔒 Security Boundaries:")
            if concretized.boundaries.never_allowed:
                print(f"  ❌ Never Allowed: {len(concretized.boundaries.never_allowed)} restrictions")
            if concretized.boundaries.ask_first:
                print(f"  ⚠️ Ask First: {len(concretized.boundaries.ask_first)} operations")

        # Get approval
        print("\n" + "=" * 70)
        choice = input("Review this specification? (approve/edit/reject): ").lower()

        if choice in ['a', 'approve', 'yes', 'y']:
            return ApprovalDecision.APPROVE
        elif choice in ['e', 'edit']:
            return ApprovalDecision.EDIT
        else:
            return ApprovalDecision.REJECT

    def review_design(
        self,
        design: Dict[str, Any]
    ) -> ApprovalDecision:
        """
        Review agent and task design (after Phase 3).

        Args:
            design: Design output with agents and tasks

        Returns:
            ApprovalDecision
        """
        if self.auto_approve:
            return ApprovalDecision.APPROVE

        print("\n" + "=" * 70)
        print("PHASE 3 COMPLETE: Agent & Task Design")
        print("=" * 70)

        agents = design.get("agents", [])
        tasks = design.get("tasks", [])

        # Display agents
        if agents:
            print(f"\n🤖 Agents ({len(agents)}):")
            for i, agent in enumerate(agents, 1):
                agent_id = agent.get("id", f"agent_{i}")
                role = agent.get("role", "Unknown")
                goal = agent.get("goal", "")
                tools = agent.get("tools", [])

                print(f"  {i}. {agent_id}")
                print(f"     Role: {role}")
                if len(goal) <= 80:
                    print(f"     Goal: {goal}")
                if tools:
                    print(f"     Tools: {', '.join(tools[:5])}")

        # Display tasks
        if tasks:
            print(f"\n📋 Tasks ({len(tasks)}):")
            for i, task in enumerate(tasks, 1):
                task_id = task.get("id", f"task_{i}")
                desc = task.get("description", "")
                agent_id = task.get("agent", "")

                print(f"  {i}. {task_id} (assigned to: {agent_id})")
                if len(desc) <= 80:
                    print(f"     {desc}")

        # Get approval
        print("\n" + "=" * 70)
        choice = input("Proceed to code generation? (approve/reject/redesign): ").lower()

        if choice in ['a', 'approve', 'yes', 'y']:
            return ApprovalDecision.APPROVE
        elif choice in ['r', 'redesign', 'edit']:
            return ApprovalDecision.EDIT
        else:
            return ApprovalDecision.REJECT

    def review_final_code(
        self,
        generated_code: Dict[str, str]
    ) -> ApprovalDecision:
        """
        Review generated code (after Phase 5).

        Args:
            generated_code: Dict of filename -> code content

        Returns:
            ApprovalDecision
        """
        if self.auto_approve:
            return ApprovalDecision.APPROVE

        print("\n" + "=" * 70)
        print("CODE GENERATION COMPLETE")
        print("=" * 70)

        # Display file list
        print(f"\n📄 Generated Files ({len(generated_code)}):")
        for i, (filename, content) in enumerate(generated_code.items(), 1):
            lines = content.count('\n') + 1
            size_kb = len(content) / 1024
            print(f"  {i}. {filename} ({lines} lines, {size_kb:.1f} KB)")

        # Show preview of main.py
        if "main.py" in generated_code:
            print("\n📝 Preview of main.py:")
            print("-" * 70)
            preview_lines = generated_code["main.py"].split('\n')[:30]
            print('\n'.join(preview_lines))
            if len(generated_code["main.py"].split('\n')) > 30:
                print("... (truncated)")
            print("-" * 70)

        # Get approval
        print("\n" + "=" * 70)
        choice = input("Save generated code? (yes/no): ").lower()

        if choice in ['y', 'yes', 'approve']:
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
        print("\n📊 Changes:")
        print("-" * 70)

        # Simple line-by-line diff
        before_lines = before.split('\n')
        after_lines = after.split('\n')

        for i, (b_line, a_line) in enumerate(zip(before_lines, after_lines), 1):
            if b_line != a_line:
                print(f"Line {i}:")
                print(f"  - {b_line}")
                print(f"  + {a_line}")

        print("-" * 70)
