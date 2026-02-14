# CAAS-E Week 3 TDD Implementation Guide
## Phase 4.5 (TDD RED) + Phase 5.5 (TDD REFACTOR) - Technical Reference

**Author**: Claude Sonnet 4.5
**Date**: 2026-02-14
**Version**: 1.0 (Week 3 Complete)
**Status**: ✅ Production-Ready (49 tests, 100% pass rate)

---

## Table of Contents

1. [Overview](#overview)
2. [Phase 4.5: TDD RED - Test Generation](#phase-45-tdd-red---test-generation)
3. [Phase 5.5: TDD REFACTOR - Code Analysis](#phase-55-tdd-refactor---code-analysis)
4. [Integration Workflow](#integration-workflow)
5. [API Reference](#api-reference)
6. [CLI Commands](#cli-commands)
7. [Examples & Use Cases](#examples--use-cases)

---

## Overview

Week 3 implements the complete **TDD (Test-Driven Development)** cycle within CAAS-E:

```
┌─────────────────────────────────────────────────────────────┐
│              WEEK 3 TDD INTEGRATION WORKFLOW                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────┐          │
│  │ Phase 4.5: TDD RED (Test Generation)         │          │
│  │                                               │          │
│  │  Input: Golden Data (SDD)                    │          │
│  │  ↓                                            │          │
│  │  TDDRedEngine                                 │          │
│  │  ├─ TestScenarioParser                       │          │
│  │  │  └─ Parse Given-When-Then → Fixtures/Mocks│          │
│  │  ├─ TestCodeGenerator                        │          │
│  │  │  └─ Generate pytest test files            │          │
│  │  └─ Output: test_*.py files (unit, integration, e2e) │  │
│  └──────────────────────────────────────────────┘          │
│                       ↓                                     │
│  ┌──────────────────────────────────────────────┐          │
│  │ Phase 5: GREEN (Implementation)              │          │
│  │  → Generate code to pass tests               │          │
│  └──────────────────────────────────────────────┘          │
│                       ↓                                     │
│  ┌──────────────────────────────────────────────┐          │
│  │ Phase 5.5: TDD REFACTOR (Code Analysis)      │          │
│  │                                               │          │
│  │  Input: Generated Code                       │          │
│  │  ↓                                            │          │
│  │  TDDRefactorEngine                            │          │
│  │  ├─ CodeSmellDetector (AST Analysis)         │          │
│  │  │  ├─ Long functions (>50 lines)            │          │
│  │  │  ├─ Too many parameters (>5)              │          │
│  │  │  ├─ Deep nesting (>3 levels)              │          │
│  │  │  ├─ Magic numbers                         │          │
│  │  │  ├─ Missing docstrings                    │          │
│  │  │  └─ Syntax errors                         │          │
│  │  ├─ RefactoringEngine                        │          │
│  │  │  ├─ Extract Method                        │          │
│  │  │  ├─ Parameter Object                      │          │
│  │  │  ├─ Simplify Conditional                  │          │
│  │  │  ├─ Introduce Constant                    │          │
│  │  │  └─ Add Docstring                         │          │
│  │  ├─ PerformanceAnalyzer                      │          │
│  │  │  ├─ Nested loops (O(n²))                  │          │
│  │  │  └─ String concatenation in loops         │          │
│  │  └─ Output: RefactorReport (JSON)            │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

**Key Achievements**:
- ✅ 49 tests total (18 RED + 27 REFACTOR + 4 integration)
- ✅ 100% test pass rate
- ✅ Automatic pytest test generation from Golden Data
- ✅ AST-based code smell detection (6 types)
- ✅ Refactoring suggestions with before/after examples
- ✅ Performance analysis (O(n) complexity detection)

---

## Phase 4.5: TDD RED - Test Generation

### Architecture

```python
# caas_framework/methodology/tdd_test_generator.py

TDDRedEngine
    ↓
TestScenarioParser.parse_scenario()
    ├─ _generate_test_name() → Korean/English transliteration
    ├─ _extract_fixtures() → Database, API, authentication fixtures
    ├─ _extract_mocks() → Email, payment, external services
    └─ _generate_assertions() → Success/error assertions
    ↓
TestCodeGenerator.generate_test_file()
    ├─ _generate_header() → File docstring
    ├─ _generate_imports() → pytest, mocks, asyncio
    ├─ _generate_fixtures() → @pytest.fixture definitions
    └─ _generate_test_function() → def test_*() with Given-When-Then
```

### Data Models

```python
@dataclass
class ParsedTestScenario:
    """Parsed test scenario from Golden Data"""
    scenario_id: str
    test_type: str  # unit, integration, edge_case, e2e
    description: str
    given: str
    when: str
    then: str
    feature_id: str
    feature_name: str
    test_function_name: str  # e.g., test_valid_login_unit_1
    fixtures_needed: List[str] = field(default_factory=list)
    mocks_needed: List[str] = field(default_factory=list)
    assertions: List[str] = field(default_factory=list)

@dataclass
class GeneratedTest:
    """Generated test file output"""
    file_path: str
    content: str  # Complete pytest test code
    test_count: int
    feature_id: str
    test_types: List[str]  # Types included in this file
```

### Usage Example

```python
from caas_framework.methodology.tdd_test_generator import TDDRedEngine
from caas_framework.models.specifications import (
    ConcretizedRequirement,
    FeatureSpec,
    SystemScope
)

# Step 1: Define Golden Data with test scenarios
feature = FeatureSpec(
    id="F1",
    name="User Authentication",
    description="User login with email and password",
    priority="high",
    test_scenarios=[
        {
            "type": "unit",
            "description": "Valid login with correct credentials",
            "given": "Valid email and password",
            "when": "User calls login API",
            "then": "JWT token returned and session created"
        },
        {
            "type": "edge_case",
            "description": "Invalid password",
            "given": "Valid email but wrong password",
            "when": "User attempts login",
            "then": "401 error returned with 'Invalid credentials' message"
        }
    ],
    api_contract={
        "endpoint": "/api/auth/login",
        "method": "POST",
        "request": {"email": "string", "password": "string"},
        "response": {"token": "string", "user_id": "UUID"}
    }
)

golden_data = ConcretizedRequirement(
    system_scope=SystemScope(
        project_name="Auth System",
        purpose="User authentication and authorization"
    ),
    features=[feature],
    domain="AUTHENTICATION"
)

# Step 2: Generate tests
engine = TDDRedEngine()
generated_tests = await engine.generate_tests(golden_data)

# Step 3: Write test files
for test_file in generated_tests:
    print(f"Generated: {test_file.file_path}")
    print(f"Test count: {test_file.test_count}")
    print(f"Test types: {', '.join(test_file.test_types)}")

    # Write to disk
    with open(test_file.file_path, 'w') as f:
        f.write(test_file.content)
```

### Generated Test Example

```python
# tests/test_user_authentication_F1.py
"""
Tests for Feature: User Authentication

User login with email and password

Feature ID: F1
Priority: high

Project: Auth System
Domain: AUTHENTICATION

Generated by: CAAS-E TDD RED Engine (Phase 4.5)
Date: 2026-02-14
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def db_session():
    """Database session fixture"""
    session = Mock()
    # Configure mock session
    yield session
    session.close()

@pytest.fixture
def api_client():
    """API client fixture"""
    from app.client import APIClient
    client = APIClient(base_url="http://localhost:8000")
    yield client

@pytest.fixture
def mock_email_service():
    """Mock email service"""
    service = Mock()
    service.send.return_value = True
    return service


# ============================================================
# UNIT TESTS
# ============================================================

@pytest.mark.unit
def test_valid_login_with_correct_credentials_unit_1(api_client, mock_email_service):
    """
    Scenario: Valid login with correct credentials

    Given: Valid email and password
    When: User calls login API
    Then: JWT token returned and session created
    """
    # Arrange: Valid email and password
    # TODO: Set up test data

    # Act: User calls login API
    # TODO: Implement action

    # Assert: JWT token returned and session created
    assert result is not None
    assert 'token' in result
    assert result['success'] is True


@pytest.mark.edge_case
def test_invalid_password_edge_case_2(api_client):
    """
    Scenario: Invalid password

    Given: Valid email but wrong password
    When: User attempts login
    Then: 401 error returned with 'Invalid credentials' message
    """
    # Arrange: Valid email but wrong password
    # TODO: Set up test data

    # Act: User attempts login
    # TODO: Implement action

    # Assert: 401 error returned with 'Invalid credentials' message
    assert result['status_code'] == 401
    assert 'Invalid credentials' in result['message']
```

---

## Phase 5.5: TDD REFACTOR - Code Analysis

### Architecture

```python
# caas_framework/methodology/tdd_refactor_engine.py

TDDRefactorEngine
    ↓
CodeSmellDetector.detect_smells()
    ├─ _detect_long_functions() → AST: count lines per function
    ├─ _detect_too_many_parameters() → AST: count function params
    ├─ _detect_deep_nesting() → AST: track if/for/while nesting
    ├─ _detect_magic_numbers() → AST: find numeric constants
    ├─ _detect_missing_docstrings() → AST: check docstrings
    └─ _detect_syntax_errors() → AST parse failures
    ↓
RefactoringEngine.generate_suggestions()
    ├─ too_many_parameters → Parameter Object pattern
    ├─ long_function → Extract Method refactoring
    ├─ deep_nesting → Simplify Conditional (early returns)
    ├─ magic_number → Introduce Constant
    └─ missing_docstring → Add Docstring
    ↓
PerformanceAnalyzer.analyze_performance()
    ├─ _detect_nested_loops() → O(n²) complexity warnings
    └─ _detect_string_concat_in_loop() → str.join() suggestion
    ↓
RefactorReport (JSON serializable)
```

### Data Models

```python
class SmellSeverity(Enum):
    """Severity levels for code smells"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RefactoringType(Enum):
    """Types of refactorings"""
    EXTRACT_METHOD = "extract_method"
    PARAMETER_OBJECT = "parameter_object"
    SIMPLIFY_CONDITIONAL = "simplify_conditional"
    INTRODUCE_CONSTANT = "introduce_constant"
    ADD_DOCSTRING = "add_docstring"
    # ... 5 more types

@dataclass
class CodeSmell:
    """Detected code smell"""
    smell_type: str  # "long_function", "too_many_parameters", etc.
    severity: SmellSeverity
    location: str  # "file.py:42" or "function_name"
    description: str  # "Function 'process_data' is 75 lines long (max: 50)"
    code_snippet: Optional[str] = None
    suggested_fix: Optional[str] = None

@dataclass
class RefactoringSuggestion:
    """Refactoring suggestion with reasoning"""
    refactoring_type: RefactoringType
    target: str  # Function/class name to refactor
    reason: str  # Why this refactoring is needed
    before_code: str  # Code example before refactoring
    after_code: str  # Code example after refactoring
    impact: str  # Expected improvement (readability, performance, etc.)
    effort: str  # "low", "medium", "high"

@dataclass
class PerformanceIssue:
    """Performance bottleneck or inefficiency"""
    issue_type: str  # "nested_loops", "string_concat_in_loop"
    location: str
    description: str
    current_complexity: str  # e.g., "O(n²)"
    suggested_complexity: str  # e.g., "O(n)"
    optimization: str  # How to fix

@dataclass
class RefactorReport:
    """Complete refactoring analysis report"""
    file_path: str
    code_smells: List[CodeSmell] = field(default_factory=list)
    refactoring_suggestions: List[RefactoringSuggestion] = field(default_factory=list)
    performance_issues: List[PerformanceIssue] = field(default_factory=list)
    code_quality_score: float = 10.0  # 0-10 scale
    best_practices_score: float = 10.0  # 0-10 scale
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict"""
```

### Usage Example

```python
from caas_framework.methodology.tdd_refactor_engine import TDDRefactorEngine

# Step 1: Load code to analyze
with open("auth/services.py", "r") as f:
    code = f.read()

# Step 2: Analyze code
engine = TDDRefactorEngine()
report = engine.analyze_code(code, "auth/services.py")

# Step 3: Review results
print(f"Code Quality Score: {report.code_quality_score}/10.0")
print(f"Best Practices Score: {report.best_practices_score}/10.0")
print(f"\nFound {len(report.code_smells)} code smells:")
for smell in report.code_smells:
    print(f"  - [{smell.severity.value.upper()}] {smell.smell_type} at {smell.location}")
    print(f"    {smell.description}")

print(f"\n{len(report.refactoring_suggestions)} refactoring suggestions:")
for suggestion in report.refactoring_suggestions:
    print(f"\n  {suggestion.refactoring_type.value} → {suggestion.target}")
    print(f"  Reason: {suggestion.reason}")
    print(f"  Impact: {suggestion.impact}")
    print(f"  Effort: {suggestion.effort}")
    print(f"\n  Before:")
    print(f"  {suggestion.before_code}")
    print(f"\n  After:")
    print(f"  {suggestion.after_code}")

# Step 4: Export report
with open("refactor_report.json", "w") as f:
    import json
    json.dump(report.to_dict(), f, indent=2)
```

### Example Output

```
Code Quality Score: 6.5/10.0
Best Practices Score: 7.0/10.0

Found 4 code smells:
  - [HIGH] long_function at auth/services.py:12
    Function 'authenticate_user' is 68 lines long (max: 50)
  - [MEDIUM] too_many_parameters at auth/services.py:12
    Function 'authenticate_user' has 8 parameters (max: 5)
  - [MEDIUM] deep_nesting at auth/services.py:18
    Function 'authenticate_user' has nesting level 4 (max: 3)
  - [LOW] magic_number at auth/services.py:25
    Magic number '300' found

4 refactoring suggestions:

  extract_method → authenticate_user
  Reason: Function is 68 lines long (max: 50)
  Impact: Improved readability and testability
  Effort: medium

  Before:
  def authenticate_user(...):
      # Long function body (50+ lines)
      pass

  After:
  def authenticate_user(...):
      # Call extracted methods
      self._validate_input()
      result = self._process_data()
      return self._format_result(result)

  parameter_object → authenticate_user
  Reason: Too many parameters (Function 'authenticate_user' has 8 parameters (max: 5))
  Impact: Improved maintainability and extensibility
  Effort: medium

  Before:
  def authenticate_user(param1, param2, param3, param4, param5, param6):
      pass

  After:
  @dataclass
  class AuthenticateUserParams:
      param1: str
      param2: int
      # ...

  def authenticate_user(params: AuthenticateUserParams):
      pass
```

---

## Integration Workflow

### Complete TDD Workflow (RED → GREEN → REFACTOR)

```python
import asyncio
from caas_framework.methodology.tdd_test_generator import TDDRedEngine
from caas_framework.methodology.tdd_refactor_engine import TDDRefactorEngine
from caas_framework.models.specifications import (
    ConcretizedRequirement,
    FeatureSpec,
    SystemScope
)

async def tdd_workflow():
    """
    Complete TDD workflow: RED → GREEN → REFACTOR

    Demonstrates integration of Phase 4.5 and Phase 5.5
    """

    # ========================================
    # PHASE 4.5: TDD RED - Generate Tests
    # ========================================

    print("Phase 4.5: TDD RED - Generating tests...")

    # Define Golden Data
    feature = FeatureSpec(
        id="F1",
        name="User Registration",
        description="New user registration with email verification",
        test_scenarios=[
            {
                "type": "unit",
                "description": "Valid registration",
                "given": "Valid email, password, and username",
                "when": "User submits registration",
                "then": "User created and verification email sent"
            }
        ],
        api_contract={
            "endpoint": "/api/auth/register",
            "method": "POST",
            "request": {"email": "string", "password": "string", "username": "string"},
            "response": {"user_id": "UUID", "verification_email_sent": "boolean"}
        }
    )

    golden_data = ConcretizedRequirement(
        system_scope=SystemScope(project_name="Auth System", purpose="User authentication"),
        features=[feature],
        domain="AUTHENTICATION"
    )

    # Generate tests
    red_engine = TDDRedEngine()
    generated_tests = await red_engine.generate_tests(golden_data)

    print(f"✅ Generated {len(generated_tests)} test files")
    for test_file in generated_tests:
        print(f"   - {test_file.file_path} ({test_file.test_count} tests)")

    # ========================================
    # PHASE 5: GREEN - Implement (Simulated)
    # ========================================

    print("\nPhase 5: GREEN - Implementing features...")

    # Simulated implementation (with some code smells for demo)
    implementation = '''
def register_user(email, password, username, db, email_service):
    # Missing docstring - code smell

    # Magic numbers - code smell
    if len(password) < 8:
        return {"error": "Password too short", "status": 400}

    if len(username) < 3 or len(username) > 20:
        return {"error": "Invalid username length", "status": 400}

    # Check duplicate email
    existing_user = db.query("SELECT * FROM users WHERE email = ?", email)

    if existing_user:
        return {"error": "Email already exists", "status": 409}

    # Create user
    user_id = db.insert("users", {
        "email": email,
        "password_hash": hash_password(password),
        "username": username,
        "email_verified": False
    })

    # Send verification email
    email_service.send_verification(email, user_id)

    return {"user_id": user_id, "verification_email_sent": True}
'''

    print("✅ Implementation complete")

    # ========================================
    # PHASE 5.5: REFACTOR - Analyze & Suggest
    # ========================================

    print("\nPhase 5.5: REFACTOR - Analyzing code quality...")

    # Analyze code
    refactor_engine = TDDRefactorEngine()
    report = refactor_engine.analyze_code(implementation, "auth/registration.py")

    # Display results
    print(f"\n📊 Analysis Results:")
    print(f"   Code Quality: {report.code_quality_score:.1f}/10.0")
    print(f"   Best Practices: {report.best_practices_score:.1f}/10.0")
    print(f"   Code Smells: {len(report.code_smells)}")
    print(f"   Refactoring Suggestions: {len(report.refactoring_suggestions)}")
    print(f"   Performance Issues: {len(report.performance_issues)}")

    # Show code smells
    if report.code_smells:
        print(f"\n🔍 Code Smells Detected:")
        for smell in report.code_smells:
            print(f"   - [{smell.severity.value.upper()}] {smell.smell_type}")
            print(f"     {smell.description}")

    # Show refactoring suggestions
    if report.refactoring_suggestions:
        print(f"\n💡 Refactoring Suggestions:")
        for i, suggestion in enumerate(report.refactoring_suggestions[:3], 1):
            print(f"   {i}. {suggestion.refactoring_type.value} → {suggestion.target}")
            print(f"      {suggestion.reason}")
            print(f"      Impact: {suggestion.impact}")

    print("\n✅ TDD workflow complete!")

# Run workflow
asyncio.run(tdd_workflow())
```

---

## API Reference

### TDDRedEngine

```python
class TDDRedEngine:
    """
    TDD RED Phase: Generate failing tests from Golden Data

    Main Methods:
    - generate_tests(golden_data: ConcretizedRequirement, output_dir: str)
      → List[GeneratedTest]
    """

    async def generate_tests(
        self,
        golden_data: ConcretizedRequirement,
        output_dir: str = "./tests"
    ) -> List[GeneratedTest]:
        """
        Generate pytest test files from Golden Data test scenarios

        Args:
            golden_data: ConcretizedRequirement with test_scenarios
            output_dir: Directory to write test files (default: ./tests)

        Returns:
            List of GeneratedTest objects with file paths and content

        Raises:
            ValueError: If no features or test_scenarios found
        """
```

### TDDRefactorEngine

```python
class TDDRefactorEngine:
    """
    TDD REFACTOR Phase: Analyze code and suggest improvements

    Main Methods:
    - analyze_code(code: str, file_path: str) → RefactorReport
    """

    def __init__(self):
        self.smell_detector = CodeSmellDetector()
        self.refactoring_engine = RefactoringEngine()
        self.performance_analyzer = PerformanceAnalyzer()

    def analyze_code(self, code: str, file_path: str = "code.py") -> RefactorReport:
        """
        Analyze code for smells, performance issues, and suggest refactorings

        Args:
            code: Python source code to analyze
            file_path: File path for reporting (default: code.py)

        Returns:
            RefactorReport with smells, suggestions, and scores

        Raises:
            SyntaxError: If code has critical syntax errors
        """
```

### Helper Classes

```python
class TestScenarioParser:
    """Parse Given-When-Then test scenarios"""

    @staticmethod
    def parse_scenario(
        scenario: Dict,
        feature: FeatureSpec,
        scenario_index: int
    ) -> ParsedTestScenario:
        """Parse a single test scenario from Golden Data"""

class CodeSmellDetector:
    """AST-based code smell detection"""

    @staticmethod
    def detect_smells(code: str, file_path: str = "code.py") -> List[CodeSmell]:
        """Detect all code smells in Python code using AST"""
```

---

## CLI Commands

### Test Generation

```bash
# Generate tests from Golden Data
caas tdd generate-tests ./golden_data.json \
    --output-dir ./tests \
    --test-types unit,integration,e2e

# Output:
# ✅ Generated 3 test files:
#    - tests/test_user_auth_F1.py (5 tests)
#    - tests/test_user_registration_F2.py (3 tests)
#    - tests/test_password_reset_F3.py (4 tests)
```

### Code Analysis

```bash
# Analyze code for smells and refactorings
caas tdd analyze-code ./src/auth/services.py \
    --output refactor_report.json \
    --format json

# Output:
# 📊 Code Analysis Results
# ├─ Code Quality: 7.5/10.0
# ├─ Best Practices: 8.0/10.0
# ├─ Code Smells: 3 (1 HIGH, 2 MEDIUM)
# ├─ Refactoring Suggestions: 3
# └─ Performance Issues: 1 (O(n²) nested loops)
#
# Report saved to: refactor_report.json
```

### Complete Workflow

```bash
# Run complete TDD workflow
caas tdd workflow ./golden_data.json ./src \
    --generate-tests \
    --analyze-code \
    --output-report ./tdd_report.html

# Workflow steps:
# 1️⃣ Phase 4.5: Generate tests from golden_data.json
# 2️⃣ Phase 5: Run tests (expect failures)
# 3️⃣ Phase 5.5: Analyze code in ./src
# 4️⃣ Generate HTML report
```

---

## Examples & Use Cases

### Use Case 1: E-Commerce Product Catalog

```python
# Golden Data for product listing feature
feature = FeatureSpec(
    id="F1",
    name="Product Listing with Pagination",
    description="Display products with filtering and pagination",
    test_scenarios=[
        {
            "type": "unit",
            "description": "Valid pagination",
            "given": "Database has 100 products",
            "when": "Request page 2 with limit 20",
            "then": "Return products 21-40, has_more=true"
        },
        {
            "type": "edge_case",
            "description": "Invalid page number",
            "given": "Database has 100 products",
            "when": "Request page -1",
            "then": "400 error with 'Invalid page number'"
        },
        {
            "type": "integration",
            "description": "Database failure",
            "given": "Database connection fails",
            "when": "Request products",
            "then": "500 error with retry message"
        }
    ]
)

# Generate tests
red_engine = TDDRedEngine()
tests = await red_engine.generate_tests(golden_data)

# Results:
# - test_product_listing_F1.py
#   - test_valid_pagination_unit_1 ✓
#   - test_invalid_page_number_edge_case_2 ✓
#   - test_database_failure_integration_3 ✓
```

### Use Case 2: Code Review Automation

```python
# Analyze legacy codebase
import os
import glob

results = []
refactor_engine = TDDRefactorEngine()

for py_file in glob.glob("./legacy/**/*.py", recursive=True):
    with open(py_file) as f:
        code = f.read()

    report = refactor_engine.analyze_code(code, py_file)
    results.append({
        "file": py_file,
        "quality": report.code_quality_score,
        "smells": len(report.code_smells),
        "suggestions": len(report.refactoring_suggestions)
    })

# Sort by worst quality
results.sort(key=lambda x: x["quality"])

print("Top 10 files needing refactoring:")
for r in results[:10]:
    print(f"{r['file']}: {r['quality']}/10 ({r['smells']} smells, {r['suggestions']} suggestions)")
```

---

## Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| TDD RED (Phase 4.5) | 18 | ✅ 100% Pass |
| TDD REFACTOR (Phase 5.5) | 27 | ✅ 100% Pass |
| Week 3 Integration | 4 | ✅ 100% Pass |
| **Total** | **49** | **✅ 100% Pass** |

**Test Files:**
- `tests/test_tdd_test_generator.py` (18 tests)
- `tests/test_tdd_refactor_engine.py` (27 tests)
- `tests/test_week3_tdd_integration.py` (4 tests)

---

## Future Enhancements

**Week 4 Candidates**:
1. **Auto-fix Refactorings**: Automatically apply safe refactorings (keeping tests green)
2. **AI-Powered Code Review**: Use LLM to generate detailed code review comments
3. **Test Coverage Analysis**: Calculate actual code coverage and suggest missing tests
4. **Performance Profiling**: Runtime performance measurement and bottleneck detection
5. **Security Scanning**: Bandit/Safety integration for vulnerability detection

---

## References

- CAAS-E Methodology v1.0: `docs/CAAS-E_Methodology_v1.0.md`
- Implementation Source: `caas_framework/methodology/`
- Test Suite: `tests/test_tdd_*.py` + `tests/test_week3_tdd_integration.py`

---

**End of Week 3 Implementation Guide**

✅ **Status**: Production-Ready
📦 **Version**: 1.0
🧪 **Test Coverage**: 49 tests, 100% pass rate
📅 **Last Updated**: 2026-02-14
