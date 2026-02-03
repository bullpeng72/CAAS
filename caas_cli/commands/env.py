"""
Env Command

Manage .env file configuration for CAAS projects.
"""

from pathlib import Path

import click

from caas_cli.utils import echo_error, echo_info, echo_success, echo_warning


@click.command()
@click.option(
    "--create", "-c", is_flag=True, help="Create .env file from template in current directory"
)
@click.option(
    "--show", "-s", is_flag=True, help="Show required environment variables and their descriptions"
)
@click.option("--validate", "-v", is_flag=True, help="Validate existing .env file")
@click.option(
    "--path", "-p", type=click.Path(), default=".env", help="Path to .env file (default: .env)"
)
def env(create, show, validate, path):
    """
    \b
    Manage .env file configuration for CAAS projects

    \b
    📝 WHAT IT DOES:
    ═══════════════════════════════════════════════════════════════════════════
    Help you set up and manage environment variables required for:
    • OpenAI API access (for LLM-based generation)
    • Optional API keys for other services
    • Configuration overrides

    \b
    🔑 REQUIRED VARIABLES:
    ═══════════════════════════════════════════════════════════════════════════
    • OPENAI_API_KEY            - OpenAI API key for GPT models (required)
                                  Get from: https://platform.openai.com/api-keys

    \b
    ⚙️  OPTIONAL VARIABLES:
    ═══════════════════════════════════════════════════════════════════════════
    • ANTHROPIC_API_KEY         - Anthropic Claude API key (optional)
    • CAAS_API_KEY              - CAAS API server authentication key
    • CAAS_API_URL              - CAAS API server URL
                                  (default: http://localhost:8000)
    • CAAS_DEFAULT_DOMAIN       - Default domain for generation
                                  (FINANCE, HEALTHCARE, etc.)
    • CAAS_DEFAULT_DEPLOYMENT   - Default deployment target
                                  (docker, kubernetes, serverless)
    • CAAS_OUTPUT_DIR           - Default output directory
                                  (default: ./generated)

    \b
    💡 USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Show all environment variables (help):
       $ caas env --show
       $ caas env -s

    \b
    2️⃣  Create .env file from template:
       $ caas env --create
       $ caas env -c

    \b
    3️⃣  Create .env in specific directory:
       $ caas env --create --path ./my-project/.env

    \b
    4️⃣  Validate existing .env file:
       $ caas env --validate
       $ caas env -v

    \b
    5️⃣  Validate .env in specific location:
       $ caas env --validate --path ./my-project/.env

    \b
    📋 .ENV FILE TEMPLATE:
    ═══════════════════════════════════════════════════════════════════════════
    # OpenAI Configuration (Required)
    OPENAI_API_KEY=sk-...your-key-here...

    # Anthropic Configuration (Optional)
    # ANTHROPIC_API_KEY=sk-ant-...your-key-here...

    # CAAS API Configuration (Optional - for remote API mode)
    # CAAS_API_KEY=your-caas-api-key
    # CAAS_API_URL=http://localhost:8000

    # CAAS Default Settings (Optional)
    # CAAS_DEFAULT_DOMAIN=FINANCE
    # CAAS_DEFAULT_DEPLOYMENT=docker
    # CAAS_OUTPUT_DIR=./generated

    \b
    🔒 SECURITY BEST PRACTICES:
    ═══════════════════════════════════════════════════════════════════════════
    • Never commit .env files to version control
    • Add .env to .gitignore
    • Use different keys for development/production
    • Rotate API keys regularly
    • Set restrictive file permissions: chmod 600 .env

    \b
    ⚠️  TROUBLESHOOTING:
    ═══════════════════════════════════════════════════════════════════════════
    • "OpenAI API key not found" error
      → Set OPENAI_API_KEY in .env file
      → Or export OPENAI_API_KEY=sk-... in your shell

    • Generated code fails to run
      → Verify .env exists in project directory
      → Check API key is valid: test at https://platform.openai.com

    • Permission denied
      → Check file permissions: ls -la .env
      → Should be readable: chmod 644 .env (or 600 for more security)

    \b
    📚 See also:
       caas init --help        (CLI configuration)
       caas config --help      (Manage CLI settings)
       caas generate --help    (Generate projects)
    """
    env_path = Path(path)

    # Default behavior: show help
    if not create and not show and not validate:
        show = True

    if show:
        _show_env_info()
        return

    if create:
        _create_env_file(env_path)
        return

    if validate:
        _validate_env_file(env_path)
        return


def _show_env_info():
    """Show environment variables information"""
    click.echo(
        """
╔══════════════════════════════════════════════════════════════╗
║           CAAS Environment Variables Reference               ║
╚══════════════════════════════════════════════════════════════╝
"""
    )

    click.echo("🔑 REQUIRED:")
    click.echo("─────────────────────────────────────────────────────────────")
    click.echo("  OPENAI_API_KEY")
    click.echo("    Purpose:  OpenAI API access for GPT models")
    click.echo("    Get from: https://platform.openai.com/api-keys")
    click.echo("    Example:  OPENAI_API_KEY=sk-proj-...")
    click.echo()

    click.echo("⚙️  OPTIONAL:")
    click.echo("─────────────────────────────────────────────────────────────")
    click.echo("  ANTHROPIC_API_KEY")
    click.echo("    Purpose:  Anthropic Claude API access (if using Claude)")
    click.echo("    Example:  ANTHROPIC_API_KEY=sk-ant-...")
    click.echo()

    click.echo("  CAAS_API_KEY")
    click.echo("    Purpose:  Authentication for CAAS API server (remote mode)")
    click.echo("    Example:  CAAS_API_KEY=your-api-key")
    click.echo()

    click.echo("  CAAS_API_URL")
    click.echo("    Purpose:  CAAS API server URL")
    click.echo("    Default:  http://localhost:8000")
    click.echo("    Example:  CAAS_API_URL=https://api.caas.dev")
    click.echo()

    click.echo("  CAAS_DEFAULT_DOMAIN")
    click.echo("    Purpose:  Default domain for code generation")
    click.echo("    Options:  FINANCE, HEALTHCARE, E_COMMERCE, TASK_MANAGEMENT, etc.")
    click.echo("    Example:  CAAS_DEFAULT_DOMAIN=FINANCE")
    click.echo()

    click.echo("  CAAS_DEFAULT_DEPLOYMENT")
    click.echo("    Purpose:  Default deployment target")
    click.echo("    Options:  docker, kubernetes, serverless")
    click.echo("    Example:  CAAS_DEFAULT_DEPLOYMENT=kubernetes")
    click.echo()

    click.echo("  CAAS_OUTPUT_DIR")
    click.echo("    Purpose:  Default output directory for generated code")
    click.echo("    Default:  ./generated")
    click.echo("    Example:  CAAS_OUTPUT_DIR=./my-projects")
    click.echo()

    echo_info("💡 Create .env file: caas env --create")
    echo_info("💡 Validate .env:    caas env --validate")


def _create_env_file(env_path: Path):
    """Create .env file from template"""
    if env_path.exists():
        if not click.confirm(f"{env_path} already exists. Overwrite?", default=False):
            echo_warning("Operation cancelled")
            return

    template = """# CAAS Environment Configuration
# Generated by: caas env --create

# ============================================================================
# OpenAI Configuration (REQUIRED)
# ============================================================================
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-proj-your-key-here

# ============================================================================
# Anthropic Configuration (OPTIONAL)
# ============================================================================
# Uncomment if you want to use Claude models
# ANTHROPIC_API_KEY=sk-ant-your-key-here

# ============================================================================
# CAAS API Configuration (OPTIONAL - for remote API mode)
# ============================================================================
# Uncomment if using CAAS API server instead of local framework
# CAAS_API_KEY=your-caas-api-key
# CAAS_API_URL=http://localhost:8000

# ============================================================================
# CAAS Default Settings (OPTIONAL)
# ============================================================================
# These can be overridden via CLI options

# Default domain for generation (FINANCE, HEALTHCARE, E_COMMERCE, etc.)
# CAAS_DEFAULT_DOMAIN=FINANCE

# Default deployment target (docker, kubernetes, serverless)
# CAAS_DEFAULT_DEPLOYMENT=docker

# Default output directory for generated code
# CAAS_OUTPUT_DIR=./generated

# ============================================================================
# Security Notes
# ============================================================================
# 1. NEVER commit this file to version control
# 2. Add .env to your .gitignore file
# 3. Use different keys for development/production
# 4. Set restrictive permissions: chmod 600 .env
"""

    try:
        env_path.write_text(template)
        echo_success(f"Created .env file: {env_path}")
        echo_info("")
        echo_info("Next steps:")
        echo_info("  1. Edit .env and add your OPENAI_API_KEY")
        echo_info("  2. Secure the file: chmod 600 .env")
        echo_info("  3. Add .env to .gitignore")
        echo_info("  4. Validate: caas env --validate")
    except Exception as e:
        echo_error(f"Failed to create .env file: {e}")


def _validate_env_file(env_path: Path):
    """Validate .env file"""
    click.echo(
        """
╔══════════════════════════════════════════════════════════════╗
║              .env File Validation                            ║
╚══════════════════════════════════════════════════════════════╝
"""
    )

    echo_info(f"Checking: {env_path}")
    click.echo()

    if not env_path.exists():
        echo_error(f"✗ File not found: {env_path}")
        echo_info("")
        echo_info("Create .env file with: caas env --create")
        return

    echo_success(f"✓ File exists: {env_path}")

    # Check file permissions
    import stat

    mode = env_path.stat().st_mode
    if mode & stat.S_IROTH or mode & stat.S_IRGRP:
        echo_warning("⚠ File permissions too open (readable by others)")
        echo_info("  Recommended: chmod 600 .env")
    else:
        echo_success("✓ File permissions OK")

    # Read and parse .env
    try:
        content = env_path.read_text()
        lines = [
            line.strip()
            for line in content.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]

        env_vars = {}
        for line in lines:
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

        # Check required variables
        click.echo()
        click.echo("🔑 Required Variables:")
        click.echo("─────────────────────────────────────────────────────────────")

        if "OPENAI_API_KEY" in env_vars:
            key_value = env_vars["OPENAI_API_KEY"]
            if key_value and key_value != "sk-proj-your-key-here" and key_value.startswith("sk-"):
                echo_success("✓ OPENAI_API_KEY is set")
            else:
                echo_error("✗ OPENAI_API_KEY is not set or using placeholder")
                echo_info("  Get your key from: https://platform.openai.com/api-keys")
        else:
            echo_error("✗ OPENAI_API_KEY not found")
            echo_info("  Add: OPENAI_API_KEY=sk-proj-your-key-here")

        # Check optional variables
        click.echo()
        click.echo("⚙️  Optional Variables:")
        click.echo("─────────────────────────────────────────────────────────────")

        optional_vars = {
            "ANTHROPIC_API_KEY": "Anthropic Claude API",
            "CAAS_API_KEY": "CAAS API authentication",
            "CAAS_API_URL": "CAAS API server URL",
            "CAAS_DEFAULT_DOMAIN": "Default domain",
            "CAAS_DEFAULT_DEPLOYMENT": "Default deployment target",
            "CAAS_OUTPUT_DIR": "Default output directory",
        }

        for var, description in optional_vars.items():
            if var in env_vars:
                echo_success(f"✓ {var} is set ({description})")
            else:
                echo_info(f"  {var} not set ({description})")

        click.echo()
        echo_success("✓ Validation complete")

    except Exception as e:
        echo_error(f"✗ Failed to parse .env file: {e}")
