"""
Auto-Fixer

Golden Data-based automatic fixing with 3-level strategy:
1. Template-based fixing
2. Rule-based fixing
3. LLM-based fixing
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from caas_framework.models.specifications import (
    AgentSpecModel,
    ConcretizedRequirement,
    TaskSpecModel,
)
from caas_framework.models.validation import GoldenValidationReport


def _to_dict(item: Union[Dict, BaseModel]) -> Dict:
    """Convert Pydantic model to dictionary"""
    if isinstance(item, BaseModel):
        return item.model_dump()
    return item


def _to_model(item: Union[Dict, BaseModel], model_class) -> BaseModel:
    """Convert dictionary to Pydantic model"""
    if isinstance(item, BaseModel):
        return item
    return model_class(**item)


@dataclass
class FixResult:
    """Auto-fix result"""

    success: bool
    fixed_output: Any
    fixes_applied: List[str]
    errors: List[str]
    fix_level_used: Optional[str] = None  # "template", "rule", or "llm"


class AutoFixer:
    """
    Auto-Fixer

    Automatically fixes Phase outputs based on Golden Data.

    Fixing Strategies (3-level):
    1. Template-based: Use templates for standard patterns
    2. Rule-based: Apply explicit rules for well-defined fixes
    3. LLM-based: Use LLM for complex, context-dependent fixes
    """

    def __init__(self, golden_data: ConcretizedRequirement, llm_plugin=None):
        """
        Args:
            golden_data: Golden Data as fixing baseline
            llm_plugin: Optional LLM plugin for Level 3 fixes
        """
        self.golden_data = golden_data
        self.llm_plugin = llm_plugin

    async def fix_design(
        self,
        agent_specs: List[Union[Dict, AgentSpecModel]],
        task_specs: List[Union[Dict, TaskSpecModel]],
        validation_report: GoldenValidationReport,
        max_iterations: int = 3,
    ) -> FixResult:
        """
        Fix Design Phase automatically.

        Args:
            agent_specs: Agent specs (dict or AgentSpecModel)
            task_specs: Task specs (dict or TaskSpecModel)
            validation_report: Validation results
            max_iterations: Maximum fix iterations

        Returns:
            FixResult: Fix results
        """
        # Convert to dict for internal processing
        agents_dict = [_to_dict(a) for a in agent_specs]
        tasks_dict = [_to_dict(t) for t in task_specs]

        if not validation_report.needs_fixing:
            return FixResult(
                success=True,
                fixed_output={"agents": agents_dict, "tasks": tasks_dict},
                fixes_applied=[],
                errors=[],
            )

        fixes_applied = []
        errors = []
        fix_level = None

        # Iterate through fix attempts
        for iteration in range(max_iterations):
            # Level 1: Template-based fixes
            (
                agents_dict,
                tasks_dict,
                template_fixes,
                template_errors,
            ) = self._apply_template_fixes(agents_dict, tasks_dict, validation_report)
            fixes_applied.extend(template_fixes)
            errors.extend(template_errors)
            if template_fixes:
                fix_level = "template"

            # Level 2: Rule-based fixes
            agents_dict, tasks_dict, rule_fixes, rule_errors = self._apply_rule_fixes(
                agents_dict, tasks_dict, validation_report
            )
            fixes_applied.extend(rule_fixes)
            errors.extend(rule_errors)
            if rule_fixes:
                fix_level = "rule"

            # Level 3: LLM-based fixes (if available and previous levels didn't fix everything)
            if self.llm_plugin and validation_report.needs_fixing:
                (
                    agents_dict,
                    tasks_dict,
                    llm_fixes,
                    llm_errors,
                ) = await self._apply_llm_fixes(
                    agents_dict, tasks_dict, validation_report
                )
                fixes_applied.extend(llm_fixes)
                errors.extend(llm_errors)
                if llm_fixes:
                    fix_level = "llm"

            # Check if all fixes were applied
            if not errors and fixes_applied:
                break

        success = len(errors) == 0

        return FixResult(
            success=success,
            fixed_output={"agents": agents_dict, "tasks": tasks_dict},
            fixes_applied=fixes_applied,
            errors=errors,
            fix_level_used=fix_level,
        )

    def _apply_template_fixes(
        self,
        agents: List[Dict],
        tasks: List[Dict],
        validation_report: GoldenValidationReport,
    ) -> tuple[List[Dict], List[Dict], List[str], List[str]]:
        """
        Level 1: Apply template-based fixes.

        Returns:
            (agents, tasks, fixes_applied, errors)
        """
        fixes_applied = []
        errors = []

        # Fix missing features by adding tasks
        for missing_item in validation_report.missing_items:
            if missing_item.item_type in ["feature", "task"]:
                try:
                    # Find Golden Data feature
                    golden_feature = next(
                        (
                            f
                            for f in self.golden_data.features
                            if f.id == missing_item.item_id
                            or f.name == missing_item.item_name
                        ),
                        None,
                    )

                    if golden_feature:
                        # Generate task ID (prevent duplicates)
                        base_task_id = golden_feature.id.lower().replace("f", "task_")
                        task_id = base_task_id
                        counter = 1
                        while any(t.get("id") == task_id for t in tasks):
                            task_id = f"{base_task_id}_{counter}"
                            counter += 1

                        # Assign to first agent (or create default agent)
                        if agents:
                            assigned_agent = agents[0]["id"]
                        else:
                            # Create default agent if none exist
                            default_agent = {
                                "id": "agent_default",
                                "role": "executor",
                                "goal": "Execute tasks as assigned",
                                "backstory": "A versatile agent that can handle various tasks",
                                "tools": [],
                                "verbose": True,
                                "memory": True,
                                "allow_delegation": False,
                                "max_iter": 15,
                            }
                            agents.append(default_agent)
                            assigned_agent = "agent_default"
                            fixes_applied.append("✅ Created default agent")

                        # Create task from template
                        new_task = {
                            "id": task_id,
                            "description": golden_feature.description,
                            "expected_output": f"Completed {golden_feature.name}",
                            "agent": assigned_agent,
                            "context": [],
                            "async_execution": False,
                            "output_file": None,
                            "human_input": False,
                        }

                        tasks.append(new_task)
                        fixes_applied.append(
                            f"✅ Added task '{golden_feature.name}' (template-based)"
                        )

                except Exception as e:
                    errors.append(
                        f"Failed to add task {missing_item.item_name}: {str(e)}"
                    )

        return agents, tasks, fixes_applied, errors

    def _apply_rule_fixes(
        self,
        agents: List[Dict],
        tasks: List[Dict],
        validation_report: GoldenValidationReport,
    ) -> tuple[List[Dict], List[Dict], List[str], List[str]]:
        """
        Level 2: Apply rule-based fixes.

        Returns:
            (agents, tasks, fixes_applied, errors)
        """
        fixes_applied = []
        errors = []

        # Rule: If high-priority features are missing, create specialized agents
        high_priority_missing = [
            item for item in validation_report.missing_items if item.severity == "high"
        ]

        if high_priority_missing and len(agents) < 3:
            # Rule: Create specialized agent for high-priority features
            for missing_item in high_priority_missing[:2]:  # Limit to 2 new agents
                try:
                    # Check if agent exists
                    agent_id = (
                        f"agent_{missing_item.item_name.lower().replace(' ', '_')}"
                    )
                    if not any(a.get("id") == agent_id for a in agents):
                        new_agent = {
                            "id": agent_id,
                            "role": "executor",
                            "goal": f"Handle {missing_item.item_name}",
                            "backstory": f"Specialist for {missing_item.item_name}",
                            "tools": [],
                            "verbose": True,
                            "memory": True,
                            "allow_delegation": False,
                            "max_iter": 15,
                        }
                        agents.append(new_agent)
                        fixes_applied.append(
                            f"✅ Created specialized agent for '{missing_item.item_name}' (rule-based)"
                        )
                except Exception as e:
                    errors.append(f"Failed to create agent: {str(e)}")

        return agents, tasks, fixes_applied, errors

    async def _apply_llm_fixes(
        self,
        agents: List[Dict],
        tasks: List[Dict],
        validation_report: GoldenValidationReport,
    ) -> tuple[List[Dict], List[Dict], List[str], List[str]]:
        """
        Level 3: Apply LLM-based fixes.

        Returns:
            (agents, tasks, fixes_applied, errors)
        """
        if not self.llm_plugin:
            return agents, tasks, [], []

        fixes_applied = []
        errors = []

        # LLM-based fix for complex missing items
        complex_missing = [
            item
            for item in validation_report.missing_items
            if item.severity in ["high", "critical"]
        ]

        if complex_missing:
            try:
                # Prepare context for LLM
                missing_features = []
                for item in complex_missing:
                    # Find corresponding feature in Golden Data
                    feature = next(
                        (
                            f
                            for f in self.golden_data.features
                            if f.id == item.item_id or f.name == item.item_name
                        ),
                        None,
                    )
                    if feature:
                        missing_features.append(feature.model_dump())

                prompt = f"""You are an expert AI agent and task designer. Analyze the missing features and generate appropriate agents and tasks.

Golden Data Features (All):
{[f.model_dump() for f in self.golden_data.features]}

Current Agents:
{[{"id": a["id"], "role": a["role"], "goal": a.get("goal", "")} for a in agents]}

Current Tasks:
{[{"id": t["id"], "description": t.get("description", "")[:100]} for t in tasks]}

Missing Features (High/Critical Priority):
{missing_features}

Your task:
1. Decide if existing agents can handle the missing features OR if new agents are needed
2. Generate tasks for each missing feature
3. Assign tasks to appropriate agents (existing or new)

Generate JSON with:
{{
    "new_agents": [
        {{
            "id": "agent_id",
            "role": "role_name",
            "goal": "clear goal",
            "backstory": "relevant backstory",
            "tools": []
        }}
    ],
    "new_tasks": [
        {{
            "id": "task_id",
            "description": "detailed task description",
            "expected_output": "expected output",
            "agent": "agent_id_to_assign",
            "context": []
        }}
    ]
}}

Important:
- Only create new agents if absolutely necessary
- Prefer assigning to existing agents if they can handle the task
- Ensure agent IDs are unique (don't conflict with existing)
- Ensure task IDs follow pattern: task_f1, task_f2, etc.
- Be specific in descriptions

Return ONLY valid JSON, no additional text."""

                # Call LLM
                response = await self.llm_plugin.ainvoke(
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                )

                # Parse response
                import json

                response_text = (
                    response.get("content", "")
                    if isinstance(response, dict)
                    else str(response)
                )

                try:
                    llm_output = json.loads(response_text)
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown
                    import re

                    json_match = re.search(
                        r"```json\s*(.*?)\s*```", response_text, re.DOTALL
                    )
                    if json_match:
                        llm_output = json.loads(json_match.group(1))
                    else:
                        raise ValueError("Could not parse LLM response as JSON")

                # Apply LLM suggestions
                new_agents = llm_output.get("new_agents", [])
                new_tasks = llm_output.get("new_tasks", [])

                # Add new agents (with duplicate check)
                existing_agent_ids = {a["id"] for a in agents}
                for new_agent in new_agents:
                    if new_agent["id"] not in existing_agent_ids:
                        # Ensure required fields
                        agent = {
                            "id": new_agent["id"],
                            "role": new_agent.get("role", "executor"),
                            "goal": new_agent.get("goal", ""),
                            "backstory": new_agent.get("backstory", ""),
                            "tools": new_agent.get("tools", []),
                            "verbose": True,
                            "memory": True,
                            "allow_delegation": False,
                            "max_iter": 15,
                        }
                        agents.append(agent)
                        fixes_applied.append(
                            f"✅ Added agent '{new_agent['id']}' (LLM-based)"
                        )

                # Add new tasks (with duplicate check)
                existing_task_ids = {t["id"] for t in tasks}
                for new_task in new_tasks:
                    if new_task["id"] not in existing_task_ids:
                        task = {
                            "id": new_task["id"],
                            "description": new_task.get("description", ""),
                            "expected_output": new_task.get("expected_output", ""),
                            "agent": new_task.get(
                                "agent", agents[0]["id"] if agents else "agent_1"
                            ),
                            "context": new_task.get("context", []),
                            "async_execution": False,
                            "output_file": None,
                            "human_input": False,
                        }
                        tasks.append(task)
                        fixes_applied.append(
                            f"✅ Added task '{new_task['id']}' (LLM-based)"
                        )

                if not fixes_applied:
                    fixes_applied.append(
                        "✅ LLM analysis completed (no new items needed)"
                    )

            except Exception as e:
                errors.append(f"LLM fix failed: {str(e)}")

        return agents, tasks, fixes_applied, errors

    def fix_code(
        self, generated_spec: Dict[str, Any], validation_report: GoldenValidationReport
    ) -> FixResult:
        """
        Fix Development Phase (code generation).

        Args:
            generated_spec: Generated spec
            validation_report: Validation results

        Returns:
            FixResult: Fix results
        """
        if not validation_report.needs_fixing:
            return FixResult(
                success=True, fixed_output=generated_spec, fixes_applied=[], errors=[]
            )

        # Code-level fixes require regeneration - log for now
        fixes_applied = []
        errors = []

        for missing_item in validation_report.missing_items:
            if missing_item.item_type == "task_implementation":
                fixes_applied.append(
                    f"⚠️ Code regeneration needed for: {missing_item.item_name}"
                )

        return FixResult(
            success=True,
            fixed_output=generated_spec,
            fixes_applied=fixes_applied,
            errors=errors,
            fix_level_used="rule",
        )
