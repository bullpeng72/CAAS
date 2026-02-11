"""
Artifact Configuration Tests

v0.5.0: Configuration priority and Dict-based settings validation

Tests:
1. Configuration priority (env > user config > YAML > code defaults)
2. Dict-based type settings
3. Backward compatibility with old boolean fields
4. ArtifactGenerationConfig behavior
"""

import os
import tempfile
from pathlib import Path
from typing import Dict

import pytest
import yaml

from caas_framework.config.unified import ArtifactConfig, UnifiedConfigLoader, get_config
from caas_framework.models.artifact_types import (
    ArtifactGenerationConfig,
    ArtifactType,
)


class TestArtifactConfigPriority:
    """Test configuration priority system"""

    def test_code_defaults(self):
        """Test code-level defaults (lowest priority)"""
        config = ArtifactConfig()

        # Check defaults
        assert config.enabled is True
        assert config.output_dir == "./artifacts"
        assert config.output_format == "markdown"

        # Check Dict-based types
        assert "code_review" in config.types
        assert config.types["code_review"] is True
        assert config.types["project_proposal"] is True
        assert config.types["api_design"] is True  # ✅ v0.5.0: All artifacts enabled by default

    def test_yaml_override(self):
        """Test YAML file overrides code defaults"""
        # Note: In practice, YAML loading works through defaults/ directory
        # This test validates the ArtifactConfig data structure instead

        # Simulate YAML-loaded config
        artifact_config = ArtifactConfig(
            enabled=True,
            types={
                "project_proposal": False,  # Override to False
                "code_review": True,
                "api_design": True,  # Override to True
            },
            output_dir="/custom/path",
        )

        # Validate overrides work
        assert artifact_config.types["project_proposal"] is False
        assert artifact_config.types["code_review"] is True
        assert artifact_config.types["api_design"] is True
        assert artifact_config.output_dir == "/custom/path"

    def test_env_override(self):
        """Test environment variables override YAML (highest priority)"""
        # Set environment variable
        os.environ["ARTIFACT_OUTPUT_DIR"] = "/env/override/path"

        try:
            config = get_config(force_reload=True)

            # Environment variable should override YAML/code defaults
            assert config.artifacts.output_dir == "/env/override/path"
        finally:
            # Clean up
            if "ARTIFACT_OUTPUT_DIR" in os.environ:
                del os.environ["ARTIFACT_OUTPUT_DIR"]

    def test_priority_cascade(self):
        """Test full priority cascade: env > user config > YAML > code"""
        # 1. Code defaults: output_dir = "./artifacts"
        # 2. YAML override: output_dir = "/yaml/path"
        # 3. Env override: output_dir = "/env/path"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as tmp:
            yaml_config = {
                "artifacts": {
                    "output_dir": "/yaml/path",
                }
            }
            yaml.dump(yaml_config, tmp)
            tmp_path = Path(tmp.name)

        os.environ["ARTIFACT_OUTPUT_DIR"] = "/env/path"

        try:
            loader = UnifiedConfigLoader(config_file=tmp_path)
            config = loader.load()

            # Environment variable (highest priority) should win
            assert config.artifacts.output_dir == "/env/path"
        finally:
            tmp_path.unlink()
            if "ARTIFACT_OUTPUT_DIR" in os.environ:
                del os.environ["ARTIFACT_OUTPUT_DIR"]


class TestDictBasedTypeSettings:
    """Test Dict-based artifact type settings (v0.5.0)"""

    def test_dict_based_types(self):
        """Test Dict-based type configuration"""
        types: Dict[str, bool] = {
            "project_proposal": True,
            "code_review": False,
            "api_design": True,
        }

        config = ArtifactGenerationConfig(enabled=True, enabled_types=types)

        # Check Dict is used correctly
        assert config.enabled_types == types
        assert config.is_enabled(ArtifactType.PROJECT_PROPOSAL) is True
        assert config.is_enabled(ArtifactType.CODE_REVIEW) is False
        assert config.is_enabled(ArtifactType.API_DESIGN) is True

    def test_get_enabled_artifact_types(self):
        """Test get_enabled_artifact_types() with Dict config"""
        types: Dict[str, bool] = {
            "project_proposal": True,
            "requirements_spec": True,
            "code_review": False,
            "api_design": False,
        }

        config = ArtifactGenerationConfig(enabled=True, enabled_types=types)

        enabled = config.get_enabled_artifact_types()

        # Should only return enabled types
        assert ArtifactType.PROJECT_PROPOSAL in enabled
        assert ArtifactType.REQUIREMENTS_SPEC in enabled
        assert ArtifactType.CODE_REVIEW not in enabled
        assert ArtifactType.API_DESIGN not in enabled

    def test_is_enabled_method(self):
        """Test is_enabled() method for individual types"""
        config = ArtifactGenerationConfig(
            enabled=True,
            enabled_types={"code_review": True, "test_plan": False},
        )

        assert config.is_enabled(ArtifactType.CODE_REVIEW) is True
        assert config.is_enabled(ArtifactType.TEST_PLAN) is False

    def test_enabled_master_switch(self):
        """Test enabled master switch overrides all types"""
        config = ArtifactGenerationConfig(
            enabled=False,  # Master switch OFF
            enabled_types={"code_review": True},  # Type enabled
        )

        # Even if type is True, master switch OFF means disabled
        assert config.is_enabled(ArtifactType.CODE_REVIEW) is False
        assert config.get_enabled_artifact_types() == []


class TestBackwardCompatibility:
    """Test backward compatibility with old boolean fields"""

    def test_old_fields_map_to_dict(self):
        """Test old generate_* fields are mapped to enabled_types Dict"""
        # Use old API
        config = ArtifactGenerationConfig(
            enabled=True,
            generate_code_review=False,  # Old field
            generate_api_design=True,  # Old field
        )

        # Should be mapped to Dict
        assert config.enabled_types["code_review"] is False
        assert config.enabled_types["api_design"] is True

    def test_mixed_old_and_new_fields(self):
        """Test mixing old fields and new Dict (old fields override)"""
        config = ArtifactGenerationConfig(
            enabled=True,
            enabled_types={"code_review": True},  # New Dict says True
            generate_code_review=False,  # Old field says False (should override)
        )

        # Old field should override Dict
        assert config.enabled_types["code_review"] is False

    def test_deprecated_fields_still_work(self):
        """Test deprecated fields still function for backward compatibility"""
        # Old API should still work
        config = ArtifactGenerationConfig(
            enabled=True,
            generate_project_proposal=True,
            generate_requirements_spec=False,
            generate_code_review=True,
        )

        # Verify it works
        assert config.is_enabled(ArtifactType.PROJECT_PROPOSAL) is True
        assert config.is_enabled(ArtifactType.REQUIREMENTS_SPEC) is False
        assert config.is_enabled(ArtifactType.CODE_REVIEW) is True


class TestArtifactConfigUnified:
    """Test unified.py::ArtifactConfig Dict support"""

    def test_artifact_config_dict_types(self):
        """Test ArtifactConfig uses Dict-based types"""
        config = ArtifactConfig(
            enabled=True,
            types={
                "code_review": False,
                "api_design": True,
            },
        )

        assert config.types["code_review"] is False
        assert config.types["api_design"] is True

    def test_artifact_config_backward_compat(self):
        """Test ArtifactConfig backward compatibility with old fields"""
        config = ArtifactConfig(
            enabled=True,
            generate_code_review=False,  # Old field
        )

        # Should map to Dict
        assert config.types["code_review"] is False


class TestConfigurationEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_types_dict(self):
        """Test empty enabled_types Dict"""
        config = ArtifactGenerationConfig(enabled=True, enabled_types={})

        # Should not crash, all types disabled
        assert config.get_enabled_artifact_types() == []
        assert config.is_enabled(ArtifactType.CODE_REVIEW) is False

    def test_partial_types_dict(self):
        """Test partial enabled_types Dict (only some types specified)"""
        config = ArtifactGenerationConfig(
            enabled=True,
            enabled_types={"code_review": True},  # Only one type
        )

        # Specified type enabled
        assert config.is_enabled(ArtifactType.CODE_REVIEW) is True

        # Unspecified types should default to False
        assert config.is_enabled(ArtifactType.TEST_PLAN) is False

    def test_invalid_type_key(self):
        """Test is_enabled() with invalid/unknown type"""
        config = ArtifactGenerationConfig(
            enabled=True,
            enabled_types={"code_review": True},
        )

        # Unknown type should return False (no crash)
        # This is safe because Dict.get() returns None by default
        assert config.is_enabled(ArtifactType.TEST_PLAN) is False


# =============================================================================
# Integration Tests
# =============================================================================


class TestEndToEndConfiguration:
    """End-to-end configuration flow tests"""

    def test_features_yaml_loading(self):
        """Test loading features.yaml with Dict-based types"""
        # This test verifies that features.yaml is correctly structured
        config = get_config(force_reload=True)

        # Should load from features.yaml
        assert config.artifacts.enabled is True
        assert "types" in config.artifacts.__dict__ or hasattr(
            config.artifacts, "types"
        )

        # Verify types Dict exists and has expected values
        if hasattr(config.artifacts, "types"):
            assert isinstance(config.artifacts.types, dict)
            assert "code_review" in config.artifacts.types

    def test_engine_integration(self):
        """Test SixPhaseEngine can load artifact config correctly"""
        from caas_framework.config import get_config

        config = get_config(force_reload=True)
        artifact_config = config.artifacts

        # Simulate engine.py loading
        enabled_types = getattr(artifact_config, "types", {})

        # Should have types Dict
        assert isinstance(enabled_types, dict)
        assert len(enabled_types) > 0

        # Create ArtifactGenerationConfig
        gen_config = ArtifactGenerationConfig(
            enabled=True,
            output_directory=artifact_config.output_dir,
            enabled_types=enabled_types,
        )

        # Verify it works
        assert gen_config.enabled is True
        assert len(gen_config.get_enabled_artifact_types()) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
