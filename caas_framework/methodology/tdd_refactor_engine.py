"""
TDD REFACTOR Phase: Code Review & Refactoring Engine (CAAS-E Week 3)

Analyzes generated code and suggests refactorings following TDD REFACTOR principles.
Detects code smells, performance issues, and best practice violations.

Author: CAAS Framework Team
Version: 0.6.0 (CAAS-E Implementation)
"""

import ast
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SmellSeverity(Enum):
    """Severity levels for code smells"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RefactoringType(Enum):
    """Types of refactorings"""
    EXTRACT_METHOD = "extract_method"
    EXTRACT_VARIABLE = "extract_variable"
    PARAMETER_OBJECT = "parameter_object"
    SIMPLIFY_CONDITIONAL = "simplify_conditional"
    REMOVE_DUPLICATION = "remove_duplication"
    INTRODUCE_CONSTANT = "introduce_constant"
    ADD_TYPE_HINTS = "add_type_hints"
    ADD_DOCSTRING = "add_docstring"
    RENAME = "rename"
    OPTIMIZE_PERFORMANCE = "optimize_performance"


@dataclass
class CodeSmell:
    """Detected code smell"""
    smell_type: str
    severity: SmellSeverity
    location: str  # file:line or function_name
    description: str
    code_snippet: Optional[str] = None
    suggested_fix: Optional[str] = None


@dataclass
class RefactoringSuggestion:
    """Refactoring suggestion with reasoning"""
    refactoring_type: RefactoringType
    target: str  # What to refactor (function name, variable, etc.)
    reason: str
    before_code: str
    after_code: str
    impact: str  # Expected impact (readability, performance, maintainability)
    effort: str  # low, medium, high


@dataclass
class PerformanceIssue:
    """Performance bottleneck or inefficiency"""
    issue_type: str
    location: str
    description: str
    current_complexity: str  # e.g., "O(n²)"
    suggested_complexity: str  # e.g., "O(n)"
    optimization: str


@dataclass
class RefactorReport:
    """Complete refactoring analysis report"""
    file_path: str
    code_smells: List[CodeSmell] = field(default_factory=list)
    refactoring_suggestions: List[RefactoringSuggestion] = field(default_factory=list)
    performance_issues: List[PerformanceIssue] = field(default_factory=list)
    code_quality_score: float = 0.0  # 0-10
    best_practices_score: float = 0.0  # 0-10
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "file_path": self.file_path,
            "code_smells": [
                {
                    "type": s.smell_type,
                    "severity": s.severity.value,
                    "location": s.location,
                    "description": s.description,
                    "suggested_fix": s.suggested_fix
                }
                for s in self.code_smells
            ],
            "refactoring_suggestions": [
                {
                    "type": r.refactoring_type.value,
                    "target": r.target,
                    "reason": r.reason,
                    "impact": r.impact,
                    "effort": r.effort
                }
                for r in self.refactoring_suggestions
            ],
            "performance_issues": [
                {
                    "type": p.issue_type,
                    "location": p.location,
                    "description": p.description,
                    "optimization": p.optimization
                }
                for p in self.performance_issues
            ],
            "code_quality_score": self.code_quality_score,
            "best_practices_score": self.best_practices_score,
            "summary": self.summary
        }


class CodeSmellDetector:
    """
    Detects code smells using AST analysis

    Detects:
    - Long functions (>50 lines)
    - Too many parameters (>5)
    - Deeply nested conditionals (>3 levels)
    - Magic numbers
    - Duplicated code patterns
    """

    @staticmethod
    def detect_smells(code: str, file_path: str = "<code>") -> List[CodeSmell]:
        """Detect all code smells in code"""
        smells = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            smells.append(CodeSmell(
                smell_type="syntax_error",
                severity=SmellSeverity.CRITICAL,
                location=f"{file_path}:{e.lineno}",
                description=f"Syntax error: {e.msg}",
                suggested_fix="Fix syntax error before refactoring"
            ))
            return smells

        # Detect long functions
        smells.extend(CodeSmellDetector._detect_long_functions(tree, file_path))

        # Detect too many parameters
        smells.extend(CodeSmellDetector._detect_too_many_parameters(tree, file_path))

        # Detect deep nesting
        smells.extend(CodeSmellDetector._detect_deep_nesting(tree, file_path))

        # Detect magic numbers
        smells.extend(CodeSmellDetector._detect_magic_numbers(tree, file_path))

        # Detect missing docstrings
        smells.extend(CodeSmellDetector._detect_missing_docstrings(tree, file_path))

        return smells

    @staticmethod
    def _detect_long_functions(tree: ast.AST, file_path: str) -> List[CodeSmell]:
        """Detect functions longer than 50 lines"""
        smells = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Calculate function length
                if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                    func_length = node.end_lineno - node.lineno + 1

                    if func_length > 50:
                        severity = SmellSeverity.HIGH if func_length > 100 else SmellSeverity.MEDIUM

                        smells.append(CodeSmell(
                            smell_type="long_function",
                            severity=severity,
                            location=f"{file_path}:{node.lineno}",
                            description=f"Function '{node.name}' is {func_length} lines long (max: 50)",
                            suggested_fix="Consider breaking into smaller functions using Extract Method refactoring"
                        ))

        return smells

    @staticmethod
    def _detect_too_many_parameters(tree: ast.AST, file_path: str) -> List[CodeSmell]:
        """Detect functions with more than 5 parameters"""
        smells = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                param_count = len(node.args.args)

                if param_count > 5:
                    smells.append(CodeSmell(
                        smell_type="too_many_parameters",
                        severity=SmellSeverity.MEDIUM,
                        location=f"{file_path}:{node.lineno}",
                        description=f"Function '{node.name}' has {param_count} parameters (max: 5)",
                        suggested_fix="Consider using a parameter object or builder pattern"
                    ))

        return smells

    @staticmethod
    def _detect_deep_nesting(tree: ast.AST, file_path: str) -> List[CodeSmell]:
        """Detect deeply nested conditionals (>3 levels)"""
        smells = []

        class NestingVisitor(ast.NodeVisitor):
            def __init__(self):
                self.max_nesting = 0
                self.current_nesting = 0
                self.current_function = None

            def visit_FunctionDef(self, node):
                self.current_function = node.name
                self.max_nesting = 0
                self.current_nesting = 0
                self.generic_visit(node)

                if self.max_nesting > 3:
                    smells.append(CodeSmell(
                        smell_type="deep_nesting",
                        severity=SmellSeverity.MEDIUM,
                        location=f"{file_path}:{node.lineno}",
                        description=f"Function '{node.name}' has nesting level {self.max_nesting} (max: 3)",
                        suggested_fix="Consider early returns or extracting nested logic to separate functions"
                    ))

            def visit_If(self, node):
                self.current_nesting += 1
                self.max_nesting = max(self.max_nesting, self.current_nesting)
                self.generic_visit(node)
                self.current_nesting -= 1

            def visit_For(self, node):
                self.current_nesting += 1
                self.max_nesting = max(self.max_nesting, self.current_nesting)
                self.generic_visit(node)
                self.current_nesting -= 1

            def visit_While(self, node):
                self.current_nesting += 1
                self.max_nesting = max(self.max_nesting, self.current_nesting)
                self.generic_visit(node)
                self.current_nesting -= 1

        visitor = NestingVisitor()
        visitor.visit(tree)

        return smells

    @staticmethod
    def _detect_magic_numbers(tree: ast.AST, file_path: str) -> List[CodeSmell]:
        """Detect magic numbers (literal numbers in expressions)"""
        smells = []
        magic_numbers_found = []

        class MagicNumberVisitor(ast.NodeVisitor):
            def visit_Num(self, node):
                # Deprecated but still works for older code
                # Ignore common constants (0, 1, 2, -1, 100)
                if node.n not in (0, 1, 2, -1, 100):
                    magic_numbers_found.append((node.lineno, node.n))

            def visit_Constant(self, node):
                # Modern AST: handle numeric constants
                if isinstance(node.value, (int, float)):
                    # Ignore common constants (0, 1, 2, -1, 100)
                    if node.value not in (0, 1, 2, -1, 100):
                        magic_numbers_found.append((node.lineno, node.value))

        visitor = MagicNumberVisitor()
        visitor.visit(tree)

        # Group by line to avoid duplicates
        seen_lines = set()
        for lineno, num in magic_numbers_found:
            if lineno not in seen_lines:
                seen_lines.add(lineno)
                smells.append(CodeSmell(
                    smell_type="magic_number",
                    severity=SmellSeverity.LOW,
                    location=f"{file_path}:{lineno}",
                    description=f"Magic number '{num}' found",
                    suggested_fix="Consider using a named constant"
                ))

        return smells

    @staticmethod
    def _detect_missing_docstrings(tree: ast.AST, file_path: str) -> List[CodeSmell]:
        """Detect functions/classes without docstrings"""
        smells = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Check if has docstring
                has_docstring = (
                    ast.get_docstring(node) is not None
                )

                if not has_docstring:
                    node_type = "Function" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "Class"

                    smells.append(CodeSmell(
                        smell_type="missing_docstring",
                        severity=SmellSeverity.LOW,
                        location=f"{file_path}:{node.lineno}",
                        description=f"{node_type} '{node.name}' missing docstring",
                        suggested_fix="Add docstring describing purpose, parameters, and return value"
                    ))

        return smells


class RefactoringEngine:
    """
    Generates refactoring suggestions

    Suggests:
    - Extract Method for long functions
    - Extract Variable for complex expressions
    - Simplify Conditional for nested if/else
    - Introduce Constant for magic numbers
    """

    @staticmethod
    def generate_suggestions(
        code: str,
        code_smells: List[CodeSmell],
        file_path: str = "<code>"
    ) -> List[RefactoringSuggestion]:
        """Generate refactoring suggestions based on code smells"""
        suggestions = []

        # Map smells to refactorings
        smell_to_refactoring = {
            "long_function": RefactoringEngine._suggest_extract_method,
            "too_many_parameters": RefactoringEngine._suggest_parameter_object,
            "deep_nesting": RefactoringEngine._suggest_simplify_conditional,
            "magic_number": RefactoringEngine._suggest_introduce_constant,
            "missing_docstring": RefactoringEngine._suggest_add_docstring,
        }

        for smell in code_smells:
            if smell.smell_type in smell_to_refactoring:
                suggestion = smell_to_refactoring[smell.smell_type](smell, code)
                if suggestion:
                    suggestions.append(suggestion)

        return suggestions

    @staticmethod
    def _suggest_extract_method(smell: CodeSmell, code: str) -> Optional[RefactoringSuggestion]:
        """Suggest Extract Method refactoring for long functions"""
        # Extract function name from location
        func_name_match = re.search(r"'(\w+)'", smell.description)
        if not func_name_match:
            return None

        func_name = func_name_match.group(1)

        return RefactoringSuggestion(
            refactoring_type=RefactoringType.EXTRACT_METHOD,
            target=func_name,
            reason=f"Function is too long ({smell.description})",
            before_code=f"def {func_name}(...):\n    # Long function body (50+ lines)\n    pass",
            after_code=f"def {func_name}(...):\n    # Call extracted methods\n    self._validate_input()\n    result = self._process_data()\n    return self._format_result(result)",
            impact="Improved readability and testability",
            effort="medium"
        )

    @staticmethod
    def _suggest_parameter_object(smell: CodeSmell, code: str) -> Optional[RefactoringSuggestion]:
        """Suggest Parameter Object pattern for functions with many parameters"""
        func_name_match = re.search(r"'(\w+)'", smell.description)
        if not func_name_match:
            return None

        func_name = func_name_match.group(1)

        return RefactoringSuggestion(
            refactoring_type=RefactoringType.PARAMETER_OBJECT,
            target=func_name,
            reason=f"Too many parameters ({smell.description})",
            before_code=f"def {func_name}(param1, param2, param3, param4, param5, param6):\n    pass",
            after_code=f"@dataclass\nclass {func_name.title()}Params:\n    param1: str\n    param2: int\n    # ...\n\ndef {func_name}(params: {func_name.title()}Params):\n    pass",
            impact="Improved maintainability and extensibility",
            effort="medium"
        )

    @staticmethod
    def _suggest_simplify_conditional(smell: CodeSmell, code: str) -> Optional[RefactoringSuggestion]:
        """Suggest simplifying deeply nested conditionals"""
        func_name_match = re.search(r"'(\w+)'", smell.description)
        if not func_name_match:
            return None

        func_name = func_name_match.group(1)

        return RefactoringSuggestion(
            refactoring_type=RefactoringType.SIMPLIFY_CONDITIONAL,
            target=func_name,
            reason=f"Deep nesting ({smell.description})",
            before_code=f"def {func_name}(...):\n    if condition1:\n        if condition2:\n            if condition3:\n                # Deeply nested logic",
            after_code=f"def {func_name}(...):\n    if not condition1:\n        return early_exit\n    if not condition2:\n        return early_exit\n    # Flattened logic",
            impact="Improved readability and reduced cognitive complexity",
            effort="low"
        )

    @staticmethod
    def _suggest_introduce_constant(smell: CodeSmell, code: str) -> Optional[RefactoringSuggestion]:
        """Suggest introducing named constant for magic number"""
        number_match = re.search(r"'([\d.]+)'", smell.description)
        if not number_match:
            return None

        magic_num = number_match.group(1)

        return RefactoringSuggestion(
            refactoring_type=RefactoringType.INTRODUCE_CONSTANT,
            target=f"magic_number_{magic_num}",
            reason=f"Magic number found ({smell.description})",
            before_code=f"result = value * {magic_num}",
            after_code=f"# At module level\nCONVERSION_FACTOR = {magic_num}\n\n# In function\nresult = value * CONVERSION_FACTOR",
            impact="Improved code documentation and maintainability",
            effort="low"
        )

    @staticmethod
    def _suggest_add_docstring(smell: CodeSmell, code: str) -> Optional[RefactoringSuggestion]:
        """Suggest adding docstring"""
        target_match = re.search(r"(?:Function|Class) '(\w+)'", smell.description)
        if not target_match:
            return None

        target_name = target_match.group(1)

        return RefactoringSuggestion(
            refactoring_type=RefactoringType.ADD_DOCSTRING,
            target=target_name,
            reason="Missing docstring",
            before_code=f"def {target_name}(param1, param2):\n    return param1 + param2",
            after_code=f'def {target_name}(param1, param2):\n    """\n    Add two values together.\n\n    Args:\n        param1: First value\n        param2: Second value\n\n    Returns:\n        Sum of param1 and param2\n    """\n    return param1 + param2',
            impact="Improved code documentation",
            effort="low"
        )


class PerformanceAnalyzer:
    """
    Analyzes code for performance issues

    Detects:
    - Nested loops (O(n²) complexity)
    - String concatenation in loops
    - Missing list comprehensions
    - Inefficient data structures
    """

    @staticmethod
    def analyze_performance(code: str, file_path: str = "<code>") -> List[PerformanceIssue]:
        """Analyze code for performance issues"""
        issues = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return issues

        # Detect nested loops
        issues.extend(PerformanceAnalyzer._detect_nested_loops(tree, file_path))

        # Detect string concatenation in loops
        issues.extend(PerformanceAnalyzer._detect_string_concat_in_loops(tree, file_path))

        return issues

    @staticmethod
    def _detect_nested_loops(tree: ast.AST, file_path: str) -> List[PerformanceIssue]:
        """Detect nested loops that may cause O(n²) complexity"""
        issues = []

        class LoopVisitor(ast.NodeVisitor):
            def __init__(self):
                self.loop_depth = 0
                self.current_function = None

            def visit_FunctionDef(self, node):
                self.current_function = node.name
                self.loop_depth = 0
                self.generic_visit(node)

            def visit_For(self, node):
                self.loop_depth += 1
                if self.loop_depth >= 2:
                    issues.append(PerformanceIssue(
                        issue_type="nested_loops",
                        location=f"{file_path}:{node.lineno}",
                        description=f"Nested loop (depth: {self.loop_depth}) may cause O(n²) or worse complexity",
                        current_complexity="O(n²) or worse",
                        suggested_complexity="O(n) or O(n log n)",
                        optimization="Consider using hash maps, sets, or optimized algorithms"
                    ))
                self.generic_visit(node)
                self.loop_depth -= 1

        visitor = LoopVisitor()
        visitor.visit(tree)

        return issues

    @staticmethod
    def _detect_string_concat_in_loops(tree: ast.AST, file_path: str) -> List[PerformanceIssue]:
        """Detect string concatenation in loops (inefficient)"""
        issues = []

        class StringConcatVisitor(ast.NodeVisitor):
            def __init__(self):
                self.in_loop = False

            def visit_For(self, node):
                self.in_loop = True
                self.generic_visit(node)
                self.in_loop = False

            def visit_AugAssign(self, node):
                if self.in_loop and isinstance(node.op, ast.Add):
                    # Check if left side is likely a string
                    if isinstance(node.target, ast.Name):
                        issues.append(PerformanceIssue(
                            issue_type="string_concat_in_loop",
                            location=f"{file_path}:{node.lineno}",
                            description="String concatenation in loop (creates new string each iteration)",
                            current_complexity="O(n²) for string building",
                            suggested_complexity="O(n)",
                            optimization="Use list append + ''.join() or io.StringIO"
                        ))

        visitor = StringConcatVisitor()
        visitor.visit(tree)

        return issues


class TDDRefactorEngine:
    """
    TDD REFACTOR Phase Engine

    Orchestrates code analysis and refactoring suggestion generation:
    1. Detect code smells
    2. Generate refactoring suggestions
    3. Analyze performance
    4. Calculate quality scores
    5. Generate comprehensive report
    """

    def __init__(self):
        self.smell_detector = CodeSmellDetector()
        self.refactoring_engine = RefactoringEngine()
        self.performance_analyzer = PerformanceAnalyzer()
        self.logger = logging.getLogger(self.__class__.__name__)

    def analyze_code(self, code: str, file_path: str = "<code>") -> RefactorReport:
        """
        Analyze code and generate refactoring report

        Args:
            code: Python source code to analyze
            file_path: Path to the file (for reporting)

        Returns:
            RefactorReport with all findings and suggestions
        """
        self.logger.info(f"Analyzing {file_path}...")

        # Step 1: Detect code smells
        code_smells = self.smell_detector.detect_smells(code, file_path)
        self.logger.info(f"Found {len(code_smells)} code smells")

        # Step 2: Generate refactoring suggestions
        refactoring_suggestions = self.refactoring_engine.generate_suggestions(
            code, code_smells, file_path
        )
        self.logger.info(f"Generated {len(refactoring_suggestions)} refactoring suggestions")

        # Step 3: Analyze performance
        performance_issues = self.performance_analyzer.analyze_performance(code, file_path)
        self.logger.info(f"Found {len(performance_issues)} performance issues")

        # Step 4: Calculate quality scores
        code_quality_score = self._calculate_code_quality_score(code, code_smells)
        best_practices_score = self._calculate_best_practices_score(code, code_smells)

        # Step 5: Generate summary
        summary = self._generate_summary(code_smells, refactoring_suggestions, performance_issues)

        report = RefactorReport(
            file_path=file_path,
            code_smells=code_smells,
            refactoring_suggestions=refactoring_suggestions,
            performance_issues=performance_issues,
            code_quality_score=code_quality_score,
            best_practices_score=best_practices_score,
            summary=summary
        )

        self.logger.info(
            f"Analysis complete: Quality={code_quality_score:.1f}/10.0, "
            f"Best Practices={best_practices_score:.1f}/10.0"
        )

        return report

    def _calculate_code_quality_score(self, code: str, smells: List[CodeSmell]) -> float:
        """Calculate code quality score (0-10)"""
        # Start with perfect score
        score = 10.0

        # Deduct points based on smell severity
        severity_penalties = {
            SmellSeverity.LOW: 0.1,
            SmellSeverity.MEDIUM: 0.3,
            SmellSeverity.HIGH: 0.7,
            SmellSeverity.CRITICAL: 2.0
        }

        for smell in smells:
            score -= severity_penalties.get(smell.severity, 0.5)

        return max(0.0, score)

    def _calculate_best_practices_score(self, code: str, smells: List[CodeSmell]) -> float:
        """Calculate best practices adherence score (0-10)"""
        score = 10.0

        # Count specific smell types related to best practices
        docstring_smells = [s for s in smells if s.smell_type == "missing_docstring"]
        magic_number_smells = [s for s in smells if s.smell_type == "magic_number"]

        # Deduct for missing docstrings
        score -= len(docstring_smells) * 0.5

        # Deduct for magic numbers
        score -= len(magic_number_smells) * 0.2

        return max(0.0, score)

    def _generate_summary(
        self,
        smells: List[CodeSmell],
        suggestions: List[RefactoringSuggestion],
        perf_issues: List[PerformanceIssue]
    ) -> str:
        """Generate human-readable summary"""
        total_issues = len(smells) + len(perf_issues)

        if total_issues == 0:
            return "✅ Code quality excellent! No issues found."

        summary_parts = [
            f"Found {total_issues} total issues:",
            f"  - {len(smells)} code smells",
            f"  - {len(perf_issues)} performance issues",
            f"\n{len(suggestions)} refactoring suggestions generated."
        ]

        # Highlight critical issues
        critical_smells = [s for s in smells if s.severity == SmellSeverity.CRITICAL]
        if critical_smells:
            summary_parts.append(f"\n⚠️ {len(critical_smells)} CRITICAL issues require immediate attention!")

        return "\n".join(summary_parts)
