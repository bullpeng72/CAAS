"""
Project Management Service

Manages code generation projects, built on top of SessionService.
Projects represent complete code generation tasks with requirements and outputs.
"""

from typing import Dict, Any, List, Optional

from caas_app.workflow.session_service import SessionService, get_session_service
from caas_framework.utils.logger import get_logger

logger = get_logger("project_service")


class ProjectService:
    """
    Project Management Service

    Projects are code generation tasks with:
    - Requirements
    - Generated code/files
    - Generation status
    - Metadata (domain, deployment target, etc.)
    """

    def __init__(self, session_service: Optional[SessionService] = None):
        """
        Initialize project service.

        Args:
            session_service: Optional session service (will create if not provided)
        """
        self.session_service = session_service or get_session_service()

    # ========== Project Management ==========

    def create_project(
        self,
        requirement: str,
        domain: Optional[str] = None,
        deployment_target: Optional[str] = None,
        enable_validation: bool = True,
        enable_auto_fix: bool = True,
        enable_tests: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new project.

        Args:
            requirement: Natural language requirement
            domain: Optional domain hint
            deployment_target: Deployment target (docker, kubernetes, etc.)
            enable_validation: Enable validation
            enable_auto_fix: Enable auto-fix
            enable_tests: Generate tests
            metadata: Additional metadata

        Returns:
            Project data
        """
        # Create session for project
        project_name = self._generate_project_name(requirement)

        project_metadata = {
            "type": "code_generation",
            "requirement": requirement,
            "domain": domain,
            "deployment_target": deployment_target or "docker",
            "enable_validation": enable_validation,
            "enable_auto_fix": enable_auto_fix,
            "enable_tests": enable_tests,
            "files": {},
            "generation_time": 0.0,
            "phases_completed": [],
            **(metadata or {})
        }

        session = self.session_service.create_session(
            name=project_name,
            workflow_id="code_generation",
            metadata=project_metadata
        )

        # Convert to project format
        project = self._session_to_project(session)

        logger.info(f"Created project: {project['project_id']} - {requirement[:50]}")
        return project

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get project by ID.

        Args:
            project_id: Project ID (same as session ID)

        Returns:
            Project data or None
        """
        session = self.session_service.get_session(project_id)
        if not session:
            return None

        return self._session_to_project(session)

    def list_projects(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List projects.

        Args:
            status: Filter by status (generating, completed, failed)
            limit: Maximum number of projects

        Returns:
            List of projects
        """
        # Map project status to session status
        session_status = None
        if status == "generating":
            session_status = "active"
        elif status in ["completed", "failed"]:
            session_status = status

        sessions = self.session_service.list_sessions(status=session_status)

        # Filter to only code generation projects
        projects = []
        for session in sessions:
            if session.get("metadata", {}).get("type") == "code_generation":
                projects.append(self._session_to_project(session))

        return projects[:limit]

    def update_project(
        self,
        project_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update project.

        Args:
            project_id: Project ID
            updates: Fields to update

        Returns:
            Updated project or None
        """
        # Update session
        session_updates = {}

        # Map project fields to session fields
        if "status" in updates:
            status_map = {
                "generating": "active",
                "completed": "completed",
                "failed": "failed"
            }
            session_updates["status"] = status_map.get(updates["status"], "active")

        if "progress" in updates:
            session_updates["progress"] = updates["progress"]

        if "current_phase" in updates:
            session_updates["current_phase"] = updates["current_phase"]

        # Update metadata with project-specific fields
        session = self.session_service.get_session(project_id)
        if not session:
            return None

        metadata = session.get("metadata", {})

        if "files" in updates:
            metadata["files"] = updates["files"]

        if "generation_time" in updates:
            metadata["generation_time"] = updates["generation_time"]

        if "phases_completed" in updates:
            metadata["phases_completed"] = updates["phases_completed"]

        if "error_message" in updates:
            metadata["error_message"] = updates["error_message"]

        session_updates["metadata"] = metadata

        # Update session
        updated_session = self.session_service.update_session(project_id, session_updates)

        if updated_session:
            return self._session_to_project(updated_session)

        return None

    def delete_project(self, project_id: str) -> bool:
        """
        Delete project.

        Args:
            project_id: Project ID

        Returns:
            True if deleted successfully
        """
        return self.session_service.delete_session(project_id)

    def complete_project(
        self,
        project_id: str,
        files: Dict[str, str],
        generation_time: float,
        phases_completed: List[str]
    ) -> bool:
        """
        Mark project as completed.

        Args:
            project_id: Project ID
            files: Generated files (path -> content)
            generation_time: Time taken to generate
            phases_completed: List of completed phases

        Returns:
            True if updated successfully
        """
        result = self.update_project(project_id, {
            "status": "completed",
            "progress": 100,
            "files": files,
            "generation_time": generation_time,
            "phases_completed": phases_completed
        })

        return result is not None

    def fail_project(
        self,
        project_id: str,
        error_message: str
    ) -> bool:
        """
        Mark project as failed.

        Args:
            project_id: Project ID
            error_message: Error message

        Returns:
            True if updated successfully
        """
        result = self.update_project(project_id, {
            "status": "failed",
            "error_message": error_message
        })

        return result is not None

    # ========== Helper Methods ==========

    def _generate_project_name(self, requirement: str) -> str:
        """Generate project name from requirement"""
        # Take first 50 chars and clean up
        name = requirement[:50].strip()
        if len(requirement) > 50:
            name += "..."
        return f"Project: {name}"

    def _session_to_project(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Convert session to project format"""
        metadata = session.get("metadata", {})

        # Map session status to project status
        session_status = session.get("status", "active")
        project_status = "generating"

        if session_status == "completed":
            project_status = "completed"
        elif session_status == "failed":
            project_status = "failed"
        elif session_status == "paused":
            project_status = "paused"

        return {
            "project_id": session["id"],
            "requirement": metadata.get("requirement", ""),
            "status": project_status,
            "progress": session.get("progress", 0) / 100.0,  # Convert to 0-1
            "current_phase": session.get("current_phase", 0),
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
            "domain": metadata.get("domain"),
            "deployment_target": metadata.get("deployment_target", "docker"),
            "enable_validation": metadata.get("enable_validation", True),
            "enable_auto_fix": metadata.get("enable_auto_fix", True),
            "enable_tests": metadata.get("enable_tests", True),
            "files": metadata.get("files", {}),
            "generation_time": metadata.get("generation_time", 0.0),
            "phases_completed": metadata.get("phases_completed", []),
            "error_message": metadata.get("error_message"),
            "session_id": session["id"]
        }


# Global instance
_project_service: Optional[ProjectService] = None


def get_project_service() -> ProjectService:
    """Get or create global project service instance"""
    global _project_service

    if _project_service is None:
        _project_service = ProjectService()

    return _project_service
