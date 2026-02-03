"""
Integration test for BMAD Engine with ProjectBootstrapper

Tests that BMAD Engine can successfully bootstrap a complete project.
"""

import json

import pytest

from caas_framework.automation import BootstrapResult
from caas_framework.bmad.engine import BMADEngine, BMADResult
from caas_framework.models.specifications import (
    ConcretizedRequirement,
    FeatureSpec,
    SystemScope,
)


# Mock LLM for testing
class MockLLM:
    """Mock LLM that returns predefined responses"""

    async def ainvoke(self, messages, **kwargs):
        """Return mock response based on prompt content"""

        prompt = messages[0].get("content", "") if isinstance(messages, list) else str(messages)

        # Mock response class
        class MockResponse:
            def __init__(self, content):
                self.content = content if isinstance(content, str) else json.dumps(content)

        # Golden Data generation
        if "Golden Data" in prompt or "구조화된 요구사항" in prompt:
            response_data = {
                "original_requirement": "테스트 시스템",
                "domain": "automation",
                "concretized_description": "자동화된 테스트 시스템",
                "features": [
                    {
                        "id": "feature_1",
                        "name": "기본 기능",
                        "description": "테스트용 기본 기능",
                        "priority": "high"
                    }
                ],
                "constraints": [],
                "success_criteria": []
            }
            return MockResponse(response_data)

        # Requirement analysis
        elif "요구사항을 분석" in prompt:
            response_data = {
                "analysis": "테스트 분석",
                "requirements": ["기본 요구사항"],
                "success_criteria": ["성공 기준"]
            }
            return MockResponse(response_data)

        # Architecture design
        elif "아키텍처" in prompt or "architecture" in prompt.lower():
            response_data = {
                "components": ["Component1"],
                "data_models": ["Model1"],
                "apis": ["API1"]
            }
            return MockResponse(response_data)

        # Agent/Task design
        elif "agent" in prompt.lower() and "task" in prompt.lower():
            response_data = {
                "agents": [
                    {
                        "id": "test_agent",
                        "role": "Tester",
                        "goal": "Run tests",
                        "backstory": "Expert tester",
                        "tools": [],
                        "allow_delegation": False
                    }
                ],
                "tasks": [
                    {
                        "id": "test_task",
                        "description": "Execute tests",
                        "expected_output": "Test results",
                        "agent": "test_agent",
                        "human_input": False
                    }
                ]
            }
            return MockResponse(response_data)

        # Default fallback
        return MockResponse({"result": "ok"})


@pytest.fixture
def sample_golden_data():
    """Sample golden data for testing"""
    return ConcretizedRequirement(
        system_scope=SystemScope(
            project_name="test_system",
            purpose="Automated test system",
            target_users=["Testers", "Developers"],
            system_type="cli_tool",
            scope_description="A simple test automation system"
        ),
        features=[
            FeatureSpec(
                id="feature_1",
                name="기본 기능",
                description="테스트용 기본 기능",
                priority="high"
            )
        ],
        constraints=[],
        success_criteria=[],
        domain="automation"
    )


class TestBMADBootstrapIntegration:
    """Test BMAD Engine bootstrap integration"""

    @pytest.mark.asyncio
    async def test_bootstrap_integration_disabled(self, tmp_path, sample_golden_data):
        """Test that bootstrap is optional and disabled by default"""
        mock_llm = MockLLM()
        engine = BMADEngine(
            llm_plugin=mock_llm,
            use_expert_agents=False  # Use legacy path for simpler test
        )

        # Run without bootstrap
        result = await engine.run(
            requirement="테스트 시스템을 만들어주세요",
            domain="automation",
            golden_data=sample_golden_data,  # Use pre-existing golden data
            bootstrap_project=False  # Explicitly disable
        )

        # Should complete without bootstrap
        assert isinstance(result, BMADResult)
        assert result.success is True
        assert result.bootstrap_result is None  # No bootstrap result

    @pytest.mark.asyncio
    async def test_bootstrap_integration_enabled(self, tmp_path, sample_golden_data):
        """Test that BMAD Engine can bootstrap a project"""
        mock_llm = MockLLM()
        engine = BMADEngine(
            llm_plugin=mock_llm,
            use_expert_agents=False  # Use legacy path
        )

        # Run with bootstrap enabled
        result = await engine.run(
            requirement="테스트 시스템을 만들어주세요",
            domain="automation",
            golden_data=sample_golden_data,
            bootstrap_project=True,
            project_name="test_project",
            bootstrap_dir=tmp_path
        )

        # Should complete successfully
        assert isinstance(result, BMADResult)
        assert result.success is True

        # Should have bootstrap result
        assert result.bootstrap_result is not None
        assert isinstance(result.bootstrap_result, BootstrapResult)

        # Check bootstrap details
        bootstrap = result.bootstrap_result
        assert bootstrap.project_dir == tmp_path / "test_project"
        assert bootstrap.project_dir.exists()
        assert bootstrap.files_created > 0

    @pytest.mark.asyncio
    async def test_bootstrap_creates_project_structure(self, tmp_path, sample_golden_data):
        """Test that bootstrap creates expected project structure"""
        mock_llm = MockLLM()
        engine = BMADEngine(
            llm_plugin=mock_llm,
            use_expert_agents=False
        )

        result = await engine.run(
            requirement="테스트 시스템",
            golden_data=sample_golden_data,
            bootstrap_project=True,
            project_name="test_project",
            bootstrap_dir=tmp_path
        )

        project_dir = result.bootstrap_result.project_dir

        # Should have some Python files
        py_files = list(project_dir.glob("*.py"))
        assert len(py_files) > 0, "Should have at least one Python file"

        # Should have requirements.txt
        assert (project_dir / "requirements.txt").exists()

        # Should have README.md (generated by bootstrapper)
        assert (project_dir / "README.md").exists()

    @pytest.mark.asyncio
    async def test_bootstrap_initializes_git(self, tmp_path, sample_golden_data):
        """Test that bootstrap initializes git repository"""
        # Skip if git is not available
        import subprocess
        try:
            subprocess.run(['git', '--version'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("git not available")

        mock_llm = MockLLM()
        engine = BMADEngine(
            llm_plugin=mock_llm,
            use_expert_agents=False
        )

        result = await engine.run(
            requirement="테스트 시스템",
            golden_data=sample_golden_data,
            bootstrap_project=True,
            project_name="test_project",
            bootstrap_dir=tmp_path
        )

        project_dir = result.bootstrap_result.project_dir

        # Should have git initialized
        assert result.bootstrap_result.git_initialized is True
        assert (project_dir / ".git").exists()
        assert (project_dir / ".gitignore").exists()

    @pytest.mark.asyncio
    async def test_bootstrap_creates_venv(self, tmp_path, sample_golden_data):
        """Test that bootstrap creates virtual environment"""
        mock_llm = MockLLM()
        engine = BMADEngine(
            llm_plugin=mock_llm,
            use_expert_agents=False
        )

        result = await engine.run(
            requirement="테스트 시스템",
            golden_data=sample_golden_data,
            bootstrap_project=True,
            project_name="test_project",
            bootstrap_dir=tmp_path
        )

        project_dir = result.bootstrap_result.project_dir

        # Should have venv created
        assert (project_dir / "venv").exists()
        assert (project_dir / "venv").is_dir()

    @pytest.mark.asyncio
    async def test_bootstrap_with_default_project_name(self, tmp_path, sample_golden_data):
        """Test bootstrap with default project name"""
        mock_llm = MockLLM()
        engine = BMADEngine(
            llm_plugin=mock_llm,
            use_expert_agents=False
        )

        result = await engine.run(
            requirement="테스트 시스템",
            golden_data=sample_golden_data,
            bootstrap_project=True,
            # No project_name provided - should use default
            bootstrap_dir=tmp_path
        )

        # Should use default name
        assert result.bootstrap_result is not None
        assert result.bootstrap_result.project_dir.name == "generated_project"

    @pytest.mark.asyncio
    async def test_bootstrap_only_runs_with_generated_code(self, tmp_path, sample_golden_data):
        """Test that bootstrap only runs if code was generated"""
        mock_llm = MockLLM()
        engine = BMADEngine(
            llm_plugin=mock_llm,
            use_expert_agents=False
        )

        result = await engine.run(
            requirement="테스트 시스템",
            golden_data=sample_golden_data,
            bootstrap_project=True,
            project_name="test_project",
            bootstrap_dir=tmp_path
        )

        # If code generation failed, bootstrap should not run
        # But in our test, code generation succeeds, so:
        if result.generated_code:
            assert result.bootstrap_result is not None
        else:
            assert result.bootstrap_result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
