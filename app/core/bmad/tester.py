"""
CAAS BMAD Test Generator

자동 테스트 생성 및 실행을 수행합니다.
pytest 기반 테스트를 생성하고 실행합니다.
"""

import subprocess
import tempfile
from typing import Any, Dict, List
from pathlib import Path

from app.utils.logger import get_logger, LoggerMixin

logger = get_logger("bmad.tester")


class TestResult:
    """테스트 실행 결과"""

    def __init__(self):
        self.success = False
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        self.test_files: List[str] = []
        self.failures: List[Dict[str, str]] = []
        self.stdout = ""
        self.stderr = ""
        self.duration = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "success": self.success,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "test_files": self.test_files,
            "failures": self.failures,
            "duration": self.duration,
        }


class TestGenerator(LoggerMixin):
    """
    테스트 생성 및 실행기

    pytest 테스트를 자동 생성하고 실행합니다.
    """

    def __init__(self):
        pass

    def generate_tests(
        self,
        project_name: str,
        agent_specs: List[Dict[str, Any]],
        task_specs: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """
        프로젝트 테스트 생성

        Args:
            project_name: 프로젝트 이름
            agent_specs: 에이전트 스펙 목록
            task_specs: 태스크 스펙 목록

        Returns:
            Dict[str, str]: 테스트 파일명 -> 코드 매핑
        """
        test_files = {}

        # 1. 에이전트 테스트 생성
        test_files["tests/test_agents.py"] = self._generate_agent_tests(
            project_name, agent_specs
        )

        # 2. 태스크 테스트 생성
        test_files["tests/test_tasks.py"] = self._generate_task_tests(
            project_name, task_specs
        )

        # 3. 통합 테스트 생성
        test_files["tests/test_integration.py"] = self._generate_integration_tests(
            project_name, agent_specs, task_specs
        )

        # 4. conftest.py 생성 (pytest 설정)
        test_files["tests/conftest.py"] = self._generate_conftest()

        # 5. __init__.py 생성
        test_files["tests/__init__.py"] = '"""Tests for {project_name}"""\n'

        self.logger.info(f"테스트 파일 {len(test_files)}개 생성 완료")
        return test_files

    def _generate_agent_tests(
        self,
        project_name: str,
        agent_specs: List[Dict[str, Any]],
    ) -> str:
        """에이전트 테스트 생성"""
        test_code = f'''"""
Agent Tests for {project_name}

Tests for individual agents.
"""

import pytest
from crewai import Agent


class TestAgents:
    """Agent tests"""

'''

        for agent in agent_specs:
            agent_id = agent.get("id", "unknown")
            role = agent.get("role", "Unknown")

            test_code += f'''    def test_{agent_id}_creation(self):
        """Test {agent_id} agent creation"""
        agent = Agent(
            role="{role}",
            goal="{agent.get('goal', '')}",
            backstory="{agent.get('backstory', '')}",
            verbose=True,
        )

        assert agent.role == "{role}"
        assert agent.goal is not None
        assert agent.backstory is not None

    def test_{agent_id}_has_required_attributes(self):
        """Test {agent_id} has required attributes"""
        agent = Agent(
            role="{role}",
            goal="{agent.get('goal', '')}",
            backstory="{agent.get('backstory', '')}",
        )

        assert hasattr(agent, 'role')
        assert hasattr(agent, 'goal')
        assert hasattr(agent, 'backstory')

'''

        return test_code

    def _generate_task_tests(
        self,
        project_name: str,
        task_specs: List[Dict[str, Any]],
    ) -> str:
        """태스크 테스트 생성"""
        test_code = f'''"""
Task Tests for {project_name}

Tests for individual tasks.
"""

import pytest
from crewai import Task, Agent


class TestTasks:
    """Task tests"""

    @pytest.fixture
    def dummy_agent(self):
        """Dummy agent for testing"""
        return Agent(
            role="Test Agent",
            goal="Test goal",
            backstory="Test backstory",
        )

'''

        for task in task_specs:
            task_id = task.get("id", "unknown")
            description = task.get("description", "")[:100]  # 처음 100자만

            test_code += f'''    def test_{task_id}_creation(self, dummy_agent):
        """Test {task_id} task creation"""
        task = Task(
            description="{description}...",
            expected_output="{task.get('expected_output', '')}",
            agent=dummy_agent,
        )

        assert task.description is not None
        assert task.expected_output is not None
        assert task.agent is not None

'''

        return test_code

    def _generate_integration_tests(
        self,
        project_name: str,
        agent_specs: List[Dict[str, Any]],
        task_specs: List[Dict[str, Any]],
    ) -> str:
        """통합 테스트 생성"""
        test_code = f'''"""
Integration Tests for {project_name}

Tests for the complete crew workflow.
"""

import pytest
from crewai import Agent, Task, Crew


class TestIntegration:
    """Integration tests"""

    @pytest.fixture
    def crew_setup(self):
        """Setup crew with all agents and tasks"""
        # Create agents
        agents = []
'''

        # 에이전트 생성
        for agent in agent_specs:
            test_code += f'''        agents.append(Agent(
            role="{agent.get('role', '')}",
            goal="{agent.get('goal', '')}",
            backstory="{agent.get('backstory', '')}",
        ))
'''

        test_code += '''
        # Create tasks
        tasks = []
'''

        # 태스크 생성 (에이전트 매핑)
        for i, task in enumerate(task_specs):
            test_code += f'''        tasks.append(Task(
            description="{task.get('description', '')[:100]}...",
            expected_output="{task.get('expected_output', '')}",
            agent=agents[{min(i, len(agent_specs) - 1)}],
        ))
'''

        test_code += '''
        return {"agents": agents, "tasks": tasks}

    def test_crew_creation(self, crew_setup):
        """Test crew can be created with all agents and tasks"""
        crew = Crew(
            agents=crew_setup["agents"],
            tasks=crew_setup["tasks"],
            verbose=True,
        )

        assert len(crew.agents) > 0
        assert len(crew.tasks) > 0

    def test_crew_has_all_components(self, crew_setup):
        """Test crew has all required components"""
        crew = Crew(
            agents=crew_setup["agents"],
            tasks=crew_setup["tasks"],
        )

        assert hasattr(crew, 'agents')
        assert hasattr(crew, 'tasks')
        assert len(crew.agents) == len(crew_setup["agents"])
        assert len(crew.tasks) == len(crew_setup["tasks"])

    @pytest.mark.slow
    def test_crew_execution_mock(self, crew_setup, monkeypatch):
        """Test crew execution (mocked to avoid actual LLM calls)"""
        # This test would mock LLM calls in a real scenario
        crew = Crew(
            agents=crew_setup["agents"],
            tasks=crew_setup["tasks"],
        )

        # In a real test, you would mock the kickoff method
        # For now, just verify the crew is properly configured
        assert crew is not None
'''

        return test_code

    def _generate_conftest(self) -> str:
        """pytest conftest.py 생성"""
        return '''"""
pytest configuration for the test suite
"""

import pytest


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


@pytest.fixture(scope="session")
def project_config():
    """Project configuration fixture"""
    return {
        "name": "test_project",
        "version": "0.1.0",
    }
'''

    def run_tests(
        self,
        code_files: Dict[str, str],
        test_files: Dict[str, str],
        timeout: int = 60,
    ) -> TestResult:
        """
        테스트 실행

        Args:
            code_files: 프로젝트 코드 파일
            test_files: 테스트 파일
            timeout: 실행 시간 제한 (초)

        Returns:
            TestResult: 테스트 결과
        """
        result = TestResult()

        # 임시 디렉토리에 파일 작성
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # 프로젝트 코드 작성
            for filename, code in code_files.items():
                file_path = tmp_path / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(code, encoding="utf-8")

            # 테스트 코드 작성
            for filename, code in test_files.items():
                file_path = tmp_path / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(code, encoding="utf-8")

            result.test_files = list(test_files.keys())

            # pytest 실행
            self.logger.info(f"pytest 실행: {tmpdir}")

            try:
                # pytest with json report
                cmd = [
                    "python", "-m", "pytest",
                    str(tmp_path / "tests"),
                    "-v",
                    "--tb=short",
                    "-m", "not slow",  # 느린 테스트는 스킵
                ]

                process = subprocess.run(
                    cmd,
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                result.stdout = process.stdout
                result.stderr = process.stderr

                # 결과 파싱
                self._parse_pytest_output(process.stdout, result)

                result.success = process.returncode == 0

                self.logger.info(
                    f"테스트 완료: {result.passed_tests}/{result.total_tests} passed"
                )

            except subprocess.TimeoutExpired:
                self.logger.error(f"테스트 타임아웃 ({timeout}초)")
                result.success = False
                result.stderr = f"Test execution timed out after {timeout} seconds"

            except FileNotFoundError:
                self.logger.error("pytest를 찾을 수 없습니다. pip install pytest")
                result.success = False
                result.stderr = "pytest not found. Install with: pip install pytest"

            except Exception as e:
                self.logger.error(f"테스트 실행 실패: {e}")
                result.success = False
                result.stderr = str(e)

        return result

    def _parse_pytest_output(self, output: str, result: TestResult):
        """
        pytest 출력 파싱

        Args:
            output: pytest stdout
            result: 테스트 결과
        """
        lines = output.split("\n")

        for line in lines:
            # 테스트 요약 라인 파싱
            # 예: "====== 3 passed, 1 failed in 0.50s ======"
            if " passed" in line or " failed" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed":
                        try:
                            result.passed_tests = int(parts[i - 1])
                        except (ValueError, IndexError):
                            pass
                    elif part == "failed":
                        try:
                            result.failed_tests = int(parts[i - 1])
                        except (ValueError, IndexError):
                            pass
                    elif part == "skipped":
                        try:
                            result.skipped_tests = int(parts[i - 1])
                        except (ValueError, IndexError):
                            pass

            # 실패한 테스트 추출
            if "FAILED" in line:
                result.failures.append({
                    "test": line.strip(),
                    "message": "Test failed",
                })

        result.total_tests = result.passed_tests + result.failed_tests + result.skipped_tests
