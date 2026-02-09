"""
Test suite for caas_framework/exceptions.py

Tests all custom exception classes and exception formatting utilities.
Target coverage: 95%+
"""

import pytest
from caas_framework.exceptions import (
    # Base
    CaasError,
    # Agent errors
    AgentError,
    AgentInitializationError,
    AgentExecutionError,
    AgentCollaborationError,
    # Code generation errors
    CodeGenerationError,
    TemplateRenderingError,
    CodeCompilationError,
    DependencyResolutionError,
    # Validation errors
    ValidationError,
    OntologyValidationError,
    GoldenDataValidationError,
    SpecificationValidationError,
    DependencyValidationError,
    # Methodology errors
    MethodologyError,
    PhaseExecutionError,
    WorkflowError,
    QualityGateError,
    # Plugin errors
    PluginError,
    LLMPluginError,
    GraphDBPluginError,
    VectorDBPluginError,
    # Configuration errors
    ConfigurationError,
    MissingConfigError,
    InvalidConfigError,
    EnvironmentError as CaasEnvironmentError,  # Avoid conflict with built-in
    # Utilities
    format_exception_chain,
)


class TestCaasError:
    """Test base CaasError class."""

    def test_init_with_message_only(self):
        """Test initialization with message only."""
        error = CaasError("Test error")
        assert str(error) == "Test error"
        assert error.details == {}

    def test_init_with_message_and_details(self):
        """Test initialization with message and details."""
        error = CaasError(
            "Test error",
            details={"key1": "value1", "key2": 42}
        )
        error_str = str(error)
        assert "Test error" in error_str
        assert "key1=value1" in error_str
        assert "key2=42" in error_str

    def test_details_default_to_empty_dict(self):
        """Test that details default to empty dict."""
        error = CaasError("Test error")
        assert isinstance(error.details, dict)
        assert len(error.details) == 0

    def test_exception_chaining(self):
        """Test exception chaining with cause."""
        original = ValueError("Original error")
        try:
            raise CaasError("Wrapped error") from original
        except CaasError as chained:
            assert chained.__cause__ == original


class TestAgentErrors:
    """Test agent-related exception classes."""

    def test_agent_error_base(self):
        """Test AgentError base class."""
        error = AgentError("Agent failed")
        assert str(error) == "Agent failed"
        assert isinstance(error, CaasError)

    def test_agent_initialization_error(self):
        """Test AgentInitializationError."""
        error = AgentInitializationError(
            "Failed to initialize agent",
            details={"agent_name": "test_agent"}
        )
        error_str = str(error)
        assert "Failed to initialize agent" in error_str
        assert "agent_name=test_agent" in error_str
        assert isinstance(error, AgentError)

    def test_agent_execution_error(self):
        """Test AgentExecutionError."""
        error = AgentExecutionError(
            "Agent execution failed",
            details={"phase": "discovery", "attempt": 3}
        )
        error_str = str(error)
        assert "Agent execution failed" in error_str
        assert "phase=discovery" in error_str
        assert "attempt=3" in error_str
        assert isinstance(error, AgentError)


class TestCodeGenerationErrors:
    """Test code generation exception classes."""

    def test_code_generation_error_base(self):
        """Test CodeGenerationError base class."""
        error = CodeGenerationError("Code generation failed")
        assert str(error) == "Code generation failed"
        assert isinstance(error, CaasError)

    def test_template_rendering_error(self):
        """Test TemplateRenderingError."""
        error = TemplateRenderingError(
            "Template rendering failed",
            details={"template": "agents.py.j2", "line": 42}
        )
        error_str = str(error)
        assert "Template rendering failed" in error_str
        assert "template=agents.py.j2" in error_str
        assert "line=42" in error_str
        assert isinstance(error, CodeGenerationError)

    def test_code_compilation_error(self):
        """Test CodeCompilationError."""
        error = CodeCompilationError(
            "Generated code is invalid",
            details={"file": "main.py", "issue": "syntax error"}
        )
        error_str = str(error)
        assert "Generated code is invalid" in error_str
        assert "file=main.py" in error_str
        assert "issue=syntax error" in error_str
        assert isinstance(error, CodeGenerationError)


class TestValidationErrors:
    """Test validation exception classes."""

    def test_validation_error_base(self):
        """Test ValidationError base class."""
        error = ValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, CaasError)

    def test_ontology_validation_error(self):
        """Test OntologyValidationError."""
        error = OntologyValidationError(
            "Ontology constraint violated",
            details={"constraint": "agent_count", "expected": "3-5", "actual": 2}
        )
        error_str = str(error)
        assert "Ontology constraint violated" in error_str
        assert "constraint=agent_count" in error_str
        assert isinstance(error, ValidationError)

    def test_golden_data_validation_error(self):
        """Test GoldenDataValidationError."""
        error = GoldenDataValidationError(
            "Golden data is incomplete",
            details={"missing_fields": ["business_rules", "constraints"]}
        )
        error_str = str(error)
        assert "Golden data is incomplete" in error_str
        assert "missing_fields" in error_str
        assert isinstance(error, ValidationError)

    def test_specification_validation_error(self):
        """Test SpecificationValidationError."""
        error = SpecificationValidationError(
            "Agent spec is invalid",
            details={"agent_id": "agent_1", "field": "tools", "reason": "empty list"}
        )
        error_str = str(error)
        assert "Agent spec is invalid" in error_str
        assert "agent_id=agent_1" in error_str
        assert isinstance(error, ValidationError)


class TestMethodologyErrors:
    """Test methodology exception classes."""

    def test_methodology_error_base(self):
        """Test MethodologyError base class."""
        error = MethodologyError("Methodology error")
        assert str(error) == "Methodology error"
        assert isinstance(error, CaasError)

    def test_phase_execution_error(self):
        """Test PhaseExecutionError."""
        error = PhaseExecutionError(
            "Phase execution failed",
            details={"phase": "DISCOVERY", "reason": "timeout"}
        )
        error_str = str(error)
        assert "Phase execution failed" in error_str
        assert "phase=DISCOVERY" in error_str
        assert "reason=timeout" in error_str
        assert isinstance(error, MethodologyError)

    def test_quality_gate_error(self):
        """Test QualityGateError."""
        error = QualityGateError(
            "Quality gate failed",
            details={
                "phase": "ARCHITECTURE",
                "metric": "traceability",
                "threshold": 0.8,
                "actual": 0.6
            }
        )
        error_str = str(error)
        assert "Quality gate failed" in error_str
        assert "phase=ARCHITECTURE" in error_str
        assert "metric=traceability" in error_str
        assert isinstance(error, MethodologyError)


class TestPluginErrors:
    """Test plugin exception classes."""

    def test_plugin_error_base(self):
        """Test PluginError base class."""
        error = PluginError("Plugin error")
        assert str(error) == "Plugin error"
        assert isinstance(error, CaasError)

    def test_llm_plugin_error(self):
        """Test LLMPluginError."""
        error = LLMPluginError(
            "LLM plugin failed",
            details={"provider": "openai", "model": "gpt-4"}
        )
        error_str = str(error)
        assert "LLM plugin failed" in error_str
        assert "provider=openai" in error_str
        assert isinstance(error, PluginError)

    def test_graphdb_plugin_error(self):
        """Test GraphDBPluginError."""
        error = GraphDBPluginError(
            "Graph DB connection failed",
            details={"uri": "bolt://localhost:7687"}
        )
        error_str = str(error)
        assert "Graph DB connection failed" in error_str
        assert isinstance(error, PluginError)

    def test_vectordb_plugin_error(self):
        """Test VectorDBPluginError."""
        error = VectorDBPluginError(
            "Vector DB operation failed",
            details={"operation": "insert"}
        )
        error_str = str(error)
        assert "Vector DB operation failed" in error_str
        assert isinstance(error, PluginError)


class TestConfigurationErrors:
    """Test configuration exception classes."""

    def test_configuration_error_base(self):
        """Test ConfigurationError base class."""
        error = ConfigurationError("Configuration error")
        assert str(error) == "Configuration error"
        assert isinstance(error, CaasError)

    def test_missing_config_error(self):
        """Test MissingConfigError."""
        error = MissingConfigError(
            "Required configuration missing",
            details={"config_key": "llm.api_key", "source": "environment"}
        )
        error_str = str(error)
        assert "Required configuration missing" in error_str
        assert "config_key=llm.api_key" in error_str
        assert "source=environment" in error_str
        assert isinstance(error, ConfigurationError)

    def test_invalid_config_error(self):
        """Test InvalidConfigError."""
        error = InvalidConfigError(
            "Invalid configuration value",
            details={"config_key": "llm.temperature", "value": 2.5, "valid_range": "0-2"}
        )
        error_str = str(error)
        assert "Invalid configuration value" in error_str
        assert "config_key=llm.temperature" in error_str
        assert "value=2.5" in error_str
        assert isinstance(error, ConfigurationError)

    def test_environment_error(self):
        """Test EnvironmentError (CaasEnvironmentError to avoid built-in conflict)."""
        error = CaasEnvironmentError(
            "Environment variable missing",
            details={"var": "OPENAI_API_KEY"}
        )
        error_str = str(error)
        assert "Environment variable missing" in error_str
        assert "var=OPENAI_API_KEY" in error_str
        assert isinstance(error, ConfigurationError)


class TestFormatExceptionChain:
    """Test format_exception_chain() utility function."""

    def test_format_single_exception(self):
        """Test formatting a single exception."""
        error = ValueError("Test error")
        formatted = format_exception_chain(error)
        assert formatted == "ValueError: Test error"

    def test_format_exception_chain_two_levels(self):
        """Test formatting exception chain with two levels."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise RuntimeError("Wrapped error") from e
        except RuntimeError as error:
            formatted = format_exception_chain(error)
            assert "RuntimeError: Wrapped error" in formatted
            assert "ValueError: Original error" in formatted
            assert " -> " in formatted  # Chain separator

    def test_format_exception_chain_three_levels(self):
        """Test formatting exception chain with three levels."""
        try:
            try:
                try:
                    raise ValueError("Root error")
                except ValueError as e:
                    raise RuntimeError("Middle error") from e
            except RuntimeError as e:
                raise TypeError("Top error") from e
        except TypeError as error:
            formatted = format_exception_chain(error)
            assert "TypeError: Top error" in formatted
            assert "RuntimeError: Middle error" in formatted
            assert "ValueError: Root error" in formatted
            # Should have two arrows (3 exceptions)
            assert formatted.count(" -> ") == 2

    def test_format_caas_error_with_details(self):
        """Test formatting CaasError with details."""
        error = AgentExecutionError(
            "Agent failed",
            details={"agent": "test_agent", "phase": "discovery"}
        )
        formatted = format_exception_chain(error)
        # CaasError uses __str__ which includes details
        assert "Agent failed" in formatted
        assert "agent=test_agent" in formatted
        assert "phase=discovery" in formatted

    def test_format_exception_without_cause(self):
        """Test formatting exception without cause."""
        error = CaasError("Simple error")
        formatted = format_exception_chain(error)
        assert formatted == "Simple error"
        assert " -> " not in formatted  # No chain

    def test_format_exception_with_caas_and_standard(self):
        """Test formatting chain with both CaasError and standard exceptions."""
        try:
            try:
                raise ValueError("Standard error")
            except ValueError as e:
                raise AgentExecutionError("Agent error") from e
        except AgentExecutionError as error:
            formatted = format_exception_chain(error)
            assert "Agent error" in formatted
            assert "ValueError: Standard error" in formatted
            assert " -> " in formatted


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_caas_error(self):
        """Test that all custom exceptions inherit from CaasError."""
        exception_classes = [
            AgentError,
            AgentInitializationError,
            AgentExecutionError,
            AgentCollaborationError,
            CodeGenerationError,
            TemplateRenderingError,
            CodeCompilationError,
            DependencyResolutionError,
            ValidationError,
            OntologyValidationError,
            GoldenDataValidationError,
            SpecificationValidationError,
            DependencyValidationError,
            MethodologyError,
            PhaseExecutionError,
            WorkflowError,
            QualityGateError,
            PluginError,
            LLMPluginError,
            GraphDBPluginError,
            VectorDBPluginError,
            ConfigurationError,
            MissingConfigError,
            InvalidConfigError,
            CaasEnvironmentError,
        ]

        for exc_class in exception_classes:
            error = exc_class("Test")
            assert isinstance(error, CaasError)
            assert isinstance(error, Exception)

    def test_agent_error_hierarchy(self):
        """Test AgentError inheritance hierarchy."""
        init_error = AgentInitializationError("Test")
        exec_error = AgentExecutionError("Test")
        collab_error = AgentCollaborationError("Test")

        assert isinstance(init_error, AgentError)
        assert isinstance(exec_error, AgentError)
        assert isinstance(collab_error, AgentError)
        assert isinstance(init_error, CaasError)

    def test_code_generation_error_hierarchy(self):
        """Test CodeGenerationError inheritance hierarchy."""
        template_error = TemplateRenderingError("Test")
        compilation_error = CodeCompilationError("Test")

        assert isinstance(template_error, CodeGenerationError)
        assert isinstance(compilation_error, CodeGenerationError)
        assert isinstance(template_error, CaasError)

    def test_validation_error_hierarchy(self):
        """Test ValidationError inheritance hierarchy."""
        ontology_error = OntologyValidationError("Test")
        golden_error = GoldenDataValidationError("Test")
        spec_error = SpecificationValidationError("Test")

        assert isinstance(ontology_error, ValidationError)
        assert isinstance(golden_error, ValidationError)
        assert isinstance(spec_error, ValidationError)
        assert isinstance(ontology_error, CaasError)
