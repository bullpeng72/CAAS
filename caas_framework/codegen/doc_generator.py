"""
Documentation Generator

Generates comprehensive documentation for generated projects.
Supports Sphinx and MkDocs formats.
"""

from typing import Dict, List
from dataclasses import dataclass

from caas_framework.models.specifications import (
    ConcretizedRequirement,
    AgentSpecModel,
    TaskSpecModel
)


@dataclass
class DocumentationConfig:
    """Documentation configuration"""
    format: str = "mkdocs"  # "mkdocs" or "sphinx"
    project_name: str = "My Project"
    author: str = "CAAS Framework"
    include_api_docs: bool = True
    include_architecture_diagram: bool = True


class DocumentationGenerator:
    """
    Documentation Generator

    Generates project documentation in MkDocs or Sphinx format.
    """

    def generate_all(
        self,
        golden_data: ConcretizedRequirement,
        agents: List[AgentSpecModel],
        tasks: List[TaskSpecModel],
        config: DocumentationConfig
    ) -> Dict[str, str]:
        """
        Generate all documentation files.

        Args:
            golden_data: Golden Data
            agents: Agent specifications
            tasks: Task specifications
            config: Documentation configuration

        Returns:
            Dict[str, str]: Documentation files
        """
        files = {}

        if config.format == "mkdocs":
            files.update(self._generate_mkdocs(golden_data, agents, tasks, config))
        elif config.format == "sphinx":
            files.update(self._generate_sphinx(golden_data, agents, tasks, config))

        return files

    def _generate_mkdocs(
        self,
        golden_data: ConcretizedRequirement,
        agents: List[AgentSpecModel],
        tasks: List[TaskSpecModel],
        config: DocumentationConfig
    ) -> Dict[str, str]:
        """Generate MkDocs documentation"""
        files = {}

        # mkdocs.yml
        files["mkdocs.yml"] = f'''
site_name: {config.project_name} Documentation
site_author: {config.author}
site_description: Documentation for {config.project_name}

theme:
  name: material
  palette:
    primary: indigo
    accent: indigo
  features:
    - navigation.tabs
    - navigation.sections
    - toc.integrate

nav:
  - Home: index.md
  - Getting Started:
    - Installation: getting-started/installation.md
    - Quick Start: getting-started/quickstart.md
  - Architecture:
    - Overview: architecture/overview.md
    - Agents: architecture/agents.md
    - Tasks: architecture/tasks.md
  - API Reference: api/reference.md
  - Contributing: contributing.md

markdown_extensions:
  - pymdownx.highlight
  - pymdownx.superfences
  - admonition
  - codehilite
'''

        # docs/index.md
        files["docs/index.md"] = f'''# {golden_data.project_name or "Project"} Documentation

{golden_data.description}

## Overview

- **Domain**: {golden_data.domain}
- **Workflow Type**: {golden_data.workflow_type}
- **Deployment**: {golden_data.deployment_target}

## Features

{chr(10).join(f"- **{f.name}** ({f.priority}): {f.description}" for f in golden_data.features[:10])}

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Architecture

This project uses a multi-agent architecture with {len(agents)} agents and {len(tasks)} tasks.

See [Architecture Overview](architecture/overview.md) for more details.
'''

        # docs/getting-started/installation.md
        files["docs/getting-started/installation.md"] = '''# Installation

## Prerequisites

- Python 3.9 or higher
- pip package manager

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Environment Setup

Create a `.env` file with your configuration:

```env
OPENAI_API_KEY=your_api_key_here
```

## Verify Installation

```bash
python -c "import crewai; print('CrewAI installed successfully')"
```
'''

        # docs/getting-started/quickstart.md
        files["docs/getting-started/quickstart.md"] = '''# Quick Start Guide

## Running the Application

```bash
python main.py
```

## Testing

Run the test suite:

```bash
pytest tests/
```

## Docker

Build and run with Docker:

```bash
docker-compose up --build
```
'''

        # docs/architecture/overview.md
        files["docs/architecture/overview.md"] = f'''# Architecture Overview

## System Design

This project implements a multi-agent system using CrewAI.

### Components

- **Agents**: {len(agents)} specialized agents
- **Tasks**: {len(tasks)} coordinated tasks
- **Workflow**: {golden_data.workflow_type}

## Data Models

{chr(10).join(f"- **{dm.entity_name}**: {', '.join(dm.attributes[:5])}" for dm in golden_data.data_models[:5])}

## Deployment

- **Target**: {golden_data.deployment_target}
- **Containerization**: Docker support included
'''

        # docs/architecture/agents.md
        agents_content = "# Agents\n\n"
        for agent in agents:
            agents_content += f'''
## {agent.role.title()}

**ID**: `{agent.id}`

**Goal**: {agent.goal}

**Backstory**: {agent.backstory}

**Tools**: {", ".join(agent.tools) if agent.tools else "None"}

**Delegation**: {"Enabled" if agent.allow_delegation else "Disabled"}

---

'''
        files["docs/architecture/agents.md"] = agents_content

        # docs/architecture/tasks.md
        tasks_content = "# Tasks\n\n"
        for task in tasks:
            tasks_content += f'''
## {task.id}

**Description**: {task.description}

**Expected Output**: {task.expected_output}

**Agent**: `{task.agent}`

**Context**: {", ".join(task.context) if task.context else "None"}

**Async**: {"Yes" if task.async_execution else "No"}

---

'''
        files["docs/architecture/tasks.md"] = tasks_content

        # docs/api/reference.md
        files["docs/api/reference.md"] = '''# API Reference

## Core Modules

### Agents Module (`src/agents.py`)

Defines all agents used in the system.

### Tasks Module (`src/tasks.py`)

Defines all tasks executed by the agents.

### Crew Module (`src/crew.py`)

Main crew configuration and orchestration.

## Functions

### `kickoff()`

Execute the crew synchronously.

**Returns**: Crew execution result

### `kickoff_async()`

Execute the crew asynchronously.

**Returns**: Crew execution result (async)
'''

        # docs/contributing.md
        files["docs/contributing.md"] = '''# Contributing

## Development Setup

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Run tests:
   ```bash
   pytest tests/ -v
   ```

## Code Style

- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for all functions

## Testing

- Write tests for new features
- Maintain test coverage above 80%
- Run tests before submitting PR

## Pull Requests

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit PR with description
'''

        return files

    def _generate_sphinx(
        self,
        golden_data: ConcretizedRequirement,
        agents: List[AgentSpecModel],
        tasks: List[TaskSpecModel],
        config: DocumentationConfig
    ) -> Dict[str, str]:
        """Generate Sphinx documentation"""
        files = {}

        # conf.py
        files["docs/conf.py"] = f'''
# Configuration file for Sphinx documentation
project = '{config.project_name}'
author = '{config.author}'
release = '1.0.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
'''

        # index.rst
        files["docs/index.rst"] = f'''
{config.project_name} Documentation
{'=' * len(config.project_name)}

{golden_data.description}

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   architecture
   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
'''

        return files
