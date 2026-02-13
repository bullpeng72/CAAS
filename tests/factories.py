"""
Test Data Factories

✅ v0.5.1: Factory pattern for consistent test data generation

Provides reusable factories for creating test objects:
- GoldenDataFactory: ConcretizedRequirement objects
- AgentFactory: AgentSpecModel objects
- TaskFactory: TaskSpecModel objects
- ModelFactory: Generic Pydantic model factory

Benefits:
- DRY principle
- Type-safe test data
- Consistent defaults
- Easy customization
"""

from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


class ModelFactory:
    """
    Generic Pydantic model factory.

    Creates model instances with sensible defaults and easy customization.
    """

    @staticmethod
    def build(
        model_class: Type[T],
        defaults: Optional[Dict[str, Any]] = None,
        **overrides
    ) -> T:
        """
        Build a model instance with defaults and overrides.

        Args:
            model_class: Pydantic model class
            defaults: Default field values
            **overrides: Override specific fields

        Returns:
            Model instance

        Example:
            >>> agent = ModelFactory.build(
            ...     AgentSpecModel,
            ...     defaults={"role": "Analyst"},
            ...     id="custom_id",
            ... )
        """
        data = {**(defaults or {}), **overrides}
        return model_class(**data)


class GoldenDataFactory:
    """
    Factory for creating ConcretizedRequirement (Golden Data) test objects.

    Provides consistent defaults and validation.
    """

    DEFAULT_SYSTEM_SCOPE = {
        "project_name": "test_project",
        "purpose": "Test application for automated testing",
    }

    DEFAULT_FEATURE = {
        "id": "feat_default",
        "name": "Default Feature",
        "description": "Default test feature",
        "acceptance_criteria": ["Default criterion"],
    }

    @classmethod
    def create(
        cls,
        project_name: Optional[str] = None,
        purpose: Optional[str] = None,
        features: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict:
        """
        Create Golden Data dictionary (for JSON serialization).

        Args:
            project_name: Project name (default: "test_project")
            purpose: Project purpose
            features: List of feature dicts
            **kwargs: Additional fields

        Returns:
            Dictionary ready for ConcretizedRequirement(**data)

        Example:
            >>> golden_data = GoldenDataFactory.create(
            ...     project_name="todo_app",
            ...     purpose="Task management",
            ...     features=[{"id": "f1", "name": "Add task", ...}]
            ... )
            >>> requirement = ConcretizedRequirement(**golden_data)
        """
        system_scope = {
            "project_name": project_name or cls.DEFAULT_SYSTEM_SCOPE["project_name"],
            "purpose": purpose or cls.DEFAULT_SYSTEM_SCOPE["purpose"],
        }

        return {
            "system_scope": system_scope,
            "features": features or [],
            **kwargs,
        }

    @classmethod
    def create_with_features(
        cls,
        project_name: str,
        purpose: str,
        feature_count: int = 1,
        **kwargs
    ) -> Dict:
        """
        Create Golden Data with N default features.

        Args:
            project_name: Project name
            purpose: Project purpose
            feature_count: Number of features to generate
            **kwargs: Additional fields

        Returns:
            Golden Data dictionary with N features

        Example:
            >>> data = GoldenDataFactory.create_with_features(
            ...     "my_app", "My Application", feature_count=3
            ... )
            >>> len(data["features"])
            3
        """
        features = [
            {
                **cls.DEFAULT_FEATURE,
                "id": f"feat_{i}",
                "name": f"Feature {i}",
                "description": f"Test feature {i}",
            }
            for i in range(1, feature_count + 1)
        ]

        return cls.create(
            project_name=project_name,
            purpose=purpose,
            features=features,
            **kwargs,
        )

    @classmethod
    def create_minimal(cls) -> Dict:
        """
        Create minimal valid Golden Data (empty features).

        Returns:
            Minimal Golden Data dictionary
        """
        return cls.create()


class AgentFactory:
    """
    Factory for creating AgentSpecModel test objects.
    """

    DEFAULT_AGENT = {
        "id": "agent_default",
        "role": "Default Agent",
        "goal": "Perform default tasks",
        "backstory": "An agent created for testing purposes",
        "tools": [],
    }

    @classmethod
    def create(
        cls,
        agent_id: Optional[str] = None,
        role: Optional[str] = None,
        goal: Optional[str] = None,
        backstory: Optional[str] = None,
        tools: Optional[List[str]] = None,
        **kwargs
    ) -> Dict:
        """
        Create Agent dictionary.

        Args:
            agent_id: Agent ID
            role: Agent role
            goal: Agent goal
            backstory: Agent backstory
            tools: List of tool names
            **kwargs: Additional fields

        Returns:
            Dictionary ready for AgentSpecModel(**data)

        Example:
            >>> agent = AgentFactory.create(
            ...     agent_id="task_manager",
            ...     role="Task Manager",
            ...     tools=["AddTaskTool", "ListTasksTool"]
            ... )
        """
        return {
            "id": agent_id or cls.DEFAULT_AGENT["id"],
            "role": role or cls.DEFAULT_AGENT["role"],
            "goal": goal or cls.DEFAULT_AGENT["goal"],
            "backstory": backstory or cls.DEFAULT_AGENT["backstory"],
            "tools": tools if tools is not None else cls.DEFAULT_AGENT["tools"],
            **kwargs,
        }

    @classmethod
    def create_batch(cls, count: int, prefix: str = "agent") -> List[Dict]:
        """
        Create multiple agents.

        Args:
            count: Number of agents to create
            prefix: Agent ID prefix

        Returns:
            List of agent dictionaries

        Example:
            >>> agents = AgentFactory.create_batch(3, prefix="worker")
            >>> len(agents)
            3
            >>> agents[0]["id"]
            'worker_1'
        """
        return [
            cls.create(
                agent_id=f"{prefix}_{i}",
                role=f"{prefix.title()} {i}",
                goal=f"Goal for {prefix} {i}",
                backstory=f"Backstory for {prefix} {i}",
            )
            for i in range(1, count + 1)
        ]


class TaskFactory:
    """
    Factory for creating TaskSpecModel test objects.
    """

    DEFAULT_TASK = {
        "id": "task_default",
        "description": "Default task description",
        "expected_output": "Default expected output",
        "agent": "agent_default",  # ✅ Note: 'agent' not 'agent_id'
    }

    @classmethod
    def create(
        cls,
        task_id: Optional[str] = None,
        description: Optional[str] = None,
        expected_output: Optional[str] = None,
        agent: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Create Task dictionary.

        ✅ Important: Uses 'agent' field (not 'agent_id')

        Args:
            task_id: Task ID
            description: Task description
            expected_output: Expected output
            agent: Agent ID (who executes this task)
            **kwargs: Additional fields

        Returns:
            Dictionary ready for TaskSpecModel(**data)

        Example:
            >>> task = TaskFactory.create(
            ...     task_id="add_task",
            ...     description="Add a new task",
            ...     agent="task_manager"
            ... )
        """
        return {
            "id": task_id or cls.DEFAULT_TASK["id"],
            "description": description or cls.DEFAULT_TASK["description"],
            "expected_output": expected_output or cls.DEFAULT_TASK["expected_output"],
            "agent": agent or cls.DEFAULT_TASK["agent"],  # ✅ Correct field name
            **kwargs,
        }

    @classmethod
    def create_batch(
        cls,
        count: int,
        agent: str = "agent_default",
        prefix: str = "task",
    ) -> List[Dict]:
        """
        Create multiple tasks for an agent.

        Args:
            count: Number of tasks to create
            agent: Agent ID who executes tasks
            prefix: Task ID prefix

        Returns:
            List of task dictionaries

        Example:
            >>> tasks = TaskFactory.create_batch(3, agent="manager", prefix="work")
            >>> len(tasks)
            3
            >>> tasks[0]["agent"]
            'manager'
        """
        return [
            cls.create(
                task_id=f"{prefix}_{i}",
                description=f"{prefix.title()} {i} description",
                expected_output=f"Output for {prefix} {i}",
                agent=agent,
            )
            for i in range(1, count + 1)
        ]


class FileArtifactFactory:
    """
    Factory for creating code artifact dictionaries.
    """

    @staticmethod
    def create_flat(files: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Create flat code artifact structure.

        Args:
            files: File dictionary (default: sample files)

        Returns:
            Flat dictionary: {"main.py": "...", "agents.py": "..."}

        Example:
            >>> artifacts = FileArtifactFactory.create_flat({
            ...     "main.py": "print('hello')",
            ... })
        """
        if files is None:
            files = {
                "main.py": "#!/usr/bin/env python\nprint('Main')",
                "agents.py": "# Agent definitions",
                "tasks.py": "# Task definitions",
            }
        return files

    @staticmethod
    def create_nested(files: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Create nested code artifact structure.

        Args:
            files: File dictionary

        Returns:
            Nested dictionary: {"files": {"main.py": "...", ...}}

        Example:
            >>> artifacts = FileArtifactFactory.create_nested()
            >>> "files" in artifacts
            True
        """
        return {"files": FileArtifactFactory.create_flat(files)}


# Convenience aliases
create_golden_data = GoldenDataFactory.create
create_agent = AgentFactory.create
create_task = TaskFactory.create


if __name__ == "__main__":
    # Demo usage
    print("=== Golden Data Factory ===")
    golden = GoldenDataFactory.create_with_features(
        "demo_app", "Demo Application", feature_count=2
    )
    print(f"Created Golden Data with {len(golden['features'])} features")

    print("\n=== Agent Factory ===")
    agents = AgentFactory.create_batch(3, prefix="worker")
    print(f"Created {len(agents)} agents")

    print("\n=== Task Factory ===")
    tasks = TaskFactory.create_batch(3, agent="worker_1", prefix="job")
    print(f"Created {len(tasks)} tasks")

    print("\n=== File Artifact Factory ===")
    flat = FileArtifactFactory.create_flat()
    nested = FileArtifactFactory.create_nested()
    print(f"Flat: {list(flat.keys())}")
    print(f"Nested: {list(nested.keys())}")
