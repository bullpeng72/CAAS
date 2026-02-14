"""
Unit Tests for YAML Exporter

Tests for caas_framework/sdd/yaml_exporter.py

Part of CAAS-E Week 4 implementation (Task 4.1).
"""

import pytest
import yaml
from pathlib import Path
from datetime import datetime

from caas_framework.sdd.yaml_exporter import YAMLExporter, export_specifications
from caas_framework.models.specifications import (
    ConcretizedRequirement,
    AgentSpecModel,
    TaskSpecModel,
    FeatureSpec,
    SystemScope,
)


@pytest.fixture
def sample_golden_data():
    """Create sample Golden Data for testing."""
    return ConcretizedRequirement(
        domain="E_COMMERCE",
        project_name="Todo App",
        description="Simple todo management system",
        system_scope=SystemScope(
            project_name="Todo App",
            purpose="Task management",
            target_users=["End users"],
        ),
        features=[
            FeatureSpec(
                id="F1",
                name="Create Todo",
                description="User can create a todo item",
                priority="high",
                acceptance_criteria=["Todo created successfully"],
                api_contract={
                    "endpoint": "POST /api/todos",
                    "inputs": {"title": "string", "description": "string"},
                    "outputs": {"id": "UUID", "title": "string"},
                    "error_cases": ["400: Invalid input"],
                },
                data_model={
                    "entity": "Todo",
                    "schema": {
                        "id": "UUID (primary key)",
                        "title": "str (required)",
                        "description": "str (optional)",
                        "completed": "bool (default: false)",
                    },
                    "validation_rules": ["Title must not be empty"],
                },
                business_rules=[
                    "A todo must have a title",
                    "Completed todos cannot be edited",
                ],
                test_scenarios=[
                    {
                        "name": "Create todo successfully",
                        "given": "User is logged in",
                        "when": "User submits todo form with valid data",
                        "then": "Todo is created and saved to database",
                    }
                ],
            ),
            FeatureSpec(
                id="F2",
                name="List Todos",
                description="User can view all todos",
                priority="medium",
                acceptance_criteria=["Todos displayed in list"],
            ),
        ],
    )


@pytest.fixture
def sample_agents():
    """Create sample agent specs for testing."""
    return [
        AgentSpecModel(
            id="todo_creator",
            role="Todo Creator",
            goal="Create new todo items",
            backstory="Expert at creating todos",
            tools=["database_tool", "validation_tool"],
        ),
        AgentSpecModel(
            id="todo_lister",
            role="Todo Lister",
            goal="List all todos",
            backstory="Expert at listing todos",
            tools=["database_tool"],
        ),
    ]


@pytest.fixture
def sample_tasks():
    """Create sample task specs for testing."""
    return [
        TaskSpecModel(
            id="create_todo_task",
            description="Create a new todo item",
            expected_output="Todo ID",
            agent="todo_creator",
            context=[],
        ),
        TaskSpecModel(
            id="list_todos_task",
            description="List all todo items",
            expected_output="List of todos",
            agent="todo_lister",
            context=["create_todo_task"],
        ),
    ]


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    return tmp_path / "specs"


class TestYAMLExporter:
    """Test YAMLExporter class."""

    def test_init(self, temp_output_dir):
        """Test YAMLExporter initialization."""
        exporter = YAMLExporter(temp_output_dir)

        assert exporter.output_dir == temp_output_dir
        assert temp_output_dir.exists()

    def test_export_agent_specs(self, temp_output_dir, sample_agents):
        """Test exporting agent specs to YAML."""
        exporter = YAMLExporter(temp_output_dir)

        # Export
        output_file = exporter.export_agent_specs(sample_agents)

        # Verify file exists
        assert output_file.exists()
        assert output_file.name == "agent_specs.yaml"

        # Load and verify YAML content
        with open(output_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert "metadata" in data
        assert data["metadata"]["total_agents"] == 2

        assert "agents" in data
        assert len(data["agents"]) == 2

        # Verify first agent
        agent = data["agents"][0]
        assert agent["id"] == "todo_creator"
        assert agent["role"] == "Todo Creator"
        assert "database_tool" in agent["tools"]

    def test_export_task_specs(self, temp_output_dir, sample_tasks):
        """Test exporting task specs to YAML."""
        exporter = YAMLExporter(temp_output_dir)

        # Export
        output_file = exporter.export_task_specs(sample_tasks)

        # Verify file exists
        assert output_file.exists()
        assert output_file.name == "task_specs.yaml"

        # Load and verify YAML content
        with open(output_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert "metadata" in data
        assert data["metadata"]["total_tasks"] == 2

        assert "tasks" in data
        assert len(data["tasks"]) == 2

        # Verify first task
        task = data["tasks"][0]
        assert task["id"] == "create_todo_task"
        assert task["agent"] == "todo_creator"

    def test_export_tool_specs(self, temp_output_dir, sample_golden_data, sample_agents):
        """Test exporting tool specs to YAML."""
        exporter = YAMLExporter(temp_output_dir)

        # Export
        output_file = exporter.export_tool_specs(sample_golden_data, sample_agents)

        # Verify file exists
        assert output_file.exists()
        assert output_file.name == "tool_specs.yaml"

        # Load and verify YAML content
        with open(output_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert "metadata" in data
        assert "tools" in data

        # Verify tools from agents
        tool_names = [t["name"] for t in data["tools"]]
        assert "database_tool" in tool_names
        assert "validation_tool" in tool_names

    def test_export_data_models(self, temp_output_dir, sample_golden_data):
        """Test exporting data models to YAML."""
        exporter = YAMLExporter(temp_output_dir)

        # Export
        output_file = exporter.export_data_models(sample_golden_data)

        # Verify file exists
        assert output_file.exists()
        assert output_file.name == "data_models.yaml"

        # Load and verify YAML content
        with open(output_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert "metadata" in data
        assert data["metadata"]["total_models"] == 1

        assert "data_models" in data
        assert len(data["data_models"]) == 1

        # Verify data model
        model = data["data_models"][0]
        assert model["feature_id"] == "F1"
        assert model["entity"] == "Todo"
        assert "id" in model["schema"]
        assert "Title must not be empty" in model["validation_rules"]

    def test_export_business_rules(self, temp_output_dir, sample_golden_data):
        """Test exporting business rules to YAML."""
        exporter = YAMLExporter(temp_output_dir)

        # Export
        output_file = exporter.export_business_rules(sample_golden_data)

        # Verify file exists
        assert output_file.exists()
        assert output_file.name == "business_rules.yaml"

        # Load and verify YAML content
        with open(output_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert "metadata" in data
        assert data["metadata"]["total_features_with_rules"] == 1
        assert data["metadata"]["total_rules"] == 2

        assert "business_rules" in data
        assert len(data["business_rules"]) == 1

        # Verify business rules
        rules = data["business_rules"][0]
        assert rules["feature_id"] == "F1"
        assert "A todo must have a title" in rules["rules"]

    def test_export_api_contracts(self, temp_output_dir, sample_golden_data):
        """Test exporting API contracts to YAML."""
        exporter = YAMLExporter(temp_output_dir)

        # Export
        output_file = exporter.export_api_contracts(sample_golden_data)

        # Verify file exists
        assert output_file.exists()
        assert output_file.name == "api_contracts.yaml"

        # Load and verify YAML content
        with open(output_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert "metadata" in data
        assert data["metadata"]["total_contracts"] == 1

        assert "api_contracts" in data
        assert len(data["api_contracts"]) == 1

        # Verify API contract
        contract = data["api_contracts"][0]
        assert contract["feature_id"] == "F1"
        assert contract["endpoint"] == "POST /api/todos"
        assert "title" in contract["inputs"]

    def test_export_all(
        self, temp_output_dir, sample_golden_data, sample_agents, sample_tasks
    ):
        """Test exporting all specs at once."""
        exporter = YAMLExporter(temp_output_dir)

        # Export all
        exported_files = exporter.export_all(
            sample_golden_data, sample_agents, sample_tasks
        )

        # Verify all files exported
        assert "agents" in exported_files
        assert "tasks" in exported_files
        assert "tools" in exported_files
        assert "data_models" in exported_files
        assert "business_rules" in exported_files

        # Verify all files exist
        for file_path in exported_files.values():
            assert file_path.exists()

    def test_infer_tool_type(self, temp_output_dir):
        """Test tool type inference."""
        exporter = YAMLExporter(temp_output_dir)

        assert exporter._infer_tool_type("search_tool") == "search"
        assert exporter._infer_tool_type("file_reader") == "file_operations"
        assert exporter._infer_tool_type("web_scraper") == "web_scraping"
        assert exporter._infer_tool_type("api_client") == "api_integration"
        assert exporter._infer_tool_type("database_query") == "database"
        assert exporter._infer_tool_type("custom_tool") == "custom"


class TestExportSpecificationsFunction:
    """Test export_specifications convenience function."""

    def test_export_specifications(
        self, temp_output_dir, sample_golden_data, sample_agents, sample_tasks
    ):
        """Test export_specifications convenience function."""
        exported_files = export_specifications(
            output_dir=temp_output_dir,
            golden_data=sample_golden_data,
            agents=sample_agents,
            tasks=sample_tasks,
            include_api_contracts=True,
        )

        # Verify all files exported (5 + 1 bonus)
        assert len(exported_files) == 6
        assert "api_contracts" in exported_files

        # Verify all files exist
        for file_path in exported_files.values():
            assert file_path.exists()

    def test_export_specifications_minimal(self, temp_output_dir, sample_golden_data):
        """Test export_specifications with minimal inputs."""
        exported_files = export_specifications(
            output_dir=temp_output_dir,
            golden_data=sample_golden_data,
        )

        # Verify minimal files exported
        assert "tools" in exported_files
        assert "data_models" in exported_files
        assert "business_rules" in exported_files

        # Agents and tasks should not be in result if not provided
        assert "agents" not in exported_files
        assert "tasks" not in exported_files


class TestYAMLEncoding:
    """Test YAML encoding and Unicode support."""

    def test_korean_encoding(self, temp_output_dir):
        """Test Korean text encoding in YAML."""
        golden_data = ConcretizedRequirement(
            domain="E_COMMERCE",
            project_name="할일 앱",
            description="간단한 할일 관리 시스템",
            system_scope=SystemScope(
                project_name="할일 앱",
                purpose="작업 관리",
                target_users=["최종 사용자"],
            ),
            features=[
                FeatureSpec(
                    id="F1",
                    name="할일 생성",
                    description="사용자가 할일을 생성할 수 있음",
                    priority="high",
                    business_rules=["할일은 제목이 있어야 함"],
                )
            ],
        )

        exporter = YAMLExporter(temp_output_dir)
        output_file = exporter.export_business_rules(golden_data)

        # Load and verify Korean text
        with open(output_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        rules = data["business_rules"][0]
        assert "할일은 제목이 있어야 함" in rules["rules"]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_features(self, temp_output_dir):
        """Test export with no features."""
        golden_data = ConcretizedRequirement(
            domain="CUSTOM",
            project_name="Empty Project",
            description="Project with no features",
            system_scope=SystemScope(
                project_name="Empty Project",
                purpose="Testing",
                target_users=[],
            ),
            features=[],
        )

        exporter = YAMLExporter(temp_output_dir)

        # Export should succeed even with empty features
        data_models_file = exporter.export_data_models(golden_data)
        assert data_models_file.exists()

        with open(data_models_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert data["metadata"]["total_models"] == 0
        assert len(data["data_models"]) == 0

    def test_features_without_sdd_fields(self, temp_output_dir):
        """Test export with features missing SDD fields."""
        golden_data = ConcretizedRequirement(
            domain="CUSTOM",
            project_name="Minimal Project",
            description="Project with minimal features",
            system_scope=SystemScope(
                project_name="Minimal Project",
                purpose="Testing",
                target_users=[],
            ),
            features=[
                FeatureSpec(
                    id="F1",
                    name="Basic Feature",
                    description="Feature without SDD fields",
                    priority="low",
                    # No api_contract, data_model, or business_rules
                )
            ],
        )

        exporter = YAMLExporter(temp_output_dir)

        # Export should succeed
        exported_files = exporter.export_all(golden_data)

        # Verify files exist but have no data
        with open(exported_files["data_models"], 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        assert data["metadata"]["total_models"] == 0

        with open(exported_files["business_rules"], 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        assert data["metadata"]["total_rules"] == 0
