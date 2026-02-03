"""
Test CAAS_API Integration

Verifies that CAAS_API and SDK clients work correctly.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from caas_framework.api import CAAS_API, GenerationConfig, GenerationResult


@pytest.fixture
def mock_llm():
    """Mock LLM plugin"""
    llm = Mock()
    llm.generate = AsyncMock(return_value="Generated response")
    return llm


@pytest.fixture
def mock_golden_data():
    """Mock golden data"""
    from caas_framework.models.specifications import ConcretizedRequirement
    return Mock(spec=ConcretizedRequirement)


def test_generation_config():
    """Test GenerationConfig dataclass"""
    # Default config
    config = GenerationConfig()
    assert config.llm_provider == "openai"
    assert config.llm_model == "gpt-4"
    assert config.enable_feedback_loop == True
    assert config.max_retries == 3

    # Custom config
    config = GenerationConfig(
        llm_provider="openai",
        llm_model="gpt-3.5-turbo",
        enable_plan_mode=True,
        output_dir="./my_output",
        verbosity="debug"
    )
    assert config.llm_model == "gpt-3.5-turbo"
    assert config.enable_plan_mode == True
    assert config.output_dir == "./my_output"
    assert config.verbosity == "debug"


def test_generation_result():
    """Test GenerationResult dataclass"""
    # Success result
    result = GenerationResult(
        success=True,
        files={"main.py": "print('hello')", "agents.py": "# agents"},
        metadata={"duration": 10.5, "phases_completed": ["discovery", "design"]},
        errors=[],
        warnings=["Warning: unused variable"]
    )

    assert result.success == True
    assert len(result.files) == 2
    assert "main.py" in result.files
    assert result.metadata["duration"] == 10.5
    assert len(result.warnings) == 1

    # Failure result
    result = GenerationResult(
        success=False,
        errors=["Generation failed: timeout"]
    )

    assert result.success == False
    assert len(result.errors) == 1


def test_caas_api_initialization(mock_llm):
    """Test CAAS_API initialization"""
    config = GenerationConfig(llm_provider="openai")

    api = CAAS_API(config, llm_plugin=mock_llm)

    assert api.config == config
    assert api.llm == mock_llm
    assert api.event_bus is not None


def test_caas_api_subscribe_event(mock_llm):
    """Test event subscription"""
    config = GenerationConfig()
    api = CAAS_API(config, llm_plugin=mock_llm)

    # Subscribe to event
    callback_called = []

    def on_phase_start(event):
        callback_called.append(event)

    api.subscribe_event("phase_start", on_phase_start)

    # Verify subscription
    assert "phase_start" in api._event_subscriptions
    assert on_phase_start in api._event_subscriptions["phase_start"]


def test_caas_api_unsubscribe_event(mock_llm):
    """Test event unsubscription"""
    config = GenerationConfig()
    api = CAAS_API(config, llm_plugin=mock_llm)

    def on_phase_start(event):
        pass

    # Subscribe then unsubscribe
    api.subscribe_event("phase_start", on_phase_start)
    api.unsubscribe_event("phase_start", on_phase_start)

    # Verify unsubscription
    assert on_phase_start not in api._event_subscriptions.get("phase_start", [])


@pytest.mark.asyncio
async def test_caas_api_generate_mock(mock_llm, mock_golden_data):
    """Test generate method with mocks"""
    config = GenerationConfig()
    api = CAAS_API(config, llm_plugin=mock_llm)

    # Mock collaboration result
    mock_collab_result = Mock()
    mock_collab_result.success = True
    mock_collab_result.total_duration = 10.5
    mock_collab_result.phases_completed = []
    mock_collab_result.feedback_loops_executed = 1
    mock_collab_result.agent_summaries = {}
    mock_collab_result.errors = []
    mock_collab_result.context = Mock()
    mock_collab_result.context.code_artifacts = {
        'files': {
            'main.py': 'print("hello")',
            'agents.py': '# agents'
        }
    }

    # Mock _generate_golden_data
    with patch.object(api, '_generate_golden_data', new_callable=AsyncMock) as mock_gen_golden:
        mock_gen_golden.return_value = mock_golden_data

        # Mock _create_collaboration
        with patch.object(api, '_create_collaboration') as mock_create_collab:
            mock_collaboration = Mock()
            mock_collaboration.collaborate = AsyncMock(return_value=mock_collab_result)
            mock_create_collab.return_value = mock_collaboration

            # Execute generate
            result = await api.generate("Create a blog system")

            # Verify result
            assert result.success == True
            assert len(result.files) == 2
            assert "main.py" in result.files
            assert result.metadata["duration"] == 10.5


@pytest.mark.asyncio
async def test_caas_api_generate_from_design(mock_llm):
    """Test generate_from_design method"""
    config = GenerationConfig()
    api = CAAS_API(config, llm_plugin=mock_llm)

    agents = [
        {"id": "writer", "role": "Writer", "goal": "Write content"}
    ]
    tasks = [
        {"description": "Write blog post", "agent": "writer"}
    ]

    # Mock code generator result
    mock_agent_result = Mock()
    mock_agent_result.success = True
    mock_agent_result.duration = 5.0
    mock_agent_result.output = {
        'files': {
            'main.py': 'print("generated")'
        }
    }
    mock_agent_result.errors = []

    with patch('caas_framework.api.caas_api.CodeGeneratorAgent') as mock_generator_class:
        mock_generator = Mock()
        mock_generator.work = AsyncMock(return_value=mock_agent_result)
        mock_generator_class.return_value = mock_generator

        # Execute
        result = await api.generate_from_design(agents, tasks)

        # Verify
        assert result.success == True
        assert len(result.files) == 1
        assert "main.py" in result.files


def test_format_result(mock_llm):
    """Test _format_result method"""
    config = GenerationConfig()
    api = CAAS_API(config, llm_plugin=mock_llm)

    # Create mock collaboration result
    mock_result = Mock()
    mock_result.success = True
    mock_result.total_duration = 15.3
    mock_result.phases_completed = []
    mock_result.feedback_loops_executed = 2
    mock_result.agent_summaries = {"agent1": {}, "agent2": {}}
    mock_result.errors = []
    mock_result.context = Mock()
    mock_result.context.code_artifacts = {
        'files': {
            'main.py': 'code',
            'agents.py': 'code'
        }
    }

    # Format result
    result = api._format_result(mock_result)

    # Verify
    assert isinstance(result, GenerationResult)
    assert result.success == True
    assert len(result.files) == 2
    assert result.metadata["duration"] == 15.3
    assert result.metadata["feedback_loops_executed"] == 2
    assert len(result.metadata["agents_used"]) == 2


@pytest.mark.asyncio
async def test_save_files_mock(mock_llm, tmp_path):
    """Test _save_files method"""
    config = GenerationConfig(output_dir=str(tmp_path))
    api = CAAS_API(config, llm_plugin=mock_llm)

    files = {
        "main.py": "print('hello')",
        "agents.py": "# agents code"
    }

    # Save files
    await api._save_files(files, str(tmp_path))

    # Verify files exist
    assert (tmp_path / "main.py").exists()
    assert (tmp_path / "agents.py").exists()

    # Verify content
    assert (tmp_path / "main.py").read_text() == "print('hello')"
    assert (tmp_path / "agents.py").read_text() == "# agents code"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
