"""
BDD Test Generator (Behavior-Driven Development)

테스트 코드 우선 생성 - 테스트 시나리오에서 pytest 코드 생성

This module generates test code from BDD-style test scenarios (Given-When-Then).
Renamed from test_generator.py to bdd_test_generator.py to distinguish from TDD test generator.

Classes:
    - TestFirstGenerator: Generate pytest tests from BDD scenarios (~170 lines)
    - TestCodeResult: Result model for generated test code
"""

from typing import List

from pydantic import BaseModel

from .test_scenario import TestScenario


class TestCodeResult(BaseModel):
    """테스트 코드 생성 결과"""

    test_file_path: str
    test_code: str
    scenario_count: int
    framework: str = "pytest"


class TestFirstGenerator:
    """테스트 우선 생성기"""

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: LLM 클라이언트 (선택적)
        """
        self.llm = llm_client

    def generate_test_code(
        self,
        scenarios: List[TestScenario],
        entity_name: str,
        framework: str = "pytest",
    ) -> TestCodeResult:
        """
        테스트 시나리오에서 테스트 코드 생성

        Args:
            scenarios: 테스트 시나리오 목록
            entity_name: 엔티티 이름 (예: "Task", "User")
            framework: 테스트 프레임워크 (pytest, unittest)

        Returns:
            TestCodeResult
        """

        if framework == "pytest":
            test_code = self._generate_pytest_code(scenarios, entity_name)
            test_file_path = f"tests/test_{entity_name.lower()}.py"
        else:
            raise ValueError(f"Unsupported framework: {framework}")

        return TestCodeResult(
            test_file_path=test_file_path,
            test_code=test_code,
            scenario_count=len(scenarios),
            framework=framework,
        )

    def _generate_pytest_code(self, scenarios: List[TestScenario], entity: str) -> str:
        """Pytest 코드 생성"""

        entity_lower = entity.lower()
        entity_title = entity.title()

        # 헤더
        code = f'''"""
Test Suite for {entity_title}

Auto-generated from test scenarios.
"""

import pytest
from backend.crud import (
    create_{entity_lower},
    get_{entity_lower},
    get_{entity_lower}s,
    update_{entity_lower},
    delete_{entity_lower},
)
from backend.schemas import {entity_title}Create, {entity_title}Update
from backend.database import SessionLocal
from backend.models import {entity_title}


@pytest.fixture
def db():
    """Database fixture"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_{entity_lower}(db):
    """Sample {entity_lower} fixture"""
    {entity_lower}_data = {entity_title}Create(
        # TODO: Add sample data based on your schema
    )
    {entity_lower} = create_{entity_lower}(db, {entity_lower}_data)
    yield {entity_lower}
    # Cleanup
    delete_{entity_lower}(db, {entity_lower}.id)


'''

        # 각 시나리오에 대한 테스트 함수 생성
        for scenario in scenarios:
            code += self._generate_test_function(scenario, entity_lower)
            code += "\n\n"

        return code

    def _generate_test_function(self, scenario: TestScenario, entity: str) -> str:
        """단일 테스트 함수 생성"""

        # 함수명 생성 (시나리오 ID 기반)
        func_name = f"test_{scenario.scenario_id}"

        # Docstring
        docstring = f'"""{scenario.description}"""'

        # Given-When-Then 코멘트
        given_comments = "\n    ".join([f"# Given: {g}" for g in scenario.bdd.given])
        when_comments = "\n    ".join([f"# When: {w}" for w in scenario.bdd.when])
        then_comments = "\n    ".join([f"# Then: {t}" for t in scenario.bdd.then])

        # 테스트 본문 (템플릿)
        body = f"""    # Arrange
    {given_comments}
    # TODO: Setup test data

    # Act
    {when_comments}
    # TODO: Execute the action

    # Assert
    {then_comments}
    # TODO: Add assertions
    assert True  # Placeholder - replace with actual assertion"""

        return f"def {func_name}(db):\n    {docstring}\n{body}"


def generate_test_code(
    scenarios: List[TestScenario], entity_name: str, framework: str = "pytest"
) -> TestCodeResult:
    """
    Helper function - 테스트 코드 생성

    Args:
        scenarios: 테스트 시나리오
        entity_name: 엔티티 이름
        framework: 테스트 프레임워크

    Returns:
        TestCodeResult
    """
    generator = TestFirstGenerator()
    return generator.generate_test_code(scenarios, entity_name, framework)
