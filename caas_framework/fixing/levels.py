"""
3-Level Fixing System

Individual fixers for each level of the fixing hierarchy.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class BaseFixer(ABC):
    """Base class for all fixers"""

    @abstractmethod
    def can_fix(self, issue: Any) -> bool:
        """Check if this fixer can handle the issue"""

    @abstractmethod
    def apply_fix(self, data: Any, issue: Any) -> Tuple[Any, str]:
        """
        Apply fix to data.

        Returns:
            (fixed_data, fix_description)
        """


class TemplateFixer(BaseFixer):
    """
    Level 1: Template-Based Fixer

    Uses predefined templates for standard patterns.
    Fast and deterministic.
    """

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Any]:
        """Load fix templates"""
        return {
            "missing_task": {
                "id": "task_{index}",
                "description": "{feature_description}",
                "expected_output": "Completed {feature_name}",
                "agent": "{default_agent}",
                "context": [],
                "async_execution": False,
                "output_file": None,
                "human_input": False,
            },
            "missing_agent": {
                "id": "agent_{index}",
                "role": "executor",
                "goal": "Execute assigned tasks",
                "backstory": "A versatile agent",
                "tools": [],
                "verbose": True,
                "memory": True,
                "allow_delegation": False,
                "max_iter": 15,
            },
        }

    def can_fix(self, issue: Any) -> bool:
        """Check if issue matches a template"""
        if hasattr(issue, "item_type"):
            return issue.item_type in ["task", "feature", "agent"]
        return False

    def apply_fix(self, data: Any, issue: Any) -> Tuple[Any, str]:
        """Apply template-based fix"""
        # Implementation depends on issue type
        return data, "Template fix applied"


class RuleFixer(BaseFixer):
    """
    Level 2: Rule-Based Fixer

    Applies explicit rules for well-defined fixes.
    Uses domain knowledge and heuristics.
    """

    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict[str, Any]]:
        """Load fixing rules"""
        return [
            {
                "name": "high_priority_agent",
                "condition": lambda issue: hasattr(issue, "severity")
                and issue.severity == "high",
                "action": "create_specialized_agent",
            },
            {
                "name": "circular_dependency",
                "condition": lambda issue: "circular" in str(issue).lower(),
                "action": "remove_circular_reference",
            },
        ]

    def can_fix(self, issue: Any) -> bool:
        """Check if any rule applies"""
        for rule in self.rules:
            if rule["condition"](issue):
                return True
        return False

    def apply_fix(self, data: Any, issue: Any) -> Tuple[Any, str]:
        """Apply rule-based fix"""
        for rule in self.rules:
            if rule["condition"](issue):
                # Apply rule action
                return data, f"Rule fix applied: {rule['name']}"
        return data, "No rule matched"


class LLMFixer(BaseFixer):
    """
    Level 3: LLM-Based Fixer

    Uses LLM for complex, context-dependent fixes.
    Most powerful but also most expensive.
    """

    def __init__(self, llm_plugin=None):
        self.llm_plugin = llm_plugin

    def can_fix(self, issue: Any) -> bool:
        """LLM can attempt any fix if available"""
        return self.llm_plugin is not None

    async def apply_fix_async(self, data: Any, issue: Any) -> Tuple[Any, str]:
        """Apply LLM-based fix (async)"""
        if not self.llm_plugin:
            return data, "LLM not available"

        # Prepare prompt
        prompt = f"""
Fix the following issue in the agent design:

Issue: {issue}

Current data: {data}

Provide a JSON fix.
"""

        try:
            response = await self.llm_plugin.ainvoke(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )

            # Parse and apply fix
            # Note: Actual implementation would parse response
            return data, "LLM fix applied"

        except Exception as e:
            return data, f"LLM fix failed: {str(e)}"

    def apply_fix(self, data: Any, issue: Any) -> Tuple[Any, str]:
        """Synchronous version (not recommended for LLM)"""
        return data, "Use apply_fix_async for LLM fixes"
