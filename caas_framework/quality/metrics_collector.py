"""
Auto Metrics Collector

Automatically extracts quality metrics from code artifacts.
Used by Quality Gate System to reduce manual metric collection.
"""

import ast
import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)


class AutoMetricsCollector:
    """
    Automatic Quality Metrics Collector

    Extracts metrics from code artifacts without manual intervention:
    - code_quality: AST-based code quality score
    - test_coverage: pytest-cov coverage percentage
    - security_score: Bandit security scan score
    - complexity_score: Radon cyclomatic complexity score
    """

    @staticmethod
    def extract_from_code(code_artifacts: Dict[str, str]) -> Dict[str, float]:
        """
        Extract all metrics from code artifacts.

        Args:
            code_artifacts: Dict mapping file paths to code content

        Returns:
            Dict of metric_name -> metric_value
        """
        metrics = {}

        try:
            # 1. Code Quality (AST-based)
            metrics["code_quality"] = AutoMetricsCollector._calculate_code_quality(
                code_artifacts
            )

            # 2. Test Coverage (pytest-cov simulation)
            metrics["test_coverage"] = AutoMetricsCollector._extract_test_coverage(
                code_artifacts
            )

            # 3. Security Score (Bandit simulation)
            metrics["security_score"] = AutoMetricsCollector._run_security_scan(
                code_artifacts
            )

            # 4. Complexity Score (Radon simulation)
            metrics["complexity_score"] = AutoMetricsCollector._calculate_complexity(
                code_artifacts
            )

            # 5. Implementation Completeness (required by DELIVERY quality gate)
            # Derived from code structure: functions/classes count and code_quality
            metrics["implementation_completeness"] = AutoMetricsCollector._calculate_implementation_completeness(
                code_artifacts, metrics.get("code_quality", 0.0)
            )

            logger.info(f"✅ Auto-extracted {len(metrics)} metrics from code")

        except Exception as e:
            logger.warning(f"⚠️ Failed to extract some metrics: {e}")

        return metrics

    @staticmethod
    def _calculate_code_quality(code_artifacts: Dict[str, str]) -> float:
        """
        Calculate code quality score (0-10) based on AST analysis.

        Factors:
        - Function/class documentation coverage
        - Type hints coverage
        - Import organization
        - Naming conventions
        - File structure

        Returns:
            Quality score (0.0-10.0)
        """
        if not code_artifacts:
            return 0.0

        total_score = 0.0
        file_count = 0

        for file_path, code_content in code_artifacts.items():
            # Skip non-Python files
            if not file_path.endswith(".py"):
                continue

            try:
                tree = ast.parse(code_content)
                file_score = AutoMetricsCollector._analyze_ast_quality(tree, code_content)
                total_score += file_score
                file_count += 1
            except SyntaxError:
                # Invalid Python syntax
                logger.warning(f"⚠️ Syntax error in {file_path}")
                total_score += 3.0  # Penalty for syntax errors
                file_count += 1

        if file_count == 0:
            return 7.0  # Default score if no Python files

        avg_score = total_score / file_count
        return round(avg_score, 1)

    @staticmethod
    def _analyze_ast_quality(tree: ast.AST, code_content: str) -> float:
        """
        Analyze AST tree for quality metrics.

        Returns:
            Quality score (0.0-10.0) for this file
        """
        score = 10.0  # Start with perfect score

        # 1. Count functions and classes
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        # 2. Check docstring coverage
        documented_functions = sum(
            1 for func in functions
            if ast.get_docstring(func) is not None
        )
        documented_classes = sum(
            1 for cls in classes
            if ast.get_docstring(cls) is not None
        )

        total_definitions = len(functions) + len(classes)
        if total_definitions > 0:
            docstring_coverage = (documented_functions + documented_classes) / total_definitions
            if docstring_coverage < 0.5:
                score -= 1.5  # Penalty for low documentation
            elif docstring_coverage < 0.8:
                score -= 0.5

        # 3. Check type hints coverage
        typed_functions = sum(
            1 for func in functions
            if func.returns is not None or any(
                arg.annotation is not None for arg in func.args.args
            )
        )

        if len(functions) > 0:
            type_hints_coverage = typed_functions / len(functions)
            if type_hints_coverage < 0.3:
                score -= 1.0  # Penalty for low type hints
            elif type_hints_coverage < 0.6:
                score -= 0.5

        # 4. Check import organization (heuristic)
        lines = code_content.split("\n")
        import_lines = [
            i for i, line in enumerate(lines)
            if line.strip().startswith(("import ", "from "))
        ]

        if import_lines:
            # Imports should be at the top
            first_import = import_lines[0]
            if first_import > 10:  # Imports not at top
                score -= 0.5

        # 5. Check for overly complex functions (> 50 lines)
        for func in functions:
            func_lines = len(ast.unparse(func).split("\n"))
            if func_lines > 50:
                score -= 0.3  # Penalty per complex function

        # 6. Check naming conventions
        for func in functions:
            if not func.name.islower() or func.name.startswith("_") and not func.name.startswith("__"):
                # Good: lowercase with underscores
                pass
            elif func.name[0].isupper():
                # Bad: CamelCase for function
                score -= 0.1

        for cls in classes:
            if cls.name[0].isupper():
                # Good: PascalCase for class
                pass
            else:
                # Bad: lowercase for class
                score -= 0.1

        return max(0.0, min(10.0, score))

    @staticmethod
    def _extract_test_coverage(code_artifacts: Dict[str, str]) -> float:
        """
        Extract test coverage percentage (0-100).

        Heuristic:
        - Count test files vs source files
        - Check for test functions in test files

        Returns:
            Coverage percentage (0.0-100.0)
        """
        source_files = [
            path for path in code_artifacts.keys()
            if path.endswith(".py") and not path.startswith("test_")
        ]

        test_files = [
            path for path in code_artifacts.keys()
            if path.endswith(".py") and (path.startswith("test_") or "tests/" in path)
        ]

        if not source_files:
            return 100.0  # No source files, assume full coverage

        # Count test functions
        total_test_functions = 0
        for test_file in test_files:
            code = code_artifacts.get(test_file, "")
            try:
                tree = ast.parse(code)
                test_functions = [
                    node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
                ]
                total_test_functions += len(test_functions)
            except SyntaxError:
                pass

        # Heuristic: Estimate coverage based on test density
        # Assume each test function covers ~10% of a source file
        estimated_coverage = min(100.0, (total_test_functions / len(source_files)) * 10)

        return round(estimated_coverage, 1)

    @staticmethod
    def _run_security_scan(code_artifacts: Dict[str, str]) -> float:
        """
        Run security scan and return security score (0-10).

        Checks for common security issues:
        - SQL injection patterns
        - Command injection patterns
        - Hardcoded secrets
        - Unsafe deserialization

        Returns:
            Security score (0.0-10.0)
        """
        score = 10.0  # Start with perfect score

        # Security patterns (simplified Bandit checks)
        security_issues = {
            r"eval\(": "Use of eval() is dangerous",
            r"exec\(": "Use of exec() is dangerous",
            r"__import__\(": "Dynamic imports can be dangerous",
            r"pickle\.loads\(": "Pickle deserialization is unsafe",
            r"os\.system\(": "Command injection risk",
            r"subprocess\.call\(.+shell=True": "Shell injection risk",
            r"password\s*=\s*['\"][^'\"]+['\"]": "Hardcoded password",
            r"api_key\s*=\s*['\"][^'\"]+['\"]": "Hardcoded API key",
            r"secret\s*=\s*['\"][^'\"]+['\"]": "Hardcoded secret",
        }

        issue_count = 0
        for file_path, code_content in code_artifacts.items():
            if not file_path.endswith(".py"):
                continue

            for pattern, description in security_issues.items():
                matches = re.findall(pattern, code_content, re.IGNORECASE)
                if matches:
                    logger.warning(f"⚠️ Security issue in {file_path}: {description}")
                    issue_count += len(matches)

        # Penalty: -0.5 per issue, max -5.0
        penalty = min(5.0, issue_count * 0.5)
        score -= penalty

        return max(0.0, score)

    @staticmethod
    def _calculate_complexity(code_artifacts: Dict[str, str]) -> float:
        """
        Calculate complexity score (0-10) based on cyclomatic complexity.

        Simplified Radon-style complexity:
        - Low complexity: 1-5 (simple)
        - Medium complexity: 6-10 (moderate)
        - High complexity: 11-20 (complex)
        - Very high complexity: 21+ (very complex)

        Returns:
            Complexity score (0.0-10.0), where 10.0 = low complexity
        """
        if not code_artifacts:
            return 10.0

        total_complexity = 0
        function_count = 0

        for file_path, code_content in code_artifacts.items():
            if not file_path.endswith(".py"):
                continue

            try:
                tree = ast.parse(code_content)
                functions = [
                    node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef)
                ]

                for func in functions:
                    complexity = AutoMetricsCollector._calculate_function_complexity(func)
                    total_complexity += complexity
                    function_count += 1
            except SyntaxError:
                pass

        if function_count == 0:
            return 10.0  # No functions, assume low complexity

        avg_complexity = total_complexity / function_count

        # Convert complexity to score (inverse relationship)
        # Complexity 1-5 → Score 10
        # Complexity 6-10 → Score 8
        # Complexity 11-20 → Score 6
        # Complexity 21+ → Score 3
        if avg_complexity <= 5:
            score = 10.0
        elif avg_complexity <= 10:
            score = 8.0
        elif avg_complexity <= 20:
            score = 6.0
        else:
            score = 3.0

        return score

    @staticmethod
    def _calculate_implementation_completeness(
        code_artifacts: Dict[str, str], code_quality: float
    ) -> float:
        """
        Calculate implementation completeness score (0-10).

        Measures whether the generated code has sufficient implementation:
        - Presence of required CrewAI files (agents.py, tasks.py, main.py)
        - Function/class count indicates implementation depth
        - Weighted average with code_quality

        Returns:
            Completeness score (0.0-10.0)
        """
        if not code_artifacts:
            return 0.0

        # Required file presence check
        required_files = {"agents.py", "tasks.py", "main.py"}
        present_files = {f for f in code_artifacts if any(f.endswith(r) for r in required_files)}
        file_coverage = len(present_files) / len(required_files)

        # Count total functions and classes as implementation depth indicator
        total_functions = 0
        total_classes = 0
        for file_path, code_content in code_artifacts.items():
            if not file_path.endswith(".py"):
                continue
            try:
                tree = ast.parse(code_content)
                total_functions += sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
                total_classes += sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
            except SyntaxError:
                pass

        # Score based on implementation depth (more functions/classes = more complete)
        depth_score = min(10.0, (total_functions + total_classes * 2) / 3.0)

        # Weighted combination: file coverage (40%), depth (30%), code quality (30%)
        score = (file_coverage * 10.0 * 0.4) + (depth_score * 0.3) + (code_quality * 0.3)
        return min(10.0, max(0.0, score))

    @staticmethod
    def _calculate_function_complexity(func: ast.FunctionDef) -> int:
        """
        Calculate cyclomatic complexity for a function.

        Simplified calculation:
        - Start with 1
        - +1 for each if/elif/for/while/except/with
        - +1 for each boolean operator (and/or)

        Returns:
            Complexity score (integer)
        """
        complexity = 1  # Base complexity

        for node in ast.walk(func):
            # Control flow statements
            if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With)):
                complexity += 1

            # Boolean operators
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

            # Ternary expressions
            elif isinstance(node, ast.IfExp):
                complexity += 1

        return complexity


class MetricsFormatter:
    """
    Format metrics for display in Quality Gate reports.
    """

    @staticmethod
    def format_metrics(metrics: Dict[str, float]) -> str:
        """
        Format metrics as human-readable string.

        Returns:
            Formatted metrics string
        """
        lines = ["📊 Auto-Extracted Metrics:"]

        metric_names = {
            "code_quality": "Code Quality",
            "test_coverage": "Test Coverage",
            "security_score": "Security Score",
            "complexity_score": "Complexity Score",
        }

        for key, value in metrics.items():
            name = metric_names.get(key, key)

            if "coverage" in key:
                lines.append(f"  • {name}: {value:.1f}%")
            else:
                lines.append(f"  • {name}: {value:.1f}/10.0")

        return "\n".join(lines)
