"""
Agent-Task Matching Utility

Consolidates duplicate agent-task matching logic found across validators.
Eliminates 3+ instances of nested loop patterns for finding suitable agents.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from caas_framework.utils.safe_access import safe_get_value


class AgentMatcher:
    """
    Utility for matching agents to tasks based on roles and requirements.

    Consolidates agent-task matching logic that was duplicated across:
    - ontology_validator.py (2 instances)
    - knowledge/validator.py (1 instance)
    """

    def __init__(self, ontology_manager=None):
        """
        Initialize AgentMatcher.

        Args:
            ontology_manager: Optional OntologyManager for role inference
        """
        self.ontology = ontology_manager

    @staticmethod
    def find_suitable_agent_by_role(
        agents: List[Union[Dict, BaseModel]],
        suitable_roles: List[str],
        ontology_manager=None,
    ) -> Optional[Union[Dict, BaseModel]]:
        """
        Find first agent matching one of the suitable roles.

        Eliminates duplicate nested loop pattern found 3 times in validators.

        Args:
            agents: List of agent dictionaries or models
            suitable_roles: List of acceptable role names
            ontology_manager: Optional OntologyManager for role inference

        Returns:
            First matching agent, or None if no match found

        Example:
            >>> agents = [{"id": "agent1", "role": "Analyst", "goal": "..."}]
            >>> suitable_roles = ["analyst", "researcher"]
            >>> agent = AgentMatcher.find_suitable_agent_by_role(
            ...     agents, suitable_roles, ontology
            ... )
        """
        for role in suitable_roles:
            for agent in agents:
                # Get agent role and goal
                agent_role_text = safe_get_value(agent, "role", "")
                agent_goal = safe_get_value(agent, "goal", "")

                # Infer role from description if ontology available
                if ontology_manager:
                    inferred_role = ontology_manager.infer_role_from_description(
                        f"{agent_role_text} {agent_goal}"
                    )
                    if inferred_role == role:
                        return agent
                else:
                    # Simple string matching if no ontology
                    if role.lower() in agent_role_text.lower():
                        return agent

        return None

    @staticmethod
    def find_agents_by_task_type(
        agents: List[Union[Dict, BaseModel]],
        task_type: str,
        role_mapping: Optional[Dict[str, List[str]]] = None,
    ) -> List[Union[Dict, BaseModel]]:
        """
        Find all agents suitable for a specific task type.

        Args:
            agents: List of agent dictionaries or models
            task_type: Type of task (e.g., "data_analysis", "content_creation")
            role_mapping: Optional mapping of task types to suitable roles

        Returns:
            List of matching agents

        Example:
            >>> role_mapping = {"data_analysis": ["analyst", "researcher"]}
            >>> matching = AgentMatcher.find_agents_by_task_type(
            ...     agents, "data_analysis", role_mapping
            ... )
        """
        if not role_mapping or task_type not in role_mapping:
            return []

        suitable_roles = role_mapping[task_type]
        matching_agents = []

        for agent in agents:
            agent_role = safe_get_value(agent, "role", "").lower()
            for role in suitable_roles:
                if role.lower() in agent_role:
                    matching_agents.append(agent)
                    break

        return matching_agents

    @staticmethod
    def get_agent_tasks(
        agent: Union[Dict, BaseModel],
        tasks: List[Union[Dict, BaseModel]],
    ) -> List[Union[Dict, BaseModel]]:
        """
        Get all tasks assigned to a specific agent.

        Another common pattern consolidated from validators.

        Args:
            agent: Agent dictionary or model
            tasks: List of task dictionaries or models

        Returns:
            List of tasks assigned to this agent

        Example:
            >>> agent = {"id": "analyst_1", "role": "Analyst"}
            >>> agent_tasks = AgentMatcher.get_agent_tasks(agent, all_tasks)
        """
        agent_id = safe_get_value(agent, "id", "unknown").lower()
        agent_role = safe_get_value(agent, "role", "").lower()

        matching_tasks = []
        for task in tasks:
            # Check if task is assigned to this agent
            assigned_agent = safe_get_value(task, "assigned_agent", "")
            task_agent = safe_get_value(task, "agent", "")

            # Match by agent ID or role
            if (
                agent_id in assigned_agent.lower()
                or agent_id in task_agent.lower()
                or agent_role in assigned_agent.lower()
                or agent_role in task_agent.lower()
            ):
                matching_tasks.append(task)

        return matching_tasks

    @staticmethod
    def find_best_agent_for_task(
        task: Union[Dict, BaseModel],
        agents: List[Union[Dict, BaseModel]],
        ontology_manager=None,
    ) -> Optional[Union[Dict, BaseModel]]:
        """
        Find the best agent for a given task based on task type and requirements.

        Args:
            task: Task dictionary or model
            agents: List of available agents
            ontology_manager: Optional OntologyManager for intelligent matching

        Returns:
            Best matching agent, or None if no suitable agent found

        Example:
            >>> task = {"type": "data_analysis", "description": "Analyze metrics"}
            >>> best_agent = AgentMatcher.find_best_agent_for_task(
            ...     task, agents, ontology
            ... )
        """
        # Get task type and description
        task_type = safe_get_value(task, "type", "")
        task_description = safe_get_value(task, "description", "")

        # If ontology available, infer suitable roles
        if ontology_manager and task_type:
            suitable_roles = ontology_manager.get_suitable_roles_for_task_type(
                task_type
            )
            if suitable_roles:
                return AgentMatcher.find_suitable_agent_by_role(
                    agents, suitable_roles, ontology_manager
                )

        # Fallback: simple keyword matching
        keywords = task_description.lower()
        for agent in agents:
            agent_role = safe_get_value(agent, "role", "").lower()
            agent_goal = safe_get_value(agent, "goal", "").lower()

            # Check if agent role/goal matches task keywords
            if any(
                keyword in agent_role or keyword in agent_goal
                for keyword in keywords.split()[:5]  # Check first 5 words
            ):
                return agent

        return None
