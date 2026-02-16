"""
Ontology-Based Validator

Validates agent and task configurations using ontology rules.
Provides automatic fixing suggestions.
"""

from typing import Any, Dict, List, Optional, Tuple


from caas_framework.knowledge.ontology import OntologyManager
from caas_framework.models.validation import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)
from caas_framework.utils.safe_access import safe_get_value as _safe_get
from caas_framework.validation.agent_matcher import AgentMatcher
from caas_framework.validation.issue_factory import ValidationIssueFactory


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

        # Generate summary using factory method
        summary = ValidationIssueFactory.create_validation_summary(issues)
        is_valid = summary["is_valid"]

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
                _safe_get(task, "id", _safe_get(task, "name", "unknown"))

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

                    suitable_roles = self.ontology.get_suitable_roles(task_type)

                    # Use AgentMatcher to find suitable agent
                    suitable_agent = AgentMatcher.find_suitable_agent_by_role(
                        agents, suitable_roles, self.ontology
                    )

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
                    # Use AgentMatcher to find the best suitable agent
                    best_agent = AgentMatcher.find_suitable_agent_by_role(
                        agents, suitable_roles, self.ontology
                    )

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
                    set(task_methods) - set(required_methods)

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

    def validate_design_time(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        golden_data: Optional[Any] = None,
    ) -> ValidationResult:
        """
        ✅ v0.5.0: Design-Time validation before code generation.

        Validates:
        1. UI requirements mapping (critical for preventing empty input sections)
        2. Template variable consistency
        3. Tool compatibility with roles
        4. Semantic consistency between agents and tasks

        This runs AFTER Phase 3 (Design) and BEFORE Phase 4 (Delivery).

        Args:
            agents: List of agent specifications
            tasks: List of task specifications
            golden_data: Optional ConcretizedRequirement for context

        Returns:
            ValidationResult with design-time issues
        """
        issues: List[ValidationIssue] = []

        # Check 1: UI requirements mapping (CRITICAL - prevents empty input sections)
        issues.extend(self._validate_ui_requirements_mapping(tasks, golden_data))

        # Check 2: Template variable consistency
        issues.extend(self._validate_template_variables(tasks))

        # Check 3: Tool-role compatibility (enhanced from existing)
        issues.extend(self._validate_tool_role_compatibility(agents))

        # Check 4: Semantic consistency (agent goals match task descriptions)
        issues.extend(self._validate_semantic_consistency(agents, tasks))

        # Check 5: Data flow consistency (task dependencies and output types)
        issues.extend(self._validate_data_flow(tasks))

        # Generate summary
        summary = ValidationIssueFactory.create_validation_summary(issues)
        is_valid = summary["is_valid"]

        return ValidationResult(is_valid=is_valid, issues=issues, summary=summary)

    def _validate_ui_requirements_mapping(
        self,
        tasks: List[Dict[str, Any]],
        golden_data: Optional[Any] = None,
    ) -> List[ValidationIssue]:
        """
        ✅ v0.5.0: Validate that UI requirements are properly mapped.

        This is the KEY check that would have prevented the empty input section bug!

        Checks:
        - If tasks have template variables ({keyword}), inputs are expected
        - If golden_data mentions input/검색/키워드, inputs should be captured
        """
        issues = []

        # Extract template variables from all tasks
        import re

        template_vars = set()
        for task in tasks:
            description = _safe_get(task, "description", "")
            matches = re.findall(r"\{(\w+)\}", description)
            template_vars.update(matches)

        # Check if template variables exist but golden_data doesn't mention inputs
        if template_vars and golden_data:
            # Check if golden_data mentions these inputs
            golden_desc = str(golden_data)  # Convert to string for searching

            for var_name in template_vars:
                # Check if variable is mentioned in golden data
                mentioned = (
                    var_name.lower() in golden_desc.lower()
                    or "입력" in golden_desc
                    or "input" in golden_desc.lower()
                )

                if not mentioned:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            issue_type="ui_requirement",
                            message=f"Template variable '{var_name}' used but not mentioned in requirements",
                            suggested_fix=f"Add requirement describing '{var_name}' input or remove template variable",
                            auto_fix_available=False,
                        )
                    )

        # Check reverse: golden_data mentions input but no template variables
        if golden_data and not template_vars:
            golden_desc = str(golden_data).lower()

            # Input-related keywords
            input_keywords = [
                "입력",
                "검색",
                "키워드",
                "input",
                "search",
                "keyword",
                "query",
            ]

            mentions_input = any(kw in golden_desc for kw in input_keywords)

            if mentions_input:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        issue_type="missing_ui_mapping",
                        message="Requirements mention user input but no template variables found in tasks",
                        suggested_fix="Add template variables like {keyword} to task descriptions",
                        auto_fix_available=True,
                        auto_fix_data={
                            "action": "add_template_variable",
                            "variable_name": "keyword",
                            "task_id": _safe_get(tasks[0], "id") if tasks else None,
                        },
                    )
                )

        return issues

    def _validate_template_variables(
        self, tasks: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """
        ✅ v0.5.0: Validate template variable consistency across tasks.

        Checks:
        - All template variables use consistent naming
        - No undefined variables
        """
        issues = []

        import re

        all_template_vars = {}

        for task in tasks:
            task_id = _safe_get(task, "id", "unknown")
            description = _safe_get(task, "description", "")

            # Find all {variable} patterns
            matches = re.findall(r"\{(\w+)\}", description)

            for var_name in matches:
                if var_name not in all_template_vars:
                    all_template_vars[var_name] = []
                all_template_vars[var_name].append(task_id)

        # Check for inconsistent usage (different variable names for same concept)
        keyword_variants = ["keyword", "query", "search", "search_term"]
        used_keyword_variants = [v for v in keyword_variants if v in all_template_vars]

        if len(used_keyword_variants) > 1:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    issue_type="inconsistent_variables",
                    message=f"Multiple keyword variants used: {', '.join(used_keyword_variants)}",
                    suggested_fix=f"Standardize to single variable name: '{used_keyword_variants[0]}'",
                    auto_fix_available=True,
                    auto_fix_data={
                        "action": "standardize_variables",
                        "variants": used_keyword_variants,
                        "canonical": used_keyword_variants[0],
                    },
                )
            )

        return issues

    def _validate_tool_role_compatibility(
        self, agents: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """
        ✅ v0.5.0: Enhanced tool-role compatibility check using ontology.

        Checks if assigned tools are appropriate for agent roles.
        """
        issues = []

        # Tool-role compatibility map from ontology
        tool_role_map = {
            "web_search": ["researcher", "analyst", "investigator"],
            "file_read": ["analyst", "developer", "researcher"],
            "file_write": ["developer", "writer", "reporter"],
            "code_interpreter": ["developer", "analyst"],
            "directory_read": ["developer", "analyst"],
        }

        for agent in agents:
            agent_id = _safe_get(agent, "id", "unknown")
            role = _safe_get(agent, "role", "").lower()
            tools = _safe_get(agent, "tools", [])

            for tool_name in tools:
                compatible_roles = tool_role_map.get(tool_name, [])

                if compatible_roles and role not in compatible_roles:
                    # Check if role is similar to any compatible role
                    similar_role = any(
                        comp_role in role or role in comp_role
                        for comp_role in compatible_roles
                    )

                    if not similar_role:
                        issues.append(
                            ValidationIssue(
                                severity=ValidationSeverity.WARNING,
                                issue_type="tool_role_mismatch",
                                agent_id=agent_id,
                                message=f"Tool '{tool_name}' may not be suitable for role '{role}'",
                                suggested_fix=f"Consider roles: {', '.join(compatible_roles)}",
                                auto_fix_available=False,
                            )
                        )

        return issues

    def _validate_semantic_consistency(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
    ) -> List[ValidationIssue]:
        """
        ✅ v0.5.0: Validate semantic consistency between agents and tasks.

        Checks if agent goals semantically match assigned task descriptions.
        Uses simple keyword overlap for now (can be enhanced with embeddings).
        """
        issues = []

        for task in tasks:
            task_id = _safe_get(task, "id", "unknown")
            task_desc = _safe_get(task, "description", "").lower()
            assigned_agent_id = _safe_get(task, "agent") or _safe_get(
                task, "assigned_agent"
            )

            if not assigned_agent_id:
                continue

            # Find agent
            agent = next(
                (a for a in agents if _safe_get(a, "id") == assigned_agent_id), None
            )

            if not agent:
                continue

            agent_goal = _safe_get(agent, "goal", "").lower()

            # Simple keyword overlap check
            agent_keywords = set(agent_goal.split())
            task_keywords = set(task_desc.split())

            # Remove common words
            stop_words = {
                "the",
                "a",
                "an",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
                "는",
                "을",
                "를",
                "이",
                "가",
                "의",
            }
            agent_keywords -= stop_words
            task_keywords -= stop_words

            overlap = len(agent_keywords & task_keywords)

            # If overlap is very low, flag as potential mismatch
            if overlap < 2 and len(agent_keywords) > 3:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        issue_type="semantic_mismatch",
                        agent_id=assigned_agent_id,
                        task_id=task_id,
                        message=f"Agent '{assigned_agent_id}' goal may not match task '{task_id}' description (low keyword overlap)",
                        suggested_fix="Review agent-task assignment for semantic consistency",
                        auto_fix_available=False,
                    )
                )

        return issues

    def _validate_data_flow(
        self, tasks: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """
        ✅ v0.5.0: Validate data flow consistency between tasks.

        Checks:
        - Task dependencies are properly defined
        - Output types match expected input types in dependent tasks
        - No circular dependencies
        - Template variables flow correctly through task chain
        """
        issues = []

        # Build dependency graph
        task_map = {_safe_get(t, "id", f"task_{i}"): t for i, t in enumerate(tasks)}
        dependencies = {}

        for task in tasks:
            task_id = _safe_get(task, "id", "unknown")
            context_deps = _safe_get(task, "context", [])

            # Extract dependencies from context
            if context_deps:
                dependencies[task_id] = context_deps if isinstance(context_deps, list) else [context_deps]

        # Check 1: Validate all dependencies exist
        for task_id, deps in dependencies.items():
            for dep_id in deps:
                if dep_id not in task_map:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            issue_type="missing_dependency",
                            task_id=task_id,
                            message=f"Task '{task_id}' depends on non-existent task '{dep_id}'",
                            suggested_fix=f"Remove dependency or create task '{dep_id}'",
                            auto_fix_available=False,
                        )
                    )

        # Check 2: Detect circular dependencies
        def has_cycle(task_id: str, visited: set, rec_stack: set) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            for dep in dependencies.get(task_id, []):
                if dep not in visited:
                    if has_cycle(dep, visited, rec_stack):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        visited = set()
        for task_id in task_map.keys():
            if task_id not in visited:
                rec_stack = set()
                if has_cycle(task_id, visited, rec_stack):
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            issue_type="circular_dependency",
                            task_id=task_id,
                            message=f"Circular dependency detected involving task '{task_id}'",
                            suggested_fix="Remove circular dependencies to create a valid task flow",
                            auto_fix_available=False,
                        )
                    )
                    break  # Only report once

        # Check 3: Validate template variable flow
        import re

        for task in tasks:
            task_id = _safe_get(task, "id", "unknown")
            description = _safe_get(task, "description", "")
            deps = dependencies.get(task_id, [])

            # Find template variables in description
            template_vars = set(re.findall(r"\{(\w+)\}", description))

            if template_vars and deps:
                # Check if dependent tasks provide these variables in their output
                for dep_id in deps:
                    dep_task = task_map.get(dep_id)
                    if dep_task:
                        dep_output = _safe_get(dep_task, "expected_output", "").lower()

                        # Check if output mentions the required variables
                        for var in template_vars:
                            if var.lower() not in dep_output:
                                issues.append(
                                    ValidationIssue(
                                        severity=ValidationSeverity.WARNING,
                                        issue_type="data_flow_mismatch",
                                        task_id=task_id,
                                        message=f"Task '{task_id}' requires '{var}' but dependency '{dep_id}' may not provide it",
                                        suggested_fix=f"Ensure task '{dep_id}' output includes '{var}' or remove dependency",
                                        auto_fix_available=False,
                                    )
                                )

        return issues

        return agents, tasks
