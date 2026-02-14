"""
Code Generation Module

Production-ready code generation for CrewAI projects.

✅ v0.5.1: Legacy CodeGenerationEngine removed - use Expert Agent path only
"""

from caas_framework.codegen.deployment_generator import DeploymentGenerator
from caas_framework.codegen.domain_strategy import CodeGenStrategy, DomainCodeStrategy
from caas_framework.codegen.injectors import ErrorHandlingInjector, LoggingInjector
from caas_framework.codegen.tdd_test_generator import TestGenerator
from caas_framework.codegen.test_parser import TestParser, ParsedTestFile
from caas_framework.codegen.test_driven_generator import (
    TestDrivenCodeGenerator,
    TDDGenerationResult,
)
from caas_framework.codegen.tdd_orchestrator import TDDOrchestrator, TDDWorkflowConfig

# ✅ v0.5.1: CodeGenerationEngine, CodeGenerationResult, GeneratedFile removed
# Use CodeGeneratorAgent (Expert Agent path) instead

__all__ = [
    "DomainCodeStrategy",
    "CodeGenStrategy",
    "ErrorHandlingInjector",
    "LoggingInjector",
    "TestGenerator",
    "DeploymentGenerator",
    # TDD Components (v0.6.1 - Week 4)
    "TestParser",
    "ParsedTestFile",
    "TestDrivenCodeGenerator",
    "TDDGenerationResult",
    "TDDOrchestrator",
    "TDDWorkflowConfig",
]
