"""
Test Parser for Test-Driven Code Generation

Parses pytest test files to extract test expectations and requirements.
Used to generate code that passes the tests.

Part of CAAS-E Week 4 implementation (Task 4.2).
"""

import ast
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from caas_framework.utils.logger import get_logger


@dataclass
class TestAssertion:
    """Represents a test assertion."""

    type: str  # "equal", "true", "false", "in", "raises", "called", etc.
    target: str  # What is being tested
    expected: Optional[str] = None  # Expected value
    line_number: int = 0


@dataclass
class TestFixture:
    """Represents a pytest fixture."""

    name: str
    scope: str = "function"  # function, class, module, session
    params: List[str] = field(default_factory=list)
    return_type: Optional[str] = None


@dataclass
class TestFunction:
    """Represents a parsed test function."""

    name: str
    description: str
    fixtures: List[str] = field(default_factory=list)
    assertions: List[TestAssertion] = field(default_factory=list)
    mocks: List[str] = field(default_factory=list)
    setup_code: List[str] = field(default_factory=list)
    teardown_code: List[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class ParsedTestFile:
    """Represents a parsed test file."""

    file_path: Path
    imports: List[str] = field(default_factory=list)
    fixtures: List[TestFixture] = field(default_factory=list)
    test_functions: List[TestFunction] = field(default_factory=list)
    required_modules: Set[str] = field(default_factory=set)


class TestParser:
    """
    Parser for pytest test files.

    Extracts test expectations to guide code generation:
    - Test functions and their assertions
    - Fixtures and their dependencies
    - Mocked objects
    - Required imports

    Uses AST (Abstract Syntax Tree) for parsing.
    """

    def __init__(self):
        self.logger = get_logger(__name__)

    def parse_test_file(self, file_path: Path) -> ParsedTestFile:
        """
        Parse a pytest test file.

        Args:
            file_path: Path to test file

        Returns:
            ParsedTestFile with extracted information
        """
        self.logger.info(f"Parsing test file: {file_path}")

        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # Parse AST
        try:
            tree = ast.parse(source_code, filename=str(file_path))
        except SyntaxError as e:
            self.logger.error(f"Syntax error in test file: {e}")
            return ParsedTestFile(file_path=file_path)

        # Extract information
        parsed = ParsedTestFile(file_path=file_path)

        # Extract imports
        parsed.imports = self._extract_imports(tree)
        parsed.required_modules = self._extract_required_modules(parsed.imports)

        # Extract fixtures
        parsed.fixtures = self._extract_fixtures(tree)

        # Extract test functions
        parsed.test_functions = self._extract_test_functions(tree)

        self.logger.info(
            f"Parsed {len(parsed.test_functions)} tests, "
            f"{len(parsed.fixtures)} fixtures from {file_path.name}"
        )

        return parsed

    def parse_test_directory(self, test_dir: Path) -> List[ParsedTestFile]:
        """
        Parse all test files in a directory.

        Args:
            test_dir: Directory containing test files

        Returns:
            List of ParsedTestFile objects
        """
        self.logger.info(f"Parsing test directory: {test_dir}")

        parsed_files = []

        # Find all test files
        test_files = list(test_dir.glob("test_*.py")) + list(test_dir.glob("*_test.py"))

        for test_file in test_files:
            parsed = self.parse_test_file(test_file)
            parsed_files.append(parsed)

        self.logger.info(f"Parsed {len(parsed_files)} test files")

        return parsed_files

    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements."""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = ", ".join([alias.name for alias in node.names])
                imports.append(f"from {module} import {names}")

        return imports

    def _extract_required_modules(self, imports: List[str]) -> Set[str]:
        """Extract required module names from imports."""
        modules = set()

        for import_stmt in imports:
            if import_stmt.startswith("import "):
                # "import module" or "import module as alias"
                parts = import_stmt[7:].split()
                module = parts[0]
                modules.add(module)

            elif import_stmt.startswith("from "):
                # "from module import ..."
                parts = import_stmt[5:].split()
                module = parts[0]
                modules.add(module)

        return modules

    def _extract_fixtures(self, tree: ast.AST) -> List[TestFixture]:
        """Extract pytest fixtures."""
        fixtures = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue

            # Check if function has @pytest.fixture decorator
            has_fixture_decorator = False
            fixture_scope = "function"

            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id == "fixture":
                    has_fixture_decorator = True

                elif isinstance(decorator, ast.Attribute):
                    if decorator.attr == "fixture":
                        has_fixture_decorator = True

                elif isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Name) and decorator.func.id == "fixture":
                        has_fixture_decorator = True
                        # Extract scope
                        for keyword in decorator.keywords:
                            if keyword.arg == "scope":
                                if isinstance(keyword.value, ast.Constant):
                                    fixture_scope = keyword.value.value

                    elif isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "fixture":
                        has_fixture_decorator = True

            if has_fixture_decorator:
                fixture = TestFixture(
                    name=node.name,
                    scope=fixture_scope,
                )
                fixtures.append(fixture)

        return fixtures

    def _extract_test_functions(self, tree: ast.AST) -> List[TestFunction]:
        """Extract test functions."""
        test_functions = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue

            # Check if function name starts with "test_"
            if not node.name.startswith("test_"):
                continue

            # Extract test function details
            test_func = TestFunction(
                name=node.name,
                description=self._extract_docstring(node),
                line_number=node.lineno,
            )

            # Extract fixtures (function parameters)
            test_func.fixtures = [arg.arg for arg in node.args.args]

            # Extract assertions
            test_func.assertions = self._extract_assertions(node)

            # Extract mocks
            test_func.mocks = self._extract_mocks(node)

            test_functions.append(test_func)

        return test_functions

    def _extract_docstring(self, node: ast.FunctionDef) -> str:
        """Extract function docstring."""
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            return node.body[0].value.value
        return ""

    def _extract_assertions(self, node: ast.FunctionDef) -> List[TestAssertion]:
        """Extract assertions from test function."""
        assertions = []

        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Assert):
                assertion = self._parse_assertion(stmt)
                if assertion:
                    assertions.append(assertion)

        return assertions

    def _parse_assertion(self, assert_node: ast.Assert) -> Optional[TestAssertion]:
        """Parse a single assertion."""
        test = assert_node.test

        # assert something == expected
        if isinstance(test, ast.Compare):
            left = ast.unparse(test.left)

            if test.ops:
                op = test.ops[0]

                if isinstance(op, ast.Eq):
                    # assert x == y
                    right = ast.unparse(test.comparators[0])
                    return TestAssertion(
                        type="equal",
                        target=left,
                        expected=right,
                        line_number=assert_node.lineno,
                    )

                elif isinstance(op, ast.In):
                    # assert x in y
                    right = ast.unparse(test.comparators[0])
                    return TestAssertion(
                        type="in",
                        target=left,
                        expected=right,
                        line_number=assert_node.lineno,
                    )

                elif isinstance(op, ast.Is):
                    # assert x is y
                    right = ast.unparse(test.comparators[0])
                    return TestAssertion(
                        type="is",
                        target=left,
                        expected=right,
                        line_number=assert_node.lineno,
                    )

        # assert something (truthy check)
        else:
            target = ast.unparse(test)
            return TestAssertion(
                type="truthy",
                target=target,
                line_number=assert_node.lineno,
            )

        return None

    def _extract_mocks(self, node: ast.FunctionDef) -> List[str]:
        """Extract mocked objects from test function."""
        mocks = []

        for stmt in ast.walk(node):
            # Look for @patch decorators
            if isinstance(stmt, ast.FunctionDef):
                for decorator in stmt.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Name) and decorator.func.id == "patch":
                            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                                mocks.append(decorator.args[0].value)

            # Look for Mock() calls
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Name) and stmt.func.id == "Mock":
                    mocks.append("Mock()")
                elif isinstance(stmt.func, ast.Name) and stmt.func.id == "MagicMock":
                    mocks.append("MagicMock()")

        return mocks

    def extract_requirements_from_tests(
        self, parsed_files: List[ParsedTestFile]
    ) -> Dict[str, List[str]]:
        """
        Extract code requirements from test expectations.

        Args:
            parsed_files: List of parsed test files

        Returns:
            Dict mapping requirement type to list of requirements
        """
        requirements = {
            "functions": [],
            "classes": [],
            "methods": [],
            "attributes": [],
            "imports": [],
        }

        for parsed in parsed_files:
            # Extract required imports
            requirements["imports"].extend(parsed.imports)

            # Extract requirements from assertions
            for test_func in parsed.test_functions:
                for assertion in test_func.assertions:
                    # Infer what needs to exist from assertions
                    self._infer_requirements(assertion, requirements)

        # Deduplicate
        for key in requirements:
            requirements[key] = list(set(requirements[key]))

        return requirements

    def _infer_requirements(
        self, assertion: TestAssertion, requirements: Dict[str, List[str]]
    ):
        """Infer code requirements from an assertion."""
        target = assertion.target

        # Check for function calls
        if "(" in target and ")" in target:
            func_name = target.split("(")[0].strip()
            if "." in func_name:
                # Method call
                requirements["methods"].append(func_name)
            else:
                # Function call
                requirements["functions"].append(func_name)

        # Check for attribute access
        elif "." in target:
            requirements["attributes"].append(target)
