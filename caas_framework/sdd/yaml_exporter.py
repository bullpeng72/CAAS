"""
YAML Specification Exporter

Exports Golden Data and specifications to YAML files for Spec-Driven Development (SDD).

Generates 5 YAML files:
1. agent_specs.yaml - Agent specifications
2. task_specs.yaml - Task specifications
3. tool_specs.yaml - Tool specifications
4. data_models.yaml - Data model schemas
5. business_rules.yaml - Business rules

Part of CAAS-E Week 4 implementation (Task 4.1).
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from caas_framework.models.specifications import (
    AgentSpecModel,
    TaskSpecModel,
    FeatureSpec,
    ConcretizedRequirement,
)
from caas_framework.utils.logger import get_logger


class YAMLExporter:
    """
    YAML Specification Exporter for SDD (Spec-Driven Development).

    Exports structured specifications from Golden Data to YAML files
    that can be used for:
    - Documentation
    - Code generation
    - Test generation (TDD RED phase)
    - Validation
    - Human review
    """

    def __init__(self, output_dir: Path):
        """
        Initialize YAML Exporter.

        Args:
            output_dir: Directory to write YAML files
        """
        self.output_dir = Path(output_dir)
        self.logger = get_logger(__name__)

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        golden_data: ConcretizedRequirement,
        agents: Optional[List[AgentSpecModel]] = None,
        tasks: Optional[List[TaskSpecModel]] = None,
    ) -> Dict[str, Path]:
        """
        Export all specifications to YAML files.

        Args:
            golden_data: Golden Data (ConcretizedRequirement)
            agents: Optional list of agent specs (if available)
            tasks: Optional list of task specs (if available)

        Returns:
            Dict mapping spec type to file path
        """
        self.logger.info(f"Exporting specifications to {self.output_dir}")

        exported_files = {}

        # 1. Export agent specs
        if agents:
            agent_file = self.export_agent_specs(agents)
            exported_files["agents"] = agent_file
            self.logger.info(f"✅ Exported {len(agents)} agents to {agent_file.name}")

        # 2. Export task specs
        if tasks:
            task_file = self.export_task_specs(tasks)
            exported_files["tasks"] = task_file
            self.logger.info(f"✅ Exported {len(tasks)} tasks to {task_file.name}")

        # 3. Export tool specs (from agents and Golden Data)
        tool_file = self.export_tool_specs(golden_data, agents)
        exported_files["tools"] = tool_file
        self.logger.info(f"✅ Exported tool specs to {tool_file.name}")

        # 4. Export data models (from Golden Data features)
        data_model_file = self.export_data_models(golden_data)
        exported_files["data_models"] = data_model_file
        self.logger.info(f"✅ Exported data models to {data_model_file.name}")

        # 5. Export business rules (from Golden Data features)
        business_rules_file = self.export_business_rules(golden_data)
        exported_files["business_rules"] = business_rules_file
        self.logger.info(f"✅ Exported business rules to {business_rules_file.name}")

        self.logger.info(f"🎉 Successfully exported {len(exported_files)} specification files")

        return exported_files

    def export_agent_specs(self, agents: List[AgentSpecModel]) -> Path:
        """
        Export agent specifications to YAML.

        Args:
            agents: List of agent specs

        Returns:
            Path to agent_specs.yaml
        """
        output_file = self.output_dir / "agent_specs.yaml"

        # Convert agents to dict format
        agents_data = {
            "metadata": {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "total_agents": len(agents),
            },
            "agents": [
                {
                    "id": agent.id,
                    "role": agent.role,
                    "goal": agent.goal,
                    "backstory": agent.backstory,
                    "tools": agent.tools,
                    "verbose": agent.verbose,
                    "memory": agent.memory,
                    "allow_delegation": agent.allow_delegation,
                    "max_iter": agent.max_iter,
                }
                for agent in agents
            ],
        }

        # Write YAML
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(
                agents_data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        return output_file

    def export_task_specs(self, tasks: List[TaskSpecModel]) -> Path:
        """
        Export task specifications to YAML.

        Args:
            tasks: List of task specs

        Returns:
            Path to task_specs.yaml
        """
        output_file = self.output_dir / "task_specs.yaml"

        # Convert tasks to dict format
        tasks_data = {
            "metadata": {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "total_tasks": len(tasks),
            },
            "tasks": [
                {
                    "id": task.id,
                    "description": task.description,
                    "expected_output": task.expected_output,
                    "agent": task.agent,
                    "context": task.context,
                    "async_execution": task.async_execution,
                    "output_file": task.output_file,
                    "human_input": task.human_input,
                }
                for task in tasks
            ],
        }

        # Write YAML
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(
                tasks_data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        return output_file

    def export_tool_specs(
        self,
        golden_data: ConcretizedRequirement,
        agents: Optional[List[AgentSpecModel]] = None,
    ) -> Path:
        """
        Export tool specifications to YAML.

        Extracts tools from:
        1. Agent tool assignments
        2. Feature requirements

        Args:
            golden_data: Golden Data
            agents: Optional list of agent specs

        Returns:
            Path to tool_specs.yaml
        """
        output_file = self.output_dir / "tool_specs.yaml"

        # Collect unique tools
        tools_set = set()

        # From agents
        if agents:
            for agent in agents:
                tools_set.update(agent.tools)

        # From features (if they specify required tools)
        for feature in golden_data.features:
            # Check if feature has tool requirements in description
            # This is a simple heuristic - could be enhanced
            if "tool" in feature.description.lower():
                # Extract tool names (this is simplified)
                pass

        # Create tool specs
        tools_data = {
            "metadata": {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "total_tools": len(tools_set),
            },
            "tools": [
                {
                    "name": tool_name,
                    "description": f"Tool for {tool_name.replace('_', ' ')}",
                    "type": self._infer_tool_type(tool_name),
                    "required": True,
                }
                for tool_name in sorted(tools_set)
            ],
        }

        # Write YAML
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(
                tools_data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        return output_file

    def export_data_models(self, golden_data: ConcretizedRequirement) -> Path:
        """
        Export data model schemas to YAML.

        Extracts data models from feature specs (data_model field).

        Args:
            golden_data: Golden Data

        Returns:
            Path to data_models.yaml
        """
        output_file = self.output_dir / "data_models.yaml"

        # Extract data models from features
        data_models = []

        for feature in golden_data.features:
            if feature.data_model:
                model_data = {
                    "feature_id": feature.id,
                    "feature_name": feature.name,
                    "entity": feature.data_model.get("entity", "Unknown"),
                    "schema": feature.data_model.get("schema", {}),
                    "validation_rules": feature.data_model.get("validation_rules", []),
                }
                data_models.append(model_data)

        # Create data models spec
        data_models_data = {
            "metadata": {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "total_models": len(data_models),
            },
            "data_models": data_models,
        }

        # Write YAML
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(
                data_models_data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        return output_file

    def export_business_rules(self, golden_data: ConcretizedRequirement) -> Path:
        """
        Export business rules to YAML.

        Extracts business rules from feature specs.

        Args:
            golden_data: Golden Data

        Returns:
            Path to business_rules.yaml
        """
        output_file = self.output_dir / "business_rules.yaml"

        # Extract business rules from features
        rules_by_feature = []

        for feature in golden_data.features:
            if feature.business_rules:
                rule_data = {
                    "feature_id": feature.id,
                    "feature_name": feature.name,
                    "rules": feature.business_rules,
                }
                rules_by_feature.append(rule_data)

        # Create business rules spec
        business_rules_data = {
            "metadata": {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "total_features_with_rules": len(rules_by_feature),
                "total_rules": sum(len(r["rules"]) for r in rules_by_feature),
            },
            "business_rules": rules_by_feature,
        }

        # Write YAML
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(
                business_rules_data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        return output_file

    def export_api_contracts(self, golden_data: ConcretizedRequirement) -> Path:
        """
        Export API contracts to YAML (bonus file).

        Extracts API contracts from feature specs.

        Args:
            golden_data: Golden Data

        Returns:
            Path to api_contracts.yaml
        """
        output_file = self.output_dir / "api_contracts.yaml"

        # Extract API contracts from features
        api_contracts = []

        for feature in golden_data.features:
            if feature.api_contract:
                contract_data = {
                    "feature_id": feature.id,
                    "feature_name": feature.name,
                    "endpoint": feature.api_contract.get("endpoint", ""),
                    "inputs": feature.api_contract.get("inputs", {}),
                    "outputs": feature.api_contract.get("outputs", {}),
                    "error_cases": feature.api_contract.get("error_cases", []),
                }
                api_contracts.append(contract_data)

        # Create API contracts spec
        api_contracts_data = {
            "metadata": {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "total_contracts": len(api_contracts),
            },
            "api_contracts": api_contracts,
        }

        # Write YAML
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(
                api_contracts_data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        return output_file

    def _infer_tool_type(self, tool_name: str) -> str:
        """
        Infer tool type from tool name.

        Args:
            tool_name: Tool name

        Returns:
            Tool type category
        """
        tool_name_lower = tool_name.lower()

        # Search tools
        if any(keyword in tool_name_lower for keyword in ["search", "serper", "google", "duckduckgo"]):
            return "search"

        # File tools
        if any(keyword in tool_name_lower for keyword in ["file", "read", "write", "directory"]):
            return "file_operations"

        # Web tools
        if any(keyword in tool_name_lower for keyword in ["scrape", "web", "browser", "selenium"]):
            return "web_scraping"

        # API tools
        if any(keyword in tool_name_lower for keyword in ["api", "http", "request"]):
            return "api_integration"

        # Database tools
        if any(keyword in tool_name_lower for keyword in ["database", "sql", "query"]):
            return "database"

        # Default
        return "custom"


def export_specifications(
    output_dir: Path,
    golden_data: ConcretizedRequirement,
    agents: Optional[List[AgentSpecModel]] = None,
    tasks: Optional[List[TaskSpecModel]] = None,
    include_api_contracts: bool = False,
) -> Dict[str, Path]:
    """
    Convenience function to export all specifications.

    Args:
        output_dir: Directory to write YAML files
        golden_data: Golden Data (ConcretizedRequirement)
        agents: Optional list of agent specs
        tasks: Optional list of task specs
        include_api_contracts: Whether to include api_contracts.yaml (bonus file)

    Returns:
        Dict mapping spec type to file path
    """
    exporter = YAMLExporter(output_dir)

    # Export main 5 files
    exported_files = exporter.export_all(golden_data, agents, tasks)

    # Optional: Export API contracts
    if include_api_contracts:
        api_contracts_file = exporter.export_api_contracts(golden_data)
        exported_files["api_contracts"] = api_contracts_file

    return exported_files
