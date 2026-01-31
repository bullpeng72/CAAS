"""
Session Management Service

Manages workflow sessions using StateManager and PersistenceBackend.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

from caas_framework.workflow.state_manager import StateManager, Checkpoint
from caas_framework.workflow.persistence import (
    PersistenceBackend,
    DatabasePersistenceBackend,
    FilePersistenceBackend
)
from app.utils.logger import get_logger

logger = get_logger("session_service")


class SessionService:
    """
    Session Management Service

    Provides high-level session management using StateManager and persistence.
    """

    def __init__(
        self,
        state_storage_dir: str = ".caas/state",
        session_storage_dir: str = ".caas/sessions"
    ):
        """
        Initialize session service.

        Args:
            state_storage_dir: Directory for state checkpoints
            session_storage_dir: Directory for session metadata
        """
        self.state_manager = StateManager(storage_dir=state_storage_dir)
        self.session_backend = FilePersistenceBackend(storage_dir=session_storage_dir)

    # ========== Session Management ==========

    def create_session(
        self,
        name: str,
        workflow_id: str = "bmad_workflow",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new session.

        Args:
            name: Session name
            workflow_id: Workflow identifier
            metadata: Additional metadata

        Returns:
            Session data
        """
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()

        session = {
            "id": session_id,
            "name": name,
            "workflow_id": workflow_id,
            "status": "active",
            "current_phase": 0,
            "progress": 0,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "duration": 0,
            "checkpoint_count": 0,
            "metadata": metadata or {}
        }

        # Save to persistence
        self.session_backend.save(session_id, session)

        # Initialize state (use string for phase to match StateHistory model)
        initial_state = {
            "current_phase": "0",  # Use string for phase
            "workflow_id": workflow_id,
            "status": "active"
        }

        # Set initial state (bypassing _record_history to avoid validation error)
        self.state_manager.active_states[session_id] = initial_state

        logger.info(f"Created session: {session_id} - {name}")
        return session

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        session = self.session_backend.load(session_id)

        if session:
            # Calculate actual duration
            created = datetime.fromisoformat(session["created_at"])
            updated = datetime.fromisoformat(session["updated_at"])
            session["duration"] = int((updated - created).total_seconds())

        return session

    def list_sessions(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        order_by: str = "updated_at",
        order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """
        List all sessions.

        Args:
            status: Filter by status (active, paused, completed, failed)
            limit: Maximum number of sessions to return
            order_by: Field to sort by (default: updated_at)
            order: Sort order - 'asc' or 'desc' (default: desc)

        Returns:
            List of sessions
        """
        all_keys = self.session_backend.list_keys(prefix="sess_")
        sessions = []

        for key in all_keys:
            session = self.session_backend.load(key)
            if session:
                # Apply status filter
                if status and session.get("status") != status:
                    continue

                # Update checkpoint count
                checkpoints = self.state_manager.list_checkpoints(session_id=key)
                session["checkpoint_count"] = len(checkpoints)

                # Calculate duration
                created = datetime.fromisoformat(session["created_at"])
                updated = datetime.fromisoformat(session["updated_at"])
                session["duration"] = int((updated - created).total_seconds())

                sessions.append(session)

        # Sort by specified field
        reverse_order = (order.lower() == "desc")
        sessions.sort(key=lambda s: s.get(order_by, ""), reverse=reverse_order)

        # Apply limit if specified
        if limit is not None and limit > 0:
            sessions = sessions[:limit]

        return sessions

    def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update session.

        Args:
            session_id: Session ID
            updates: Fields to update

        Returns:
            Updated session or None if not found
        """
        session = self.session_backend.load(session_id)
        if not session:
            return None

        # Update fields
        session.update(updates)
        session["updated_at"] = datetime.utcnow().isoformat()

        # Save
        self.session_backend.save(session_id, session)

        # Update state if phase or status changed
        if "current_phase" in updates or "status" in updates:
            state_updates = {}
            if "current_phase" in updates:
                # Convert phase to string for StateHistory compatibility
                state_updates["current_phase"] = str(updates["current_phase"])
            if "status" in updates:
                state_updates["status"] = updates["status"]

            # Update state directly to avoid _record_history validation issues
            if session_id in self.state_manager.active_states:
                self.state_manager.active_states[session_id].update(state_updates)
            else:
                self.state_manager.active_states[session_id] = state_updates

        logger.info(f"Updated session: {session_id}")
        return session

    def pause_session(self, session_id: str) -> bool:
        """Pause session"""
        session = self.update_session(session_id, {"status": "paused"})
        return session is not None

    def resume_session(self, session_id: str) -> bool:
        """Resume session"""
        session = self.update_session(session_id, {"status": "active"})
        return session is not None

    def complete_session(self, session_id: str) -> bool:
        """Mark session as completed"""
        session = self.update_session(session_id, {
            "status": "completed",
            "progress": 100
        })
        return session is not None

    def fail_session(self, session_id: str, error: str) -> bool:
        """Mark session as failed"""
        session = self.update_session(session_id, {
            "status": "failed",
            "metadata": {"error": error}
        })
        return session is not None

    def delete_session(self, session_id: str) -> bool:
        """
        Delete session and all its checkpoints.

        Args:
            session_id: Session ID

        Returns:
            True if deleted successfully
        """
        # Delete all checkpoints
        checkpoints = self.state_manager.list_checkpoints(session_id=session_id)
        for checkpoint in checkpoints:
            self.state_manager.delete_checkpoint(checkpoint.checkpoint_id)

        # Clear state
        self.state_manager.clear_state(session_id)

        # Delete session metadata
        success = self.session_backend.delete(session_id)

        if success:
            logger.info(f"Deleted session: {session_id}")

        return success

    def clone_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Clone a session (create a new session with same settings).

        Args:
            session_id: Session ID to clone

        Returns:
            New session data or None if source not found
        """
        source = self.get_session(session_id)
        if not source:
            return None

        # Create new session with same name + " (Clone)"
        new_session = self.create_session(
            name=f"{source['name']} (Clone)",
            workflow_id=source["workflow_id"],
            metadata=source.get("metadata", {})
        )

        logger.info(f"Cloned session {session_id} -> {new_session['id']}")
        return new_session

    # ========== Checkpoint Management ==========

    def create_checkpoint(
        self,
        session_id: str,
        name: str,
        description: Optional[str] = None
    ) -> Optional[str]:
        """
        Create checkpoint for session.

        Args:
            session_id: Session ID
            name: Checkpoint name
            description: Optional description

        Returns:
            Checkpoint ID or None if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return None

        # Get current state
        state = self.state_manager.get_state(session_id)
        if not state:
            # Create initial state from session (convert phase to string)
            state = {
                "current_phase": str(session["current_phase"]),
                "workflow_id": session["workflow_id"],
                "status": session["status"]
            }

        # Create checkpoint
        checkpoint_id = self.state_manager.save_checkpoint(
            session_id=session_id,
            workflow_id=session["workflow_id"],
            phase=str(session["current_phase"]),
            state=state,
            metadata={
                "name": name,
                "description": description or ""
            }
        )

        # Update session checkpoint count
        self.update_session(session_id, {
            "checkpoint_count": session.get("checkpoint_count", 0) + 1
        })

        logger.info(f"Created checkpoint: {checkpoint_id} for session {session_id}")
        return checkpoint_id

    def get_checkpoints(
        self,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get checkpoints.

        Args:
            session_id: Filter by session ID (None = all)

        Returns:
            List of checkpoint data
        """
        checkpoints = self.state_manager.list_checkpoints(session_id=session_id)

        # Convert to dict format
        result = []
        for ckpt in checkpoints:
            result.append({
                "id": ckpt.checkpoint_id,
                "session_id": ckpt.session_id,
                "workflow_id": ckpt.workflow_id,
                "name": ckpt.metadata.get("name", f"Checkpoint at {ckpt.timestamp}"),
                "description": ckpt.metadata.get("description", ""),
                "phase": ckpt.phase,
                "created_at": ckpt.timestamp.isoformat(),
                "size_mb": 0.0  # Not tracking size yet
            })

        return result

    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Restore from checkpoint.

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            True if restored successfully
        """
        # Rollback to checkpoint
        state = self.state_manager.rollback_to_checkpoint(checkpoint_id)
        if not state:
            return False

        # Load checkpoint to get metadata
        checkpoint = self.state_manager.load_checkpoint(checkpoint_id)
        if not checkpoint:
            return False

        # Update session to match checkpoint
        session = self.update_session(checkpoint.session_id, {
            "current_phase": int(checkpoint.phase) if checkpoint.phase.isdigit() else 0,
            "status": state.get("status", "active")
        })

        logger.info(f"Restored checkpoint: {checkpoint_id}")
        return session is not None

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete checkpoint"""
        success = self.state_manager.delete_checkpoint(checkpoint_id)

        if success:
            logger.info(f"Deleted checkpoint: {checkpoint_id}")

        return success

    # ========== Cleanup ==========

    def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """
        Clean up old sessions and checkpoints.

        Args:
            days: Delete data older than this

        Returns:
            Count of deleted items
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        deleted_sessions = 0
        deleted_checkpoints = 0

        # Delete old sessions
        sessions = self.list_sessions()
        for session in sessions:
            updated = datetime.fromisoformat(session["updated_at"])
            if updated < cutoff and session["status"] in ["completed", "failed"]:
                if self.delete_session(session["id"]):
                    deleted_sessions += 1

        # Delete orphaned checkpoints
        deleted_checkpoints = self.state_manager.cleanup_old_checkpoints(days=days)

        logger.info(f"Cleanup: deleted {deleted_sessions} sessions, {deleted_checkpoints} checkpoints")

        return {
            "sessions": deleted_sessions,
            "checkpoints": deleted_checkpoints
        }


# Global instance
_session_service: Optional[SessionService] = None


def get_session_service() -> SessionService:
    """Get or create global session service instance"""
    global _session_service

    if _session_service is None:
        _session_service = SessionService()

    return _session_service
