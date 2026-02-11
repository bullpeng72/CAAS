"""
Test .env individual artifact type control (v0.5.0+)

Verifies that environment variables like ARTIFACT_GENERATION_API_DESIGN
can control individual artifact types.

Tests:
1. Individual type env vars override defaults
2. Master switch (ARTIFACT_GENERATION_ENABLED)
3. Multiple type env vars work together
4. Case-insensitive parsing
5. Integration with ConfigBuilder
"""

import os
import pytest
from unittest.mock import patch

from caas_framework.config.unified import get_config


@pytest.fixture(autouse=True)
def clear_config_cache():
    """Clear the lru_cache before each test"""
    get_config.cache_clear()
    yield
    get_config.cache_clear()


class TestIndividualArtifactTypeEnvVars:
    """Test individual artifact type control via .env variables"""

    @patch.dict(
        os.environ,
        {
            "ARTIFACT_GENERATION_ENABLED": "true",
            "ARTIFACT_GENERATION_API_DESIGN": "false",
        },
        clear=False,
    )
    def test_api_design_disabled_via_env(self):
        """Test ARTIFACT_GENERATION_API_DESIGN=false disables API design artifact"""
        config = get_config(force_reload=True)

        # Master switch enabled
        assert config.artifacts.enabled is True

        # API design specifically disabled
        assert config.artifacts.types["api_design"] is False

        # Other types remain default (True)
        assert config.artifacts.types["requirements_spec"] is True
        assert config.artifacts.types["code_review"] is True

    @patch.dict(
        os.environ,
        {
            "ARTIFACT_GENERATION_ENABLED": "true",
            "ARTIFACT_GENERATION_PROJECT_PROPOSAL": "false",
            "ARTIFACT_GENERATION_REQUIREMENTS_SPEC": "false",
            "ARTIFACT_GENERATION_ARCHITECTURE_DESIGN": "false",
        },
        clear=False,
    )
    def test_multiple_types_disabled(self):
        """Test multiple artifact types can be disabled via env vars"""
        config = get_config(force_reload=True)

        assert config.artifacts.enabled is True
        assert config.artifacts.types["project_proposal"] is False
        assert config.artifacts.types["requirements_spec"] is False
        assert config.artifacts.types["architecture_design"] is False

        # Others remain default
        assert config.artifacts.types["api_design"] is True
        assert config.artifacts.types["code_review"] is True

    @patch.dict(
        os.environ,
        {
            "ARTIFACT_GENERATION_ENABLED": "true",
            "ARTIFACT_GENERATION_DATA_DESIGN": "true",
            "ARTIFACT_GENERATION_API_DESIGN": "true",
            "ARTIFACT_GENERATION_AGENT_DESIGN": "true",
        },
        clear=False,
    )
    def test_selective_types_enabled(self):
        """Test selectively enabling specific artifact types"""
        config = get_config(force_reload=True)

        assert config.artifacts.enabled is True
        assert config.artifacts.types["data_design"] is True
        assert config.artifacts.types["api_design"] is True
        assert config.artifacts.types["agent_design"] is True

    @patch.dict(
        os.environ,
        {
            "ARTIFACT_GENERATION_ENABLED": "true",
            "ARTIFACT_GENERATION_TEST_PLAN": "FALSE",
            "ARTIFACT_GENERATION_TEST_REPORT": "False",
            "ARTIFACT_GENERATION_DEPLOYMENT_GUIDE": "false",
        },
        clear=False,
    )
    def test_case_insensitive_parsing(self):
        """Test env var parsing is case-insensitive"""
        config = get_config(force_reload=True)

        # All should be parsed as False regardless of case
        assert config.artifacts.types["test_plan"] is False
        assert config.artifacts.types["test_report"] is False
        assert config.artifacts.types["deployment_guide"] is False

    @patch.dict(
        os.environ,
        {
            "ARTIFACT_GENERATION_ENABLED": "true",
            "ARTIFACT_GENERATION_PROJECT_PROPOSAL": "false",
            "ARTIFACT_GENERATION_REQUIREMENTS_SPEC": "false",
            "ARTIFACT_GENERATION_ARCHITECTURE_DESIGN": "false",
            "ARTIFACT_GENERATION_DATA_DESIGN": "false",
            "ARTIFACT_GENERATION_API_DESIGN": "false",
            "ARTIFACT_GENERATION_AGENT_DESIGN": "false",
            "ARTIFACT_GENERATION_TEST_PLAN": "false",
            "ARTIFACT_GENERATION_TEST_REPORT": "false",
            "ARTIFACT_GENERATION_CODE_REVIEW": "false",
            "ARTIFACT_GENERATION_DEPLOYMENT_GUIDE": "false",
        },
        clear=False,
    )
    def test_all_types_disabled_individually(self):
        """Test all 10 artifact types can be disabled via env vars"""
        config = get_config(force_reload=True)

        # Master switch still enabled
        assert config.artifacts.enabled is True

        # All types disabled
        for type_key in config.artifacts.types:
            assert config.artifacts.types[type_key] is False, (
                f"Expected {type_key} to be False"
            )

    @patch.dict(
        os.environ,
        {
            "ARTIFACT_GENERATION_ENABLED": "false",
            "ARTIFACT_GENERATION_API_DESIGN": "true",
        },
        clear=False,
    )
    def test_master_switch_overrides_individual_types(self):
        """Test master switch OFF overrides individual type settings"""
        config = get_config(force_reload=True)

        # Master switch disabled
        assert config.artifacts.enabled is False

        # Individual type setting should be stored but not used
        # (Generator will check enabled first)
        assert config.artifacts.types["api_design"] is True


class TestEnvVarMapping:
    """Test the artifact_type_mapping in unified.py"""

    @patch.dict(
        os.environ,
        {
            "ARTIFACT_GENERATION_ENABLED": "true",
            "ARTIFACT_GENERATION_CODE_REVIEW": "false",
        },
        clear=False,
    )
    def test_code_review_mapping(self):
        """Test ARTIFACT_GENERATION_CODE_REVIEW maps to code_review"""
        config = get_config(force_reload=True)

        assert config.artifacts.types["code_review"] is False

    @patch.dict(
        os.environ,
        {
            "ARTIFACT_GENERATION_ENABLED": "true",
            "ARTIFACT_GENERATION_DEPLOYMENT_GUIDE": "false",
        },
        clear=False,
    )
    def test_deployment_guide_mapping(self):
        """Test ARTIFACT_GENERATION_DEPLOYMENT_GUIDE maps to deployment_guide"""
        config = get_config(force_reload=True)

        assert config.artifacts.types["deployment_guide"] is False


class TestEnvVarIntegration:
    """Integration tests with real .env file simulation"""

    @patch.dict(
        os.environ,
        {
            # Simulate production .env settings
            "ARTIFACT_GENERATION_ENABLED": "true",
            "ARTIFACT_OUTPUT_FORMAT": "markdown",
            "ARTIFACT_OUTPUT_DIR": "./production_artifacts",
            # Only generate core artifacts
            "ARTIFACT_GENERATION_PROJECT_PROPOSAL": "true",
            "ARTIFACT_GENERATION_REQUIREMENTS_SPEC": "true",
            "ARTIFACT_GENERATION_ARCHITECTURE_DESIGN": "true",
            "ARTIFACT_GENERATION_API_DESIGN": "true",
            "ARTIFACT_GENERATION_CODE_REVIEW": "true",
            # Skip non-essential artifacts
            "ARTIFACT_GENERATION_DATA_DESIGN": "false",
            "ARTIFACT_GENERATION_AGENT_DESIGN": "false",
            "ARTIFACT_GENERATION_TEST_PLAN": "false",
            "ARTIFACT_GENERATION_TEST_REPORT": "false",
            "ARTIFACT_GENERATION_DEPLOYMENT_GUIDE": "false",
        },
        clear=False,
    )
    def test_production_env_config(self):
        """Test realistic production .env configuration"""
        config = get_config(force_reload=True)

        # Master settings
        assert config.artifacts.enabled is True
        assert config.artifacts.output_format == "markdown"
        assert str(config.artifacts.output_dir) == "./production_artifacts"

        # Core artifacts enabled
        assert config.artifacts.types["project_proposal"] is True
        assert config.artifacts.types["requirements_spec"] is True
        assert config.artifacts.types["architecture_design"] is True
        assert config.artifacts.types["api_design"] is True
        assert config.artifacts.types["code_review"] is True

        # Non-essential disabled
        assert config.artifacts.types["data_design"] is False
        assert config.artifacts.types["agent_design"] is False
        assert config.artifacts.types["test_plan"] is False
        assert config.artifacts.types["test_report"] is False
        assert config.artifacts.types["deployment_guide"] is False

    @patch.dict(
        os.environ,
        {
            # Simulate development .env settings (all artifacts)
            "ARTIFACT_GENERATION_ENABLED": "true",
            "ARTIFACT_OUTPUT_FORMAT": "json",
            "ARTIFACT_OUTPUT_DIR": "./dev_artifacts",
        },
        clear=False,
    )
    def test_development_env_config(self):
        """Test development .env configuration (all artifacts enabled)"""
        config = get_config(force_reload=True)

        assert config.artifacts.enabled is True
        assert config.artifacts.output_format == "json"

        # All artifacts enabled by default
        for type_key in config.artifacts.types:
            assert config.artifacts.types[type_key] is True


class TestEnvVarEdgeCases:
    """Test edge cases and error handling"""

    @patch.dict(
        os.environ,
        {
            "ARTIFACT_GENERATION_ENABLED": "true",
            "ARTIFACT_GENERATION_API_DESIGN": "invalid_value",
        },
        clear=False,
    )
    def test_invalid_boolean_value(self):
        """Test handling of invalid boolean value"""
        config = get_config(force_reload=True)

        # Invalid value should be treated as False (safe default)
        assert config.artifacts.types["api_design"] is False

    @patch.dict(
        os.environ,
        {
            "ARTIFACT_GENERATION_ENABLED": "true",
            "ARTIFACT_GENERATION_NONEXISTENT_TYPE": "false",
        },
        clear=False,
    )
    def test_unknown_env_var_ignored(self):
        """Test unknown env var is safely ignored"""
        config = get_config(force_reload=True)

        # Should not crash, unknown var ignored
        assert config.artifacts.enabled is True

        # Standard types should still work
        assert "api_design" in config.artifacts.types


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
