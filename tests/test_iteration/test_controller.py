"""
Unit tests for IterationController

Tests 3-level iteration system (Macro/Micro/Nano).

Part of CAAS-E Week 6 implementation (Task 6.2).
"""

import pytest
from pathlib import Path
from caas_framework.iteration import (
    IterationController,
    IterationConfig,
    IterationLevel,
    IterationStatus,
)


@pytest.fixture
def controller():
    """Create IterationController instance"""
    config = IterationConfig(
        max_nano_retries=3,
        max_micro_retries=3,
        max_macro_retries=3,
    )
    return IterationController(config=config)


@pytest.fixture
def temp_test_files(tmp_path):
    """Create temporary test and implementation files"""
    test_file = tmp_path / "test_example.py"
    test_file.write_text("""
def test_addition():
    assert 1 + 1 == 2

def test_subtraction():
    assert 5 - 3 == 2
""")

    impl_file = tmp_path / "example.py"
    impl_file.write_text("""
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
""")

    return test_file, impl_file


class TestIterationController:
    """Test IterationController class"""

    def test_initialization(self):
        """Test basic initialization"""
        config = IterationConfig(max_nano_retries=5)
        controller = IterationController(config=config)

        assert controller.config.max_nano_retries == 5
        assert controller.nano_iterator is not None
        assert controller.micro_iterator is not None
        assert controller.macro_iterator is not None

    def test_nano_iteration_execution(self, controller, temp_test_files):
        """Test nano-level iteration"""
        test_file, impl_file = temp_test_files

        result = controller.execute_nano(
            test_file=test_file,
            implementation_file=impl_file,
        )

        # Should complete (tests already pass)
        assert result.level == IterationLevel.NANO
        assert result.successful is True
        assert result.status == IterationStatus.SUCCESS

    def test_micro_iteration_execution(self, controller):
        """Test micro-level iteration"""

        def mock_phase_function(**kwargs):
            """Mock phase function that returns valid result"""
            return {
                "features": ["feature1", "feature2"],
                "agents": ["agent1"],
            }

        result = controller.execute_micro(
            story_id="story_1",
            story_name="Test Story",
            phase="discovery",
            phase_function=mock_phase_function,
        )

        assert result.level == IterationLevel.MICRO
        assert result.successful is True
        assert result.status == IterationStatus.SUCCESS

    def test_micro_iteration_with_retry(self, controller):
        """Test micro iteration with failures and retry"""

        attempt_count = 0

        def mock_failing_function(**kwargs):
            """Function that fails first 2 times, succeeds on 3rd"""
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count < 3:
                return None  # Fail
            else:
                return {"features": ["success"]}  # Success

        result = controller.execute_micro(
            story_id="story_retry",
            story_name="Retry Story",
            phase="discovery",
            phase_function=mock_failing_function,
        )

        # Should succeed on attempt 3
        assert result.successful is True
        assert attempt_count == 3

    def test_micro_iteration_max_retries(self, controller):
        """Test micro iteration exhausting retries"""

        def always_fail(**kwargs):
            """Function that always fails"""
            return None

        result = controller.execute_micro(
            story_id="story_fail",
            story_name="Failing Story",
            phase="discovery",
            phase_function=always_fail,
        )

        # Should exhaust retries
        assert result.successful is False
        assert result.status == IterationStatus.EXHAUSTED
        assert result.total_attempts == 3  # max_micro_retries

    def test_macro_iteration_execution(self, controller):
        """Test macro-level iteration with multiple stories"""

        executed_stories = []

        def mock_story_executor(story):
            """Mock story executor"""
            executed_stories.append(story["id"])
            return True  # Success

        stories = [
            {"id": "story_1", "name": "Story 1", "dependencies": []},
            {"id": "story_2", "name": "Story 2", "dependencies": ["story_1"]},
            {"id": "story_3", "name": "Story 3", "dependencies": []},
        ]

        result = controller.execute_macro(
            epic_id="epic_1",
            epic_name="Test Epic",
            stories=stories,
            story_executor=mock_story_executor,
        )

        assert result.level == IterationLevel.MACRO
        assert result.successful is True
        assert len(executed_stories) == 3

        # Verify story 1 executed before story 2 (dependency)
        assert executed_stories.index("story_1") < executed_stories.index("story_2")

    def test_macro_iteration_with_failures(self, controller):
        """Test macro iteration with story failures"""

        def mock_failing_executor(story):
            """Executor that fails for story_2"""
            if story["id"] == "story_2":
                return False  # Fail
            return True  # Success

        stories = [
            {"id": "story_1", "name": "Story 1", "dependencies": []},
            {"id": "story_2", "name": "Story 2", "dependencies": []},
            {"id": "story_3", "name": "Story 3", "dependencies": []},
        ]

        result = controller.execute_macro(
            epic_id="epic_fail",
            epic_name="Failing Epic",
            stories=stories,
            story_executor=mock_failing_executor,
        )

        # Should fail due to story_2
        assert result.successful is False

    def test_metrics_tracking(self, controller):
        """Test metrics tracking across iterations"""

        # Execute some iterations
        def success_fn(**kwargs):
            return {"features": ["test"]}

        controller.execute_micro(
            story_id="s1",
            story_name="Story 1",
            phase="discovery",
            phase_function=success_fn,
        )

        controller.execute_micro(
            story_id="s2",
            story_name="Story 2",
            phase="discovery",
            phase_function=success_fn,
        )

        # Get metrics
        metrics = controller.get_metrics(IterationLevel.MICRO)

        assert metrics.total_iterations == 2
        assert metrics.successful_iterations == 2
        assert metrics.success_rate == 1.0

    def test_metrics_reset(self, controller):
        """Test metrics reset"""

        def success_fn(**kwargs):
            return {"features": ["test"]}

        # Execute iteration
        controller.execute_micro(
            story_id="s1",
            story_name="Story 1",
            phase="discovery",
            phase_function=success_fn,
        )

        # Reset metrics
        controller.reset_metrics()

        # Metrics should be empty
        metrics = controller.get_metrics(IterationLevel.MICRO)
        assert metrics.total_iterations == 0

    def test_get_summary(self, controller):
        """Test summary generation"""

        def success_fn(**kwargs):
            return {"features": ["test"]}

        # Execute different levels
        controller.execute_micro(
            story_id="s1",
            story_name="Story 1",
            phase="discovery",
            phase_function=success_fn,
        )

        summary = controller.get_summary()

        assert "micro" in summary
        assert "overall" in summary
        assert summary["micro"]["total"] == 1
        assert "success_rate" in summary["overall"]

    def test_iteration_config(self):
        """Test iteration configuration"""
        config = IterationConfig(
            max_nano_retries=5,
            max_micro_retries=4,
            max_macro_retries=2,
            enable_auto_rollback=False,
            retry_delay_seconds=2.0,
        )

        assert config.max_nano_retries == 5
        assert config.max_micro_retries == 4
        assert config.max_macro_retries == 2
        assert config.enable_auto_rollback is False
        assert config.retry_delay_seconds == 2.0

    def test_checkpoint_directory(self, tmp_path):
        """Test checkpoint directory creation"""
        checkpoint_dir = tmp_path / "checkpoints"

        controller = IterationController(checkpoint_dir=checkpoint_dir)

        assert controller.checkpoint_dir == checkpoint_dir
        assert controller.micro_iterator.checkpoint_dir == checkpoint_dir
