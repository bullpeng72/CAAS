"""
Progress Reporting Interfaces

UI-independent interfaces for progress reporting.
Allows different UIs (CLI, Streamlit, VSCode) to implement their own reporters.
"""

from typing import Protocol, Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class VerbosityLevel(Enum):
    """Verbosity levels for progress reporting"""
    QUIET = 0      # Only critical errors
    MINIMAL = 1    # Phase transitions only
    NORMAL = 2     # Phase + agent execution (default)
    VERBOSE = 3    # + validation + feedback loops
    DEBUG = 4      # Everything including agent outputs


@dataclass
class PhaseInfo:
    """Phase information for UI-independent reporting"""
    phase_name: str
    agent_name: str
    description: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PhaseResult:
    """Phase completion result"""
    phase_name: str
    duration: float
    success: bool
    metadata: Optional[Dict[str, Any]] = None


class ProgressReporter(Protocol):
    """
    UI-independent Progress Reporter Interface

    All UI implementations (CLI, Streamlit, VSCode) must implement this protocol
    to provide consistent progress reporting across different interfaces.

    Examples:
        # CLI Implementation
        class RichProgressReporter:
            def start_workflow(self, description: str) -> None:
                console.print(f"[bold cyan]{description}[/bold cyan]")

        # Streamlit Implementation
        class StreamlitProgressReporter:
            def start_workflow(self, description: str) -> None:
                st.header(description)

        # VSCode Implementation
        class VSCodeProgressReporter:
            def start_workflow(self, description: str) -> None:
                vscode.window.showInformationMessage(description)
    """

    def start_workflow(self, description: str) -> None:
        """
        Start workflow reporting.

        Args:
            description: Workflow description (e.g., "Generating CrewAI Blog System")
        """
        ...

    def start_phase(
        self,
        phase_name: str,
        agent_name: str,
        description: str
    ) -> None:
        """
        Report phase start.

        Args:
            phase_name: Phase name (e.g., "Phase 1: Discovery")
            agent_name: Agent name (e.g., "RequirementAnalyst")
            description: Phase description
        """
        ...

    def update_phase_progress(
        self,
        phase_name: str,
        message: str,
        progress: Optional[float] = None
    ) -> None:
        """
        Update phase progress (optional).

        Args:
            phase_name: Phase name
            message: Progress message
            progress: Progress percentage (0.0-1.0), None if indeterminate
        """
        ...

    def complete_phase(
        self,
        phase_name: str,
        duration: float,
        success: bool
    ) -> None:
        """
        Report phase completion.

        Args:
            phase_name: Phase name
            duration: Duration in seconds
            success: Whether phase succeeded
        """
        ...

    def log_message(
        self,
        message: str,
        level: str = "info"
    ) -> None:
        """
        Log a message.

        Args:
            message: Message text
            level: Log level ("debug", "info", "warning", "error")
        """
        ...

    def log_validation(
        self,
        phase_name: str,
        passed: bool,
        issues: Optional[List[str]] = None
    ) -> None:
        """
        Log validation result (optional).

        Args:
            phase_name: Phase name
            passed: Whether validation passed
            issues: List of validation issues
        """
        ...

    def log_feedback_iteration(
        self,
        phase_name: str,
        iteration: int,
        total_iterations: int
    ) -> None:
        """
        Log feedback loop iteration (optional).

        Args:
            phase_name: Phase name
            iteration: Current iteration
            total_iterations: Total iterations
        """
        ...

    def end_workflow(
        self,
        success: bool,
        duration: float,
        summary: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        End workflow reporting.

        Args:
            success: Whether workflow succeeded
            duration: Total duration in seconds
            summary: Optional summary data
        """
        ...


class NullProgressReporter:
    """
    Null implementation of ProgressReporter.

    Does nothing - useful for testing or when progress reporting is disabled.
    """

    def start_workflow(self, description: str) -> None:
        pass

    def start_phase(
        self,
        phase_name: str,
        agent_name: str,
        description: str
    ) -> None:
        pass

    def update_phase_progress(
        self,
        phase_name: str,
        message: str,
        progress: Optional[float] = None
    ) -> None:
        pass

    def complete_phase(
        self,
        phase_name: str,
        duration: float,
        success: bool
    ) -> None:
        pass

    def log_message(
        self,
        message: str,
        level: str = "info"
    ) -> None:
        pass

    def log_validation(
        self,
        phase_name: str,
        passed: bool,
        issues: Optional[List[str]] = None
    ) -> None:
        pass

    def log_feedback_iteration(
        self,
        phase_name: str,
        iteration: int,
        total_iterations: int
    ) -> None:
        pass

    def end_workflow(
        self,
        success: bool,
        duration: float,
        summary: Optional[Dict[str, Any]] = None
    ) -> None:
        pass
