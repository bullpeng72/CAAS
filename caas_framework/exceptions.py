"""
CAAS Framework Custom Exceptions

Hierarchy:
    CaasError (base)
    ├── AgentError
    │   ├── AgentInitializationError
    │   ├── AgentExecutionError
    │   └── AgentCollaborationError
    ├── CodeGenerationError
    │   ├── TemplateRenderingError
    │   ├── CodeCompilationError
    │   └── DependencyResolutionError
    ├── ValidationError
    │   ├── OntologyValidationError
    │   ├── GoldenDataValidationError
    │   ├── SpecificationValidationError
    │   └── DependencyValidationError
    ├── MethodologyError
    │   ├── PhaseExecutionError
    │   ├── WorkflowError
    │   └── QualityGateError
    ├── PluginError
    │   ├── LLMPluginError
    │   ├── GraphDBPluginError
    │   └── VectorDBPluginError
    └── ConfigurationError
        ├── MissingConfigError
        ├── InvalidConfigError
        └── EnvironmentError
"""


class CaasError(Exception):
    """Base exception for all CAAS framework errors"""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            details_str = ", ".join([f"{k}={v}" for k, v in self.details.items()])
            return f"{self.message} ({details_str})"
        return self.message


# ============================================================================
# Agent Errors
# ============================================================================


class AgentError(CaasError):
    """Base exception for agent-related errors"""


class AgentInitializationError(AgentError):
    """Raised when agent initialization fails"""


class AgentExecutionError(AgentError):
    """Raised when agent execution fails"""


class AgentCollaborationError(AgentError):
    """Raised when agent collaboration fails"""


# ============================================================================
# Code Generation Errors
# ============================================================================


class CodeGenerationError(CaasError):
    """Base exception for code generation errors"""


class TemplateRenderingError(CodeGenerationError):
    """Raised when template rendering fails"""


class CodeCompilationError(CodeGenerationError):
    """Raised when generated code fails to compile"""


class DependencyResolutionError(CodeGenerationError):
    """Raised when dependency resolution fails"""


# ============================================================================
# Validation Errors
# ============================================================================


class ValidationError(CaasError):
    """Base exception for validation errors"""


class OntologyValidationError(ValidationError):
    """Raised when ontology validation fails"""


class GoldenDataValidationError(ValidationError):
    """Raised when golden data validation fails"""


class SpecificationValidationError(ValidationError):
    """Raised when specification validation fails"""


class DependencyValidationError(ValidationError):
    """Raised when dependency validation fails"""


# ============================================================================
# Methodology Errors
# ============================================================================


class MethodologyError(CaasError):
    """Base exception for methodology/workflow errors"""


class PhaseExecutionError(MethodologyError):
    """Raised when phase execution fails"""


class WorkflowError(MethodologyError):
    """Raised when workflow execution fails"""


class QualityGateError(MethodologyError):
    """Raised when quality gate validation fails"""


# ============================================================================
# Plugin Errors
# ============================================================================


class PluginError(CaasError):
    """Base exception for plugin errors"""


class LLMPluginError(PluginError):
    """Raised when LLM plugin operation fails"""


class GraphDBPluginError(PluginError):
    """Raised when Graph DB plugin operation fails"""


class VectorDBPluginError(PluginError):
    """Raised when Vector DB plugin operation fails"""


# ============================================================================
# Configuration Errors
# ============================================================================


class ConfigurationError(CaasError):
    """Base exception for configuration errors"""


class MissingConfigError(ConfigurationError):
    """Raised when required configuration is missing"""


class InvalidConfigError(ConfigurationError):
    """Raised when configuration is invalid"""


class EnvironmentError(ConfigurationError):
    """Raised when environment setup fails"""


# ============================================================================
# Utility Functions
# ============================================================================


def format_exception_chain(exc: Exception) -> str:
    """
    Format exception chain for logging

    Args:
        exc: Exception to format

    Returns:
        Formatted string with full exception chain
    """
    messages = []
    current = exc
    while current:
        if isinstance(current, CaasError):
            messages.append(str(current))
        else:
            messages.append(f"{type(current).__name__}: {current}")
        current = current.__cause__
    return " -> ".join(messages)
