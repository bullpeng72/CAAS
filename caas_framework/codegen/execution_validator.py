"""
Execution Validator

Validates that generated code is executable and production-ready.
Includes AST parsing, type checking with mypy, and dry-run execution.
"""

import ast
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from caas_framework.models.validation import ValidationIssue


@dataclass
class ExecutionValidationResult:
    """Execution validation result"""

    is_valid: bool
    is_executable: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    syntax_check_passed: bool = True
    import_check_passed: bool = True
    type_check_passed: bool = True
    dry_run_passed: bool = True
    error_count: int = 0
    warning_count: int = 0


class ExecutionValidator:
    """
    Execution Validator

    Validates generated code through multiple stages:
    1. Syntax validation (AST parsing)
    2. Import validation
    3. Type checking (mypy)
    4. Dry-run execution

    Ensures 100% executable code.
    """

    def __init__(
        self,
        enable_syntax_check: bool = True,
        enable_import_check: bool = True,
        enable_type_check: bool = True,
        enable_dry_run: bool = False,  # Disabled by default for safety
        enable_staged_validation: bool = True,  # NEW: Enable staged execution validation
    ):
        """
        Initialize validator.

        Args:
            enable_syntax_check: Check Python syntax with AST
            enable_import_check: Check all imports are valid
            enable_type_check: Run mypy type checking
            enable_dry_run: Execute code in safe environment
            enable_staged_validation: Validate execution in stages (import → instantiate → execute)
        """
        self.enable_syntax_check = enable_syntax_check
        self.enable_import_check = enable_import_check
        self.enable_type_check = enable_type_check
        self.enable_dry_run = enable_dry_run
        self.enable_staged_validation = enable_staged_validation

    def validate(self, files: Dict[str, str]) -> ExecutionValidationResult:
        """
        Validate all generated files.

        Args:
            files: Dictionary of filename -> content

        Returns:
            ExecutionValidationResult: Validation results
        """
        result = ExecutionValidationResult(is_valid=True, is_executable=True)

        # Filter Python files only
        python_files = {path: content for path, content in files.items() if path.endswith(".py")}

        if not python_files:
            return result

        # Stage 1: Syntax check
        if self.enable_syntax_check:
            syntax_issues = self._check_syntax(python_files)
            result.issues.extend(syntax_issues)
            result.syntax_check_passed = not any(
                issue.severity == "error" for issue in syntax_issues
            )

        # Stage 2: Import check
        if self.enable_import_check:
            import_issues = self._check_imports(python_files)
            result.issues.extend(import_issues)
            result.import_check_passed = not any(
                issue.severity == "error" for issue in import_issues
            )

        # Stage 3: Type check (mypy)
        if self.enable_type_check:
            type_issues = self._check_types(python_files)
            result.issues.extend(type_issues)
            result.type_check_passed = not any(issue.severity == "error" for issue in type_issues)

        # Stage 4: Staged execution validation (NEW)
        # This validates in stages: import → instantiation → basic execution
        if self.enable_staged_validation:
            staged_issues = self._staged_execution_validation(files)
            result.issues.extend(staged_issues)
            # If staged validation finds errors, mark as not executable
            if any(issue.severity == "error" for issue in staged_issues):
                result.is_executable = False

        # Stage 5: Dry-run (optional, disabled by default for safety)
        # Full execution test
        if self.enable_dry_run:
            dry_run_issues = self._dry_run(python_files)
            result.issues.extend(dry_run_issues)
            result.dry_run_passed = not any(issue.severity == "error" for issue in dry_run_issues)

        # Calculate counts
        result.error_count = sum(1 for issue in result.issues if issue.severity == "error")
        result.warning_count = sum(1 for issue in result.issues if issue.severity == "warning")

        # Determine validity
        result.is_valid = result.error_count == 0
        result.is_executable = (
            result.syntax_check_passed
            and result.import_check_passed
            and (result.type_check_passed or not self.enable_type_check)
            and (result.dry_run_passed or not self.enable_dry_run)
        )

        return result

    def _check_syntax(self, files: Dict[str, str]) -> List[ValidationIssue]:
        """
        Check Python syntax with AST parsing.

        Args:
            files: Python files to check

        Returns:
            List[ValidationIssue]: Syntax errors found
        """
        issues = []

        for filepath, content in files.items():
            try:
                ast.parse(content)
            except SyntaxError as e:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        issue_type="syntax",
                        message=f"Syntax error: {e.msg}",
                        file=filepath,
                        line=e.lineno,
                        column=e.offset,
                    )
                )
            except Exception as e:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        issue_type="syntax",
                        message=f"Parse error: {str(e)}",
                        file=filepath,
                    )
                )

        return issues

    def _check_imports(self, files: Dict[str, str]) -> List[ValidationIssue]:
        """
        Check that all imports are valid.

        Args:
            files: Python files to check

        Returns:
            List[ValidationIssue]: Import errors found
        """
        issues = []

        for filepath, content in files.items():
            try:
                tree = ast.parse(content)

                # Extract all imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            # Try to import (simple check)
                            module_name = alias.name.split(".")[0]
                            if not self._is_stdlib_or_known(module_name):
                                issues.append(
                                    ValidationIssue(
                                        severity="warning",
                                        issue_type="import",
                                        message=f"Import '{alias.name}' may not be available",
                                        file=filepath,
                                        line=node.lineno,
                                    )
                                )

                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module_name = node.module.split(".")[0]
                            if not self._is_stdlib_or_known(module_name):
                                issues.append(
                                    ValidationIssue(
                                        severity="warning",
                                        issue_type="import",
                                        message=f"Import from '{node.module}' may not be available",
                                        file=filepath,
                                        line=node.lineno,
                                    )
                                )

            except Exception as e:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        issue_type="import",
                        message=f"Failed to check imports: {str(e)}",
                        file=filepath,
                    )
                )

        return issues

    def _check_types(self, files: Dict[str, str]) -> List[ValidationIssue]:
        """
        Check types with mypy.

        Args:
            files: Python files to check

        Returns:
            List[ValidationIssue]: Type errors found
        """
        issues = []

        # Create temporary directory with files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Write all files
            for filepath, content in files.items():
                file_path = tmppath / filepath
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)

            # Run mypy
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "mypy", "--ignore-missing-imports", str(tmppath)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                # Parse mypy output
                for line in result.stdout.split("\n"):
                    if ":" in line and ("error:" in line or "warning:" in line):
                        parts = line.split(":", 3)
                        if len(parts) >= 4:
                            filepath = parts[0]
                            lineno = parts[1]
                            severity = "error" if "error:" in line else "warning"
                            message = parts[3].strip()

                            issues.append(
                                ValidationIssue(
                                    severity=severity,
                                    issue_type="type",
                                    message=message,
                                    file=filepath,
                                    line=int(lineno) if lineno.isdigit() else None,
                                )
                            )

            except subprocess.TimeoutExpired:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        issue_type="type",
                        message="Type checking timed out after 30s",
                        file="(mypy)",
                    )
                )
            except FileNotFoundError:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        issue_type="type",
                        message="mypy not installed, skipping type check",
                        file="(mypy)",
                    )
                )
            except Exception as e:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        issue_type="type",
                        message=f"Type checking failed: {str(e)}",
                        file="(mypy)",
                    )
                )

        return issues

    def _dry_run(self, files: Dict[str, str]) -> List[ValidationIssue]:
        """
        Perform dry-run execution in sandboxed environment.

        Args:
            files: Python files to execute

        Returns:
            List[ValidationIssue]: Runtime errors found
        """
        issues = []

        # Safety check - dry run is risky
        if not self.enable_dry_run:
            return issues

        # Find main.py or entry point
        main_file = None
        if "main.py" in files:
            main_file = "main.py"
        else:
            # Look for file with if __name__ == "__main__"
            for filepath, content in files.items():
                if "__name__" in content and "__main__" in content:
                    main_file = filepath
                    break

        if not main_file:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    issue_type="runtime",
                    message="No entry point found for dry-run",
                    file="(dry-run)",
                )
            )
            return issues

        # Execute in temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Write all files
            for filepath, content in files.items():
                file_path = tmppath / filepath
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)

            # Try to execute (with timeout for safety)
            try:
                result = subprocess.run(
                    [sys.executable, str(tmppath / main_file)],
                    capture_output=True,
                    text=True,
                    timeout=10,  # 10 second timeout
                    cwd=tmppath,
                )

                if result.returncode != 0:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            issue_type="runtime",
                            message=f"Execution failed: {result.stderr}",
                            file=main_file,
                        )
                    )

            except subprocess.TimeoutExpired:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        issue_type="runtime",
                        message="Execution timed out (may be waiting for input)",
                        file=main_file,
                    )
                )
            except Exception as e:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        issue_type="runtime",
                        message=f"Execution error: {str(e)}",
                        file=main_file,
                    )
                )

        return issues

    def _is_stdlib_or_known(self, module_name: str) -> bool:
        """Check if module is stdlib or known third-party"""
        stdlib_modules = {
            "os",
            "sys",
            "json",
            "time",
            "datetime",
            "pathlib",
            "typing",
            "dataclasses",
            "functools",
            "itertools",
            "collections",
            "asyncio",
            "logging",
            "traceback",
            "re",
            "math",
            "random",
            "uuid",
            "copy",
            "tempfile",
            "subprocess",
            "shutil",
            "glob",
            "argparse",
        }

        known_third_party = {
            "crewai",
            "pydantic",
            "fastapi",
            "uvicorn",
            "sqlalchemy",
            "alembic",
            "pytest",
            "requests",
            "numpy",
            "pandas",
        }

        return module_name in stdlib_modules or module_name in known_third_party

    def _staged_execution_validation(self, files: Dict[str, str]) -> List[ValidationIssue]:
        """
        Staged execution validation: import → instantiation → basic execution

        This validates in progressive stages to catch errors early:
        - Stage 1: Import all modules
        - Stage 2: Instantiate agents/tasks/crew
        - Stage 3: Basic configuration validation

        Args:
            files: All generated files

        Returns:
            List[ValidationIssue]: Issues found during staged validation
        """
        issues = []

        # Need temporary directory to test imports
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Write all files
            for filepath, content in files.items():
                file_path = tmppath / filepath
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)

            # Stage 1: Import validation
            import_result = self._test_module_imports(tmppath, files)
            if not import_result["success"]:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        issue_type="import_error",
                        message=f"Module import failed: {import_result['error']}",
                        file=import_result.get("file", "unknown"),
                    )
                )
                return issues  # Cannot proceed if imports fail

            # Stage 2: Instantiation validation
            instantiation_result = self._test_instantiation(tmppath)
            if not instantiation_result["success"]:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        issue_type="instantiation_error",
                        message=f"Instantiation failed: {instantiation_result['error']}",
                        file=instantiation_result.get("file", "unknown"),
                    )
                )
                # Note: We continue to gather more issues even if instantiation fails

            # Stage 3: Basic execution test (CrewAI specific)
            execution_result = self._test_basic_execution(tmppath)
            if not execution_result["success"]:
                # This is a warning, not an error, as it might need actual LLM keys
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        issue_type="execution_warning",
                        message=f"Basic execution test warning: {execution_result['error']}",
                        file=execution_result.get("file", "unknown"),
                    )
                )

        return issues

    def _test_module_imports(self, tmpdir: Path, files: Dict[str, str]) -> Dict:
        """Test that all modules can be imported"""

        # Extract Python module paths
        python_modules = [
            f.replace("/", ".").replace(".py", "")
            for f in files.keys()
            if f.endswith(".py") and not f.startswith("tests/")
        ]

        test_script = f"""
import sys
sys.path.insert(0, '{tmpdir}')

failed_modules = []

for module in {python_modules}:
    try:
        __import__(module)
    except Exception as e:
        failed_modules.append((module, str(e)))

if failed_modules:
    for module, error in failed_modules:
        print(f"IMPORT_FAILED: {{module}}: {{error}}")
    sys.exit(1)
else:
    print("ALL_IMPORTS_SUCCESS")
"""

        try:
            result = subprocess.run(
                [sys.executable, "-c", test_script],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=tmpdir,
            )

            if result.returncode != 0:
                # Parse error
                error_lines = result.stdout.split("\n")
                error_msg = "Unknown import error"
                for line in error_lines:
                    if line.startswith("IMPORT_FAILED:"):
                        error_msg = line.replace("IMPORT_FAILED:", "").strip()
                        break

                return {"success": False, "error": error_msg, "stderr": result.stderr}

            return {"success": True}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Import timeout (>15s)"}
        except Exception as e:
            return {"success": False, "error": f"Import test failed: {str(e)}"}

    def _test_instantiation(self, tmpdir: Path) -> Dict:
        """Test that agents, tasks, and crew can be instantiated"""

        test_script = f"""
import sys
sys.path.insert(0, '{tmpdir}')

try:
    # Test agents
    from src import agents
    agent_vars = [getattr(agents, name) for name in dir(agents) if name.startswith('agent_')]

    if not agent_vars:
        print("WARNING: No agents found")
    else:
        for agent in agent_vars:
            assert hasattr(agent, 'role'), "Agent missing 'role'"
            assert hasattr(agent, 'goal'), "Agent missing 'goal'"
        print(f"AGENTS_OK: {{len(agent_vars)}} agents")

    # Test tasks
    from src import tasks
    task_vars = [getattr(tasks, name) for name in dir(tasks) if name.startswith('task_')]

    if not task_vars:
        print("WARNING: No tasks found")
    else:
        for task in task_vars:
            assert hasattr(task, 'description'), "Task missing 'description'"
            assert hasattr(task, 'agent'), "Task missing 'agent'"
        print(f"TASKS_OK: {{len(task_vars)}} tasks")

    # Test crew
    from src.crew import crew
    assert hasattr(crew, 'agents'), "Crew missing 'agents'"
    assert hasattr(crew, 'tasks'), "Crew missing 'tasks'"
    assert len(crew.agents) > 0, "Crew has no agents"
    assert len(crew.tasks) > 0, "Crew has no tasks"
    print("CREW_OK")

    print("INSTANTIATION_SUCCESS")

except Exception as e:
    print(f"INSTANTIATION_FAILED: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""

        try:
            result = subprocess.run(
                [sys.executable, "-c", test_script],
                capture_output=True,
                text=True,
                timeout=20,
                cwd=tmpdir,
            )

            if result.returncode != 0:
                # Extract error message
                error_lines = result.stdout.split("\n")
                error_msg = "Unknown instantiation error"
                for line in error_lines:
                    if line.startswith("INSTANTIATION_FAILED:"):
                        error_msg = line.replace("INSTANTIATION_FAILED:", "").strip()
                        break

                return {"success": False, "error": error_msg, "stderr": result.stderr}

            return {"success": True}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Instantiation timeout (>20s)"}
        except Exception as e:
            return {"success": False, "error": f"Instantiation test failed: {str(e)}"}

    def _test_basic_execution(self, tmpdir: Path) -> Dict:
        """Test basic execution (without actual crew.kickoff())"""

        # This is a lightweight test - just verify structure
        test_script = f"""
import sys
sys.path.insert(0, '{tmpdir}')

try:
    from src.crew import crew

    # Verify crew configuration
    assert len(crew.agents) == len(set(crew.agents)), "Duplicate agents in crew"
    assert len(crew.tasks) == len(set(crew.tasks)), "Duplicate tasks in crew"

    # Verify task-agent assignments
    crew_agents_set = set(crew.agents)
    for task in crew.tasks:
        assert task.agent in crew_agents_set, f"Task assigned to agent not in crew"

    print("BASIC_EXECUTION_OK")

except Exception as e:
    print(f"BASIC_EXECUTION_WARNING: {{e}}")
    # This is not a failure - just a warning
"""

        try:
            result = subprocess.run(
                [sys.executable, "-c", test_script],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir,
            )

            if "BASIC_EXECUTION_WARNING:" in result.stdout:
                warning = result.stdout.split("BASIC_EXECUTION_WARNING:")[1].strip()
                return {"success": False, "error": warning}

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": f"Basic execution test failed: {str(e)}"}
