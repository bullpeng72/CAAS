"""
Session Manager

Multi-session support with context isolation and switching.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Session status"""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class Session(BaseModel):
    """Session model"""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: Optional[str] = None
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Session metadata
    name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Workflow context
    current_phase: Optional[str] = None
    phase_history: List[str] = Field(default_factory=list)

    # State
    state: Dict[str, Any] = Field(default_factory=dict)

    # Checkpoints
    checkpoint_ids: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class SessionContext:
    """
    Session Context

    Provides isolated context for a session with automatic cleanup.
    """

    def __init__(self, session: Session):
        """
        Initialize session context.

        Args:
            session: Session to contextualize
        """
        self.session = session
        self._previous_context: Optional[Dict[str, Any]] = None

    def __enter__(self):
        """Enter context"""
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context"""
        # Update session timestamp
        self.session.updated_at = datetime.utcnow()

        # Handle exceptions
        if exc_type is not None:
            self.session.status = SessionStatus.FAILED
            self.session.metadata["error"] = str(exc_val)

        return False  # Don't suppress exceptions


class SessionManager:
    """
    Session Manager

    Features:
    - Multi-session management
    - Context switching
    - Session isolation
    - Session lifecycle management
    """

    def __init__(self):
        """Initialize session manager"""
        self.sessions: Dict[str, Session] = {}
        self.active_session_id: Optional[str] = None

    # ========== Session Lifecycle ==========

    def create_session(
        self,
        workflow_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        Create a new session.

        Args:
            workflow_id: Associated workflow ID
            name: Session name
            description: Session description
            tags: Session tags
            metadata: Session metadata

        Returns:
            Session: Created session
        """
        session = Session(
            workflow_id=workflow_id,
            name=name,
            description=description,
            tags=tags or [],
            metadata=metadata or {},
        )

        self.sessions[session.session_id] = session

        # Set as active if no active session
        if self.active_session_id is None:
            self.active_session_id = session.session_id

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self.sessions.get(session_id)

    def list_sessions(
        self,
        status: Optional[SessionStatus] = None,
        workflow_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Session]:
        """
        List sessions with optional filters.

        Args:
            status: Filter by status
            workflow_id: Filter by workflow ID
            tags: Filter by tags (match any)

        Returns:
            List[Session]: Matching sessions
        """
        sessions = list(self.sessions.values())

        # Apply filters
        if status:
            sessions = [s for s in sessions if s.status == status]

        if workflow_id:
            sessions = [s for s in sessions if s.workflow_id == workflow_id]

        if tags:
            tag_set = set(tags)
            sessions = [s for s in sessions if tag_set & set(s.tags)]

        # Sort by created_at (newest first)
        sessions.sort(key=lambda s: s.created_at, reverse=True)

        return sessions

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID

        Returns:
            bool: Success
        """
        if session_id in self.sessions:
            # Switch away if active
            if self.active_session_id == session_id:
                self.active_session_id = None

            del self.sessions[session_id]
            return True

        return False

    # ========== Context Switching ==========

    def switch_to(self, session_id: str) -> Optional[Session]:
        """
        Switch to a different session.

        Args:
            session_id: Session ID to switch to

        Returns:
            Optional[Session]: New active session
        """
        session = self.get_session(session_id)

        if session:
            self.active_session_id = session_id
            return session

        return None

    def get_active_session(self) -> Optional[Session]:
        """Get currently active session"""
        if self.active_session_id:
            return self.get_session(self.active_session_id)
        return None

    def with_session(self, session_id: str) -> SessionContext:
        """
        Get session context manager.

        Args:
            session_id: Session ID

        Returns:
            SessionContext: Context manager

        Example:
            with session_manager.with_session(session_id) as session:
                # Work within session context
                session.state["key"] = "value"
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        return SessionContext(session)

    # ========== State Management ==========

    def update_session_state(self, session_id: str, state_updates: Dict[str, Any]) -> bool:
        """
        Update session state.

        Args:
            session_id: Session ID
            state_updates: State updates

        Returns:
            bool: Success
        """
        session = self.get_session(session_id)

        if session:
            session.state.update(state_updates)
            session.updated_at = datetime.utcnow()
            return True

        return False

    def set_session_phase(self, session_id: str, phase: str) -> bool:
        """
        Set session's current phase.

        Args:
            session_id: Session ID
            phase: Phase name

        Returns:
            bool: Success
        """
        session = self.get_session(session_id)

        if session:
            # Record in history
            if session.current_phase and session.current_phase != phase:
                session.phase_history.append(session.current_phase)

            session.current_phase = phase
            session.updated_at = datetime.utcnow()
            return True

        return False

    # ========== Status Management ==========

    def pause_session(self, session_id: str) -> bool:
        """Pause a session"""
        session = self.get_session(session_id)

        if session and session.status == SessionStatus.ACTIVE:
            session.status = SessionStatus.PAUSED
            session.updated_at = datetime.utcnow()
            return True

        return False

    def resume_session(self, session_id: str) -> bool:
        """Resume a paused session"""
        session = self.get_session(session_id)

        if session and session.status == SessionStatus.PAUSED:
            session.status = SessionStatus.ACTIVE
            session.updated_at = datetime.utcnow()

            # Set as active
            self.active_session_id = session_id
            return True

        return False

    def complete_session(self, session_id: str, success: bool = True) -> bool:
        """
        Mark session as completed.

        Args:
            session_id: Session ID
            success: Whether completion was successful

        Returns:
            bool: Success
        """
        session = self.get_session(session_id)

        if session:
            session.status = SessionStatus.COMPLETED if success else SessionStatus.FAILED
            session.completed_at = datetime.utcnow()
            session.updated_at = datetime.utcnow()

            # Switch away if active
            if self.active_session_id == session_id:
                self.active_session_id = None

            return True

        return False

    def archive_session(self, session_id: str) -> bool:
        """Archive a session"""
        session = self.get_session(session_id)

        if session:
            session.status = SessionStatus.ARCHIVED
            session.updated_at = datetime.utcnow()
            return True

        return False

    # ========== Checkpoint Management ==========

    def add_checkpoint(self, session_id: str, checkpoint_id: str) -> bool:
        """
        Add checkpoint to session.

        Args:
            session_id: Session ID
            checkpoint_id: Checkpoint ID

        Returns:
            bool: Success
        """
        session = self.get_session(session_id)

        if session:
            session.checkpoint_ids.append(checkpoint_id)
            session.updated_at = datetime.utcnow()
            return True

        return False

    def get_checkpoints(self, session_id: str) -> List[str]:
        """Get all checkpoints for a session"""
        session = self.get_session(session_id)
        return session.checkpoint_ids if session else []

    # ========== Session Statistics ==========

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        total = len(self.sessions)
        active = sum(1 for s in self.sessions.values() if s.status == SessionStatus.ACTIVE)
        paused = sum(1 for s in self.sessions.values() if s.status == SessionStatus.PAUSED)
        completed = sum(1 for s in self.sessions.values() if s.status == SessionStatus.COMPLETED)
        failed = sum(1 for s in self.sessions.values() if s.status == SessionStatus.FAILED)

        return {
            "total": total,
            "active": active,
            "paused": paused,
            "completed": completed,
            "failed": failed,
            "has_active_session": self.active_session_id is not None,
        }

    # ========== Cleanup ==========

    def cleanup_completed(self, keep_recent: int = 10) -> int:
        """
        Clean up completed sessions, keeping recent ones.

        Args:
            keep_recent: Number of recent completed sessions to keep

        Returns:
            int: Number of sessions deleted
        """
        completed_sessions = [
            s
            for s in self.sessions.values()
            if s.status in [SessionStatus.COMPLETED, SessionStatus.FAILED]
        ]

        # Sort by completion time (newest first)
        completed_sessions.sort(key=lambda s: s.completed_at or s.updated_at, reverse=True)

        # Delete old ones
        deleted = 0
        for session in completed_sessions[keep_recent:]:
            if self.delete_session(session.session_id):
                deleted += 1

        return deleted

    def clear_all(self):
        """Clear all sessions (use with caution)"""
        self.sessions.clear()
        self.active_session_id = None
