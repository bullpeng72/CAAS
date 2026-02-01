"""
Requirement Analysis Prompts

Prompt templates for requirement analysis, agent design, and task design.
"""

# TODO: Implement actual prompt templates
# These are placeholders until proper prompts are defined

REQUIREMENT_ANALYSIS_SYSTEM = """You are an expert requirement analyst.
Analyze the user's requirements and extract structured information about the domain,
agents needed, tasks to perform, and tools required.

Respond with a JSON object following the RequirementAnalysis schema."""

REQUIREMENT_ANALYSIS_USER = """Analyze the following requirement:

{requirement}

Provide a detailed analysis including:
- Domain and subdomain
- List of agents needed
- List of tasks to perform
- Suggested tools
- Constraints and success criteria"""

AGENT_DESIGN_SYSTEM = """You are an expert agent designer.
Design agents that can fulfill the analyzed requirements.

Respond with a JSON array of AgentSpecModel objects."""

AGENT_DESIGN_USER = """Based on this requirement analysis:

{analysis}

Design the necessary agents with their roles, goals, backstories, and required tools."""

TASK_DESIGN_SYSTEM = """You are an expert task designer.
Design tasks that agents should perform to fulfill requirements.

Respond with a JSON array of TaskSpecModel objects."""

TASK_DESIGN_USER = """Based on this requirement analysis:

{analysis}

Design the necessary tasks with descriptions, expected outputs, and agent assignments."""

ONTOLOGY_CONTEXT_TEMPLATE = """
**Available Agent Roles:**
{agent_roles}

**Available Task Types:**
{task_types}

**Role-Task Mappings:**
{role_task_mappings}

**Task-Tool Capability Mappings:**
{task_capability_mappings}
"""

PATTERN_CONTEXT_TEMPLATE = """
**Common Patterns:**
{patterns}

**Best Practices:**
{best_practices}
"""
