"""
Tests for TDD RED Test Generator (CAAS-E Week 3)

Tests the automatic pytest test generation from Golden Data test_scenarios.
"""

import pytest
import re
from caas_framework.methodology.tdd_test_generator import (
    TDDRedEngine,
    TestScenarioParser,
    TestCodeGenerator,
    ParsedTestScenario,
    GeneratedTest
)
from caas_framework.models.specifications import (
    ConcretizedRequirement,
    FeatureSpec,
    SystemScope
)


class TestTestScenarioParser:
    """Test TestScenarioParser"""

    def test_parse_unit_test_scenario(self):
        """Test parsing a unit test scenario"""
        scenario = {
            "type": "unit",
            "description": "정상 회원가입 프로세스",
            "given": "유효한 이메일과 강력한 비밀번호",
            "when": "사용자가 회원가입 API를 호출",
            "then": "사용자 계정 생성되고 인증 이메일 발송됨"
        }

        feature = FeatureSpec(
            id="F1",
            name="사용자 회원가입",
            description="이메일과 비밀번호로 회원가입",
            data_model={
                "entity": "User",
                "schema": {"id": "UUID", "email": "string"}
            }
        )

        parsed = TestScenarioParser.parse_scenario(scenario, feature, 0)

        assert parsed.scenario_id == "F1_scenario_1"
        assert parsed.test_type == "unit"
        assert parsed.description == "정상 회원가입 프로세스"
        assert parsed.given == "유효한 이메일과 강력한 비밀번호"
        assert parsed.when == "사용자가 회원가입 API를 호출"
        assert parsed.then == "사용자 계정 생성되고 인증 이메일 발송됨"
        assert parsed.feature_id == "F1"
        assert parsed.test_function_name.startswith("test_")
        assert len(parsed.fixtures_needed) >= 0
        assert len(parsed.assertions) > 0

    def test_generate_test_name_from_korean(self):
        """Test test name generation from Korean description"""
        name = TestScenarioParser._generate_test_name("정상 로그인", "unit", 0)

        assert name.startswith("test_")
        assert "login" in name or "normal" in name
        assert name.endswith("_1")

    def test_generate_test_name_from_english(self):
        """Test test name generation from English description"""
        name = TestScenarioParser._generate_test_name("Valid user registration", "integration", 2)

        assert name.startswith("test_")
        assert "valid" in name
        assert "user" in name
        assert "registration" in name
        assert "_integration_" in name
        assert name.endswith("_3")

    def test_extract_fixtures_for_database(self):
        """Test fixture extraction for database operations"""
        given = "데이터베이스에 사용자 데이터 존재"
        when = "사용자 정보를 데이터베이스에 저장"
        feature = FeatureSpec(id="F1", name="Test", description="Test")

        fixtures = TestScenarioParser._extract_fixtures(given, when, feature)

        assert "db_session" in fixtures

    def test_extract_fixtures_for_api(self):
        """Test fixture extraction for API calls"""
        given = "유효한 요청 데이터"
        when = "POST /api/users API를 호출"
        feature = FeatureSpec(id="F1", name="Test", description="Test")

        fixtures = TestScenarioParser._extract_fixtures(given, when, feature)

        assert "api_client" in fixtures

    def test_extract_mocks_for_email_service(self):
        """Test mock extraction for email service"""
        given = "이메일 서비스 사용 가능"
        when = "인증 이메일을 발송"
        mocks = TestScenarioParser._extract_mocks(given, when, "unit")

        assert "mock_email_service" in mocks

    def test_generate_assertions_for_success(self):
        """Test assertion generation for success cases"""
        then = "사용자 계정이 성공적으로 생성됨"
        assertions = TestScenarioParser._generate_assertions(then)

        assert any("success" in a for a in assertions)
        assert len(assertions) > 0

    def test_generate_assertions_for_error(self):
        """Test assertion generation for error cases"""
        then = "400 에러 반환 및 'Invalid email' 메시지"
        assertions = TestScenarioParser._generate_assertions(then)

        assert any("400" in a for a in assertions)


class TestTestCodeGenerator:
    """Test TestCodeGenerator"""

    def test_generate_test_file(self):
        """Test complete test file generation"""
        feature = FeatureSpec(
            id="F1",
            name="User Registration",
            description="User registration feature",
            priority="high",
            data_model={
                "entity": "User",
                "schema": {
                    "id": "UUID",
                    "email": "string",
                    "password_hash": "string"
                }
            }
        )

        parsed_scenarios = [
            ParsedTestScenario(
                scenario_id="F1_scenario_1",
                test_type="unit",
                description="Valid registration",
                given="Valid email and password",
                when="User submits registration form",
                then="User account created successfully",
                feature_id="F1",
                feature_name="User Registration",
                test_function_name="test_valid_registration_unit_1",
                fixtures_needed=["db_session", "api_client"],
                mocks_needed=["mock_email_service"],
                assertions=["assert result is not None", "assert result.status == 'success'"]
            ),
            ParsedTestScenario(
                scenario_id="F1_scenario_2",
                test_type="edge_case",
                description="Duplicate email",
                given="Email already exists",
                when="User tries to register with existing email",
                then="409 error returned",
                feature_id="F1",
                feature_name="User Registration",
                test_function_name="test_duplicate_email_edge_case_2",
                fixtures_needed=["db_session"],
                mocks_needed=[],
                assertions=["assert response.status_code == 409"]
            )
        ]

        golden_data = ConcretizedRequirement(
            system_scope=SystemScope(
                project_name="Auth System",
                purpose="User authentication"
            ),
            domain="E_COMMERCE"
        )

        generated = TestCodeGenerator.generate_test_file(
            feature, parsed_scenarios, golden_data
        )

        # Verify generated test
        assert isinstance(generated, GeneratedTest)
        assert generated.file_path.endswith(".py")
        assert generated.test_count == 2
        assert generated.feature_id == "F1"
        assert "unit" in generated.test_types
        assert "edge_case" in generated.test_types

        # Verify content structure
        content = generated.content
        assert '"""' in content  # Has docstring
        assert "import pytest" in content
        assert "def test_valid_registration_unit_1" in content
        assert "def test_duplicate_email_edge_case_2" in content
        assert "@pytest.mark.edge_case" in content

    def test_generate_header(self):
        """Test file header generation"""
        feature = FeatureSpec(
            id="F1",
            name="Test Feature",
            description="Test description",
            priority="high"
        )
        golden_data = ConcretizedRequirement(
            system_scope=SystemScope(
                project_name="Test Project",
                purpose="Testing"
            ),
            domain="TESTING"
        )

        header = TestCodeGenerator._generate_header(feature, golden_data)

        assert "Test Feature" in header
        assert "Test description" in header
        assert "Test Project" in header
        assert "TESTING" in header

    def test_generate_imports(self):
        """Test imports generation"""
        scenarios = [
            ParsedTestScenario(
                scenario_id="S1",
                test_type="unit",
                description="Test",
                given="",
                when="async call",
                then="",
                feature_id="F1",
                feature_name="Test"
            )
        ]

        imports = TestCodeGenerator._generate_imports(scenarios)

        assert "import pytest" in imports
        assert "from unittest.mock import" in imports
        assert "import asyncio" in imports  # Because when contains 'async'

    def test_generate_fixtures(self):
        """Test fixture generation"""
        scenarios = [
            ParsedTestScenario(
                scenario_id="S1",
                test_type="unit",
                description="Test",
                given="",
                when="",
                then="",
                feature_id="F1",
                feature_name="Test",
                fixtures_needed=["db_session", "api_client"]
            )
        ]

        feature = FeatureSpec(
            id="F1",
            name="Test",
            description="Test",
            data_model={
                "entity": "User",
                "schema": {"id": "UUID"}
            }
        )

        golden_data = ConcretizedRequirement(
            system_scope=SystemScope(project_name="Test", purpose="Test"),
            domain="TEST"
        )

        fixtures = TestCodeGenerator._generate_fixtures(scenarios, feature, golden_data)

        assert "@pytest.fixture" in fixtures
        assert "def db_session" in fixtures
        assert "def api_client" in fixtures

    def test_generate_test_function_unit(self):
        """Test unit test function generation"""
        scenario = ParsedTestScenario(
            scenario_id="S1",
            test_type="unit",
            description="Test user creation",
            given="Valid user data",
            when="create_user() is called",
            then="User is created in database",
            feature_id="F1",
            feature_name="User Management",
            test_function_name="test_user_creation_unit_1",
            fixtures_needed=["db_session"],
            mocks_needed=["mock_email_service"],
            assertions=["assert user is not None", "assert user.email == 'test@example.com'"]
        )

        feature = FeatureSpec(id="F1", name="Test", description="Test")

        function_code = TestCodeGenerator._generate_test_function(scenario, feature)

        assert "def test_user_creation_unit_1" in function_code
        assert "db_session" in function_code
        assert "mock_email_service" in function_code
        assert "Test user creation" in function_code
        assert "assert user is not None" in function_code

    def test_generate_test_function_async(self):
        """Test async test function generation"""
        scenario = ParsedTestScenario(
            scenario_id="S1",
            test_type="integration",
            description="Async API call",
            given="API is running",
            when="await api.call()",
            then="Response is received",
            feature_id="F1",
            feature_name="API",
            test_function_name="test_async_call_integration_1",
            fixtures_needed=["api_client"],
            mocks_needed=[],
            assertions=["assert response.status == 200"]
        )

        feature = FeatureSpec(id="F1", name="Test", description="Test")

        function_code = TestCodeGenerator._generate_test_function(scenario, feature)

        assert "@pytest.mark.asyncio" in function_code
        assert "@pytest.mark.integration" in function_code
        assert "async def test_async_call_integration_1" in function_code


class TestTDDRedEngine:
    """Test TDDRedEngine"""

    @pytest.mark.asyncio
    async def test_generate_tests_from_golden_data(self):
        """Test full test generation workflow"""
        # Create Golden Data with test scenarios
        feature_with_tests = FeatureSpec(
            id="F1",
            name="User Authentication",
            description="User login and registration",
            priority="high",
            test_scenarios=[
                {
                    "type": "unit",
                    "description": "정상 로그인",
                    "given": "유효한 이메일과 비밀번호",
                    "when": "로그인 API 호출",
                    "then": "JWT 토큰 발급 및 세션 생성"
                },
                {
                    "type": "edge_case",
                    "description": "잘못된 비밀번호",
                    "given": "올바른 이메일, 잘못된 비밀번호",
                    "when": "로그인 시도",
                    "then": "401 에러 반환"
                }
            ],
            data_model={
                "entity": "User",
                "schema": {"id": "UUID", "email": "string", "password_hash": "string"}
            }
        )

        golden_data = ConcretizedRequirement(
            system_scope=SystemScope(
                project_name="Auth System",
                purpose="User authentication system"
            ),
            features=[feature_with_tests],
            domain="AUTHENTICATION"
        )

        # Generate tests
        engine = TDDRedEngine()
        generated_tests = await engine.generate_tests(golden_data)

        # Verify results
        assert len(generated_tests) == 1

        test_file = generated_tests[0]
        assert test_file.test_count == 2
        assert test_file.feature_id == "F1"
        assert "unit" in test_file.test_types
        assert "edge_case" in test_file.test_types

        # Verify content
        assert "def test_" in test_file.content
        assert "@pytest.mark.edge_case" in test_file.content
        assert "import pytest" in test_file.content

    @pytest.mark.asyncio
    async def test_generate_tests_skips_features_without_scenarios(self):
        """Test that features without test_scenarios are skipped"""
        feature_no_tests = FeatureSpec(
            id="F1",
            name="Feature Without Tests",
            description="No test scenarios",
            test_scenarios=[]
        )

        golden_data = ConcretizedRequirement(
            system_scope=SystemScope(project_name="Test", purpose="Test"),
            features=[feature_no_tests],
            domain="TEST"
        )

        engine = TDDRedEngine()
        generated_tests = await engine.generate_tests(golden_data)

        assert len(generated_tests) == 0

    @pytest.mark.asyncio
    async def test_generate_tests_multiple_features(self):
        """Test generation for multiple features"""
        feature1 = FeatureSpec(
            id="F1",
            name="Feature 1",
            description="First feature",
            test_scenarios=[
                {
                    "type": "unit",
                    "description": "Test 1",
                    "given": "Given 1",
                    "when": "When 1",
                    "then": "Then 1"
                }
            ]
        )

        feature2 = FeatureSpec(
            id="F2",
            name="Feature 2",
            description="Second feature",
            test_scenarios=[
                {
                    "type": "integration",
                    "description": "Test 2",
                    "given": "Given 2",
                    "when": "When 2",
                    "then": "Then 2"
                }
            ]
        )

        golden_data = ConcretizedRequirement(
            system_scope=SystemScope(project_name="Multi-Feature", purpose="Test"),
            features=[feature1, feature2],
            domain="TEST"
        )

        engine = TDDRedEngine()
        generated_tests = await engine.generate_tests(golden_data)

        assert len(generated_tests) == 2
        assert generated_tests[0].feature_id == "F1"
        assert generated_tests[1].feature_id == "F2"


class TestGeneratedTestValidity:
    """Test that generated test code is valid Python"""

    @pytest.mark.asyncio
    async def test_generated_code_is_valid_python(self):
        """Test that generated test code can be compiled"""
        feature = FeatureSpec(
            id="F1",
            name="Sample Feature",
            description="Test feature",
            test_scenarios=[
                {
                    "type": "unit",
                    "description": "Sample test",
                    "given": "Sample given",
                    "when": "Sample when",
                    "then": "Sample then"
                }
            ]
        )

        golden_data = ConcretizedRequirement(
            system_scope=SystemScope(project_name="Test", purpose="Test"),
            features=[feature],
            domain="TEST"
        )

        engine = TDDRedEngine()
        generated_tests = await engine.generate_tests(golden_data)

        # Try to compile generated code
        test_code = generated_tests[0].content

        try:
            compile(test_code, "<generated>", "exec")
            compilation_success = True
        except SyntaxError as e:
            compilation_success = False
            print(f"Compilation error: {e}")
            print(f"Generated code:\n{test_code}")

        assert compilation_success, "Generated test code should be valid Python"
