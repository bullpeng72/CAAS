"""
Test ProgressReporter Protocol Implementation

Verifies that both existing ProgressReporter and new RichProgressReporter
implement the Protocol correctly and can be used interchangeably.
"""

import pytest
from typing import Protocol
from caas_framework.reporting import (
    ProgressReporterProtocol,
    ProgressReporter,
    VerbosityLevel,
    NullProgressReporter
)
from caas_cli.ui.rich_progress_reporter import RichProgressReporter


def test_protocol_implementation():
    """Test that ProgressReporter implements the Protocol"""
    # Both implementations should be compatible with the Protocol
    reporter1 = ProgressReporter(verbosity=VerbosityLevel.QUIET)
    reporter2 = RichProgressReporter(verbosity=VerbosityLevel.QUIET)
    reporter3 = NullProgressReporter()

    # Test that they have all required Protocol methods
    assert hasattr(reporter1, 'start_workflow')
    assert hasattr(reporter1, 'start_phase')
    assert hasattr(reporter1, 'complete_phase')
    assert hasattr(reporter1, 'update_phase_progress')
    assert hasattr(reporter1, 'log_message')
    assert hasattr(reporter1, 'log_validation')
    assert hasattr(reporter1, 'log_feedback_iteration')
    assert hasattr(reporter1, 'end_workflow')

    assert hasattr(reporter2, 'start_workflow')
    assert hasattr(reporter2, 'start_phase')
    assert hasattr(reporter2, 'complete_phase')
    assert hasattr(reporter2, 'update_phase_progress')
    assert hasattr(reporter2, 'log_message')
    assert hasattr(reporter2, 'log_validation')
    assert hasattr(reporter2, 'log_feedback_iteration')
    assert hasattr(reporter2, 'end_workflow')

    assert hasattr(reporter3, 'start_workflow')
    assert hasattr(reporter3, 'end_workflow')


def test_protocol_usage():
    """Test that Protocol can be used as type hint"""
    def use_reporter(reporter: ProgressReporterProtocol) -> None:
        """Function that accepts any ProgressReporter implementation"""
        reporter.start_workflow("Test Workflow")
        reporter.start_phase("Phase 1", "TestAgent", "Testing")
        reporter.update_phase_progress("Phase 1", "Working...", 0.5)
        reporter.log_message("Test message", "info")
        reporter.log_validation("Phase 1", True)
        reporter.log_feedback_iteration("Phase 1", 1, 3)
        reporter.complete_phase("Phase 1", 1.0, True)
        reporter.end_workflow(True, 1.0)

    # All implementations should work
    reporter1 = ProgressReporter(verbosity=VerbosityLevel.QUIET)
    reporter2 = RichProgressReporter(verbosity=VerbosityLevel.QUIET)
    reporter3 = NullProgressReporter()

    use_reporter(reporter1)
    use_reporter(reporter2)
    use_reporter(reporter3)


def test_existing_methods_still_work():
    """Test that existing ProgressReporter methods still work"""
    reporter = ProgressReporter(verbosity=VerbosityLevel.QUIET)

    # Old methods should still work for backward compatibility
    reporter.start_workflow("Test", total_phases=6)
    reporter.start_phase("Phase 1", agent_name="Agent1")
    reporter.agent_working("Agent1", "Working")
    reporter.agent_completed("Agent1", 1.0)
    reporter.error("Test error")
    reporter.warning("Test warning")
    reporter.info("Test info")
    reporter.debug("Test debug")
    reporter.validation_start("Validator", 10)
    reporter.validation_result("Validator", True, 0)
    reporter.feedback_iteration("Agent1", 1, 3, 2)
    reporter.complete_phase("Phase 1", success=True, duration=1.0)
    reporter.complete_workflow(success=True)

    # Protocol methods should also work
    reporter.log_message("Test", "info")
    reporter.update_phase_progress("Phase 1", "Progress", 0.5)
    reporter.log_validation("Phase 1", True)
    reporter.log_feedback_iteration("Phase 1", 1, 3)
    reporter.end_workflow(True, 1.0)


if __name__ == "__main__":
    test_protocol_implementation()
    test_protocol_usage()
    test_existing_methods_still_work()
    print("✅ All Protocol tests passed!")
