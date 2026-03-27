"""
CAAS CLI Setup - Command-Line Interface for CrewAI Agent Generation

Installation:
    # Standard installation (includes CLI)
    pip install -e .

    # Development tools
    pip install -e ".[dev]"
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = (
    readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
)

setup(
    name="caas",
    version="0.6.6",
    description="CrewAI Agent Auto-generation System - Complete Package (Framework + CLI)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="bullpeng72",
    author_email="sungwoo.kim@gmail.com",
    url="https://github.com/bullpeng72/CAAS",
    # Include framework, CLI, and SDK
    packages=find_packages(
        include=[
            "caas_framework",
            "caas_framework.*",
            "caas_cli",
            "caas_cli.*",
            "caas_sdk",
            "caas_sdk.*",
        ]
    ),
    package_data={
        "caas_framework": [
            "templates/**/*",
            "codegen/templates/**/*",
            "config/**/*",
            "*.yaml",
            "*.yml",
            "*.json",
        ],
    },
    include_package_data=True,
    python_requires=">=3.11",
    # Core dependencies - NO UI libraries (streamlit, fastapi, uvicorn, click, typer)
    install_requires=[
        # AI/ML Frameworks (Core)
        "crewai>=0.65.0,<1.0.0",
        "crewai-tools>=0.12.0,<1.0.0",
        "langchain>=0.2.0,<0.4.0",
        "langchain-openai>=0.1.0,<0.3.0",
        "langchain-anthropic>=0.1.0,<0.3.0",
        "langchain-community>=0.2.0,<0.4.0",
        "langchain-core>=0.2.0,<0.4.0",
        "openai>=1.30.0,<2.0.0",
        "anthropic>=0.25.0,<1.0.0",
        # Knowledge Management
        "neo4j>=5.18.0,<6.0.0",
        "owlready2>=0.46,<1.0.0",
        "rdflib>=7.0.0,<8.0.0",
        # Code Generation & Templates
        "jinja2>=3.1.0,<4.0.0",
        "autoflake>=2.2.0,<3.0.0",
        # Core Dependencies
        "pydantic>=2.0,<3.0",
        "pyyaml>=6.0,<7.0",
        "python-dotenv>=1.0,<2.0",
        # gRPC & Protobuf (for SDK)
        "grpcio>=1.76.0,<2.0.0",
        "grpcio-tools>=1.76.0,<2.0.0",
        "protobuf>=6.31.1,<7.0.0",
        # Utilities
        "httpx>=0.27.0,<1.0.0",
        "aiofiles>=23.2.0,<24.0.0",
        "tenacity>=8.2.0,<9.0.0",
        "rich>=13.7.0,<14.0.0",
    ],
    extras_require={
        # Development tools
        "dev": [
            # Testing Framework
            "pytest>=8.0.0,<9.0.0",
            "pytest-asyncio>=0.23.0,<1.0.0",
            "pytest-mock>=3.12.0,<4.0.0",
            "pytest-timeout>=2.2.0,<3.0.0",
            "pytest-cov>=4.1.0,<5.0.0",
            "pytest-xdist>=3.5.0,<4.0.0",
            # Code Quality & Formatting
            "black>=24.0.0,<25.0.0",
            "isort>=5.13.0,<6.0.0",
            "flake8>=7.0.0,<8.0.0",
            "mypy>=1.8.0,<2.0.0",
        ],
    },
    # Console script entry point for CLI
    entry_points={
        "console_scripts": [
            "caas=caas_cli.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="crewai multi-agent code-generation ai framework bmad sdd ontology",
    project_urls={
        "Bug Reports": "https://github.com/bullpeng72/CAAS/issues",
        "Documentation": "https://github.com/bullpeng72/CAAS#readme",
        "Source": "https://github.com/bullpeng72/CAAS",
    },
)
