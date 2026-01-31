"""
Automatic Test Scenario Generator

생성된 아티팩트를 분석하여 자동으로 테스트 시나리오와 테스트 코드를 생성합니다.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

from app.codegen.artifact_generator import GeneratedArtifact, ArtifactType
from app.utils.logger import get_logger

logger = get_logger("test_generator")


class TestLevel(str, Enum):
    """테스트 레벨"""
    UNIT = "unit"  # 단위 테스트
    INTEGRATION = "integration"  # 통합 테스트
    E2E = "e2e"  # End-to-End 테스트


class TestScenario(BaseModel):
    """테스트 시나리오"""
    scenario_id: str
    name: str
    description: str
    test_level: TestLevel
    artifact_type: ArtifactType
    test_cases: List[str] = Field(default=[])  # 테스트 케이스 설명 목록
    setup_required: List[str] = Field(default=[])  # 필요한 설정
    mocks_required: List[str] = Field(default=[])  # 필요한 Mock 객체


class GeneratedTest(BaseModel):
    """생성된 테스트 코드"""
    test_file_path: str
    test_code: str
    imports: List[str] = []
    fixtures: List[str] = []  # pytest fixture 코드
    test_count: int = 0


class TestScenarioGenerator:
    """
    테스트 시나리오 생성기

    아티팩트를 분석하여 테스트 시나리오와 테스트 코드를 자동 생성합니다.
    """

    def __init__(self):
        self.logger = logger

    def generate_scenarios(
        self,
        artifact: GeneratedArtifact,
        test_levels: Optional[List[TestLevel]] = None,
    ) -> List[TestScenario]:
        """
        아티팩트에 대한 테스트 시나리오를 생성합니다.

        Args:
            artifact: 생성된 아티팩트
            test_levels: 생성할 테스트 레벨 (기본: [UNIT, INTEGRATION])

        Returns:
            List[TestScenario]: 생성된 테스트 시나리오 목록
        """
        if test_levels is None:
            test_levels = [TestLevel.UNIT, TestLevel.INTEGRATION]

        self.logger.info(f"Generating test scenarios for {artifact.metadata.name}")

        scenarios = []

        # 아티팩트 타입별 시나리오 생성
        if artifact.metadata.type == ArtifactType.CREWAI_AGENT:
            scenarios.extend(self._generate_agent_scenarios(artifact, test_levels))

        elif artifact.metadata.type == ArtifactType.BACKEND_API:
            scenarios.extend(self._generate_api_scenarios(artifact, test_levels))

        elif artifact.metadata.type == ArtifactType.UI_COMPONENT:
            scenarios.extend(self._generate_ui_scenarios(artifact, test_levels))

        elif artifact.metadata.type == ArtifactType.DATABASE_SCHEMA:
            scenarios.extend(self._generate_db_scenarios(artifact, test_levels))

        self.logger.info(f"Generated {len(scenarios)} test scenarios")
        return scenarios

    def _generate_agent_scenarios(
        self,
        artifact: GeneratedArtifact,
        test_levels: List[TestLevel],
    ) -> List[TestScenario]:
        """CrewAI Agent 테스트 시나리오 생성"""
        scenarios = []

        # Unit Test 시나리오
        if TestLevel.UNIT in test_levels:
            scenarios.append(TestScenario(
                scenario_id=f"{artifact.metadata.name}_unit",
                name=f"{artifact.metadata.name} Unit Tests",
                description="Agent 및 Task의 기본 동작을 검증합니다.",
                test_level=TestLevel.UNIT,
                artifact_type=ArtifactType.CREWAI_AGENT,
                test_cases=[
                    "Agent 객체가 올바르게 생성되는지 확인",
                    "Agent의 role과 goal이 올바르게 설정되는지 확인",
                    "Task 객체가 올바르게 생성되는지 확인",
                    "Task의 description과 expected_output이 설정되는지 확인",
                ],
                setup_required=["CrewAI 설치", "테스트용 LLM 모델 Mock"],
                mocks_required=["ChatOpenAI", "LLM API 호출"],
            ))

        # Integration Test 시나리오
        if TestLevel.INTEGRATION in test_levels:
            scenarios.append(TestScenario(
                scenario_id=f"{artifact.metadata.name}_integration",
                name=f"{artifact.metadata.name} Integration Tests",
                description="Crew 전체 실행 및 Agent 간 협업을 검증합니다.",
                test_level=TestLevel.INTEGRATION,
                artifact_type=ArtifactType.CREWAI_AGENT,
                test_cases=[
                    "Crew가 정상적으로 kickoff되는지 확인",
                    "Task가 순차적으로 실행되는지 확인",
                    "Agent 간 context 전달이 올바른지 확인",
                    "최종 결과가 예상된 형식인지 확인",
                ],
                setup_required=["CrewAI 설치", "LLM API 키 설정"],
                mocks_required=["외부 도구 API (선택적)"],
            ))

        return scenarios

    def _generate_api_scenarios(
        self,
        artifact: GeneratedArtifact,
        test_levels: List[TestLevel],
    ) -> List[TestScenario]:
        """Backend API 테스트 시나리오 생성"""
        scenarios = []

        # Unit Test 시나리오
        if TestLevel.UNIT in test_levels:
            scenarios.append(TestScenario(
                scenario_id=f"{artifact.metadata.name}_unit",
                name=f"{artifact.metadata.name} Unit Tests",
                description="API 엔드포인트의 기본 동작을 검증합니다.",
                test_level=TestLevel.UNIT,
                artifact_type=ArtifactType.BACKEND_API,
                test_cases=[
                    "GET 엔드포인트가 200 OK를 반환하는지 확인",
                    "POST 엔드포인트가 요청을 올바르게 처리하는지 확인",
                    "유효하지 않은 입력에 대해 422 에러를 반환하는지 확인",
                    "응답 스키마가 예상과 일치하는지 확인",
                ],
                setup_required=["FastAPI 설치", "TestClient 설정"],
                mocks_required=["데이터베이스 (선택적)", "외부 API (선택적)"],
            ))

        # Integration Test 시나리오
        if TestLevel.INTEGRATION in test_levels:
            scenarios.append(TestScenario(
                scenario_id=f"{artifact.metadata.name}_integration",
                name=f"{artifact.metadata.name} Integration Tests",
                description="API와 데이터베이스 간 통합을 검증합니다.",
                test_level=TestLevel.INTEGRATION,
                artifact_type=ArtifactType.BACKEND_API,
                test_cases=[
                    "데이터 생성(POST)과 조회(GET)가 올바르게 동작하는지 확인",
                    "데이터 수정(PUT/PATCH)이 DB에 반영되는지 확인",
                    "데이터 삭제(DELETE)가 올바르게 동작하는지 확인",
                    "트랜잭션 롤백이 올바르게 동작하는지 확인",
                ],
                setup_required=["테스트 데이터베이스 설정", "Migration 실행"],
                mocks_required=[],
            ))

        return scenarios

    def _generate_ui_scenarios(
        self,
        artifact: GeneratedArtifact,
        test_levels: List[TestLevel],
    ) -> List[TestScenario]:
        """UI Component 테스트 시나리오 생성"""
        scenarios = []

        framework = artifact.metadata.framework

        if framework == "streamlit":
            # Streamlit UI 테스트
            if TestLevel.UNIT in test_levels:
                scenarios.append(TestScenario(
                    scenario_id=f"{artifact.metadata.name}_unit",
                    name=f"{artifact.metadata.name} Unit Tests",
                    description="Streamlit 컴포넌트의 렌더링을 검증합니다.",
                    test_level=TestLevel.UNIT,
                    artifact_type=ArtifactType.UI_COMPONENT,
                    test_cases=[
                        "페이지가 정상적으로 렌더링되는지 확인",
                        "입력 위젯이 올바르게 생성되는지 확인",
                        "버튼 클릭 이벤트가 처리되는지 확인",
                    ],
                    setup_required=["Streamlit 설치", "pytest-streamlit 설치"],
                    mocks_required=["Backend API 호출"],
                ))

        elif framework == "react":
            # React UI 테스트
            if TestLevel.UNIT in test_levels:
                scenarios.append(TestScenario(
                    scenario_id=f"{artifact.metadata.name}_unit",
                    name=f"{artifact.metadata.name} Unit Tests",
                    description="React 컴포넌트의 렌더링과 상호작용을 검증합니다.",
                    test_level=TestLevel.UNIT,
                    artifact_type=ArtifactType.UI_COMPONENT,
                    test_cases=[
                        "컴포넌트가 정상적으로 렌더링되는지 확인",
                        "State 변경이 올바르게 동작하는지 확인",
                        "이벤트 핸들러가 호출되는지 확인",
                        "props가 올바르게 전달되는지 확인",
                    ],
                    setup_required=["Jest 설치", "React Testing Library 설치"],
                    mocks_required=["API 호출", "외부 라이브러리"],
                ))

        return scenarios

    def _generate_db_scenarios(
        self,
        artifact: GeneratedArtifact,
        test_levels: List[TestLevel],
    ) -> List[TestScenario]:
        """Database Schema 테스트 시나리오 생성"""
        scenarios = []

        if TestLevel.UNIT in test_levels:
            scenarios.append(TestScenario(
                scenario_id=f"{artifact.metadata.name}_unit",
                name=f"{artifact.metadata.name} Unit Tests",
                description="데이터베이스 모델의 기본 동작을 검증합니다.",
                test_level=TestLevel.UNIT,
                artifact_type=ArtifactType.DATABASE_SCHEMA,
                test_cases=[
                    "모델이 정상적으로 생성되는지 확인",
                    "필드 타입이 올바르게 정의되는지 확인",
                    "관계(Relationship)가 올바르게 설정되는지 확인",
                    "제약 조건(Constraints)이 동작하는지 확인",
                ],
                setup_required=["테스트 데이터베이스 설정", "SQLAlchemy 설치"],
                mocks_required=[],
            ))

        if TestLevel.INTEGRATION in test_levels:
            scenarios.append(TestScenario(
                scenario_id=f"{artifact.metadata.name}_integration",
                name=f"{artifact.metadata.name} Integration Tests",
                description="데이터베이스 CRUD 작업을 검증합니다.",
                test_level=TestLevel.INTEGRATION,
                artifact_type=ArtifactType.DATABASE_SCHEMA,
                test_cases=[
                    "레코드 생성(Create)이 올바르게 동작하는지 확인",
                    "레코드 조회(Read)가 올바르게 동작하는지 확인",
                    "레코드 수정(Update)이 반영되는지 확인",
                    "레코드 삭제(Delete)가 올바르게 동작하는지 확인",
                ],
                setup_required=["테스트 데이터베이스", "Migration 실행"],
                mocks_required=[],
            ))

        return scenarios

    def generate_test_code(
        self,
        scenarios: List[TestScenario],
        artifact: GeneratedArtifact,
    ) -> GeneratedTest:
        """
        테스트 시나리오를 실제 pytest 코드로 변환합니다.

        Args:
            scenarios: 테스트 시나리오 목록
            artifact: 원본 아티팩트

        Returns:
            GeneratedTest: 생성된 테스트 코드
        """
        self.logger.info(f"Generating test code for {len(scenarios)} scenarios")

        test_code_lines = []
        imports = []
        fixtures = []

        # 기본 imports
        imports.extend([
            "import pytest",
            "from unittest.mock import Mock, patch, MagicMock",
        ])

        # 아티팩트 타입별 imports
        if artifact.metadata.type == ArtifactType.CREWAI_AGENT:
            imports.extend([
                "from crewai import Agent, Task, Crew",
            ])
        elif artifact.metadata.type == ArtifactType.BACKEND_API:
            imports.extend([
                "from fastapi.testclient import TestClient",
            ])
        elif artifact.metadata.type == ArtifactType.DATABASE_SCHEMA:
            imports.extend([
                "from sqlalchemy import create_engine",
                "from sqlalchemy.orm import sessionmaker",
            ])

        # Fixture 생성
        if artifact.metadata.type == ArtifactType.BACKEND_API:
            fixtures.append(self._generate_api_fixtures())
        elif artifact.metadata.type == ArtifactType.DATABASE_SCHEMA:
            fixtures.append(self._generate_db_fixtures())

        # 각 시나리오에 대한 테스트 코드 생성
        test_count = 0
        for scenario in scenarios:
            test_code_lines.append(f"\n# {scenario.name}")
            test_code_lines.append(f"# {scenario.description}\n")

            for idx, test_case in enumerate(scenario.test_cases):
                test_func_name = self._generate_test_function_name(scenario, idx)
                test_code = self._generate_test_function(
                    test_func_name,
                    test_case,
                    scenario,
                    artifact,
                )
                test_code_lines.append(test_code)
                test_count += 1

        # 최종 코드 조립
        final_code = "\n".join(imports)
        final_code += "\n\n"

        if fixtures:
            final_code += "\n\n".join(fixtures)
            final_code += "\n\n"

        final_code += "\n".join(test_code_lines)

        # 테스트 파일 경로
        test_file_path = f"tests/test_{artifact.metadata.name}.py"

        return GeneratedTest(
            test_file_path=test_file_path,
            test_code=final_code,
            imports=imports,
            fixtures=fixtures,
            test_count=test_count,
        )

    def _generate_test_function_name(self, scenario: TestScenario, idx: int) -> str:
        """테스트 함수 이름 생성"""
        base_name = scenario.scenario_id.replace("-", "_")
        return f"test_{base_name}_{idx + 1}"

    def _generate_test_function(
        self,
        func_name: str,
        test_case: str,
        scenario: TestScenario,
        artifact: GeneratedArtifact,
    ) -> str:
        """개별 테스트 함수 코드 생성"""
        code_lines = [
            f"def {func_name}():",
            f'    """',
            f'    {test_case}',
            f'    """',
        ]

        # 아티팩트 타입별 테스트 코드
        if artifact.metadata.type == ArtifactType.CREWAI_AGENT:
            code_lines.extend([
                "    # TODO: Implement test logic",
                "    # 예: agent = Agent(role='...', goal='...')",
                "    # assert agent.role == '...'",
                "    pass",
            ])
        elif artifact.metadata.type == ArtifactType.BACKEND_API:
            code_lines.extend([
                "    # TODO: Implement test logic",
                "    # 예: response = client.get('/endpoint')",
                "    # assert response.status_code == 200",
                "    pass",
            ])
        elif artifact.metadata.type == ArtifactType.DATABASE_SCHEMA:
            code_lines.extend([
                "    # TODO: Implement test logic",
                "    # 예: record = Model(name='test')",
                "    # assert record.name == 'test'",
                "    pass",
            ])
        else:
            code_lines.extend([
                "    # TODO: Implement test logic",
                "    pass",
            ])

        return "\n".join(code_lines) + "\n"

    def _generate_api_fixtures(self) -> str:
        """FastAPI 테스트 fixture 생성"""
        return """
@pytest.fixture
def client():
    \"\"\"FastAPI TestClient fixture\"\"\"
    from app import app  # 실제 앱 import 경로로 수정 필요
    return TestClient(app)

@pytest.fixture
def mock_db():
    \"\"\"Mock database fixture\"\"\"
    return MagicMock()
"""

    def _generate_db_fixtures(self) -> str:
        """Database 테스트 fixture 생성"""
        return """
@pytest.fixture
def db_session():
    \"\"\"테스트 데이터베이스 세션 fixture\"\"\"
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # 테이블 생성
    # Base.metadata.create_all(bind=engine)

    yield session

    session.close()
"""
