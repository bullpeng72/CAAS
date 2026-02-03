"""
Ontology-Based Validator

Validates agent and task configurations using ontology rules.
Provides automatic fixing suggestions.
"""

from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel

from caas_framework.knowledge.ontology import OntologyManager
from caas_framework.models.validation import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


def _safe_get(obj: Union[Dict, BaseModel], key: str, default: Any = None) -> Any:
    """
    Safely get value from dict or Pydantic model.

    Args:
        obj: Dict or Pydantic model object
        key: Key or attribute name
        default: Default value

    Returns:
        Found value or default
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    else:
        return getattr(obj, key, default)


class OntologyValidator:
    """
    Ontology-Based Validator

    Validates agent and task configurations against ontology rules.
    Provides suggestions and automatic fixing options.
    """

    def __init__(self, enabled_tools: Optional[List[str]] = None):
        """
        Initialize validator.

        Args:
            enabled_tools: Optional list of enabled tool IDs.
                          If None, all registered tools are considered enabled.
        """
        self.ontology = OntologyManager()
        self.enabled_tools = (
            set(enabled_tools)
            if enabled_tools
            else set(self.ontology.tool_capabilities.keys())
        )

    def validate_agents_and_tasks(
        self, agents: List[Dict[str, Any]], tasks: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate agents and tasks.

        Args:
            agents: List of agent configurations
            tasks: List of task configurations

        Returns:
            ValidationResult with issues and summary
        """
        issues: List[ValidationIssue] = []

        # 1. Validate agent roles
        issues.extend(self._validate_agent_roles(agents))

        # 2. Validate agent tools
        issues.extend(self._validate_agent_tools(agents, tasks))

        # 3. Validate task assignments
        issues.extend(self._validate_task_assignments(agents, tasks))

        # 4. Validate task dependencies
        issues.extend(self._validate_task_dependencies(tasks))

        # Generate summary
        summary = {
            "total": len(issues),
            "errors": len(
                [i for i in issues if i.severity == ValidationSeverity.ERROR]
            ),
            "warnings": len(
                [i for i in issues if i.severity == ValidationSeverity.WARNING]
            ),
            "info": len([i for i in issues if i.severity == ValidationSeverity.INFO]),
            "auto_fixable": len([i for i in issues if i.auto_fix_available]),
        }

        is_valid = summary["errors"] == 0

        return ValidationResult(is_valid=is_valid, issues=issues, summary=summary)

    def _validate_agent_roles(
        self, agents: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """Validate agent roles"""
        issues = []

        for agent in agents:
            agent_id = _safe_get(agent, "id", "unknown")
            role = _safe_get(agent, "role", "")

            # Infer role from description
            inferred_role = self.ontology.infer_role_from_description(
                f"{role} {_safe_get(agent, 'goal', '')}"
            )

            # Detect non-standard roles
            if role.lower() != inferred_role.value:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        issue_type="role",
                        agent_id=agent_id,
                        message=f"Non-standard role: '{role}'",
                        suggested_fix=f"Consider using standard role '{inferred_role.value}'.",
                        auto_fix_available=True,
                        auto_fix_data={
                            "action": "normalize_role",
                            "agent_id": agent_id,
                            "new_role": inferred_role.value,
                        },
                    )
                )

        return issues

    def _validate_agent_tools(
        self, agents: List[Dict[str, Any]], tasks: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """Validate agent tools"""
        issues = []

        for agent in agents:
            agent_id = _safe_get(agent, "id", "unknown")
            role = _safe_get(agent, "role", "")
            current_tools = set(_safe_get(agent, "tools", []))

            # Check for unregistered tools
            unregistered_tools = []
            for tool in current_tools:
                if tool not in self.enabled_tools:
                    unregistered_tools.append(tool)

            if unregistered_tools:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        issue_type="tool",
                        agent_id=agent_id,
                        message=f"Unregistered tools: {', '.join(unregistered_tools)}",
                        suggested_fix=f"Remove or register these tools: {', '.join(unregistered_tools)}",
                        auto_fix_available=True,
                        auto_fix_data={
                            "action": "remove_tools",
                            "agent_id": agent_id,
                            "tools_to_remove": unregistered_tools,
                        },
                    )
                )

            # Find agent's tasks
            agent_tasks = [
                t
                for t in tasks
                if (_safe_get(t, "assigned_agent") or _safe_get(t, "agent", "")).lower()
                in agent_id.lower()
                or (_safe_get(t, "assigned_agent") or _safe_get(t, "agent", "")).lower()
                in role.lower()
            ]

            if not agent_tasks:
                continue

            # Check for tools explicitly mentioned in task descriptions
            tools_mentioned_in_tasks = set()
            for task in agent_tasks:
                task_desc = _safe_get(task, "description", "").lower()
                task_id = _safe_get(task, "id", _safe_get(task, "name", "unknown"))

                # Extract tool names from task description
                # Look for patterns like "using X tool", "with X", "via X scraping", etc.
                import re

                tool_patterns = [
                    r"using\s+(\w+)",
                    r"with\s+(\w+)",
                    r"via\s+(\w+)",
                    r"(\w+)_scraping",
                    r"(\w+)_tool",
                    r"(\w+)_api",
                ]

                for pattern in tool_patterns:
                    matches = re.findall(pattern, task_desc)
                    for match in matches:
                        potential_tool = match.lower()
                        # Check if it's a registered tool
                        for registered_tool in self.enabled_tools:
                            if potential_tool in registered_tool.lower():
                                tools_mentioned_in_tasks.add(registered_tool)
                                break

            # Check if agent has tools mentioned in tasks
            missing_explicit_tools = tools_mentioned_in_tasks - current_tools

            if missing_explicit_tools:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        issue_type="tool",
                        agent_id=agent_id,
                        message=f"The '{agent_id}' is missing the '{', '.join(missing_explicit_tools)}' tool in its tools list, which is specified in the task.",
                        suggested_fix=f"Add tools to agent: {', '.join(missing_explicit_tools)}",
                        auto_fix_available=True,
                        auto_fix_data={
                            "action": "add_tools",
                            "agent_id": agent_id,
                            "tools_to_add": list(missing_explicit_tools),
                        },
                    )
                )

            # Calculate required tools based on ontology
            inferred_role = self.ontology.infer_role_from_description(
                f"{role} {_safe_get(agent, 'goal', '')}"
            )

            task_types = []
            for task in agent_tasks:
                task_type = self.ontology.infer_task_type_from_description(
                    _safe_get(task, "description", "")
                )
                task_types.append(task_type)

            # Recommend tools
            recommended_tools = self.ontology.recommend_agent_tools(
                role=inferred_role, assigned_tasks=task_types
            )

            # Filter to only enabled tools
            recommended_tools = [
                tool for tool in recommended_tools if tool in self.enabled_tools
            ]

            # Check for missing tools (excluding already reported explicit tools)
            missing_tools = (
                set(recommended_tools) - current_tools - missing_explicit_tools
            )

            if missing_tools:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        issue_type="tool",
                        agent_id=agent_id,
                        message=f"Missing recommended tools: {len(missing_tools)} tools",
                        suggested_fix=f"Consider adding: {', '.join(list(missing_tools)[:3])}",
                        auto_fix_available=True,
                        auto_fix_data={
                            "action": "add_tools",
                            "agent_id": agent_id,
                            "tools_to_add": list(missing_tools),
                        },
                    )
                )

        return issues

    def _validate_task_assignments(
        self, agents: List[Dict[str, Any]], tasks: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """Validate task assignments"""
        issues = []

        for task in tasks:
            task_id = _safe_get(task, "id", _safe_get(task, "name", "unknown"))
            assigned_agent_name = _safe_get(task, "assigned_agent") or _safe_get(
                task, "agent", ""
            )

            # Find assigned agent
            assigned_agent = None
            for agent in agents:
                if (
                    _safe_get(agent, "id", "").lower() in assigned_agent_name.lower()
                    or _safe_get(agent, "role", "").lower()
                    in assigned_agent_name.lower()
                ):
                    assigned_agent = agent
                    break

            if not assigned_agent:
                # Auto-fix: find suitable agent
                if len(agents) > 0:
                    task_type = self.ontology.infer_task_type_from_description(
                        _safe_get(task, "description", "")
                    )

                    suitable_agent = None
                    suitable_roles = self.ontology.get_suitable_roles(task_type)

                    for role in suitable_roles:
                        for agent in agents:
                            agent_role = self.ontology.infer_role_from_description(
                                f"{_safe_get(agent, 'role', '')} {_safe_get(agent, 'goal', '')}"
                            )
                            if agent_role == role:
                                suitable_agent = agent
                                break
                        if suitable_agent:
                            break

                    if not suitable_agent:
                        suitable_agent = agents[0]

                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            issue_type="assignment",
                            task_id=task_id,
                            message=f"Assigned agent not found: '{assigned_agent_name}'",
                            suggested_fix=f"Auto-assign to agent '{_safe_get(suitable_agent, 'id', _safe_get(suitable_agent, 'role'))}'.",
                            auto_fix_available=True,
                            auto_fix_data={
                                "action": "assign_agent",
                                "task_id": task_id,
                                "agent_id": _safe_get(
                                    suitable_agent,
                                    "id",
                                    _safe_get(suitable_agent, "role"),
                                ),
                            },
                        )
                    )
                else:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            issue_type="assignment",
                            task_id=task_id,
                            message=f"Assigned agent not found: '{assigned_agent_name}'",
                            suggested_fix="Create an agent first.",
                            auto_fix_available=False,
                        )
                    )
                continue

            # Validate role-task compatibility
            inferred_role = self.ontology.infer_role_from_description(
                f"{_safe_get(assigned_agent, 'role', '')} {_safe_get(assigned_agent, 'goal', '')}"
            )

            task_type = self.ontology.infer_task_type_from_description(
                _safe_get(task, "description", "")
            )

            is_valid = self.ontology.validate_assignment(inferred_role, task_type)

            if not is_valid:
                suitable_roles = self.ontology.get_suitable_roles(task_type)

                if suitable_roles:
                    # Find the best suitable agent
                    best_agent = None
                    for role in suitable_roles:
                        for agent in agents:
                            agent_role = self.ontology.infer_role_from_description(
                                f"{_safe_get(agent, 'role', '')} {_safe_get(agent, 'goal', '')}"
                            )
                            if agent_role == role:
                                best_agent = agent
                                break
                        if best_agent:
                            break

                    # Create clear error message with agent names
                    assigned_agent_name = _safe_get(
                        assigned_agent,
                        "id",
                        _safe_get(assigned_agent, "role", "Unknown"),
                    )
                    best_agent_name = (
                        _safe_get(
                            best_agent, "id", _safe_get(best_agent, "role", "Unknown")
                        )
                        if best_agent
                        else suitable_roles[0].value
                    )

                    # Format: "X task is assigned to Y instead of Z"
                    error_message = f"{task_type.value.replace('_', ' ').title()} task is assigned to {assigned_agent_name} instead of {best_agent_name}."

                    suggestion = f"Reassign this task to '{best_agent_name}' agent. More suitable roles: {', '.join([r.value for r in suitable_roles[:2]])}"

                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,  # Changed from WARNING to ERROR
                            issue_type="assignment",
                            task_id=task_id,
                            agent_id=_safe_get(assigned_agent, "id"),
                            message=error_message,
                            suggested_fix=suggestion,
                            auto_fix_available=True if best_agent else False,
                            auto_fix_data=(
                                {
                                    "action": "reassign_task",
                                    "task_id": task_id,
                                    "current_agent_id": _safe_get(assigned_agent, "id"),
                                    "new_agent_id": (
                                        _safe_get(best_agent, "id")
                                        if best_agent
                                        else None
                                    ),
                                    "new_agent_name": best_agent_name,
                                }
                                if best_agent
                                else None
                            ),
                        )
                    )

        return issues

    def _validate_task_dependencies(
        self, tasks: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """Validate task dependencies"""
        issues = []

        task_ids = {_safe_get(t, "id", _safe_get(t, "name")) for t in tasks}

        for task in tasks:
            task_id = _safe_get(task, "id", _safe_get(task, "name", "unknown"))
            dependencies = _safe_get(task, "dependencies", [])

            # Check for non-existent dependencies
            for dep in dependencies:
                if dep not in task_ids:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            issue_type="task",
                            task_id=task_id,
                            message=f"Non-existent dependency task: '{dep}'",
                            suggested_fix="Remove dependency or fix task ID.",
                            auto_fix_available=False,
                        )
                    )

            # Check for circular dependencies (self-dependency)
            if task_id in dependencies:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        issue_type="task",
                        task_id=task_id,
                        message="Self-referencing circular dependency",
                        suggested_fix="Remove the dependency.",
                        auto_fix_available=True,
                        auto_fix_data={
                            "action": "remove_circular_dependency",
                            "task_id": task_id,
                            "dependency_to_remove": task_id,
                        },
                    )
                )

        return issues

    def validate_requirement_task_alignment(
        self, requirements: Dict[str, Any], tasks: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """
        Validate that tasks align with their source requirements.

        Checks if task implementations match what was specified in requirements
        (e.g., if requirement specifies RSS feeds, task should mention RSS feeds).

        Args:
            requirements: Golden data or requirement specifications
            tasks: List of task configurations

        Returns:
            List of validation issues
        """
        import re

        issues = []

        # Extract features from requirements
        features = requirements.get("features", [])
        if not features:
            return issues

        # Build requirement specifications map
        requirement_specs = {}
        for feature in features:
            feature_name = _safe_get(feature, "name", "")
            feature_desc = _safe_get(feature, "description", "").lower()
            functional_reqs = _safe_get(feature, "functional_requirements", [])

            # Extract implementation methods mentioned in requirements
            methods = []
            combined_text = f"{feature_desc} {' '.join(functional_reqs)}".lower()

            # Common implementation method patterns
            method_patterns = {
                "rss": r"\brss\s+feed|rss\b",
                "api": r"\bapi\b|rest\s+api|graphql",
                "web_scraping": r"\bweb\s+scrap|scraping|beautifulsoup|selenium",
                "database": r"\bdatabase\b|sql|mysql|postgresql|mongodb",
                "websocket": r"\bwebsocket|ws://|wss://",
                "file": r"\bfile\s+upload|file\s+download|file\s+system",
                "email": r"\bemail|smtp|imap",
                "queue": r"\bqueue|kafka|rabbitmq|redis\s+queue",
            }

            for method, pattern in method_patterns.items():
                if re.search(pattern, combined_text):
                    methods.append(method)

            if methods:
                requirement_specs[feature_name.lower()] = {
                    "name": feature_name,
                    "methods": methods,
                    "description": feature_desc,
                }

        # Check each task against requirements
        for task in tasks:
            task_id = _safe_get(task, "id", _safe_get(task, "name", "unknown"))
            task_desc = _safe_get(task, "description", "").lower()
            expected_output = _safe_get(task, "expected_output", "").lower()
            task_full_text = f"{task_desc} {expected_output}"

            # Try to match task to requirement by name similarity
            for req_key, req_spec in requirement_specs.items():
                # Check if task relates to this requirement
                req_name_words = req_key.split()
                task_mentions_req = any(
                    word in task_id.lower() or word in task_desc
                    for word in req_name_words
                    if len(word) > 3
                )

                if not task_mentions_req:
                    continue

                # Check if task uses different methods than specified
                required_methods = req_spec["methods"]
                task_methods = []

                # Check what methods the task actually mentions
                method_patterns = {
                    "rss": r"\brss\b|feed\s+parser",
                    "api": r"\bapi\b|rest|graphql|endpoint",
                    "web_scraping": r"\bscrap|beautifulsoup|selenium|crawl",
                    "database": r"\bdatabase|sql|query|mysql|postgresql|mongodb",
                    "websocket": r"\bwebsocket|ws://",
                    "file": r"\bfile|upload|download",
                    "email": r"\bemail|smtp|imap",
                    "queue": r"\bqueue|kafka|rabbitmq",
                }

                for method, pattern in method_patterns.items():
                    if re.search(pattern, task_full_text):
                        task_methods.append(method)

                # Check for mismatches
                if required_methods and task_methods:
                    missing_methods = set(required_methods) - set(task_methods)
                    extra_methods = set(task_methods) - set(required_methods)

                    if missing_methods:
                        method_str = ", ".join(missing_methods)
                        task_method_str = (
                            ", ".join(task_methods) if task_methods else "other methods"
                        )

                        issues.append(
                            ValidationIssue(
                                severity=ValidationSeverity.WARNING,
                                issue_type="requirement_alignment",
                                task_id=task_id,
                                message=f"The '{req_spec['name']}' requirement specifies using {method_str}, but the task only mentions {task_method_str}.",
                                suggested_fix=f"Ensure the task implementation includes {method_str} as specified in the requirement.",
                                auto_fix_available=False,
                            )
                        )

        return issues

    def apply_auto_fix(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        issue: ValidationIssue,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Apply automatic fix for an issue.

        Args:
            agents: Agent list
            tasks: Task list
            issue: Issue to fix

        Returns:
            Tuple of (modified agents, modified tasks)
        """
        if not issue.auto_fix_available or not issue.auto_fix_data:
            return agents, tasks

        action = issue.auto_fix_data.get("action")

        if action == "normalize_role":
            agent_id = issue.auto_fix_data.get("agent_id")
            new_role = issue.auto_fix_data.get("new_role")

            for agent in agents:
                if _safe_get(agent, "id") == agent_id:
                    agent["role"] = new_role
                    break

        elif action == "add_tools":
            agent_id = issue.auto_fix_data.get("agent_id")
            tools_to_add = issue.auto_fix_data.get("tools_to_add", [])

            for agent in agents:
                if _safe_get(agent, "id") == agent_id:
                    current_tools = _safe_get(agent, "tools", [])
                    agent["tools"] = list(set(current_tools) | set(tools_to_add))
                    break

        elif action == "remove_tools":
            agent_id = issue.auto_fix_data.get("agent_id")
            tools_to_remove = issue.auto_fix_data.get("tools_to_remove", [])

            for agent in agents:
                if _safe_get(agent, "id") == agent_id:
                    current_tools = _safe_get(agent, "tools", [])
                    agent["tools"] = [
                        t for t in current_tools if t not in tools_to_remove
                    ]
                    break

        elif action == "remove_circular_dependency":
            task_id = issue.auto_fix_data.get("task_id")
            dep_to_remove = issue.auto_fix_data.get("dependency_to_remove")

            for task in tasks:
                if (
                    _safe_get(task, "id") == task_id
                    or _safe_get(task, "name") == task_id
                ):
                    deps = _safe_get(task, "dependencies", [])
                    if dep_to_remove in deps:
                        deps.remove(dep_to_remove)
                        task["dependencies"] = deps
                    break

        elif action == "assign_agent":
            task_id = issue.auto_fix_data.get("task_id")
            agent_id = issue.auto_fix_data.get("agent_id")

            for task in tasks:
                if (
                    _safe_get(task, "id") == task_id
                    or _safe_get(task, "name") == task_id
                ):
                    task["assigned_agent"] = agent_id
                    task["agent"] = agent_id
                    break

        elif action == "reassign_task":
            task_id = issue.auto_fix_data.get("task_id")
            new_agent_id = issue.auto_fix_data.get("new_agent_id")

            if new_agent_id:
                for task in tasks:
                    if (
                        _safe_get(task, "id") == task_id
                        or _safe_get(task, "name") == task_id
                    ):
                        task["assigned_agent"] = new_agent_id
                        task["agent"] = new_agent_id
                        break

        return agents, tasks
