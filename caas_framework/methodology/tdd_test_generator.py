"""
TDD RED Phase: Test Generation from Golden Data (CAAS-E Week 3)

Automatically generates executable pytest tests from Golden Data test_scenarios.
Supports Given-When-Then format and multiple test types (unit, integration, edge_case).

Author: CAAS Framework Team
Version: 0.6.0 (CAAS-E Implementation)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import re
from caas_framework.models.specifications import ConcretizedRequirement, FeatureSpec
from caas_framework.plugins.llm.base import LLMPlugin
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParsedTestScenario:
    """Parsed test scenario with structured data"""
    scenario_id: str
    test_type: str  # unit, integration, edge_case
    description: str
    given: str  # Preconditions
    when: str   # Action
    then: str   # Expected result
    feature_id: str
    feature_name: str

    # Generated test metadata
    test_function_name: str = ""
    fixtures_needed: List[str] = field(default_factory=list)
    mocks_needed: List[str] = field(default_factory=list)
    assertions: List[str] = field(default_factory=list)


@dataclass
class GeneratedTest:
    """Generated test file with metadata"""
    file_path: str
    content: str
    test_count: int
    fixture_count: int
    feature_id: str
    test_types: List[str]  # Types of tests in this file


class TestScenarioParser:
    """
    Parses Given-When-Then test scenarios into structured data

    Extracts:
    - Test function names from descriptions
    - Required fixtures from given/when clauses
    - Mock objects needed
    - Assertions from then clause
    """

    @staticmethod
    def parse_scenario(
        scenario: Dict[str, Any],
        feature: FeatureSpec,
        scenario_index: int
    ) -> ParsedTestScenario:
        """
        Parse a single test scenario

        Args:
            scenario: Test scenario dict with type, description, given, when, then
            feature: Parent feature spec
            scenario_index: Index for unique ID generation

        Returns:
            ParsedTestScenario with structured test data
        """
        # Extract basic info
        test_type = scenario.get("type", "unit")
        description = scenario.get("description", f"Test {scenario_index + 1}")
        given = scenario.get("given", "")
        when = scenario.get("when", "")
        then = scenario.get("then", "")

        # Generate test function name
        test_function_name = TestScenarioParser._generate_test_name(
            description, test_type, scenario_index
        )

        # Analyze fixtures needed
        fixtures_needed = TestScenarioParser._extract_fixtures(given, when, feature)

        # Analyze mocks needed
        mocks_needed = TestScenarioParser._extract_mocks(given, when, test_type)

        # Generate assertions from "then" clause
        assertions = TestScenarioParser._generate_assertions(then)

        return ParsedTestScenario(
            scenario_id=f"{feature.id}_scenario_{scenario_index + 1}",
            test_type=test_type,
            description=description,
            given=given,
            when=when,
            then=then,
            feature_id=feature.id,
            feature_name=feature.name,
            test_function_name=test_function_name,
            fixtures_needed=fixtures_needed,
            mocks_needed=mocks_needed,
            assertions=assertions
        )

    @staticmethod
    def _generate_test_name(description: str, test_type: str, index: int) -> str:
        """Generate valid pytest function name from description"""
        # Convert to snake_case
        name = re.sub(r'[^\w\s가-힣]', '', description)  # Remove special chars
        name = re.sub(r'\s+', '_', name.strip())  # Replace spaces with underscore
        name = name.lower()

        # Transliterate Korean to English (simple mapping)
        name = TestScenarioParser._transliterate_korean(name)

        # Ensure it starts with test_
        if not name.startswith("test_"):
            name = f"test_{name}"

        # Add type suffix for clarity
        type_suffix = f"_{test_type}" if test_type != "unit" else ""

        # Limit length and add index
        name = name[:50]  # Max 50 chars
        return f"{name}{type_suffix}_{index + 1}"

    @staticmethod
    def _transliterate_korean(text: str) -> str:
        """Simple Korean to English transliteration"""
        # Basic mapping (extend as needed)
        korean_map = {
            '정상': 'normal',
            '회원가입': 'registration',
            '로그인': 'login',
            '이메일': 'email',
            '비밀번호': 'password',
            '인증': 'verification',
            '중복': 'duplicate',
            '검증': 'validation',
            '실패': 'failure',
            '성공': 'success',
            '테스트': 'test',
            '사용자': 'user',
            '등록': 'register',
            '생성': 'create',
            '삭제': 'delete',
            '수정': 'update',
            '조회': 'read',
            '목록': 'list',
        }

        for korean, english in korean_map.items():
            text = text.replace(korean, english)

        # Remove remaining Korean characters
        text = re.sub(r'[가-힣]', '', text)
        text = re.sub(r'_+', '_', text)  # Remove duplicate underscores

        return text.strip('_')

    @staticmethod
    def _extract_fixtures(given: str, when: str, feature: FeatureSpec) -> List[str]:
        """Extract pytest fixtures needed based on given/when clauses"""
        fixtures = []

        # Check for database fixtures
        if any(keyword in given.lower() or keyword in when.lower()
               for keyword in ['database', 'db', '데이터베이스', '저장']):
            fixtures.append("db_session")

        # Check for API client fixtures
        if any(keyword in when.lower()
               for keyword in ['api', 'endpoint', 'request', '호출']):
            fixtures.append("api_client")

        # Check for user/auth fixtures
        if any(keyword in given.lower()
               for keyword in ['user', 'authenticated', '사용자', '인증된']):
            fixtures.append("authenticated_user")

        # Check for data model fixtures (from feature's data_model)
        if feature.data_model:
            entity = feature.data_model.get("entity", "").lower()
            if entity and entity in given.lower():
                fixtures.append(f"sample_{entity.lower()}")

        return list(set(fixtures))  # Remove duplicates

    @staticmethod
    def _extract_mocks(given: str, when: str, test_type: str) -> List[str]:
        """Extract mock objects needed based on test type and clauses"""
        mocks = []

        # Unit tests typically need more mocks
        if test_type == "unit":
            # Check for external service mocks
            if any(keyword in when.lower()
                   for keyword in ['email', 'send', 'notification', '이메일', '발송']):
                mocks.append("mock_email_service")

            if any(keyword in when.lower()
                   for keyword in ['payment', 'charge', '결제', '청구']):
                mocks.append("mock_payment_gateway")

            if any(keyword in when.lower()
                   for keyword in ['storage', 'file', 'upload', '파일', '업로드']):
                mocks.append("mock_storage_service")

        # Integration tests may need fewer mocks
        elif test_type == "integration":
            # Only mock external services, not internal components
            if any(keyword in when.lower()
                   for keyword in ['external', 'third-party', '외부']):
                mocks.append("mock_external_api")

        return mocks

    @staticmethod
    def _generate_assertions(then: str) -> List[str]:
        """Generate assertion statements from then clause"""
        assertions = []

        # Parse expected outcomes
        then_lower = then.lower()

        # Check for success/creation
        if any(keyword in then_lower
               for keyword in ['created', 'success', '생성', '성공']):
            assertions.append("assert result is not None")
            assertions.append("assert result.status == 'success'")

        # Check for error cases
        if any(keyword in then_lower
               for keyword in ['error', 'fail', 'exception', '에러', '실패']):
            # Extract error code if present
            error_code_match = re.search(r'(\d{3})', then)
            if error_code_match:
                code = error_code_match.group(1)
                assertions.append(f"assert response.status_code == {code}")
            else:
                assertions.append("assert 'error' in response")

        # Check for return values
        if '반환' in then or 'return' in then_lower:
            assertions.append("assert result is not None")

        # Check for state changes
        if any(keyword in then_lower
               for keyword in ['변경', 'updated', 'modified', '수정']):
            assertions.append("assert object.state_changed == True")

        # Default assertion if none found
        if not assertions:
            assertions.append("assert True  # TODO: Add specific assertion")

        return assertions


class TestCodeGenerator:
    """
    Generates pytest code from parsed test scenarios

    Creates:
    - Test functions with proper pytest decorators
    - Fixture definitions
    - Mock setups
    - Assertions
    """

    @staticmethod
    def generate_test_file(
        feature: FeatureSpec,
        parsed_scenarios: List[ParsedTestScenario],
        golden_data: ConcretizedRequirement
    ) -> GeneratedTest:
        """
        Generate complete pytest test file for a feature

        Args:
            feature: Feature specification
            parsed_scenarios: List of parsed test scenarios
            golden_data: Full golden data context

        Returns:
            GeneratedTest with file path and content
        """
        # Build file path
        feature_name_snake = TestScenarioParser._transliterate_korean(
            feature.name.lower().replace(' ', '_')
        )
        file_path = f"tests/test_{feature_name_snake}.py"

        # Generate file content
        content_parts = []

        # 1. File header
        content_parts.append(TestCodeGenerator._generate_header(feature, golden_data))

        # 2. Imports
        content_parts.append(TestCodeGenerator._generate_imports(parsed_scenarios))

        # 3. Fixtures
        fixtures_code = TestCodeGenerator._generate_fixtures(
            parsed_scenarios, feature, golden_data
        )
        if fixtures_code:
            content_parts.append("\n# Fixtures\n")
            content_parts.append(fixtures_code)

        # 4. Test functions
        content_parts.append("\n# Test Functions\n")
        for scenario in parsed_scenarios:
            test_func = TestCodeGenerator._generate_test_function(scenario, feature)
            content_parts.append(test_func)
            content_parts.append("\n")

        content = "\n".join(content_parts)

        # Count test types
        test_types = list(set(s.test_type for s in parsed_scenarios))

        # Count unique fixtures
        all_fixtures = set()
        for scenario in parsed_scenarios:
            all_fixtures.update(scenario.fixtures_needed)

        return GeneratedTest(
            file_path=file_path,
            content=content,
            test_count=len(parsed_scenarios),
            fixture_count=len(all_fixtures),
            feature_id=feature.id,
            test_types=test_types
        )

    @staticmethod
    def _generate_header(feature: FeatureSpec, golden_data: ConcretizedRequirement) -> str:
        """Generate file docstring header"""
        return f'''"""
Tests for {feature.name}

Feature: {feature.description}
Priority: {feature.priority}

Generated from Golden Data test scenarios (CAAS-E TDD RED Phase)
Project: {golden_data.project_name}
Domain: {golden_data.domain}
"""
'''

    @staticmethod
    def _generate_imports(parsed_scenarios: List[ParsedTestScenario]) -> str:
        """Generate import statements"""
        imports = [
            "import pytest",
            "from unittest.mock import Mock, AsyncMock, patch",
        ]

        # Check if async tests are needed
        has_async = any('async' in s.when.lower() or 'await' in s.when.lower()
                       for s in parsed_scenarios)

        if has_async:
            imports.append("import asyncio")

        return "\n".join(imports) + "\n"

    @staticmethod
    def _generate_fixtures(
        scenarios: List[ParsedTestScenario],
        feature: FeatureSpec,
        golden_data: ConcretizedRequirement
    ) -> str:
        """Generate pytest fixture definitions"""
        # Collect all unique fixtures needed
        all_fixtures = set()
        for scenario in scenarios:
            all_fixtures.update(scenario.fixtures_needed)

        if not all_fixtures:
            return ""

        fixture_codes = []

        # Generate each fixture
        if "db_session" in all_fixtures:
            fixture_codes.append('''
@pytest.fixture
def db_session():
    """Mock database session"""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.query = Mock()
    return session
''')

        if "api_client" in all_fixtures:
            fixture_codes.append('''
@pytest.fixture
def api_client():
    """Mock API client"""
    from fastapi.testclient import TestClient
    # TODO: Import your actual app
    # from app.main import app
    # return TestClient(app)
    return Mock()  # Placeholder
''')

        if "authenticated_user" in all_fixtures:
            fixture_codes.append('''
@pytest.fixture
def authenticated_user():
    """Mock authenticated user"""
    user = Mock()
    user.id = "user_123"
    user.email = "test@example.com"
    user.is_authenticated = True
    return user
''')

        # Generate data model fixtures
        if feature.data_model:
            entity = feature.data_model.get("entity", "Object")
            fixture_name = f"sample_{entity.lower()}"
            if fixture_name in all_fixtures:
                schema = feature.data_model.get("schema", {})
                sample_data = TestCodeGenerator._generate_sample_data(schema)
                fixture_codes.append(f'''
@pytest.fixture
def {fixture_name}():
    """Sample {entity} for testing"""
    return {sample_data}
''')

        return "\n".join(fixture_codes)

    @staticmethod
    def _generate_sample_data(schema: Dict[str, str]) -> str:
        """Generate sample data dict from schema"""
        sample = {}
        for field, field_type in schema.items():
            if 'uuid' in field_type.lower() or field == 'id':
                sample[field] = '"' + 'test_id_123' + '"'
            elif 'string' in field_type.lower() or 'str' in field_type.lower():
                sample[field] = f'"test_{field}"'
            elif 'int' in field_type.lower():
                sample[field] = '123'
            elif 'bool' in field_type.lower():
                sample[field] = 'True'
            elif 'datetime' in field_type.lower():
                sample[field] = '"2024-01-01T00:00:00"'
            else:
                sample[field] = 'None'

        return "{" + ", ".join(f'"{k}": {v}' for k, v in sample.items()) + "}"

    @staticmethod
    def _generate_test_function(scenario: ParsedTestScenario, feature: FeatureSpec) -> str:
        """Generate single test function"""
        # Build function signature
        params = ["self"] if scenario.fixtures_needed else []
        params.extend(scenario.fixtures_needed)
        params.extend(scenario.mocks_needed)

        params_str = ", ".join(params) if params else ""

        # Build decorators
        decorators = []
        if scenario.test_type == "integration":
            decorators.append("@pytest.mark.integration")
        elif scenario.test_type == "edge_case":
            decorators.append("@pytest.mark.edge_case")

        # Check if async
        is_async = 'async' in scenario.when.lower() or 'await' in scenario.when.lower()
        if is_async:
            decorators.append("@pytest.mark.asyncio")
            async_keyword = "async "
        else:
            async_keyword = ""

        decorators_str = "\n    ".join(decorators) if decorators else ""

        # Build docstring
        docstring = f'''"""
    {scenario.description}

    Given: {scenario.given}
    When: {scenario.when}
    Then: {scenario.then}
    """'''

        # Build test body
        arrange = f"# Arrange: {scenario.given}"
        act = f"# Act: {scenario.when}\n    # TODO: Implement action"
        assert_section = "# Assert: " + scenario.then + "\n    " + "\n    ".join(scenario.assertions)

        # Combine all parts
        function_code = f'''
{decorators_str}
{async_keyword}def {scenario.test_function_name}({params_str}):
    {docstring}
    {arrange}

    {act}

    {assert_section}
'''

        return function_code


class TDDRedEngine:
    """
    TDD RED Phase Engine

    Orchestrates test generation from Golden Data:
    1. Parse test scenarios from features
    2. Generate pytest test files
    3. Create fixtures and mocks
    4. Output executable test suite
    """

    def __init__(self, llm_plugin: Optional[LLMPlugin] = None):
        """
        Args:
            llm_plugin: Optional LLM for enhancing test generation
        """
        self.llm = llm_plugin
        self.parser = TestScenarioParser()
        self.generator = TestCodeGenerator()
        self.logger = logging.getLogger(self.__class__.__name__)

    async def generate_tests(
        self,
        golden_data: ConcretizedRequirement,
        output_dir: str = "generated_tests"
    ) -> List[GeneratedTest]:
        """
        Generate all tests from Golden Data

        Args:
            golden_data: ConcretizedRequirement with test_scenarios
            output_dir: Output directory for test files

        Returns:
            List of GeneratedTest objects
        """
        generated_tests = []

        for feature in golden_data.features:
            if not feature.test_scenarios:
                self.logger.warning(f"Feature {feature.id} has no test scenarios, skipping")
                continue

            # Parse all scenarios for this feature
            parsed_scenarios = []
            for idx, scenario in enumerate(feature.test_scenarios):
                parsed = self.parser.parse_scenario(scenario, feature, idx)
                parsed_scenarios.append(parsed)

            # Generate test file
            test_file = self.generator.generate_test_file(
                feature, parsed_scenarios, golden_data
            )

            generated_tests.append(test_file)

            self.logger.info(
                f"Generated {test_file.test_count} tests for feature {feature.id} "
                f"({', '.join(test_file.test_types)})"
            )

        return generated_tests

    def save_tests(self, generated_tests: List[GeneratedTest], base_dir: str):
        """
        Save generated tests to files

        Args:
            generated_tests: List of GeneratedTest objects
            base_dir: Base directory for output
        """
        import os

        for test in generated_tests:
            full_path = os.path.join(base_dir, test.file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(test.content)

            self.logger.info(f"Saved {test.test_count} tests to {full_path}")
