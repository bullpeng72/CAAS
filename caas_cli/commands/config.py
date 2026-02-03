"""
Config Command

Manage CAAS configuration.
"""

import click

from caas_cli.config import get_config
from caas_cli.utils import echo_info, echo_success, print_table


@click.command()
@click.option(
    "--set",
    "set_value",
    type=(str, str),
    multiple=True,
    help="Set configuration value(s) - can be used multiple times",
)
@click.option("--get", "get_key", type=str, help="Get specific configuration value")
@click.option("--list", "list_all", is_flag=True, help="List all configuration settings")
@click.option("--reset", is_flag=True, help="Reset configuration to default values")
def config(set_value, get_key, list_all, reset):
    """
    \b
    Manage CAAS CLI configuration settings

    \b
    ⚙️  CONFIGURATION FILE:
    ═══════════════════════════════════════════════════════════════════════════
    Location: ~/.caas/config.json

    Available settings:
      • api_url              - API server URL (default: http://localhost:8000)
      • api_key              - API authentication key (optional)
      • default_domain       - Default domain for generation
      • default_deployment   - Default deployment target (docker/kubernetes/serverless)
      • output_dir           - Default output directory (default: ./generated)
      • enable_validation    - Enable validation by default (true/false)
      • enable_auto_fix      - Enable auto-fix by default (true/false)
      • enable_tests         - Generate tests by default (true/false)
      • use_expert_agents    - Use expert agent collaboration (true/false)

    \b
    💡 USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  View all configuration:
       $ caas config --list
       $ caas config  (same as --list)

    \b
    2️⃣  Get specific value:
       $ caas config --get api_url
       $ caas config --get default_domain

    \b
    3️⃣  Set single value:
       $ caas config --set api_key "your_key_here"
       $ caas config --set api_url "http://api.caas.dev"
       $ caas config --set default_domain "FINANCE"

    \b
    4️⃣  Set multiple values at once:
       $ caas config \\
           --set api_url "http://api.caas.dev" \\
           --set default_domain "HEALTHCARE" \\
           --set enable_validation true

    \b
    5️⃣  Reset to defaults:
       $ caas config --reset

    \b
    🔒 SECURITY:
    ═══════════════════════════════════════════════════════════════════════════
    • API keys are masked in --list output (shows only last 4 chars)
    • Config file has restrictive permissions (user-only access)
    • Sensitive values can be overridden via environment variables:
      - CAAS_API_KEY
      - OPENAI_API_KEY

    \b
    🔄 OVERRIDE PRECEDENCE:
    ═══════════════════════════════════════════════════════════════════════════
    1. Command-line options (highest priority)
    2. Environment variables
    3. Config file settings
    4. Built-in defaults (lowest priority)

    \b
    ℹ️  NOTE:
    ═══════════════════════════════════════════════════════════════════════════
    • Run 'caas init' for interactive configuration wizard
    • Changes take effect immediately
    • All CLI commands respect these settings unless overridden

    \b
    📚 See also:
       caas init --help    (Interactive configuration setup)
    """
    cfg = get_config()

    if reset:
        if click.confirm("Reset configuration to defaults?", default=False):
            cfg.reset()
            echo_success("Configuration reset to defaults")
        return

    if set_value:
        for key, value in set_value:
            cfg.set(key, value)
            echo_success(f"Set {key} = {value}")
        return

    if get_key:
        value = cfg.get(get_key)
        if value is not None:
            click.echo(f"{get_key}: {value}")
        else:
            click.echo(f"{get_key}: (not set)")
        return

    if list_all or (not set_value and not get_key):
        # List all configuration
        config_data = cfg.get_all()

        click.echo(
            """
╔══════════════════════════════════════════════════════════════╗
║                  CAAS Configuration                          ║
╚══════════════════════════════════════════════════════════════╝
"""
        )

        # Hide sensitive values
        for key in config_data:
            if "key" in key.lower() and config_data[key]:
                config_data[key] = "***" + str(config_data[key])[-4:]

        # Print table
        rows = [[k, v] for k, v in config_data.items()]
        print_table(["Setting", "Value"], rows)

        click.echo()
        echo_info(f"Config file: {cfg.config_path}")
        click.echo()
        click.echo("To modify:")
        click.echo("  caas config --set <key> <value>")
        click.echo()
        click.echo("To reset:")
        click.echo("  caas config --reset")
