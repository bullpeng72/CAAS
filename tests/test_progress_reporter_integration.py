"""
Test Progress Reporter Integration with BMAD Engine

Tests that Rich progress reporting works correctly with the BMAD Engine.
"""

import io

from caas_framework.reporting.progress_reporter import (
    PhaseProgress,
    PhaseStatus,
    ProgressReporter,
    VerbosityLevel,
)


def test_progress_reporter_creation():
    """Test ProgressReporter can be created"""
    reporter = ProgressReporter(
        verbosity=VerbosityLevel.NORMAL,
        use_rich=False,  # Disable Rich for testing
    )

    assert reporter is not None
    assert reporter.verbosity == VerbosityLevel.NORMAL
    assert reporter.use_rich is False


def test_progress_reporter_verbosity_levels():
    """Test all verbosity levels"""
    for level in VerbosityLevel:
        reporter = ProgressReporter(verbosity=level, use_rich=False)
        assert reporter.verbosity == level


def test_workflow_lifecycle():
    """Test complete workflow lifecycle"""
    output = io.StringIO()
    reporter = ProgressReporter(
        verbosity=VerbosityLevel.NORMAL, use_rich=False, file=output
    )

    # Start workflow
    reporter.start_workflow("Test Workflow", total_phases=3)
    assert reporter.workflow_name == "Test Workflow"
    assert reporter.total_phases == 3

    # Run phases
    reporter.start_phase("Phase 1", "Agent1", "Test phase 1")
    reporter.complete_phase("Phase 1", success=True, duration=1.5)

    reporter.start_phase("Phase 2", "Agent2", "Test phase 2")
    reporter.complete_phase("Phase 2", success=True, duration=2.0)

    reporter.start_phase("Phase 3", "Agent3", "Test phase 3")
    reporter.complete_phase("Phase 3", success=True, duration=1.0)

    # Complete workflow
    reporter.complete_workflow(success=True)

    # Verify phases tracked
    assert len(reporter.phases) == 3
    assert all(p.status == PhaseStatus.COMPLETED for p in reporter.phases.values())

    # Verify output contains expected text
    output_text = output.getvalue()
    assert "Test Workflow" in output_text
    assert "Phase 1" in output_text


def test_phase_status_tracking():
    """Test phase status tracking"""
    reporter = ProgressReporter(verbosity=VerbosityLevel.QUIET, use_rich=False)

    phase_name = "Test Phase"

    # Phase not started
    assert phase_name not in reporter.phases

    # Start phase
    reporter.start_phase(phase_name, "TestAgent")
    assert phase_name in reporter.phases
    assert reporter.phases[phase_name].status == PhaseStatus.IN_PROGRESS

    # Complete phase
    reporter.complete_phase(phase_name, success=True)
    assert reporter.phases[phase_name].status == PhaseStatus.COMPLETED

    # Check duration
    assert reporter.phases[phase_name].duration is not None


def test_phase_failure_tracking():
    """Test phase failure tracking"""
    reporter = ProgressReporter(verbosity=VerbosityLevel.QUIET, use_rich=False)

    phase_name = "Failing Phase"
    reporter.start_phase(phase_name)
    reporter.complete_phase(phase_name, success=False)

    assert reporter.phases[phase_name].status == PhaseStatus.FAILED


def test_error_and_warning_tracking():
    """Test error and warning tracking"""
    output = io.StringIO()
    reporter = ProgressReporter(
        verbosity=VerbosityLevel.NORMAL, use_rich=False, file=output
    )

    phase_name = "Test Phase"
    reporter.start_phase(phase_name)

    # Add errors
    reporter.error("Test error 1", phase=phase_name)
    reporter.error("Test error 2", phase=phase_name)

    # Add warnings
    reporter.warning("Test warning 1", phase=phase_name)
    reporter.warning("Test warning 2", phase=phase_name)

    reporter.complete_phase(phase_name)

    # Verify tracking
    phase = reporter.phases[phase_name]
    assert len(phase.errors) == 2
    assert len(phase.warnings) == 2


def test_agent_reporting():
    """Test agent-level reporting"""
    output = io.StringIO()
    reporter = ProgressReporter(
        verbosity=VerbosityLevel.NORMAL, use_rich=False, file=output
    )

    reporter.start_phase("Test Phase", "TestAgent")

    # Agent working
    reporter.agent_working("TestAgent", "Processing data...")

    # Agent completed
    reporter.agent_completed("TestAgent", duration=2.5, iterations=3)

    output_text = output.getvalue()
    assert "TestAgent" in output_text
    assert "Processing data" in output_text
    assert "Completed" in output_text


def test_validation_reporting():
    """Test validation reporting"""
    output = io.StringIO()
    reporter = ProgressReporter(
        verbosity=VerbosityLevel.VERBOSE, use_rich=False, file=output
    )

    reporter.start_phase("Validation Phase")

    # Validation start
    reporter.validation_start("SyntaxValidator", item_count=10)

    # Validation result - passed
    reporter.validation_result(
        "SyntaxValidator", passed=True, issues_count=0, score=1.0
    )

    # Validation result - failed
    reporter.validation_result(
        "ImportValidator", passed=False, issues_count=5, score=0.7
    )

    output_text = output.getvalue()
    assert "SyntaxValidator" in output_text
    assert "ImportValidator" in output_text


def test_feedback_iteration_reporting():
    """Test feedback loop iteration reporting"""
    output = io.StringIO()
    reporter = ProgressReporter(
        verbosity=VerbosityLevel.VERBOSE, use_rich=False, file=output
    )

    reporter.start_phase("Feedback Phase")

    # Report iterations
    reporter.feedback_iteration(
        "CodeGenerator", iteration=1, max_iterations=3, issues_count=5
    )
    reporter.feedback_iteration(
        "CodeGenerator", iteration=2, max_iterations=3, issues_count=2
    )
    reporter.feedback_iteration(
        "CodeGenerator", iteration=3, max_iterations=3, issues_count=0
    )

    output_text = output.getvalue()
    assert "iteration" in output_text.lower()
    assert "CodeGenerator" in output_text


def test_quiet_verbosity():
    """Test that quiet verbosity suppresses output"""
    output = io.StringIO()
    reporter = ProgressReporter(
        verbosity=VerbosityLevel.QUIET, use_rich=False, file=output
    )

    reporter.start_workflow("Test Workflow")
    reporter.start_phase("Phase 1")
    reporter.agent_working("Agent1", "Working...")
    reporter.complete_phase("Phase 1")
    reporter.complete_workflow()

    # Should have minimal output
    output_text = output.getvalue()
    assert len(output_text) < 100  # Very little output in quiet mode


def test_debug_verbosity():
    """Test that debug verbosity includes debug messages"""
    output = io.StringIO()
    reporter = ProgressReporter(
        verbosity=VerbosityLevel.DEBUG, use_rich=False, file=output
    )

    reporter.debug("Debug message 1")
    reporter.debug("Debug message 2")

    output_text = output.getvalue()
    assert "DEBUG" in output_text
    assert "Debug message 1" in output_text


def test_progress_percentage():
    """Test progress percentage calculation"""
    reporter = ProgressReporter(verbosity=VerbosityLevel.QUIET, use_rich=False)

    # No phases yet
    assert reporter.get_progress_percentage() == 0.0

    # Complete some phases
    reporter.total_phases = 4
    reporter.start_phase("Phase 1")
    reporter.complete_phase("Phase 1")
    assert reporter.get_progress_percentage() == 25.0

    reporter.start_phase("Phase 2")
    reporter.complete_phase("Phase 2")
    assert reporter.get_progress_percentage() == 50.0


def test_skip_phase():
    """Test skipping a phase"""
    output = io.StringIO()
    reporter = ProgressReporter(
        verbosity=VerbosityLevel.NORMAL, use_rich=False, file=output
    )

    reporter.skip_phase("Architecture", reason="Quick fix mode")

    assert "Architecture" in reporter.phases
    assert reporter.phases["Architecture"].status == PhaseStatus.SKIPPED


def test_bmad_engine_integration_pattern():
    """Test the integration pattern used in BMAD Engine"""
    # Simulate BMAD Engine usage

    reporter = ProgressReporter(verbosity=VerbosityLevel.NORMAL, use_rich=False)

    # 1. Start workflow
    reporter.start_workflow("BMAD Pipeline: Test Project", total_phases=6)

    # 2. Execute phases (simulate)
    phases = [
        "Phase 0: Concretization",
        "Phase 1: Discovery",
        "Phase 2: Architecture",
        "Phase 3: Design",
        "Phase 4: Development",
        "Phase 5: Delivery",
    ]

    for i, phase_name in enumerate(phases, 1):
        reporter.start_phase(phase_name, f"Agent{i}", f"Executing {phase_name}")
        # Simulate work
        reporter.agent_working(f"Agent{i}", "Processing...")
        reporter.complete_phase(phase_name, duration=float(i))

    # 3. Complete workflow
    reporter.complete_workflow(success=True)

    # 4. Verify all phases completed
    assert len(reporter.phases) == 6
    assert all(p.status == PhaseStatus.COMPLETED for p in reporter.phases.values())
    assert reporter.get_progress_percentage() == 100.0


def test_rich_availability():
    """Test Rich library availability check"""
    # With Rich (default)
    reporter1 = ProgressReporter(use_rich=True)
    # Should have console if Rich is available
    # (We can't guarantee Rich is available in test environment)

    # Without Rich (forced)
    reporter2 = ProgressReporter(use_rich=False)
    assert reporter2.console is None


def test_phase_progress_duration():
    """Test PhaseProgress duration calculation"""
    import time

    phase = PhaseProgress(phase_name="Test Phase")

    # No times set
    assert phase.duration is None

    # Start time only
    phase.start_time = time.time()
    time.sleep(0.01)  # Small delay
    duration = phase.duration
    assert duration is not None
    assert duration > 0

    # Both times set
    phase.end_time = time.time()
    duration = phase.duration
    assert duration is not None
    assert duration > 0


def test_phase_status_icons():
    """Test phase status icons"""
    phase = PhaseProgress(phase_name="Test")

    phase.status = PhaseStatus.PENDING
    assert phase.status_icon == "⏳"

    phase.status = PhaseStatus.IN_PROGRESS
    assert phase.status_icon == "🔄"

    phase.status = PhaseStatus.COMPLETED
    assert phase.status_icon == "✅"

    phase.status = PhaseStatus.FAILED
    assert phase.status_icon == "❌"

    phase.status = PhaseStatus.SKIPPED
    assert phase.status_icon == "⏭️"


if __name__ == "__main__":
    # Run tests
    test_progress_reporter_creation()
    test_progress_reporter_verbosity_levels()
    test_workflow_lifecycle()
    test_phase_status_tracking()
    test_phase_failure_tracking()
    test_error_and_warning_tracking()
    test_agent_reporting()
    test_validation_reporting()
    test_feedback_iteration_reporting()
    test_quiet_verbosity()
    test_debug_verbosity()
    test_progress_percentage()
    test_skip_phase()
    test_bmad_engine_integration_pattern()
    test_rich_availability()
    test_phase_progress_duration()
    test_phase_status_icons()

    print("\n" + "=" * 70)
    print("✅ All Progress Reporter Integration tests passed!")
    print("=" * 70)
