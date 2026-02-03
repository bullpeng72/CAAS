"""
Code Generation Module

Production-ready code generation for CrewAI projects.
"""

from caas_framework.codegen.deployment_generator import DeploymentGenerator
from caas_framework.codegen.domain_strategy import CodeGenStrategy, DomainStrategy
from caas_framework.codegen.engine import (
    CodeGenerationEngine,
    CodeGenerationResult,
    GeneratedFile,
)
from caas_framework.codegen.injectors import ErrorHandlingInjector, LoggingInjector
from caas_framework.codegen.tdd_test_generator import TestGenerator

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
