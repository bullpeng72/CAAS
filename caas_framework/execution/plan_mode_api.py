"""
UI-Independent Plan Mode API

Provides review functionality without being tied to any specific UI.
UIs (CLI, Streamlit, VSCode) implement ReviewHandler to provide UI-specific behavior.
"""

from typing import Dict, Any, Optional
from caas_framework.api.interfaces import (
    ReviewHandler,
    ReviewRequest,
    ReviewType
)


class PlanModeAPI:
    """
    UI-Independent Plan Mode API

    Framework uses this to request reviews.
    UI provides ReviewHandler to handle review requests.
    """

    def __init__(self, review_handler: Optional[ReviewHandler] = None):
        """
        Initialize Plan Mode API.

        Args:
            review_handler: UI-specific review handler
                           (None = auto-approve, for testing/headless)
        """
        self.review_handler = review_handler

    def request_requirements_review(
        self,
        concretized: Any
    ) -> str:
        """
        Request requirements review (UI-independent).

        Args:
            concretized: ConcretizedRequirement object

        Returns:
            Decision: "approve", "edit", "reject"
        """
        if not self.review_handler:
            return "approve"  # Auto-approve if no handler

        # Prepare UI-independent data
        review_data = self._prepare_requirements_data(concretized)

        # Create review request
        request = ReviewRequest(
            review_type=ReviewType.REQUIREMENTS,
            data=review_data,
            options=["approve", "edit", "reject"]
        )

        # Delegate to UI handler
        decision = self.review_handler.handle_review(request)

        return decision

    def request_design_review(
        self,
        design: Dict[str, Any]
    ) -> str:
        """
        Request design review (UI-independent).

        Args:
            design: Design output with agents and tasks

        Returns:
            Decision: "approve", "redesign", "reject"
        """
        if not self.review_handler:
            return "approve"

        review_data = self._prepare_design_data(design)

        request = ReviewRequest(
            review_type=ReviewType.DESIGN,
            data=review_data,
            options=["approve", "redesign", "reject"]
        )

        return self.review_handler.handle_review(request)

    def request_code_review(
        self,
        files: Dict[str, str]
    ) -> str:
        """
        Request code review (UI-independent).

        Args:
            files: Generated code files (filename -> content)

        Returns:
            Decision: "approve", "reject"
        """
        if not self.review_handler:
            return "approve"

        review_data = self._prepare_code_data(files)

        request = ReviewRequest(
            review_type=ReviewType.CODE,
            data=review_data,
            options=["approve", "reject"]
        )

        return self.review_handler.handle_review(request)

    # ==================== Data Preparation (UI-independent) ====================

    def _prepare_requirements_data(self, concretized: Any) -> Dict[str, Any]:
        """
        Prepare requirements review data (UI-independent structure).

        Args:
            concretized: ConcretizedRequirement object

        Returns:
            UI-independent data structure
        """
        return {
            "project_name": concretized.project_name,
            "description": concretized.description,
            "features": [
                {
                    "name": f.name,
                    "description": f.description,
                    "priority": f.priority
                }
                for f in (concretized.features or [])
            ],
            "data_models": [
                {
                    "name": m.entity_name,
                    "attributes_count": len(m.attributes)
                }
                for m in (concretized.data_models or [])
            ],
            "boundaries": self._extract_boundaries(concretized)
        }

    def _prepare_design_data(self, design: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare design review data (UI-independent structure).

        Args:
            design: Design output

        Returns:
            UI-independent data structure
        """
        agents = design.get("agents", [])
        tasks = design.get("tasks", [])

        return {
            "agents": [
                {
                    "id": agent.get("id", "unknown"),
                    "role": agent.get("role", "N/A"),
                    "goal": agent.get("goal", "N/A"),
                    "tools": agent.get("tools", [])
                }
                for agent in agents
            ],
            "tasks": [
                {
                    "id": task.get("id", "unknown"),
                    "description": task.get("description", "N/A"),
                    "agent": task.get("agent", "N/A")
                }
                for task in tasks
            ]
        }

    def _prepare_code_data(self, files: Dict[str, str]) -> Dict[str, Any]:
        """
        Prepare code review data (UI-independent structure).

        Args:
            files: Generated files

        Returns:
            UI-independent data structure
        """
        return {
            "files": {
                name: {
                    "lines": content.count('\n') + 1,
                    "size_kb": len(content) / 1024,
                    "preview": content[:500] if name == "main.py" else None
                }
                for name, content in files.items()
            },
            "total_files": len(files),
            "total_lines": sum(content.count('\n') + 1 for content in files.values())
        }

    def _extract_boundaries(self, concretized: Any) -> Optional[Dict[str, Any]]:
        """Extract security boundaries if available."""
        if not hasattr(concretized, 'boundaries') or not concretized.boundaries:
            return None

        boundaries = concretized.boundaries
        return {
            "always_allowed": boundaries.always_allowed or [],
            "ask_first": boundaries.ask_first or [],
            "never_allowed": boundaries.never_allowed or []
        }
