# CAAS Framework

**CrewAI Agent Auto-generation System Framework**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

UI-independent, production-ready multi-agent framework for automated CrewAI project generation with CAAS 6-Phase Methodology, ontology-driven design, and Golden Data validation.

## Features

### 🚀 Core Capabilities
- **CAAS 6-Phase Methodology**: Concretization → Discovery → Architecture → Design → Development → Delivery
- **Multi-Agent System**: 8 specialized agents (Requirements Analyst, System Architect, Domain Expert, Code Reviewer, etc.)
- **Ontology-Driven Design**: 24 agent roles, 35 task types, comprehensive tool mappings
- **Pattern Library**: Neo4j-backed pattern matching with 100+ validated patterns
- **Golden Data Validation**: Automated QA framework with auto-fixing capabilities
- **MCP Integration**: Model Context Protocol support (stdio, sse, http transports)
- **Frontend Generation**: AST-based Streamlit and template-based React/Gradio generation

### 📦 Code Generation
- **Backend**: FastAPI with SQLAlchemy, Pydantic models, JWT auth
- **Frontend**: Streamlit (AST-based), Gradio (template-based), React (coming soon)
- **Tests**: Pytest with fixtures, async support, mocking
- **Deployment**: Docker Compose, Kubernetes manifests, CI/CD configs
- **Documentation**: README, API docs, architecture diagrams

### 🔧 Advanced Features
- **Scale-Adaptive Intelligence**: Domain-specific optimization strategies
- **Auto-Fixing Loop**: Iterative code refinement with feedback
- **Port Management**: Dynamic allocation (8600-8699) with conflict prevention
- **Execution Sandbox**: Docker-based secure code execution
- **Session Management**: Persistent workflow state tracking

## Installation

### From PyPI (coming soon)
```bash
pip install caas-framework
```

### From Source
```bash
git clone https://github.com/bullpeng72/CrewAI-Agent-Autogeneration-System.git
cd caas-framework
pip install -e .
```

### With Optional Dependencies
```bash
# Rich logging support
pip install caas-framework[rich]

# Docker sandbox support
pip install caas-framework[docker]

# Development tools
pip install caas-framework[dev]

# All optional dependencies
pip install caas-framework[all]
```

## Quick Start

### Basic Usage

```python
from caas_framework import CrewAIFramework

# Initialize framework
framework = CrewAIFramework(
    llm_provider="openai",  # or "anthropic"
    graph_backend="neo4j"   # optional, for pattern matching
)

# Generate project from requirement
result = await framework.generate_from_requirement(
    requirement="Build a chatbot that helps users book flights",
    domain="CONVERSATIONAL_AI",
    enable_frontend=True,
    frontend_framework="streamlit"
)

# Access generated files
for filepath, content in result.files.items():
    print(f"Generated: {filepath}")
```

### Configuration

```python
from caas_framework import FrameworkConfig

config = FrameworkConfig(
    llm_provider="anthropic",
    llm_model="claude-3-7-sonnet-20250219",
    graph_backend="neo4j",
    graph_uri="bolt://localhost:7687",
    enable_golden_data=True,
    enable_auto_fixing=True,
    max_fixing_iterations=3
)

framework = CrewAIFramework(config=config)
```

### CLI Usage

```bash
# Generate project
caas generate \
    --requirement "Build a task management API" \
    --domain DATA_PROCESSING \
    --output ./output/task_manager \
    --frontend streamlit

# Validate with Golden Data
caas validate \
    --project-path ./output/task_manager \
    --pattern-library ./patterns

# Run auto-fixing
caas fix \
    --project-path ./output/task_manager \
    --max-iterations 5
```

## Architecture

### CAAS 6-Phase Methodology

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Concretization │────▶│    Discovery    │────▶│  Architecture   │
│                 │     │                 │     │                 │
│ • Parse req.    │     │ • Domain detect │     │ • Component     │
│ • Ontology map  │     │ • Pattern match │     │ • Data model    │
│ • Constraints   │     │ • Tool select   │     │ • API design    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Design      │────▶│  Development    │────▶│    Delivery     │
│                 │     │                 │     │                 │
│ • Agent design  │     │ • Code gen      │     │ • Packaging     │
│ • Task design   │     │ • Test gen      │     │ • Deployment    │
│ • Workflow      │     │ • Frontend gen  │     │ • Documentation │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Module Structure

- **`agents/`** - 8 specialized agents (analyst, architect, reviewer, etc.)
- **`bmad/`** - 6-phase pipeline engine and context management
- **`codegen/`** - Code generation (backend, frontend, tests, deployment)
- **`config/`** - Configuration loading and validation
- **`fixing/`** - Auto-fixing loop with feedback
- **`knowledge/`** - Ontology system (24 roles, 35 tasks, tools)
- **`models/`** - Pydantic data models and schemas
- **`plugins/`** - MCP client and tool integrations
- **`reporting/`** - Metrics collection and performance tracking
- **`session/`** - Workflow state management
- **`validation/`** - Golden Data validation and pattern matching
- **`workflow/`** - Orchestration and phase execution

## Requirements

### Core Dependencies
- Python 3.11+
- crewai >= 0.65.0
- crewai-tools[mcp] >= 0.12.0
- langchain >= 0.2.0
- pydantic >= 2.0
- jinja2 >= 3.1.0

### Optional Dependencies
- **Neo4j** (pattern library): neo4j >= 5.18.0
- **Rich logging**: rich >= 13.7.0
- **Docker sandbox**: docker >= 7.0.0
- **OWL ontologies**: owlready2 >= 0.46

### Environment Variables

```bash
# LLM Provider (required)
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...

# Neo4j (optional, for pattern matching)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Framework Settings
CAAS_LOG_LEVEL=INFO
CAAS_MAX_WORKERS=4
CAAS_ENABLE_GOLDEN_DATA=true
```

## Examples

### Example 1: Data Analysis Pipeline

```python
result = await framework.generate_from_requirement(
    requirement="""
    Build a data analysis pipeline that:
    1. Ingests CSV files from S3
    2. Validates data quality
    3. Performs statistical analysis
    4. Generates visualizations
    5. Exports to PostgreSQL
    """,
    domain="DATA_PROCESSING",
    enable_frontend=True,
    frontend_framework="streamlit"
)

# Generated structure:
# backend/
#   ├── main.py (FastAPI)
#   ├── agents/ (5 agents: data_ingester, validator, analyzer, visualizer, exporter)
#   ├── models/ (Pydantic models)
#   └── tests/ (pytest)
# frontend/
#   ├── app.py (Streamlit)
#   └── pages/ (Dashboard, Upload, Analysis, Export)
# deployment/
#   ├── docker-compose.yml
#   └── kubernetes/
```

### Example 2: Chatbot with RAG

```python
result = await framework.generate_from_requirement(
    requirement="""
    Create a customer support chatbot with:
    - RAG using Pinecone vector DB
    - Conversation history
    - Multi-turn dialogue
    - Sentiment analysis
    - Ticket creation
    """,
    domain="CONVERSATIONAL_AI",
    enable_frontend=True,
    frontend_framework="gradio"
)

# Generated: 3 agents (rag_retriever, conversational_agent, ticket_creator)
# with Gradio chatbot UI
```

### Example 3: CRUD API

```python
result = await framework.generate_from_requirement(
    requirement="Build a CRUD API for managing blog posts with auth",
    domain="WEB_DEVELOPMENT"
)

# Generated: FastAPI backend with JWT auth, SQLAlchemy models, CRUD routes, tests
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=caas_framework --cov-report=html

# Run specific test suite
pytest tests/test_codegen/

# Run integration tests
pytest -m integration
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/bullpeng72/CrewAI-Agent-Autogeneration-System.git
cd caas-framework
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### Code Quality

```bash
# Format code
black caas_framework/
isort caas_framework/

# Lint
flake8 caas_framework/
pylint caas_framework/

# Type checking
mypy caas_framework/
```

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) first.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use CAAS Framework in your research, please cite:

```bibtex
@software{caas_framework,
  title = {CAAS Framework: CrewAI Agent Auto-generation System},
  author = {CAAS Team},
  year = {2024},
  url = {https://github.com/bullpeng72/CrewAI-Agent-Autogeneration-System}
}
```

## Acknowledgments

- Built on top of [CrewAI](https://github.com/joaomdmoura/crewAI)
- Ontology design based on CrewAI best practices
- CAAS 6-Phase Methodology: proprietary development process

## Support

- 📧 Email: support@caas-framework.io
- 💬 Discord: https://discord.gg/caas-framework
- 🐛 Issues: https://github.com/bullpeng72/CrewAI-Agent-Autogeneration-System/issues
- 📖 Docs: https://caas-framework.readthedocs.io
