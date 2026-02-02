"""
PromptBuildingMixin - Unified Prompt Construction

Eliminates duplicate prompt building logic across 6 agents.
Provides standardized prompt structure for consistency and maintainability.
"""

from typing import Dict, Any, List, Optional
import json


class PromptBuildingMixin:
    """
    Mixin for standardized prompt construction.

    Consolidates duplicate prompt building patterns found in:
    - requirement_analyst.py:94-182 (88 lines)
    - system_architect.py:104-199 (95 lines)
    - agent_designer.py:190-326 (136 lines)
    - code_generator.py:418-498 (80 lines)
    - qa_specialist.py:101-182 (81 lines)
    - self_aware.py:115-180 (~65 lines)

    Total: ~500+ lines of duplicate prompt building code eliminated.
    """

    def build_standard_prompt(
        self,
        role: str,
        task_description: str,
        inputs: Dict[str, Any],
        output_format: Dict[str, str],
        context: Optional[Dict[str, Any]] = None,
        examples: Optional[List[Dict]] = None,
        constraints: Optional[List[str]] = None,
        guidelines: Optional[List[str]] = None
    ) -> str:
        """
        Build standardized prompt with consistent structure.

        Args:
            role: Agent role/expertise (e.g., "Expert Requirement Analyst")
            task_description: What the agent should accomplish
            inputs: Input data for the task (dict of key-value pairs)
            output_format: Expected output fields with descriptions
            context: Optional context information
            examples: Optional examples to guide the agent
            constraints: Optional constraints to follow
            guidelines: Optional guidelines/best practices

        Returns:
            Formatted prompt string

        Example:
            prompt = self.build_standard_prompt(
                role="Expert System Architect",
                task_description="Design system architecture from requirements",
                inputs={"requirement": req, "golden_data": golden},
                output_format={"architecture": "System architecture design", ...}
            )
        """
        # Header
        prompt = f"""# Role
You are a **{role}**.

# Task
{task_description}

"""

        # Inputs Section
        prompt += "# Inputs\n\n"
        for key, value in inputs.items():
            prompt += self._format_input(key, value)

        # Context (if provided)
        if context:
            prompt += "\n# Context\n\n"
            for key, value in context.items():
                if isinstance(value, (dict, list)):
                    prompt += f"**{key}**:\n```json\n{json.dumps(value, indent=2)}\n```\n\n"
                else:
                    prompt += f"- **{key}**: {value}\n"
            prompt += "\n"

        # Constraints (if provided)
        if constraints:
            prompt += "# Constraints\n\n"
            prompt += "You MUST adhere to the following constraints:\n\n"
            for i, constraint in enumerate(constraints, 1):
                prompt += f"{i}. {constraint}\n"
            prompt += "\n"

        # Guidelines (if provided)
        if guidelines:
            prompt += "# Guidelines\n\n"
            for i, guideline in enumerate(guidelines, 1):
                prompt += f"{i}. {guideline}\n"
            prompt += "\n"

        # Examples (if provided)
        if examples:
            prompt += "# Examples\n\n"
            for i, example in enumerate(examples, 1):
                prompt += f"## Example {i}\n\n"
                if isinstance(example, dict):
                    if "input" in example and "output" in example:
                        prompt += f"**Input:**\n```json\n{json.dumps(example['input'], indent=2)}\n```\n\n"
                        prompt += f"**Output:**\n```json\n{json.dumps(example['output'], indent=2)}\n```\n\n"
                    else:
                        prompt += f"```json\n{json.dumps(example, indent=2)}\n```\n\n"
                else:
                    prompt += f"{example}\n\n"

        # Output Format
        prompt += "# Output Format\n\n"
        prompt += "Respond in **JSON format** with the following structure:\n\n"
        prompt += "```json\n{\n"
        for key, description in output_format.items():
            prompt += f'  "{key}": "{description}",\n'
        # Remove trailing comma
        prompt = prompt.rstrip(",\n") + "\n"
        prompt += "}\n```\n\n"
        prompt += "**Important**: Ensure your response is valid JSON that can be parsed.\n"

        return prompt

    def _format_input(self, key: str, value: Any) -> str:
        """
        Format a single input for the prompt.

        Args:
            key: Input name
            value: Input value

        Returns:
            Formatted string
        """
        formatted_key = key.replace("_", " ").title()

        if value is None:
            return f"## {formatted_key}\n\nNot provided.\n\n"

        if isinstance(value, (dict, list)):
            # JSON format for complex types
            return f"## {formatted_key}\n\n```json\n{json.dumps(value, indent=2)}\n```\n\n"

        if isinstance(value, str) and len(value) > 200:
            # Long text
            return f"## {formatted_key}\n\n{value}\n\n"

        # Short text
        return f"## {formatted_key}\n\n{value}\n\n"

    def add_golden_data_context(
        self,
        prompt: str,
        golden_data,
        max_features: int = 10
    ) -> str:
        """
        Add Golden Data context to existing prompt.

        Args:
            prompt: Existing prompt
            golden_data: ConcretizedRequirement object
            max_features: Maximum number of features to show

        Returns:
            Prompt with Golden Data context inserted

        Example:
            prompt = self.build_standard_prompt(...)
            if self.golden_data:
                prompt = self.add_golden_data_context(prompt, self.golden_data)
        """
        if not golden_data:
            return prompt

        # Build Golden Data context
        golden_context = "\n# Golden Data Reference\n\n"
        golden_context += f"**Domain**: {golden_data.domain}\n\n"

        if hasattr(golden_data, 'subdomain') and golden_data.subdomain:
            golden_context += f"**Subdomain**: {golden_data.subdomain}\n\n"

        if hasattr(golden_data, 'features') and golden_data.features:
            golden_context += f"**Key Features** ({len(golden_data.features)} total):\n\n"
            for i, feature in enumerate(golden_data.features[:max_features], 1):
                feature_name = feature.name if hasattr(feature, 'name') else str(feature)
                feature_desc = feature.description if hasattr(feature, 'description') else ""
                golden_context += f"{i}. **{feature_name}**: {feature_desc}\n"

            if len(golden_data.features) > max_features:
                golden_context += f"\n... and {len(golden_data.features) - max_features} more features.\n"

            golden_context += "\n"

        # Insert after Task section
        if "# Task\n" in prompt:
            parts = prompt.split("# Task\n", 1)
            if len(parts) == 2:
                # Find end of task description (next # heading)
                task_parts = parts[1].split("\n# ", 1)
                if len(task_parts) == 2:
                    return parts[0] + "# Task\n" + task_parts[0] + "\n" + golden_context + "\n# " + task_parts[1]
                else:
                    return parts[0] + "# Task\n" + task_parts[0] + "\n" + golden_context

        # Fallback: append at end
        return prompt + "\n" + golden_context

    def add_previous_outputs_context(
        self,
        prompt: str,
        previous_outputs: Dict[str, Any],
        max_outputs: int = 3
    ) -> str:
        """
        Add previous phase outputs to prompt.

        Args:
            prompt: Existing prompt
            previous_outputs: Dict of phase -> output
            max_outputs: Maximum number of outputs to include

        Returns:
            Prompt with previous outputs context

        Example:
            if previous_outputs:
                prompt = self.add_previous_outputs_context(prompt, previous_outputs)
        """
        if not previous_outputs:
            return prompt

        # Build previous outputs context
        prev_context = "\n# Previous Phase Outputs\n\n"
        prev_context += "Use these outputs from previous phases as context:\n\n"

        for i, (phase, output) in enumerate(list(previous_outputs.items())[:max_outputs], 1):
            phase_name = phase.value if hasattr(phase, 'value') else str(phase)
            prev_context += f"## Phase: {phase_name}\n\n"

            if isinstance(output, dict):
                # Show key fields only
                preview = {k: v for k, v in list(output.items())[:5]}
                prev_context += f"```json\n{json.dumps(preview, indent=2)}\n```\n\n"
            else:
                prev_context += f"{str(output)[:500]}...\n\n"

        if len(previous_outputs) > max_outputs:
            prev_context += f"\n... and {len(previous_outputs) - max_outputs} more outputs available.\n\n"

        # Insert after Context section or before Output Format
        if "# Context\n" in prompt:
            parts = prompt.split("# Output Format\n", 1)
            if len(parts) == 2:
                return parts[0] + prev_context + "\n# Output Format\n" + parts[1]

        # Fallback: insert before Output Format
        if "# Output Format\n" in prompt:
            parts = prompt.split("# Output Format\n", 1)
            return parts[0] + prev_context + "\n# Output Format\n" + parts[1]

        # Fallback: append
        return prompt + "\n" + prev_context

    def build_refinement_prompt(
        self,
        role: str,
        original_output: Dict[str, Any],
        validation_issues: List[Any],
        context: Optional[Dict[str, Any]] = None,
        max_issues: int = 20
    ) -> str:
        """
        Build prompt for refinement/improvement based on validation feedback.

        Args:
            role: Agent role
            original_output: Original output that needs refinement
            validation_issues: List of ValidationIssue objects
            context: Optional context
            max_issues: Maximum issues to include in prompt

        Returns:
            Refinement prompt

        Example:
            refinement_prompt = self.build_refinement_prompt(
                role="Expert Agent Designer",
                original_output=design,
                validation_issues=issues
            )
        """
        prompt = f"""# Role
You are a **{role}**.

# Task
Improve and refine the following output based on validation feedback.

# Original Output

```json
{json.dumps(original_output, indent=2)}
```

# Validation Feedback

"""

        # Add issues (using ValidationIssueFactory formatting if available)
        try:
            from caas_framework.validation.issue_factory import ValidationIssueFactory
            prompt += ValidationIssueFactory.format_for_agent(validation_issues, max_issues=max_issues)
        except ImportError:
            # Fallback: simple formatting
            prompt += "The following issues were found:\n\n"
            for i, issue in enumerate(validation_issues[:max_issues], 1):
                message = issue.message if hasattr(issue, 'message') else str(issue)
                prompt += f"{i}. {message}\n"

        prompt += """

# Instructions

1. **Address all validation issues** listed above
2. **Preserve what works** - don't change correct parts
3. **Return complete output** - include all fields, even unchanged ones
4. **Maintain format** - use the same JSON structure as the original

# Output

Provide the refined version in JSON format:

```json
{
  // Your refined output here
}
```
"""

        return prompt


class AgentPromptBuilder(PromptBuildingMixin):
    """
    Specialized prompt builder for agent-based tasks.

    Adds agent-specific helpers on top of PromptBuildingMixin.
    """

    def build_agent_design_prompt(
        self,
        requirement: str,
        golden_data=None,
        previous_outputs: Optional[Dict] = None,
        max_agents: int = 10
    ) -> str:
        """
        Build prompt for agent design phase.

        Args:
            requirement: User requirement
            golden_data: Optional Golden Data
            previous_outputs: Optional previous phase outputs
            max_agents: Suggested maximum agents

        Returns:
            Agent design prompt
        """
        prompt = self.build_standard_prompt(
            role="Expert Multi-Agent System Designer",
            task_description="Design a multi-agent system with appropriate agents and tasks",
            inputs={
                "requirement": requirement,
            },
            output_format={
                "agents": "List of agent specifications (id, role, goal, backstory, tools, etc.)",
                "tasks": "List of task specifications (id, description, agent, dependencies, etc.)",
                "workflow_type": "Workflow type (sequential, hierarchical, etc.)",
                "agent_collaboration_pattern": "How agents collaborate"
            },
            guidelines=[
                f"Design {max_agents} agents or fewer for efficiency",
                "Each agent should have a distinct, well-defined role",
                "Tasks should be clear and actionable",
                "Ensure proper task dependencies",
                "Assign appropriate tools to each agent"
            ]
        )

        if golden_data:
            prompt = self.add_golden_data_context(prompt, golden_data)

        if previous_outputs:
            prompt = self.add_previous_outputs_context(prompt, previous_outputs)

        return prompt

    def build_code_generation_prompt(
        self,
        agent_design: Dict[str, Any],
        architecture: Dict[str, Any],
        requirement: str
    ) -> str:
        """
        Build prompt for code generation phase.

        Args:
            agent_design: Agent/task design from previous phase
            architecture: System architecture from previous phase
            requirement: Original requirement

        Returns:
            Code generation prompt
        """
        prompt = self.build_standard_prompt(
            role="Expert Code Generator",
            task_description="Generate production-ready Python code for the CrewAI multi-agent system",
            inputs={
                "requirement": requirement,
                "agents": agent_design.get("agents", []),
                "tasks": agent_design.get("tasks", []),
                "architecture": architecture
            },
            output_format={
                "files": "Dictionary of filename -> code content",
                "dependencies": "List of required Python packages",
                "environment_variables": "Required environment variables",
                "setup_instructions": "Setup and installation instructions"
            },
            constraints=[
                "Use CrewAI framework (crewai>=0.65.0)",
                "Follow Python 3.11+ best practices",
                "Include proper error handling",
                "Add docstrings to all functions/classes",
                "Use type hints where appropriate"
            ],
            guidelines=[
                "Generate main.py, agents.py, tasks.py, tools.py at minimum",
                "Include requirements.txt and .env.example",
                "Add README.md with usage instructions",
                "Ensure code is executable without modifications",
                "Use environment variables for sensitive data"
            ]
        )

        return prompt
