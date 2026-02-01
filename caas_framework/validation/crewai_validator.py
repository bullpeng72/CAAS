"""
CrewAI Framework Validator

Validates generated code for CrewAI-specific correctness and best practices.
"""

import ast
import sys
import subprocess
from typing import List, Optional
from dataclasses import dataclass

from caas_framework.models.validation import ValidationIssue, ValidationResult


@dataclass
class ExecutionResult:
    """Execution result"""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float = 0.0
    error_message: Optional[str] = None


class CrewAIValidator:
    """
    CrewAI Framework Validator

    Validates generated code for CrewAI-specific requirements:
    - Agent initialization and configuration
    - Task definition and dependencies
    - Crew setup and execution
    - Tool integration
    - Memory configuration
    """

    # Required Agent parameters
    AGENT_REQUIRED_PARAMS = {'role', 'goal', 'backstory'}

    # Required Task parameters
    TASK_REQUIRED_PARAMS = {'description', 'expected_output', 'agent'}

    # Valid Process types
    VALID_PROCESS_TYPES = {'sequential', 'hierarchical', 'parallel'}

    def __init__(self):
        """Initialize validator"""

    def validate_agent_code(self, agent_file_content: str) -> ValidationResult:
        """
        Validate Agent definitions in agents.py

        Args:
            agent_file_content: Content of agents.py file

        Returns:
            ValidationResult with issues found
        """
        issues = []

        try:
            tree = ast.parse(agent_file_content)

            # Find all Agent(...) instantiations
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    # Check if right side is Agent() call
                    if isinstance(node.value, ast.Call):
                        if self._is_agent_call(node.value):
                            agent_name = node.targets[0].id if node.targets else "unknown"
                            issues.extend(self._validate_agent_call(
                                node.value,
                                agent_name,
                                node.lineno
                            ))

        except SyntaxError as e:
            issues.append(ValidationIssue(
                severity="error",
                issue_type="syntax_error",
                message=f"Syntax error in agents.py: {e}",
                line=e.lineno
            ))

        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == "error"]) == 0,
            issues=issues
        )

    def validate_task_code(self, task_file_content: str) -> ValidationResult:
        """
        Validate Task definitions in tasks.py

        Args:
            task_file_content: Content of tasks.py file

        Returns:
            ValidationResult with issues found
        """
        issues = []

        try:
            tree = ast.parse(task_file_content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    if isinstance(node.value, ast.Call):
                        if self._is_task_call(node.value):
                            task_name = node.targets[0].id if node.targets else "unknown"
                            issues.extend(self._validate_task_call(
                                node.value,
                                task_name,
                                node.lineno
                            ))

        except SyntaxError as e:
            issues.append(ValidationIssue(
                severity="error",
                issue_type="syntax_error",
                message=f"Syntax error in tasks.py: {e}",
                line=e.lineno
            ))

        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == "error"]) == 0,
            issues=issues
        )

    def validate_crew_code(self, crew_file_content: str) -> ValidationResult:
        """
        Validate Crew definition in crew.py

        Args:
            crew_file_content: Content of crew.py file

        Returns:
            ValidationResult with issues found
        """
        issues = []

        try:
            tree = ast.parse(crew_file_content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    if isinstance(node.value, ast.Call):
                        if self._is_crew_call(node.value):
                            issues.extend(self._validate_crew_call(
                                node.value,
                                node.lineno
                            ))

        except SyntaxError as e:
            issues.append(ValidationIssue(
                severity="error",
                issue_type="syntax_error",
                message=f"Syntax error in crew.py: {e}",
                line=e.lineno
            ))

        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == "error"]) == 0,
            issues=issues
        )

    def validate_runtime(self, temp_dir: str) -> ExecutionResult:
        """
        Validate actual CrewAI runtime execution

        This performs a dry-run to ensure:
        - Agents can be instantiated
        - Tasks can be created
        - Crew can be initialized
        - No runtime errors occur

        Args:
            temp_dir: Temporary directory containing generated code

        Returns:
            ExecutionResult with execution status
        """

        test_script = f"""
import sys
sys.path.insert(0, '{temp_dir}')

print("=" * 70)
print("CrewAI Runtime Validation")
print("=" * 70)

# Test 1: Import and validate agents
try:
    from src import agents
    print("\\n[1/4] ✓ Agents module imported")

    # Find all agent variables
    agent_vars = [
        (name, getattr(agents, name))
        for name in dir(agents)
        if name.startswith('agent_') and not name.startswith('__')
    ]

    print(f"      Found {{len(agent_vars)}} agents")

    # Validate each agent
    for name, agent in agent_vars:
        assert hasattr(agent, 'role'), f"{{name}}: missing 'role'"
        assert hasattr(agent, 'goal'), f"{{name}}: missing 'goal'"
        assert hasattr(agent, 'backstory'), f"{{name}}: missing 'backstory'"
        assert hasattr(agent, 'tools'), f"{{name}}: missing 'tools'"

        # Validate tools is a list
        assert isinstance(agent.tools, list), f"{{name}}: tools must be a list"

        print(f"      ✓ {{name}}: role='{{agent.role}}', {{len(agent.tools)}} tools")

except Exception as e:
    print(f"\\n[1/4] ✗ Agent validation failed: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Import and validate tasks
try:
    from src import tasks
    print("\\n[2/4] ✓ Tasks module imported")

    # Find all task variables
    task_vars = [
        (name, getattr(tasks, name))
        for name in dir(tasks)
        if name.startswith('task_') and not name.startswith('__')
    ]

    print(f"      Found {{len(task_vars)}} tasks")

    # Validate each task
    for name, task in task_vars:
        assert hasattr(task, 'description'), f"{{name}}: missing 'description'"
        assert hasattr(task, 'expected_output'), f"{{name}}: missing 'expected_output'"
        assert hasattr(task, 'agent'), f"{{name}}: missing 'agent'"
        assert hasattr(task, 'context'), f"{{name}}: missing 'context'"

        # Validate context is a list
        assert isinstance(task.context, list), f"{{name}}: context must be a list"

        print(f"      ✓ {{name}}: agent={{task.agent.role if hasattr(task.agent, 'role') else 'unknown'}}, {{len(task.context)}} dependencies")

except Exception as e:
    print(f"\\n[2/4] ✗ Task validation failed: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Import and validate crew
try:
    from src.crew import crew
    print("\\n[3/4] ✓ Crew module imported")

    # Validate crew
    assert hasattr(crew, 'agents'), "Crew missing 'agents'"
    assert hasattr(crew, 'tasks'), "Crew missing 'tasks'"
    assert hasattr(crew, 'process'), "Crew missing 'process'"

    assert len(crew.agents) > 0, "Crew has no agents"
    assert len(crew.tasks) > 0, "Crew has no tasks"

    print(f"      ✓ Crew: {{len(crew.agents)}} agents, {{len(crew.tasks)}} tasks")
    print(f"      ✓ Process: {{crew.process}}")

except Exception as e:
    print(f"\\n[3/4] ✗ Crew validation failed: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Validate crew configuration
try:
    print("\\n[4/4] Validating crew configuration...")

    # Check if process type is valid
    valid_processes = ['sequential', 'hierarchical', 'parallel']
    process_str = str(crew.process).split('.')[-1].lower()

    if process_str not in valid_processes:
        print(f"      ⚠️  Warning: Unknown process type '{{process_str}}'")

    # Check agent-task assignment
    crew_agents_set = set(crew.agents)
    task_agents_set = set(task.agent for task in crew.tasks)

    unassigned_agents = crew_agents_set - task_agents_set
    if unassigned_agents:
        print(f"      ⚠️  Warning: {{len(unassigned_agents)}} agents have no tasks")

    print("      ✓ Crew configuration valid")

except Exception as e:
    print(f"\\n[4/4] ✗ Configuration validation failed: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\\n" + "=" * 70)
print("✅ All CrewAI runtime validations passed!")
print("=" * 70)
"""

        try:
            result = subprocess.run(
                [sys.executable, "-c", test_script],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=temp_dir
            )

            return ExecutionResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=None if result.returncode == 0 else result.stderr
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Execution timeout (>30s)",
                error_message="Runtime validation timed out"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                error_message=f"Runtime validation error: {e}"
            )

    # ========================================
    # Private helper methods
    # ========================================

    def _is_agent_call(self, node: ast.Call) -> bool:
        """Check if AST node is an Agent() call"""
        if isinstance(node.func, ast.Name):
            return node.func.id == 'Agent'
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr == 'Agent'
        return False

    def _is_task_call(self, node: ast.Call) -> bool:
        """Check if AST node is a Task() call"""
        if isinstance(node.func, ast.Name):
            return node.func.id == 'Task'
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr == 'Task'
        return False

    def _is_crew_call(self, node: ast.Call) -> bool:
        """Check if AST node is a Crew() call"""
        if isinstance(node.func, ast.Name):
            return node.func.id == 'Crew'
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr == 'Crew'
        return False

    def _validate_agent_call(
        self,
        node: ast.Call,
        agent_name: str,
        line: int
    ) -> List[ValidationIssue]:
        """Validate Agent instantiation"""
        issues = []

        # CRITICAL: Check for positional arguments (not allowed in CrewAI Pydantic v2 models)
        if len(node.args) > 0:
            issues.append(ValidationIssue(
                severity="error",
                issue_type="invalid_api_usage",
                message=f"Agent '{agent_name}' uses positional arguments. "
                        f"CrewAI Agent (Pydantic v2 model) only accepts keyword arguments.",
                line=line,
                suggested_fix=f"Convert to keyword arguments: Agent(role='...', goal='...', backstory='...', ...)"
            ))
            # Don't continue validation if using positional args
            return issues

        # Extract provided parameters
        provided_params = {kw.arg for kw in node.keywords if kw.arg}

        # Check required parameters
        missing = self.AGENT_REQUIRED_PARAMS - provided_params
        if missing:
            issues.append(ValidationIssue(
                severity="error",
                issue_type="missing_parameter",
                message=f"Agent '{agent_name}' missing required parameters: {missing}",
                line=line,
                suggested_fix=f"Add missing parameters: {', '.join(missing)}"
            ))

        # Validate tools parameter
        for keyword in node.keywords:
            if keyword.arg == 'tools':
                issues.extend(self._validate_tools_param(
                    keyword.value,
                    agent_name,
                    line
                ))

            # Validate memory parameter (should be boolean)
            if keyword.arg == 'memory':
                if isinstance(keyword.value, ast.Constant):
                    if not isinstance(keyword.value.value, bool):
                        issues.append(ValidationIssue(
                            severity="warning",
                            issue_type="invalid_parameter_type",
                            message=f"Agent '{agent_name}': memory should be boolean",
                            line=line,
                            suggested_fix="Use True or False for memory parameter"
                        ))

        return issues

    def _validate_tools_param(
        self,
        tools_node: ast.AST,
        agent_name: str,
        line: int
    ) -> List[ValidationIssue]:
        """Validate tools parameter"""
        issues = []

        # tools must be a List
        if not isinstance(tools_node, ast.List):
            issues.append(ValidationIssue(
                severity="error",
                issue_type="invalid_type",
                message=f"Agent '{agent_name}': tools must be a list",
                line=line,
                suggested_fix="Wrap tools in square brackets: [tool1(), tool2()]"
            ))
            return issues

        # Each tool should be instantiated (Call node)
        for i, element in enumerate(tools_node.elts):
            if not isinstance(element, ast.Call):
                issues.append(ValidationIssue(
                    severity="error",
                    issue_type="tool_not_instantiated",
                    message=f"Agent '{agent_name}': tool #{i+1} not instantiated",
                    line=line,
                    suggested_fix="Add parentheses to instantiate tool: ToolName()"
                ))

        return issues

    def _validate_task_call(
        self,
        node: ast.Call,
        task_name: str,
        line: int
    ) -> List[ValidationIssue]:
        """Validate Task instantiation"""
        issues = []

        # CRITICAL: Check for positional arguments (not allowed in CrewAI Pydantic v2 models)
        if len(node.args) > 0:
            issues.append(ValidationIssue(
                severity="error",
                issue_type="invalid_api_usage",
                message=f"Task '{task_name}' uses positional arguments. "
                        f"CrewAI Task (Pydantic v2 model) only accepts keyword arguments.",
                line=line,
                suggested_fix=f"Convert to keyword arguments: Task(description='...', expected_output='...', agent=..., ...)"
            ))
            # Don't continue validation if using positional args
            return issues

        # Extract provided parameters
        provided_params = {kw.arg for kw in node.keywords if kw.arg}

        # Check required parameters
        missing = self.TASK_REQUIRED_PARAMS - provided_params
        if missing:
            issues.append(ValidationIssue(
                severity="error",
                issue_type="missing_parameter",
                message=f"Task '{task_name}' missing required parameters: {missing}",
                line=line,
                suggested_fix=f"Add missing parameters: {', '.join(missing)}"
            ))

        # Validate context parameter
        for keyword in node.keywords:
            if keyword.arg == 'context':
                issues.extend(self._validate_context_param(
                    keyword.value,
                    task_name,
                    line
                ))

        return issues

    def _validate_context_param(
        self,
        context_node: ast.AST,
        task_name: str,
        line: int
    ) -> List[ValidationIssue]:
        """Validate context (task dependencies) parameter"""
        issues = []

        # context must be a List
        if not isinstance(context_node, ast.List):
            issues.append(ValidationIssue(
                severity="error",
                issue_type="invalid_type",
                message=f"Task '{task_name}': context must be a list",
                line=line,
                suggested_fix="Wrap context in square brackets: [task_1, task_2]"
            ))
            return issues

        # Each context element should be a Name (task variable reference), NOT a string
        for i, element in enumerate(context_node.elts):
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                issues.append(ValidationIssue(
                    severity="error",
                    issue_type="invalid_context_type",
                    message=f"Task '{task_name}': context should reference Task objects, not strings",
                    line=line,
                    suggested_fix=f"Remove quotes: context=[task_1] not context=['task_1']"
                ))

        return issues

    def _validate_crew_call(
        self,
        node: ast.Call,
        line: int
    ) -> List[ValidationIssue]:
        """Validate Crew instantiation"""
        issues = []

        # CRITICAL: Check for positional arguments (not allowed in CrewAI Pydantic v2 models)
        if len(node.args) > 0:
            issues.append(ValidationIssue(
                severity="error",
                issue_type="invalid_api_usage",
                message=f"Crew uses positional arguments. "
                        f"CrewAI Crew (Pydantic v2 model) only accepts keyword arguments.",
                line=line,
                suggested_fix=f"Convert to keyword arguments: Crew(agents=[...], tasks=[...], ...)"
            ))
            # Don't continue validation if using positional args
            return issues

        # Extract provided parameters
        provided_params = {kw.arg for kw in node.keywords if kw.arg}

        # Check required parameters
        required = {'agents', 'tasks'}
        missing = required - provided_params
        if missing:
            issues.append(ValidationIssue(
                severity="error",
                issue_type="missing_parameter",
                message=f"Crew missing required parameters: {missing}",
                line=line,
                suggested_fix=f"Add: {', '.join(missing)}=[...]"
            ))

        # Validate process parameter if present
        for keyword in node.keywords:
            if keyword.arg == 'process':
                # Should be Process.sequential, Process.hierarchical, etc.
                if isinstance(keyword.value, ast.Attribute):
                    process_type = keyword.value.attr.lower()
                    if process_type not in self.VALID_PROCESS_TYPES:
                        issues.append(ValidationIssue(
                            severity="warning",
                            issue_type="invalid_process_type",
                            message=f"Unknown process type: {process_type}",
                            line=line,
                            suggested_fix=f"Use one of: {', '.join(self.VALID_PROCESS_TYPES)}"
                        ))

        return issues
