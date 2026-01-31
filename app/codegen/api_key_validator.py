"""
API Key Validator for Code Generation

Validates that required API keys are configured before generating code.
"""

from typing import List, Dict, Tuple
from app.codegen.tool_api_keys import get_tool_api_key_requirements, is_tool_requires_api_key
from app.utils.env_manager import get_env_manager
from app.utils.logger import get_logger

logger = get_logger("codegen.api_key_validator")


class ApiKeyValidationResult:
    """Result of API key validation"""

    def __init__(self):
        self.missing_required: List[Tuple[str, str]] = []  # (tool_name, env_var)
        self.missing_optional: List[Tuple[str, str]] = []  # (tool_name, env_var)
        self.configured: List[Tuple[str, str]] = []  # (tool_name, env_var)

    @property
    def has_missing_required(self) -> bool:
        """Check if any required API keys are missing"""
        return len(self.missing_required) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings (missing optional keys)"""
        return len(self.missing_optional) > 0

    def get_summary(self) -> str:
        """Get a summary of the validation result"""
        lines = []

        if self.configured:
            lines.append(f"✅ {len(self.configured)} API keys configured")

        if self.missing_required:
            lines.append(f"❌ {len(self.missing_required)} required API keys missing:")
            for tool, env_var in self.missing_required:
                lines.append(f"   - {env_var} (for {tool})")

        if self.missing_optional:
            lines.append(f"⚠️  {len(self.missing_optional)} optional API keys missing:")
            for tool, env_var in self.missing_optional:
                lines.append(f"   - {env_var} (for {tool})")

        return "\n".join(lines)


class ApiKeyValidator:
    """Validates API key configuration for tools"""

    def __init__(self):
        self.env_manager = get_env_manager()

    def validate_tools(self, tool_names: List[str]) -> ApiKeyValidationResult:
        """
        Validate that required API keys are configured for the given tools

        Args:
            tool_names: List of tool names to validate

        Returns:
            ApiKeyValidationResult with validation details
        """
        result = ApiKeyValidationResult()

        for tool_name in tool_names:
            # Skip tools that don't require API keys
            if not is_tool_requires_api_key(tool_name):
                continue

            # Get requirements for this tool
            requirements = get_tool_api_key_requirements(tool_name)

            for req in requirements:
                # Check if the key is set
                is_set = self.env_manager.is_key_set(req.env_var)

                if is_set:
                    result.configured.append((tool_name, req.env_var))
                elif req.optional:
                    result.missing_optional.append((tool_name, req.env_var))
                    logger.warning(f"Optional API key {req.env_var} not set for {tool_name}")
                else:
                    result.missing_required.append((tool_name, req.env_var))
                    logger.error(f"Required API key {req.env_var} not set for {tool_name}")

        return result

    def get_setup_instructions(self, tool_names: List[str]) -> str:
        """
        Get setup instructions for missing API keys

        Args:
            tool_names: List of tool names

        Returns:
            Formatted instructions string
        """
        result = self.validate_tools(tool_names)

        if not result.has_missing_required and not result.has_warnings:
            return "✅ All required API keys are configured!"

        instructions = ["# API Key Setup Instructions\n"]

        if result.has_missing_required:
            instructions.append("## ❌ Required API Keys (Must be configured)\n")
            instructions.append("The following API keys are required for your project to work:\n")

            for tool, env_var in result.missing_required:
                requirements = get_tool_api_key_requirements(tool)
                for req in requirements:
                    if req.env_var == env_var:
                        instructions.append(f"\n### {env_var} (for {tool})")
                        instructions.append(f"**Description:** {req.description}")
                        if req.signup_url:
                            instructions.append(f"**Get API Key:** {req.signup_url}")
                        instructions.append(f"\n**Setup:**")
                        instructions.append(f"1. Sign up at {req.signup_url or 'the service website'}")
                        instructions.append(f"2. Get your API key")
                        instructions.append(f"3. Add to your .env file:")
                        instructions.append(f"   ```")
                        instructions.append(f"   {env_var}=your-api-key-here")
                        instructions.append(f"   ```\n")

        if result.has_warnings:
            instructions.append("\n## ⚠️ Optional API Keys (Recommended)\n")
            instructions.append("These tools can work without API keys but may have limited functionality:\n")

            for tool, env_var in result.missing_optional:
                requirements = get_tool_api_key_requirements(tool)
                for req in requirements:
                    if req.env_var == env_var:
                        instructions.append(f"\n### {env_var} (for {tool})")
                        instructions.append(f"**Description:** {req.description}")
                        if req.signup_url:
                            instructions.append(f"**Get API Key:** {req.signup_url}\n")

        instructions.append("\n## Using Streamlit UI")
        instructions.append("\nYou can also manage API keys through the Streamlit UI:")
        instructions.append("1. Run: `streamlit run caas_streamlit/app.py`")
        instructions.append("2. Go to **Tool Manager → API Keys** tab")
        instructions.append("3. Configure your API keys\n")

        return "\n".join(instructions)


def validate_and_warn(tool_names: List[str], raise_on_missing: bool = False) -> ApiKeyValidationResult:
    """
    Validate API keys and warn/raise if missing

    Args:
        tool_names: List of tool names to validate
        raise_on_missing: Whether to raise an exception if required keys are missing

    Returns:
        ApiKeyValidationResult

    Raises:
        ValueError: If raise_on_missing is True and required keys are missing
    """
    validator = ApiKeyValidator()
    result = validator.validate_tools(tool_names)

    # Log summary
    logger.info(result.get_summary())

    # Raise if requested and there are missing required keys
    if raise_on_missing and result.has_missing_required:
        instructions = validator.get_setup_instructions(tool_names)
        raise ValueError(
            f"Missing required API keys. Please configure them before proceeding.\n\n{instructions}"
        )

    return result
