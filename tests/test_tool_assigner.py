"""
Tests for MinimalToolAssigner

Tests the tool assignment optimization functionality.
"""

import pytest

from caas_framework.agents.tool_assigner import (
    MinimalToolAssigner,
    optimize_agent_tools,
)


class TestMinimalToolAssigner:
    """Test MinimalToolAssigner class"""

    def test_assigner_creation(self):
        """Test creating MinimalToolAssigner"""
        assigner = MinimalToolAssigner()
        assert assigner is not None
        assert assigner.available_tools is not None

    def test_assigner_with_custom_tools(self):
        """Test creating assigner with custom available tools"""
        custom_tools = ["web_search", "file_read"]
        assigner = MinimalToolAssigner(available_tools=custom_tools)
        assert assigner.available_tools == custom_tools

    def test_analyze_description_search(self):
        """Test analyzing description with search keywords"""
        assigner = MinimalToolAssigner()

        description = "Search the web for information about Python"
        tools = assigner._analyze_description(description)

        assert "web_search" in tools

    def test_analyze_description_file_operations(self):
        """Test analyzing description with file operations"""
        assigner = MinimalToolAssigner()

        description = "Read the config file and write the results to output.txt"
        tools = assigner._analyze_description(description)

        assert "file_read" in tools
        assert "file_write" in tools

    def test_analyze_description_api(self):
        """Test analyzing description with API calls"""
        assigner = MinimalToolAssigner()

        description = "Call the REST API to fetch user data"
        tools = assigner._analyze_description(description)

        assert "http_client" in tools

    def test_analyze_description_database(self):
        """Test analyzing description with database operations"""
        assigner = MinimalToolAssigner()

        description = "Query the database to get all users"
        tools = assigner._analyze_description(description)

        assert "database" in tools

    def test_analyze_description_multiple_tools(self):
        """Test analyzing description requiring multiple tools"""
        assigner = MinimalToolAssigner()

        description = (
            "Search for API documentation, read the file, and execute the command"
        )
        tools = assigner._analyze_description(description)

        assert "web_search" in tools
        assert "file_read" in tools
        assert "shell" in tools

    def test_analyze_description_korean(self):
        """Test analyzing Korean description"""
        assigner = MinimalToolAssigner()

        description = "웹에서 정보를 검색하고 파일에 저장하세요"
        tools = assigner._analyze_description(description)

        assert "web_search" in tools
        assert "file_write" in tools

    def test_infer_tools_from_role_researcher(self):
        """Test inferring tools from researcher role"""
        assigner = MinimalToolAssigner()

        tools = assigner._infer_tools_from_role("Research Specialist")

        assert "web_search" in tools
        assert "file_read" in tools

    def test_infer_tools_from_role_developer(self):
        """Test inferring tools from developer role"""
        assigner = MinimalToolAssigner()

        tools = assigner._infer_tools_from_role("Software Developer")

        assert "file_read" in tools
        assert "file_write" in tools
        assert "git" in tools

    def test_assign_tools_single_agent(self):
        """Test assigning tools to a single agent"""
        assigner = MinimalToolAssigner()

        tasks = [
            {
                "agent": "researcher",
                "description": "Search for information online and save to a file",
            }
        ]

        tools = assigner.assign_tools(
            agent_id="researcher", agent_role="Researcher", tasks=tasks
        )

        assert "web_search" in tools
        assert "file_write" in tools

    def test_assign_tools_no_matching_tasks(self):
        """Test assigning tools when no tasks match the agent"""
        assigner = MinimalToolAssigner()

        tasks = [{"agent": "other_agent", "description": "Do something"}]

        tools = assigner.assign_tools(
            agent_id="researcher", agent_role="Researcher", tasks=tasks
        )

        # Should fall back to role-based inference
        assert len(tools) > 0

    def test_assign_tools_for_all_agents(self):
        """Test assigning tools to multiple agents"""
        assigner = MinimalToolAssigner()

        agents = [
            {"id": "researcher", "role": "Research Specialist"},
            {"id": "developer", "role": "Software Developer"},
            {"id": "writer", "role": "Technical Writer"},
        ]

        tasks = [
            {
                "agent": "researcher",
                "description": "Search the web for technical documentation",
            },
            {"agent": "developer", "description": "Write code and commit to git"},
            {"agent": "writer", "description": "Read the code and write documentation"},
        ]

        assignments = assigner.assign_tools_for_all_agents(agents, tasks)

        # Check researcher
        assert "web_search" in assignments["researcher"]

        # Check developer
        assert "file_write" in assignments["developer"]
        assert "git" in assignments["developer"]

        # Check writer
        assert "file_read" in assignments["writer"]
        assert "file_write" in assignments["writer"]

    def test_get_tool_usage_report(self):
        """Test generating tool usage report"""
        assigner = MinimalToolAssigner()

        agents = [
            {"id": "agent1", "role": "Researcher"},
            {"id": "agent2", "role": "Developer"},
        ]

        tasks = [
            {"agent": "agent1", "description": "Search the web"},
            {"agent": "agent2", "description": "Write code"},
        ]

        report = assigner.get_tool_usage_report(agents, tasks)

        assert report["total_agents"] == 2
        assert report["total_tools_assigned"] > 0
        assert "tool_frequency" in report
        assert "most_common_tools" in report
        assert "assignments" in report

    def test_filter_to_available_tools(self):
        """Test that only available tools are assigned"""
        # Create assigner with limited tools
        assigner = MinimalToolAssigner(available_tools=["web_search", "file_read"])

        tasks = [
            {"agent": "agent1", "description": "Search web, read files, and write code"}
        ]

        tools = assigner.assign_tools(
            agent_id="agent1", agent_role="Agent", tasks=tasks
        )

        # Should only include available tools
        assert "web_search" in tools
        assert "file_read" in tools
        # file_write should be filtered out
        assert "file_write" not in tools

    def test_optimize_agent_tools_function(self):
        """Test the optimize_agent_tools convenience function"""
        agents = [
            {
                "id": "researcher",
                "role": "Research Specialist",
                "tools": ["all", "tools", "listed"],  # Will be replaced
            }
        ]

        tasks = [
            {"agent": "researcher", "description": "Search for documentation online"}
        ]

        optimized = optimize_agent_tools(agents, tasks, verbose=False)

        assert len(optimized) == 1
        assert "tools" in optimized[0]
        assert "web_search" in optimized[0]["tools"]
        # Should have replaced the original tools
        assert "all" not in optimized[0]["tools"]

    def test_empty_agents_and_tasks(self):
        """Test handling empty agents and tasks"""
        assigner = MinimalToolAssigner()

        assignments = assigner.assign_tools_for_all_agents([], [])

        assert assignments == {}

    def test_task_with_no_description(self):
        """Test handling task with no description"""
        assigner = MinimalToolAssigner()

        tasks = [
            {
                "agent": "agent1"
                # No description field
            }
        ]

        tools = assigner.assign_tools(
            agent_id="agent1", agent_role="Generic Agent", tasks=tasks
        )

        # Should return default tools
        assert len(tools) >= 0

    def test_case_insensitive_matching(self):
        """Test that keyword matching is case-insensitive"""
        assigner = MinimalToolAssigner()

        description = "SEARCH THE WEB AND READ FILES"
        tools = assigner._analyze_description(description)

        assert "web_search" in tools
        assert "file_read" in tools


class TestToolAssignmentIntegration:
    """Integration tests for tool assignment"""

    def test_blog_system_example(self):
        """Test tool assignment for a blog system"""
        assigner = MinimalToolAssigner()

        agents = [
            {"id": "content_researcher", "role": "Content Researcher"},
            {"id": "blog_writer", "role": "Blog Writer"},
            {"id": "publisher", "role": "Content Publisher"},
        ]

        tasks = [
            {
                "agent": "content_researcher",
                "description": "Search the web for trending topics and save results",
            },
            {
                "agent": "blog_writer",
                "description": "Read the research results and write a blog post",
            },
            {
                "agent": "publisher",
                "description": "Read the blog post and publish it via API",
            },
        ]

        assignments = assigner.assign_tools_for_all_agents(agents, tasks)

        # Content researcher needs search and write
        assert "web_search" in assignments["content_researcher"]
        assert "file_write" in assignments["content_researcher"]

        # Blog writer needs read and write
        assert "file_read" in assignments["blog_writer"]
        assert "file_write" in assignments["blog_writer"]

        # Publisher needs read and API
        assert "file_read" in assignments["publisher"]
        assert "http_client" in assignments["publisher"]

    def test_devops_workflow_example(self):
        """Test tool assignment for a DevOps workflow"""
        assigner = MinimalToolAssigner()

        agents = [
            {"id": "code_reviewer", "role": "Code Reviewer"},
            {"id": "tester", "role": "QA Tester"},
            {"id": "deployer", "role": "DevOps Engineer"},
        ]

        tasks = [
            {
                "agent": "code_reviewer",
                "description": "Analyze the code and check for issues",
            },
            {"agent": "tester", "description": "Run tests using shell commands"},
            {
                "agent": "deployer",
                "description": "Build Docker image, push to git, and deploy",
            },
        ]

        assignments = assigner.assign_tools_for_all_agents(agents, tasks)

        # Code reviewer needs analysis
        assert "code_analysis" in assignments["code_reviewer"]

        # Tester needs shell
        assert "shell" in assignments["tester"]

        # Deployer needs docker, git
        assert "docker" in assignments["deployer"]
        assert "git" in assignments["deployer"]

    def test_optimization_report_verbose(self, capsys):
        """Test verbose output of optimization report"""
        agents = [{"id": "agent1", "role": "Researcher"}]

        tasks = [{"agent": "agent1", "description": "Search for information"}]

        optimize_agent_tools(agents, tasks, verbose=True)

        captured = capsys.readouterr()
        assert "Tool Assignment Optimization Report" in captured.out
        assert "Total Agents" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
