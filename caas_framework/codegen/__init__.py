"""
Code Generation Module

Production-ready code generation for CrewAI projects.
"""

from caas_framework.codegen.engine import (
    CodeGenerationEngine,
    CodeGenerationResult,
    GeneratedFile,
)
from caas_framework.codegen.domain_strategy import (
    DomainStrategy,
    CodeGenStrategy,
)
from caas_framework.codegen.injectors import (
    ErrorHandlingInjector,
    LoggingInjector,
)
from caas_framework.codegen.test_generator import TestGenerator
from caas_framework.codegen.deployment_generator import DeploymentGenerator

__all__ = [
    "CodeGenerationEngine",
    "CodeGenerationResult",
    "GeneratedFile",
    "DomainStrategy",
    "CodeGenStrategy",
    "ErrorHandlingInjector",
    "LoggingInjector",
    "TestGenerator",
    "DeploymentGenerator",
]
