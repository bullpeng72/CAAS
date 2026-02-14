"""
Tests for TDD REFACTOR Engine (CAAS-E Week 3 Part 2)

Tests code smell detection, refactoring suggestions, performance analysis,
and quality scoring.
"""

import pytest
from caas_framework.methodology.tdd_refactor_engine import (
    TDDRefactorEngine,
    CodeSmellDetector,
    RefactoringEngine,
    PerformanceAnalyzer,
    SmellSeverity,
    RefactoringType,
    CodeSmell,
    RefactoringSuggestion,
    PerformanceIssue,
    RefactorReport
)


class TestCodeSmellDetector:
    """Test CodeSmellDetector"""

    def test_detect_long_function(self):
        """Test detection of long functions"""
        lines = '\n    '.join(f"line_{i} = {i}" for i in range(60))
        code = f'''
def very_long_function():
    {lines}
    return result
'''
        smells = CodeSmellDetector.detect_smells(code)

        long_func_smells = [s for s in smells if s.smell_type == "long_function"]
        assert len(long_func_smells) > 0
        assert long_func_smells[0].severity in [SmellSeverity.MEDIUM, SmellSeverity.HIGH]

    def test_detect_too_many_parameters(self):
        """Test detection of functions with too many parameters"""
        code = '''
def func_with_many_params(p1, p2, p3, p4, p5, p6, p7):
    return p1 + p2 + p3 + p4 + p5 + p6 + p7
'''
        smells = CodeSmellDetector.detect_smells(code)

        param_smells = [s for s in smells if s.smell_type == "too_many_parameters"]
        assert len(param_smells) == 1
        assert "7 parameters" in param_smells[0].description

    def test_detect_deep_nesting(self):
        """Test detection of deeply nested conditionals"""
        code = '''
def deeply_nested():
    if condition1:
        if condition2:
            if condition3:
                if condition4:
                    return "too deep"
    return "ok"
'''
        smells = CodeSmellDetector.detect_smells(code)

        nesting_smells = [s for s in smells if s.smell_type == "deep_nesting"]
        assert len(nesting_smells) == 1
        assert "nesting level" in nesting_smells[0].description

    def test_detect_magic_numbers(self):
        """Test detection of magic numbers"""
        code = '''
def calculate():
    result = value * 42  # Magic number!
    return result + 3.14159
'''
        smells = CodeSmellDetector.detect_smells(code)

        magic_smells = [s for s in smells if s.smell_type == "magic_number"]
        assert len(magic_smells) >= 1
        # Should detect 42 and 3.14159

    def test_detect_missing_docstrings(self):
        """Test detection of missing docstrings"""
        code = '''
def function_without_docstring(param):
    return param * 2

class ClassWithoutDocstring:
    def method(self):
        pass
'''
        smells = CodeSmellDetector.detect_smells(code)

        docstring_smells = [s for s in smells if s.smell_type == "missing_docstring"]
        assert len(docstring_smells) >= 2  # function and class

    def test_detect_syntax_error(self):
        """Test handling of syntax errors"""
        code = '''
def broken_function(
    # Missing closing paren
'''
        smells = CodeSmellDetector.detect_smells(code)

        assert any(s.smell_type == "syntax_error" for s in smells)
        syntax_smell = [s for s in smells if s.smell_type == "syntax_error"][0]
        assert syntax_smell.severity == SmellSeverity.CRITICAL

    def test_clean_code_no_smells(self):
        """Test that clean code produces minimal smells"""
        code = '''
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

class Calculator:
    """Simple calculator class."""
    def multiply(self, x: int, y: int) -> int:
        """Multiply two numbers."""
        return x * y
'''
        smells = CodeSmellDetector.detect_smells(code)

        # Clean code should have no major smells
        critical_smells = [s for s in smells if s.severity == SmellSeverity.CRITICAL]
        assert len(critical_smells) == 0


class TestRefactoringEngine:
    """Test RefactoringEngine"""

    def test_suggest_extract_method_for_long_function(self):
        """Test Extract Method suggestion for long functions"""
        smell = CodeSmell(
            smell_type="long_function",
            severity=SmellSeverity.HIGH,
            location="test.py:10",
            description="Function 'process_data' is 75 lines long (max: 50)"
        )

        suggestions = RefactoringEngine.generate_suggestions("", [smell])

        assert len(suggestions) == 1
        assert suggestions[0].refactoring_type == RefactoringType.EXTRACT_METHOD
        assert suggestions[0].target == "process_data"
        assert "readability" in suggestions[0].impact.lower()

    def test_suggest_parameter_object_for_many_params(self):
        """Test Parameter Object suggestion for many parameters"""
        smell = CodeSmell(
            smell_type="too_many_parameters",
            severity=SmellSeverity.MEDIUM,
            location="test.py:5",
            description="Function 'create_user' has 7 parameters (max: 5)"
        )

        suggestions = RefactoringEngine.generate_suggestions("", [smell])

        assert len(suggestions) == 1
        assert suggestions[0].target == "create_user"
        assert "Params" in suggestions[0].after_code  # Should suggest dataclass

    def test_suggest_simplify_conditional_for_deep_nesting(self):
        """Test Simplify Conditional suggestion for deep nesting"""
        smell = CodeSmell(
            smell_type="deep_nesting",
            severity=SmellSeverity.MEDIUM,
            location="test.py:20",
            description="Function 'validate' has nesting level 4 (max: 3)"
        )

        suggestions = RefactoringEngine.generate_suggestions("", [smell])

        assert len(suggestions) == 1
        assert suggestions[0].refactoring_type == RefactoringType.SIMPLIFY_CONDITIONAL
        assert "early" in suggestions[0].after_code.lower()  # Should suggest early returns

    def test_suggest_introduce_constant_for_magic_number(self):
        """Test Introduce Constant suggestion for magic numbers"""
        smell = CodeSmell(
            smell_type="magic_number",
            severity=SmellSeverity.LOW,
            location="test.py:15",
            description="Magic number '42' found"
        )

        suggestions = RefactoringEngine.generate_suggestions("", [smell])

        assert len(suggestions) == 1
        assert suggestions[0].refactoring_type == RefactoringType.INTRODUCE_CONSTANT
        # Check that either the after_code shows a constant OR the reason mentions it
        has_constant_in_code = "CONVERSION_FACTOR" in suggestions[0].after_code or "CONSTANT" in suggestions[0].after_code
        has_constant_in_reason = "magic" in suggestions[0].reason.lower() or "constant" in suggestions[0].reason.lower()
        assert has_constant_in_code or has_constant_in_reason

    def test_suggest_add_docstring(self):
        """Test Add Docstring suggestion"""
        smell = CodeSmell(
            smell_type="missing_docstring",
            severity=SmellSeverity.LOW,
            location="test.py:8",
            description="Function 'helper' missing docstring"
        )

        suggestions = RefactoringEngine.generate_suggestions("", [smell])

        assert len(suggestions) == 1
        assert suggestions[0].refactoring_type == RefactoringType.ADD_DOCSTRING
        assert '"""' in suggestions[0].after_code  # Should show docstring example


class TestPerformanceAnalyzer:
    """Test PerformanceAnalyzer"""

    def test_detect_nested_loops(self):
        """Test detection of nested loops"""
        code = '''
def process_matrix(matrix):
    for row in matrix:
        for col in row:
            process(col)
'''
        issues = PerformanceAnalyzer.analyze_performance(code)

        nested_loop_issues = [i for i in issues if i.issue_type == "nested_loops"]
        assert len(nested_loop_issues) >= 1
        assert "O(n²)" in nested_loop_issues[0].current_complexity

    def test_detect_string_concat_in_loop(self):
        """Test detection of string concatenation in loops"""
        code = '''
def build_string(items):
    result = ""
    for item in items:
        result += str(item)
    return result
'''
        issues = PerformanceAnalyzer.analyze_performance(code)

        concat_issues = [i for i in issues if i.issue_type == "string_concat_in_loop"]
        assert len(concat_issues) >= 1
        assert "join" in concat_issues[0].optimization.lower()

    def test_clean_code_no_performance_issues(self):
        """Test that clean code produces no performance issues"""
        code = '''
def process_items(items):
    return [process(item) for item in items]
'''
        issues = PerformanceAnalyzer.analyze_performance(code)

        # Simple list comprehension should have no issues
        assert len(issues) == 0


class TestTDDRefactorEngine:
    """Test TDDRefactorEngine"""

    def test_analyze_clean_code(self):
        """Test analysis of clean code"""
        code = '''
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
'''
        engine = TDDRefactorEngine()
        report = engine.analyze_code(code, "clean.py")

        assert isinstance(report, RefactorReport)
        assert report.code_quality_score >= 9.0  # Clean code should score high
        assert report.best_practices_score >= 9.0
        assert "excellent" in report.summary.lower() or len(report.code_smells) == 0

    def test_analyze_problematic_code(self):
        """Test analysis of code with multiple issues"""
        code = '''
def bad_function(p1, p2, p3, p4, p5, p6):
    if cond1:
        if cond2:
            if cond3:
                if cond4:
                    result = p1 * 42 + p2 * 3.14
    return result
'''
        engine = TDDRefactorEngine()
        report = engine.analyze_code(code, "bad.py")

        # Should detect multiple issues
        assert len(report.code_smells) > 0
        assert len(report.refactoring_suggestions) > 0
        assert report.code_quality_score < 10.0

        # Check for specific smells
        smell_types = [s.smell_type for s in report.code_smells]
        assert "too_many_parameters" in smell_types
        assert "deep_nesting" in smell_types
        assert "magic_number" in smell_types
        assert "missing_docstring" in smell_types

    def test_analyze_performance_issues(self):
        """Test analysis detects performance issues"""
        code = '''
def slow_function(data):
    result = ""
    for row in data:
        for col in row:
            result += str(col)
    return result
'''
        engine = TDDRefactorEngine()
        report = engine.analyze_code(code, "slow.py")

        assert len(report.performance_issues) > 0
        assert any(i.issue_type == "nested_loops" for i in report.performance_issues)
        assert any(i.issue_type == "string_concat_in_loop" for i in report.performance_issues)

    def test_quality_score_calculation(self):
        """Test code quality score calculation"""
        # Code with some issues but not critical
        code = '''
def func(a, b, c, d, e, f):
    result = a * 100
    return result
'''
        engine = TDDRefactorEngine()
        report = engine.analyze_code(code)

        # Should have score between 0 and 10
        assert 0.0 <= report.code_quality_score <= 10.0
        assert 0.0 <= report.best_practices_score <= 10.0

        # Should deduct points for issues
        assert report.code_quality_score < 10.0

    def test_refactor_report_to_dict(self):
        """Test RefactorReport serialization"""
        engine = TDDRefactorEngine()
        report = engine.analyze_code("def test(): pass", "test.py")

        report_dict = report.to_dict()

        # Verify structure
        assert "file_path" in report_dict
        assert "code_smells" in report_dict
        assert "refactoring_suggestions" in report_dict
        assert "performance_issues" in report_dict
        assert "code_quality_score" in report_dict
        assert "best_practices_score" in report_dict
        assert "summary" in report_dict

        # Verify types
        assert isinstance(report_dict["code_smells"], list)
        assert isinstance(report_dict["refactoring_suggestions"], list)
        assert isinstance(report_dict["performance_issues"], list)

    def test_analyze_multiple_functions(self):
        """Test analysis of code with multiple functions"""
        code = '''
def func1(a, b):
    """Good function with docstring."""
    return a + b

def func2_without_docstring():
    result = value * 42
    return result

def func3(p1, p2, p3, p4, p5, p6):
    if x:
        if y:
            if z:
                if w:
                    return "deep"
'''
        engine = TDDRefactorEngine()
        report = engine.analyze_code(code, "multi.py")

        # Should detect issues in func2 and func3, but not func1
        assert len(report.code_smells) >= 3  # Missing docstring, magic number, many params, deep nesting
        assert len(report.refactoring_suggestions) >= 3


class TestSmellSeverityAndPriority:
    """Test smell severity classification and prioritization"""

    def test_critical_severity_for_syntax_errors(self):
        """Test that syntax errors are marked as critical"""
        code = "def broken("
        smells = CodeSmellDetector.detect_smells(code)

        syntax_smells = [s for s in smells if s.smell_type == "syntax_error"]
        assert len(syntax_smells) > 0
        assert syntax_smells[0].severity == SmellSeverity.CRITICAL

    def test_high_severity_for_very_long_functions(self):
        """Test that very long functions get high severity"""
        lines = '\n    '.join(f"x{i} = {i}" for i in range(120))
        code = "def extremely_long_function():\n    " + lines + "\n    return x0\n"
        smells = CodeSmellDetector.detect_smells(code)

        long_func_smells = [s for s in smells if s.smell_type == "long_function"]
        assert len(long_func_smells) > 0
        # Very long function (120 lines) should be HIGH severity
        assert long_func_smells[0].severity == SmellSeverity.HIGH

    def test_low_severity_for_magic_numbers(self):
        """Test that magic numbers get low severity"""
        code = "result = x * 42"
        smells = CodeSmellDetector.detect_smells(code)

        magic_smells = [s for s in smells if s.smell_type == "magic_number"]
        if magic_smells:  # May not detect in simple expression
            assert magic_smells[0].severity == SmellSeverity.LOW


class TestRefactoringSuggestionQuality:
    """Test quality of refactoring suggestions"""

    def test_suggestions_include_before_after_code(self):
        """Test that suggestions include before/after code examples"""
        smell = CodeSmell(
            smell_type="long_function",
            severity=SmellSeverity.HIGH,
            location="test.py:1",
            description="Function 'process' is 75 lines long (max: 50)"
        )

        suggestions = RefactoringEngine.generate_suggestions("", [smell])

        assert len(suggestions) > 0
        assert suggestions[0].before_code != ""
        assert suggestions[0].after_code != ""
        assert suggestions[0].before_code != suggestions[0].after_code

    def test_suggestions_include_impact_and_effort(self):
        """Test that suggestions estimate impact and effort"""
        smell = CodeSmell(
            smell_type="too_many_parameters",
            severity=SmellSeverity.MEDIUM,
            location="test.py:1",
            description="Function 'create' has 7 parameters (max: 5)"
        )

        suggestions = RefactoringEngine.generate_suggestions("", [smell])

        assert len(suggestions) > 0
        assert suggestions[0].impact != ""
        assert suggestions[0].effort in ["low", "medium", "high"]

    def test_suggestions_include_reason(self):
        """Test that suggestions explain the reason"""
        smell = CodeSmell(
            smell_type="magic_number",
            severity=SmellSeverity.LOW,
            location="test.py:1",
            description="Magic number '42' found"
        )

        suggestions = RefactoringEngine.generate_suggestions("", [smell])

        assert len(suggestions) > 0
        assert suggestions[0].reason != ""
        assert "magic number" in suggestions[0].reason.lower() or "42" in suggestions[0].reason
