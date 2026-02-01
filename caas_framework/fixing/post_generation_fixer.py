"""
Post-Generation Fixer

Automatically validates and fixes generated code after generation.
"""

from typing import Dict, List, Any, Tuple
import logging

from caas_framework.validation.task_validator import TaskValidator
from caas_framework.fixing.tool_fixer import ToolFixer

logger = logging.getLogger(__name__)


class PostGenerationFixer:
    """
    Validates and fixes generated agent/task designs.

    This runs AFTER AgentDesigner but BEFORE CodeGenerator.
    """

    @classmethod
    def fix_design(
        cls,
        design: Dict[str, Any],
        verbose: bool = True
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validate and fix agent/task design.

        Args:
            design: Design output from AgentDesigner
            verbose: Whether to log fixes

        Returns:
            (fixed_design, list_of_fixes_applied)
        """
        fixes_applied = []

        # Extract agents and tasks
        agents = design.get("agents", [])
        tasks = design.get("tasks", [])

        # Convert Pydantic models to dicts if needed
        from caas_framework.utils import ObjectAccessor
        agents_dict = ObjectAccessor.to_dict_list(agents)
        tasks_dict = ObjectAccessor.to_dict_list(tasks)

        # 1. Validate tasks
        issues = TaskValidator.validate_all(tasks_dict, agents_dict)

        if verbose and issues:
            logger.warning(f"Found {len(issues)} validation issues")
            for issue in issues:
                logger.warning(f"  [{issue.severity.upper()}] {issue.message}")

        # 2. Fix task descriptions - DISABLED
        # TaskDescriptionFixer is no longer used.
        # Input placeholders are now injected by InputDetector.inject_input_placeholders()
        # in CodeGenerator._generate_tasks_file() which handles both removal and injection.
        # tasks_dict = TaskDescriptionFixer.fix_all_tasks(tasks_dict)

        # 3. Fix human_input misuse
        for issue in issues:
            if issue.issue_type == "human_input_misuse":
                # Find and fix the task
                for task in tasks_dict:
                    if task.get("id") == issue.task_id:
                        # Set human_input to False
                        task["human_input"] = False
                        fixes_applied.append(
                            f"Set human_input=False for task {issue.task_id}"
                        )

        # 3. Fix missing tools
        agents_dict = ToolFixer.fix_agents_tools(agents_dict, tasks_dict)

        # Count tools added
        for agent in agents_dict:
            tools = agent.get("tools", [])
            if tools:
                fixes_applied.append(
                    f"Added {len(tools)} tools to agent {agent.get('id')}: {tools}"
                )

        # 4. Update design
        # Convert dicts back to models if needed
        if agents and hasattr(agents[0], 'model_dump'):
            # Were Pydantic models, convert back
            from caas_framework.models.specifications import AgentSpecModel, TaskSpecModel

            fixed_agents = [AgentSpecModel(**agent) for agent in agents_dict]
            fixed_tasks = [TaskSpecModel(**task) for task in tasks_dict]

            design["agents"] = fixed_agents
            design["tasks"] = fixed_tasks
        else:
            # Were dicts, keep as dicts
            design["agents"] = agents_dict
            design["tasks"] = tasks_dict

        if verbose and fixes_applied:
            logger.info(f"Applied {len(fixes_applied)} fixes:")
            for fix in fixes_applied:
                logger.info(f"  ✓ {fix}")

        return design, fixes_applied


def apply_post_generation_fixes(design: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to apply post-generation fixes.

    Args:
        design: Design output from AgentDesigner

    Returns:
        Fixed design
    """
    fixed_design, fixes = PostGenerationFixer.fix_design(design, verbose=True)
    return fixed_design
