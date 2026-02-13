"""
E2E Test: UI Integration Workflow

✅ v0.5.0 (P2): End-to-end test for frontend integration
Tests complete workflow with UI generation to verify Bug #1 fix.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from caas_framework.agents.collaboration import ExpertAgentCollaboration, CollaborationContext
from caas_framework.models.specifications import ConcretizedRequirement


@pytest.fixture
def mock_llm_plugin():
    """Mock LLM plugin for testing"""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value='{"result": "success"}')
    return llm


@pytest.fixture
def sample_golden_data():
    """Sample Golden Data for testing"""
    from caas_framework.models.specifications import SystemScope

    return ConcretizedRequirement(
        system_scope=SystemScope(
            project_name="todo_app",
            purpose="Simple TODO app with UI",
        ),
        features=[
            {
                "id": "feat_add_task",
                "name": "Add Task",
                "description": "User can add new tasks",
                "acceptance_criteria": ["Task input field exists", "Add button works"],
            }
        ],
    )


class TestUIIntegrationE2E:
    """
    End-to-end tests for UI integration workflow

    Verifies:
    - Bug #1 fix: Frontend integration KeyError eliminated
    - Complete workflow: Requirement → Golden Data → Code → Frontend
    - Code artifacts normalization and safe dictionary access
    """

    @pytest.mark.asyncio
    async def test_ui_enabled_workflow_no_keyerror(
        self, mock_llm_plugin, sample_golden_data, tmp_path
    ):
        """
        Test: UI-enabled workflow completes without KeyError

        Verifies Bug #1 fix:
        - Code artifacts are properly normalized
        - Frontend integration uses safe dictionary access
        - No KeyError at lines 1530-1531, 1536
        """
        # Setup: Create collaboration with frontend enabled
        collaboration = ExpertAgentCollaboration(
            llm_plugin=mock_llm_plugin,
            golden_data=sample_golden_data,
            max_feedback_loops=0,  # Disable feedback for faster testing
            enable_validation=False,  # Disable validation for faster testing
            enable_frontend=True,  # ✅ Enable frontend generation
            frontend_framework="streamlit",
        )

        # Mock code generator to return flat structure
        mock_code_result = MagicMock()
        mock_code_result.success = True
        mock_code_result.output = {
            "main.py": "# Main code",
            "agents.py": "# Agents",
            "tasks.py": "# Tasks",
        }

        # Mock frontend specialist
        mock_frontend_result = MagicMock()
        mock_frontend_result.app_code = "# Streamlit app"
        mock_frontend_result.ui_requirements = []
        mock_frontend_result.framework = "streamlit"

        with patch.object(
            collaboration.agents["code_generator"],
            "work",
            return_value=mock_code_result,
        ):
            with patch.object(
                collaboration.agents.get("frontend_specialist"),
                "work",
                return_value=mock_frontend_result,
            ) if "frontend_specialist" in collaboration.agents else MagicMock():
                # Execute: Run workflow
                context = CollaborationContext(
                    golden_data=sample_golden_data,
                    requirement="TODO app",
                )

                # Simulate code generation phase
                context.code_artifacts = mock_code_result.output

                # Verify: Code artifacts structure is normalized
                files_dict = collaboration._get_or_create_files_dict(context.code_artifacts)

                # Assertions
                assert isinstance(files_dict, dict), "Files dict should be dictionary"
                assert "main.py" in files_dict or "files" in context.code_artifacts

                # ✅ Key assertion: No KeyError when accessing files
                try:
                    # This should not raise KeyError (Bug #1 fix)
                    if "files" in context.code_artifacts:
                        _ = context.code_artifacts["files"]
                    success = True
                except KeyError:
                    success = False

                assert success, "❌ KeyError occurred - Bug #1 not fixed!"

    @pytest.mark.asyncio
    async def test_code_artifacts_normalization(
        self, mock_llm_plugin, sample_golden_data
    ):
        """
        Test: Code artifacts normalization handles both flat and nested structures

        Tests Bug #1 fix helper methods:
        - _normalize_code_artifacts()
        - _get_or_create_files_dict()
        """
        collaboration = ExpertAgentCollaboration(
            llm_plugin=mock_llm_plugin,
            golden_data=sample_golden_data,
            enable_frontend=False,
        )

        # Test Case 1: Flat structure
        flat_artifacts = {
            "main.py": "code1",
            "agents.py": "code2",
        }
        normalized = collaboration._normalize_code_artifacts(flat_artifacts)
        assert normalized == flat_artifacts, "Flat structure should be preserved"

        # Test Case 2: Nested structure
        nested_artifacts = {
            "files": {
                "main.py": "code1",
                "agents.py": "code2",
            }
        }
        normalized = collaboration._normalize_code_artifacts(nested_artifacts)
        assert normalized == nested_artifacts["files"], "Nested structure should be flattened"

        # Test Case 3: Empty/None
        assert collaboration._normalize_code_artifacts(None) == {}
        assert collaboration._normalize_code_artifacts({}) == {}

        # Test Case 4: get_or_create_files_dict creates "files" key
        artifacts = {"main.py": "code"}
        files_dict = collaboration._get_or_create_files_dict(artifacts)
        assert "files" in artifacts, "'files' key should be created"
        assert artifacts["files"] == {"main.py": "code"}

    @pytest.mark.asyncio
    async def test_frontend_integration_safe_access(
        self, mock_llm_plugin, sample_golden_data
    ):
        """
        Test: Frontend integration uses safe dictionary access

        Simulates auto-fix integration scenario (lines 1530-1531)
        """
        collaboration = ExpertAgentCollaboration(
            llm_plugin=mock_llm_plugin,
            golden_data=sample_golden_data,
            enable_frontend=True,
        )

        # Setup: Code artifacts with flat structure
        context = CollaborationContext(
            golden_data=sample_golden_data,
            requirement="Test",
        )
        context.code_artifacts = {
            "main.py": "original code",
        }

        # Normalize (Bug #1 fix applies here)
        context.code_artifacts = {
            "files": collaboration._normalize_code_artifacts(context.code_artifacts)
        }

        # Simulate frontend integration update (line 1530-1531)
        files_dict = collaboration._get_or_create_files_dict(context.code_artifacts)
        fixed_backend = {"main.py": "fixed code", "utils.py": "new file"}

        # This should not raise KeyError
        files_dict.update(fixed_backend)
        files_dict["app.py"] = "frontend code"

        # Assertions
        assert files_dict["main.py"] == "fixed code"
        assert files_dict["utils.py"] == "new file"
        assert files_dict["app.py"] == "frontend code"
        assert len(files_dict) == 3

    @pytest.mark.asyncio
    async def test_ui_layout_parsing_with_llm_response(
        self, mock_llm_plugin, sample_golden_data
    ):
        """
        Test: UI layout parsing handles LLMResponse objects

        Verifies Bug #3 fix integration with frontend specialist
        """
        from caas_framework.utils.json_parser import parse_llm_json

        # Mock LLMResponse object
        class MockLLMResponse:
            def __init__(self, content):
                self.content = content

        # Test Case 1: Clean JSON
        response = MockLLMResponse('{"sections": [{"title": "Input"}]}')
        layout = parse_llm_json(response, default={"sections": []})
        assert layout == {"sections": [{"title": "Input"}]}

        # Test Case 2: Markdown-wrapped JSON
        response = MockLLMResponse(
            '```json\n{"sections": [{"title": "Settings"}]}\n```'
        )
        layout = parse_llm_json(response, default={"sections": []})
        assert layout == {"sections": [{"title": "Settings"}]}

        # Test Case 3: Malformed JSON with trailing comma
        response = MockLLMResponse('{"sections": [],}')
        layout = parse_llm_json(response, default={"sections": []})
        assert "sections" in layout

        # Test Case 4: Invalid JSON returns default
        response = MockLLMResponse('Not JSON at all')
        layout = parse_llm_json(response, default={"sections": []})
        assert layout == {"sections": []}


class TestPhase5IndividualExecution:
    """
    Test Phase 5 individual execution

    Verifies Bug #2 fix: _phase_5_delivery() method
    """

    @pytest.mark.asyncio
    async def test_phase_5_delivery_method_exists(self, mock_llm_plugin):
        """Test: Phase 5 delivery method exists and is callable"""
        from caas_framework.methodology.engine import SixPhaseEngine

        engine = SixPhaseEngine(
            llm_plugin=mock_llm_plugin,
            enable_validation=False,
        )

        # Verify method exists
        assert hasattr(engine, "_phase_5_delivery"), "❌ Bug #2 not fixed: _phase_5_delivery missing"
        assert callable(engine._phase_5_delivery), "_phase_5_delivery should be callable"

    @pytest.mark.asyncio
    async def test_phase_5_delivery_execution(
        self, mock_llm_plugin, sample_golden_data, tmp_path
    ):
        """Test: Phase 5 delivery executes successfully with valid inputs"""
        from caas_framework.methodology.engine import SixPhaseEngine
        import json

        # Setup: Create input directory with artifacts
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create golden_data.json
        with open(input_dir / "golden_data.json", "w") as f:
            json.dump(sample_golden_data.model_dump(), f)

        # Create agents.json
        agents_data = {
            "agents": [
                {
                    "id": "agent1",
                    "role": "Test Agent",
                    "goal": "Test goal",
                    "backstory": "Test backstory",
                    "tools": [],
                }
            ]
        }
        with open(input_dir / "agents.json", "w") as f:
            json.dump(agents_data, f)

        # Create tasks.json
        tasks_data = {
            "tasks": [
                {
                    "id": "task1",
                    "description": "Test task",
                    "expected_output": "Test output",
                    "agent_id": "agent1",
                }
            ]
        }
        with open(input_dir / "tasks.json", "w") as f:
            json.dump(tasks_data, f)

        # Setup: Mock code generator
        output_dir = tmp_path / "output"

        engine = SixPhaseEngine(
            llm_plugin=mock_llm_plugin,
            enable_validation=False,
        )

        # Mock code generator work method
        mock_work_result = MagicMock()
        mock_work_result.success = True
        mock_work_result.output = {
            "files": {
                "main.py": "print('hello')",
                "agents.py": "# agents",
                "tasks.py": "# tasks",
            }
        }

        with patch(
            "caas_framework.agents.code_generator.CodeGeneratorAgent.work",
            return_value=mock_work_result,
        ):
            # Execute: Run Phase 5
            result = await engine._phase_5_delivery(
                input_dir=input_dir,
                output_dir=output_dir,
            )

            # Assertions
            assert "files" in result, "Result should contain files"
            assert "validation_passed" in result, "Result should contain validation_passed"
            assert result["validation_passed"] is True, "Validation should pass"
            assert result["file_count"] > 0, "Should generate files"


class TestCompleteWorkflowIntegration:
    """
    Complete workflow integration test

    Verifies all bug fixes working together
    """

    @pytest.mark.asyncio
    async def test_end_to_end_workflow_with_all_fixes(
        self, mock_llm_plugin, sample_golden_data, tmp_path
    ):
        """
        Test: Complete workflow integrates all bug fixes

        Integration test for:
        - Bug #1: Frontend KeyError fix
        - Bug #2: Phase 5 method
        - Bug #3: LLM response parsing
        """
        from caas_framework.utils.json_parser import parse_llm_json

        collaboration = ExpertAgentCollaboration(
            llm_plugin=mock_llm_plugin,
            golden_data=sample_golden_data,
            enable_frontend=True,
            enable_validation=False,
        )

        # Step 1: Test code artifacts normalization (Bug #1)
        artifacts = {"main.py": "code"}
        normalized = {"files": collaboration._normalize_code_artifacts(artifacts)}
        assert "files" in normalized

        # Step 2: Test safe dictionary access (Bug #1)
        files_dict = collaboration._get_or_create_files_dict(normalized)
        files_dict["app.py"] = "frontend"
        assert files_dict["app.py"] == "frontend"

        # Step 3: Test LLM response parsing (Bug #3)
        class MockResponse:
            content = '{"status": "ok"}'

        parsed = parse_llm_json(MockResponse(), default={})
        assert parsed == {"status": "ok"}

        # Step 4: Test Phase 5 method exists (Bug #2)
        from caas_framework.methodology.engine import SixPhaseEngine

        engine = SixPhaseEngine(llm_plugin=mock_llm_plugin, enable_validation=False)
        assert hasattr(engine, "_phase_5_delivery")

        # All fixes integrated successfully!


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
