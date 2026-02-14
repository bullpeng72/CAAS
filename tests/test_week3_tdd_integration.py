"""
Week 3 TDD Integration Tests - Phase 4.5 (RED) + Phase 5.5 (REFACTOR)

Tests the complete TDD workflow:
1. Phase 4.5: Generate tests from Golden Data (TDD RED)
2. Phase 5: Implement features (GREEN) - simulated
3. Phase 5.5: Analyze code and suggest refactorings (TDD REFACTOR)
"""

import pytest
from caas_framework.methodology.tdd_test_generator import TDDRedEngine
from caas_framework.methodology.tdd_refactor_engine import TDDRefactorEngine
from caas_framework.models.specifications import (
    ConcretizedRequirement,
    FeatureSpec,
    SystemScope
)


class TestWeek3TDDWorkflow:
    """Test complete TDD workflow: RED → GREEN → REFACTOR"""

    @pytest.mark.asyncio
    async def test_full_tdd_workflow_user_authentication(self):
        """
        Test complete TDD workflow for user authentication feature

        Steps:
        1. Phase 4.5 (RED): Generate tests from Golden Data
        2. Phase 5 (GREEN): Simulate implementation (with code smells)
        3. Phase 5.5 (REFACTOR): Analyze code and get refactoring suggestions
        """
        # ============================================================
        # PHASE 4.5: TDD RED - Generate Tests from Golden Data
        # ============================================================

        # Create Golden Data with test scenarios
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
                },
                {
                    "type": "integration",
                    "description": "Database connection failure",
                    "given": "Database is unavailable",
                    "when": "User attempts login",
                    "then": "500 error returned with retry message"
                }
            ],
            data_model={
                "entity": "User",
                "schema": {
                    "id": "UUID",
                    "email": "string",
                    "password_hash": "string",
                    "created_at": "datetime"
                }
            },
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

        # Generate tests using TDD RED Engine
        red_engine = TDDRedEngine()
        generated_tests = await red_engine.generate_tests(golden_data)

        # Verify test generation
        assert len(generated_tests) == 1
        test_file = generated_tests[0]
        assert test_file.test_count == 3
        assert "unit" in test_file.test_types
        assert "edge_case" in test_file.test_types
        assert "integration" in test_file.test_types

        # Verify test code is valid Python
        try:
            compile(test_file.content, "<generated>", "exec")
            test_generation_success = True
        except SyntaxError:
            test_generation_success = False

        assert test_generation_success, "Generated tests should be valid Python"

        # ============================================================
        # PHASE 5: GREEN - Simulated Implementation (with code smells)
        # ============================================================

        # Simulate a poorly written implementation that passes tests
        # but has code smells (long function, magic numbers, deep nesting, etc.)
        problematic_implementation = '''
def authenticate_user(email, password, db_host, db_port, db_name, db_user, db_password, cache_ttl):
    """Authenticate user with email and password"""
    import hashlib
    import time

    # Connect to database
    if db_host:
        if db_port:
            if db_name:
                if db_user:
                    # Deep nesting - code smell!
                    connection = connect_db(db_host, db_port, db_name, db_user, db_password)

                    # Magic numbers - code smell!
                    max_attempts = 3
                    lockout_time = 300  # 5 minutes in seconds
                    token_length = 32

                    # Long function - code smell!
                    user = connection.query(f"SELECT * FROM users WHERE email = '{email}'")

                    if user:
                        if user.failed_attempts < max_attempts:
                            password_hash = hashlib.sha256(password.encode()).hexdigest()

                            if user.password_hash == password_hash:
                                # Generate token
                                token = generate_random_string(token_length)

                                # Reset failed attempts
                                connection.execute(f"UPDATE users SET failed_attempts = 0 WHERE id = '{user.id}'")

                                # Cache token
                                cache_key = f"token:{user.id}"
                                cache.set(cache_key, token, ttl=cache_ttl)

                                # Log success
                                connection.execute(f"INSERT INTO auth_logs (user_id, action, timestamp) VALUES ('{user.id}', 'login_success', {time.time()})")

                                return {"token": token, "user_id": user.id}
                            else:
                                # Increment failed attempts
                                new_attempts = user.failed_attempts + 1
                                connection.execute(f"UPDATE users SET failed_attempts = {new_attempts} WHERE id = '{user.id}'")

                                # Check if should lock account
                                if new_attempts >= max_attempts:
                                    connection.execute(f"UPDATE users SET locked_until = {time.time() + lockout_time} WHERE id = '{user.id}'")

                                return {"error": "Invalid credentials", "status": 401}
                        else:
                            # Account locked
                            if user.locked_until > time.time():
                                return {"error": "Account locked", "status": 403}
                            else:
                                # Reset lock
                                connection.execute(f"UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = '{user.id}'")
                    else:
                        return {"error": "User not found", "status": 404}

    return {"error": "Database connection failed", "status": 500}

def connect_db(host, port, name, user, password):
    pass

def generate_random_string(length):
    pass

class cache:
    @staticmethod
    def set(key, value, ttl):
        pass
'''

        # ============================================================
        # PHASE 5.5: REFACTOR - Analyze Code and Get Suggestions
        # ============================================================

        # Analyze the problematic code
        refactor_engine = TDDRefactorEngine()
        refactor_report = refactor_engine.analyze_code(
            problematic_implementation,
            "auth/services.py"
        )

        # ============================================================
        # Verify Refactoring Analysis Results
        # ============================================================

        # Should detect multiple code smells
        assert len(refactor_report.code_smells) > 0, "Should detect code smells"

        smell_types = [s.smell_type for s in refactor_report.code_smells]

        # Check for specific expected smells
        assert "too_many_parameters" in smell_types, "Should detect 8 parameters (max: 5)"
        assert "deep_nesting" in smell_types, "Should detect deep nesting (4+ levels)"
        assert "long_function" in smell_types, "Should detect long function (60+ lines)"
        assert "magic_number" in smell_types, "Should detect magic numbers (3, 300, 32)"

        # Should generate refactoring suggestions
        assert len(refactor_report.refactoring_suggestions) > 0, "Should generate refactoring suggestions"

        suggestion_types = [s.refactoring_type.value for s in refactor_report.refactoring_suggestions]

        # Check for specific expected refactorings
        assert "extract_method" in suggestion_types, "Should suggest Extract Method for long function"
        assert "parameter_object" in suggestion_types, "Should suggest Parameter Object for many params"
        assert "simplify_conditional" in suggestion_types, "Should suggest Simplify Conditional for deep nesting"
        assert "introduce_constant" in suggestion_types, "Should suggest Introduce Constant for magic numbers"

        # Quality scores should reflect issues (below excellent but not terrible)
        assert refactor_report.code_quality_score < 9.0, "Code quality should be below excellent due to smells"
        assert refactor_report.best_practices_score < 9.0, "Best practices score should be below excellent"

        # Each suggestion should have actionable details
        for suggestion in refactor_report.refactoring_suggestions:
            assert suggestion.before_code != "", "Should show before code"
            assert suggestion.after_code != "", "Should show after code"
            assert suggestion.reason != "", "Should explain reason"
            assert suggestion.impact != "", "Should describe impact"
            assert suggestion.effort in ["low", "medium", "high"], "Should estimate effort"

        # Performance issues should be detected (if any)
        # In this case, deep nesting might not be flagged as performance issue,
        # but nested loops or string concatenation would be

        # Report should be serializable
        report_dict = refactor_report.to_dict()
        assert "code_smells" in report_dict
        assert "refactoring_suggestions" in report_dict
        assert "code_quality_score" in report_dict
        assert "best_practices_score" in report_dict


    @pytest.mark.asyncio
    async def test_tdd_workflow_clean_code(self):
        """
        Test TDD workflow with clean, well-written code

        Should generate tests, and when analyzing clean code,
        should report high quality scores with minimal issues.
        """
        # ============================================================
        # PHASE 4.5: Generate Tests
        # ============================================================

        feature = FeatureSpec(
            id="F2",
            name="Calculate Total",
            description="Calculate sum of numbers",
            test_scenarios=[
                {
                    "type": "unit",
                    "description": "Sum of positive numbers",
                    "given": "List of positive integers",
                    "when": "calculate_total() is called",
                    "then": "Returns correct sum"
                }
            ]
        )

        golden_data = ConcretizedRequirement(
            system_scope=SystemScope(project_name="Math Utils", purpose="Utility functions"),
            features=[feature],
            domain="CUSTOM"
        )

        red_engine = TDDRedEngine()
        generated_tests = await red_engine.generate_tests(golden_data)

        assert len(generated_tests) == 1
        assert generated_tests[0].test_count == 1

        # ============================================================
        # PHASE 5: Clean Implementation
        # ============================================================

        clean_implementation = '''
from typing import List

def calculate_total(numbers: List[int]) -> int:
    """
    Calculate the sum of a list of numbers.

    Args:
        numbers: List of integers to sum

    Returns:
        The total sum of all numbers
    """
    return sum(numbers)

class MathUtils:
    """Utility class for mathematical operations."""

    @staticmethod
    def calculate_average(numbers: List[float]) -> float:
        """
        Calculate the average of a list of numbers.

        Args:
            numbers: List of numbers to average

        Returns:
            The arithmetic mean
        """
        if not numbers:
            return 0.0
        return sum(numbers) / len(numbers)
'''

        # ============================================================
        # PHASE 5.5: Analyze Clean Code
        # ============================================================

        refactor_engine = TDDRefactorEngine()
        refactor_report = refactor_engine.analyze_code(clean_implementation, "utils/math.py")

        # Clean code should have high quality scores
        assert refactor_report.code_quality_score >= 9.0, "Clean code should score high (9+)"
        assert refactor_report.best_practices_score >= 9.0, "Should follow best practices"

        # Should have no critical issues
        critical_smells = [s for s in refactor_report.code_smells if s.severity.value == "CRITICAL"]
        assert len(critical_smells) == 0, "Clean code should have no critical issues"

        # Summary should reflect good quality
        assert "excellent" in refactor_report.summary.lower() or "good" in refactor_report.summary.lower() or len(refactor_report.code_smells) == 0


    @pytest.mark.asyncio
    async def test_tdd_workflow_with_performance_issues(self):
        """
        Test TDD workflow with code that has performance issues

        Should detect performance anti-patterns like:
        - Nested loops (O(n²))
        - String concatenation in loops
        """
        # ============================================================
        # PHASE 4.5: Generate Tests
        # ============================================================

        feature = FeatureSpec(
            id="F3",
            name="Process Data Matrix",
            description="Process 2D data matrix",
            test_scenarios=[
                {
                    "type": "unit",
                    "description": "Process matrix data",
                    "given": "2D matrix of numbers",
                    "when": "process_matrix() is called",
                    "then": "Returns processed result"
                }
            ]
        )

        golden_data = ConcretizedRequirement(
            system_scope=SystemScope(project_name="Data Processor", purpose="Data processing"),
            features=[feature],
            domain="DATA_ANALYSIS"
        )

        red_engine = TDDRedEngine()
        generated_tests = await red_engine.generate_tests(golden_data)

        assert len(generated_tests) == 1

        # ============================================================
        # PHASE 5: Implementation with Performance Issues
        # ============================================================

        slow_implementation = '''
def process_matrix(matrix):
    """Process a 2D matrix of data"""
    result = ""

    # Nested loops - O(n²) performance issue
    for row in matrix:
        for col in row:
            # String concatenation in loop - performance issue
            result += str(col) + ","

    return result

def find_duplicates(data):
    """Find duplicate values in data"""
    duplicates = []

    # Nested loops - O(n²) performance issue
    for i in range(len(data)):
        for j in range(i + 1, len(data)):
            if data[i] == data[j]:
                duplicates.append(data[i])

    return duplicates
'''

        # ============================================================
        # PHASE 5.5: Analyze Performance Issues
        # ============================================================

        refactor_engine = TDDRefactorEngine()
        refactor_report = refactor_engine.analyze_code(slow_implementation, "processing/data.py")

        # Should detect performance issues
        assert len(refactor_report.performance_issues) > 0, "Should detect performance issues"

        issue_types = [i.issue_type for i in refactor_report.performance_issues]

        assert "nested_loops" in issue_types, "Should detect nested loops"
        assert "string_concat_in_loop" in issue_types, "Should detect string concatenation in loop"

        # Performance issues should have optimization suggestions
        for issue in refactor_report.performance_issues:
            assert issue.optimization != "", "Should provide optimization suggestion"
            assert issue.current_complexity != "", "Should describe current complexity"


class TestTDDIntegrationEndToEnd:
    """Test complete end-to-end TDD integration"""

    @pytest.mark.asyncio
    async def test_e2e_tdd_red_green_refactor(self):
        """
        Full E2E test: Story → Golden Data → Tests → Implementation → Refactoring

        This simulates the complete CAAS-E Week 1-3 workflow:
        - Week 1: Story Decomposition → Golden Data (SDD)
        - Week 3 Phase 4.5: Golden Data → Tests (TDD RED)
        - Week 3 Phase 5.5: Code → Refactoring Report (TDD REFACTOR)
        """
        # Week 1: Golden Data with SDD fields
        feature = FeatureSpec(
            id="F1",
            name="User Registration",
            description="New user registration with email verification",
            priority="high",
            # SDD: API Contract
            api_contract={
                "endpoint": "/api/auth/register",
                "method": "POST",
                "request": {
                    "email": "string",
                    "password": "string",
                    "username": "string"
                },
                "response": {
                    "user_id": "UUID",
                    "verification_email_sent": "boolean"
                }
            },
            # SDD: Data Model
            data_model={
                "entity": "User",
                "schema": {
                    "id": "UUID",
                    "email": "string",
                    "username": "string",
                    "password_hash": "string",
                    "email_verified": "boolean",
                    "created_at": "datetime"
                }
            },
            # SDD: Business Rules
            business_rules=[
                "Email must be unique",
                "Password must be at least 8 characters",
                "Username must be 3-20 characters",
                "Email verification required within 24 hours"
            ],
            # SDD: Test Scenarios (for TDD RED)
            test_scenarios=[
                {
                    "type": "unit",
                    "description": "Valid registration",
                    "given": "Valid email, password, and username",
                    "when": "User submits registration",
                    "then": "User created and verification email sent"
                },
                {
                    "type": "edge_case",
                    "description": "Duplicate email",
                    "given": "Email already exists in database",
                    "when": "User tries to register",
                    "then": "409 Conflict error returned"
                }
            ]
        )

        golden_data = ConcretizedRequirement(
            system_scope=SystemScope(
                project_name="User Management System",
                purpose="Handle user authentication and authorization"
            ),
            features=[feature],
            domain="AUTHENTICATION"
        )

        # Week 3 Phase 4.5: TDD RED - Generate Tests
        red_engine = TDDRedEngine()
        generated_tests = await red_engine.generate_tests(golden_data)

        assert len(generated_tests) == 1
        test_file = generated_tests[0]
        assert test_file.test_count == 2

        # Verify test content includes test scenarios
        assert "test_" in test_file.content
        assert "valid_registration" in test_file.content.lower() or "registration" in test_file.content

        # Simulated GREEN phase: Implementation with some issues
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

    # Create user (simplified)
    user_id = db.insert("users", {
        "email": email,
        "password_hash": hash_password(password),
        "username": username,
        "email_verified": False
    })

    # Send verification email
    email_service.send_verification(email, user_id)

    return {"user_id": user_id, "verification_email_sent": True}

def hash_password(password):
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()
'''

        # Week 3 Phase 5.5: TDD REFACTOR - Analyze and Suggest
        refactor_engine = TDDRefactorEngine()
        refactor_report = refactor_engine.analyze_code(implementation, "auth/registration.py")

        # Verify analysis detected issues
        assert len(refactor_report.code_smells) > 0

        smell_types = [s.smell_type for s in refactor_report.code_smells]
        assert "missing_docstring" in smell_types
        assert "magic_number" in smell_types  # 8, 3, 20

        # Verify refactoring suggestions
        assert len(refactor_report.refactoring_suggestions) > 0

        # Verify report completeness
        assert refactor_report.file_path == "auth/registration.py"
        assert 0.0 <= refactor_report.code_quality_score <= 10.0
        assert 0.0 <= refactor_report.best_practices_score <= 10.0
        assert refactor_report.summary != ""

        # Report should be JSON serializable
        report_dict = refactor_report.to_dict()
        assert isinstance(report_dict, dict)
        assert "code_smells" in report_dict
        assert "refactoring_suggestions" in report_dict
