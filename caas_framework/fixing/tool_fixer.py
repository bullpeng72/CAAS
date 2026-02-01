"""
Tool Fixer

Automatically fixes missing tools in agent definitions.
"""

from typing import List, Dict, Any
import sys
import os


class ToolFixer:
    """
    Automatically detects and fixes missing tools in agent definitions.
    """

    @staticmethod
    def detect_missing_tools(
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Detect which agents are missing tools based on their tasks.

        Args:
            agents: List of agent definitions
            tasks: List of task definitions

        Returns:
            Dict[agent_id, List[recommended_tools]]
        """
        # Import tool recommendation function
        try:
            app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'app')
            if app_path not in sys.path:
                sys.path.insert(0, app_path)

            from caas_app.codegen.tool_generator import get_recommended_tools_for_task
            tool_func_available = True
        except ImportError:
            tool_func_available = False

        missing_tools = {}

        # Build agent map
        agent_map = {agent.get("id"): agent for agent in agents}

        # Check each task
        for task in tasks:
            agent_id = task.get("agent")
            if not agent_id or agent_id not in agent_map:
                continue

            agent = agent_map[agent_id]
            current_tools = agent.get("tools", [])

            # If agent has no tools, recommend based on task
            if not current_tools or len(current_tools) == 0:
                if tool_func_available:
                    recommended = get_recommended_tools_for_task(
                        task_description=task.get("description", ""),
                        agent_role=agent.get("role", "")
                    )

                    if agent_id not in missing_tools:
                        missing_tools[agent_id] = []

                    # Add unique tools
                    for tool in recommended:
                        if tool not in missing_tools[agent_id]:
                            missing_tools[agent_id].append(tool)

        return missing_tools

    @classmethod
    def fix_agents_tools(
        cls,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Automatically fix missing tools in agent definitions.

        Args:
            agents: List of agent definitions
            tasks: List of task definitions

        Returns:
            Fixed agent definitions
        """
        missing_tools = cls.detect_missing_tools(agents, tasks)

        # Apply fixes
        for agent in agents:
            agent_id = agent.get("id")
            if agent_id in missing_tools:
                current_tools = agent.get("tools", [])
                if not current_tools:
                    agent["tools"] = missing_tools[agent_id]
                else:
                    # Merge tools
                    for tool in missing_tools[agent_id]:
                        if tool not in current_tools:
                            current_tools.append(tool)

        return agents
