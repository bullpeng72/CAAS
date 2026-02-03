"""
Plugins Command

Manage plugins
"""

import click

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_success,
    handle_keyboard_interrupt,
)


@click.group()
def plugins():
    """Manage plugins"""
    pass


@plugins.command(name="list")
@click.option(
    "--type",
    "-t",
    type=click.Choice(["llm", "tool", "storage", "all"]),
    default="all",
    help="Filter plugins by type (default: all)",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed plugin information")
@handle_keyboard_interrupt
def list_plugins(type, verbose):
    """
    List available plugins

    \b
    USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  List all plugins:
       $ caas plugins list

    \b
    2️⃣  List LLM plugins only:
       $ caas plugins list --type llm

    \b
    3️⃣  List with details:
       $ caas plugins list --verbose

    \b
    PLUGIN TYPES:
    ═══════════════════════════════════════════════════════════════════════════
    • llm      - Language model plugins (OpenAI, Anthropic, etc.)
    • tool     - Tool plugins (search, code execution, etc.)
    • storage  - Storage plugins (file system, cloud, etc.)
    """
    try:
        from caas_framework.plugins import get_plugin_registry

        registry = get_plugin_registry()
        all_plugins = registry.list_available_plugins()

        # Filter by type
        if type != "all":
            all_plugins = [p for p in all_plugins if p.get("type") == type]

        if not all_plugins:
            echo_info(f"No {type} plugins found")
            return

        # Show plugins
        if verbose:
            # Detailed view
            for plugin in all_plugins:
                click.echo(click.style(f"\n{plugin['name']}", bold=True))
                click.echo(f"  Type:        {plugin.get('type', 'N/A')}")
                click.echo(f"  Version:     {plugin.get('version', 'N/A')}")
                click.echo(f"  Status:      {plugin.get('status', 'N/A')}")
                if "description" in plugin:
                    click.echo(f"  Description: {plugin['description']}")
                if "author" in plugin:
                    click.echo(f"  Author:      {plugin['author']}")
        else:
            # Table view
            headers = ["Name", "Type", "Version", "Status"]
            rows = []

            for plugin in all_plugins:
                name = plugin.get("name", "N/A")
                plugin_type = plugin.get("type", "N/A")
                version = plugin.get("version", "N/A")
                status = plugin.get("status", "N/A")

                rows.append([name, plugin_type, version, status])

            print_table(headers, rows)

        echo_info(f"Total plugins: {len(all_plugins)}")

    except ImportError as e:
        echo_error(f"Failed to import plugin modules: {e}")
        echo_info("Make sure caas-framework is installed: pip install -e .")
        return 1
    except Exception as e:
        echo_error(f"Failed to list plugins: {e}")
        return 1


@plugins.command()
@click.argument("plugin_name")
@click.option(
    "--verbose", "-v", is_flag=True, help="Show detailed health check results"
)
@handle_keyboard_interrupt
async def status(plugin_name, verbose):
    """
    Check plugin health status

    \b
    USAGE:
       $ caas plugins status openai
       $ caas plugins status anthropic --verbose

    \b
    CHECKS:
    ═══════════════════════════════════════════════════════════════════════════
    • Plugin availability
    • API connectivity (for LLM plugins)
    • Configuration validity
    • Dependencies
    """
    try:
        from caas_framework.plugins import get_plugin_registry

        echo_info(f"Checking status of plugin: {plugin_name}")

        registry = get_plugin_registry()
        plugin = registry.get_plugin(plugin_name)

        if not plugin:
            echo_error(f"Plugin not found: {plugin_name}")
            return 1

        # Run health check
        health_result = await plugin.health_check()

        # Show results
        click.echo()
        click.echo(click.style("Health Check Results:", bold=True))
        click.echo(f"  Plugin:      {plugin_name}")
        click.echo(f"  Status:      {health_result.get('status', 'unknown')}")
        click.echo(f"  Healthy:     {health_result.get('healthy', False)}")

        if "latency" in health_result:
            click.echo(f"  Latency:     {health_result['latency']:.2f}ms")

        if verbose and "details" in health_result:
            click.echo()
            click.echo(click.style("Details:", bold=True))
            for key, value in health_result["details"].items():
                click.echo(f"  {key}: {value}")

        # Show status
        click.echo()
        if health_result.get("healthy"):
            echo_success("Plugin is healthy")
        else:
            echo_error("Plugin has issues")
            if "error" in health_result:
                echo_error(f"Error: {health_result['error']}")
            return 1

    except ImportError as e:
        echo_error(f"Failed to import plugin modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to check plugin status: {e}")
        if verbose:
            import traceback

            echo_error(traceback.format_exc())
        return 1


@plugins.command()
@click.argument("plugin_name")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed plugin information")
@handle_keyboard_interrupt
def info(plugin_name, verbose):
    """
    Show plugin information

    \b
    USAGE:
       $ caas plugins info openai
       $ caas plugins info openai --verbose
    """
    try:
        from caas_framework.plugins import get_plugin_registry

        registry = get_plugin_registry()
        plugin = registry.get_plugin(plugin_name)

        if not plugin:
            echo_error(f"Plugin not found: {plugin_name}")
            return 1

        # Get plugin info
        info = plugin.get_info()

        # Show info
        click.echo(click.style(f"Plugin: {plugin_name}", bold=True))
        click.echo(f"  Type:        {info.get('type', 'N/A')}")
        click.echo(f"  Version:     {info.get('version', 'N/A')}")
        click.echo(f"  Status:      {info.get('status', 'N/A')}")

        if "description" in info:
            click.echo(f"  Description: {info['description']}")

        if "author" in info:
            click.echo(f"  Author:      {info['author']}")

        if "homepage" in info:
            click.echo(f"  Homepage:    {info['homepage']}")

        # Verbose info
        if verbose:
            if "capabilities" in info:
                click.echo()
                click.echo(click.style("Capabilities:", bold=True))
                for cap in info["capabilities"]:
                    click.echo(f"  • {cap}")

            if "dependencies" in info:
                click.echo()
                click.echo(click.style("Dependencies:", bold=True))
                for dep in info["dependencies"]:
                    click.echo(f"  • {dep}")

            if "configuration" in info:
                click.echo()
                click.echo(click.style("Configuration:", bold=True))
                for key, value in info["configuration"].items():
                    click.echo(f"  {key}: {value}")

    except ImportError as e:
        echo_error(f"Failed to import plugin modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to get plugin info: {e}")
        return 1


@plugins.command()
@click.argument("plugin_name")
@handle_keyboard_interrupt
def enable(plugin_name):
    """
    Enable plugin

    \b
    USAGE:
       $ caas plugins enable openai
    """
    try:
        from caas_framework.plugins import get_plugin_registry

        registry = get_plugin_registry()
        plugin = registry.get_plugin(plugin_name)

        if not plugin:
            echo_error(f"Plugin not found: {plugin_name}")
            return 1

        plugin.enable()

        echo_success(f"Plugin enabled: {plugin_name}")

    except ImportError as e:
        echo_error(f"Failed to import plugin modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to enable plugin: {e}")
        return 1


@plugins.command()
@click.argument("plugin_name")
@handle_keyboard_interrupt
def disable(plugin_name):
    """
    Disable plugin

    \b
    USAGE:
       $ caas plugins disable openai
    """
    try:
        from caas_framework.plugins import get_plugin_registry

        registry = get_plugin_registry()
        plugin = registry.get_plugin(plugin_name)

        if not plugin:
            echo_error(f"Plugin not found: {plugin_name}")
            return 1

        plugin.disable()

        echo_success(f"Plugin disabled: {plugin_name}")

    except ImportError as e:
        echo_error(f"Failed to import plugin modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to disable plugin: {e}")
        return 1


@plugins.command()
@click.argument("plugin_name")
@click.option("--key", "-k", required=True, help="Configuration key")
@click.option("--value", "-v", required=True, help="Configuration value")
@handle_keyboard_interrupt
def configure(plugin_name, key, value):
    """
    Configure plugin

    \b
    USAGE:
       $ caas plugins configure openai --key api_key --value "sk-..."
       $ caas plugins configure openai --key model --value "gpt-4"
    """
    try:
        from caas_framework.plugins import get_plugin_registry

        registry = get_plugin_registry()
        plugin = registry.get_plugin(plugin_name)

        if not plugin:
            echo_error(f"Plugin not found: {plugin_name}")
            return 1

        plugin.configure({key: value})

        echo_success(f"Plugin configured: {plugin_name}")
        echo_info(f"Set {key} = {value}")

    except ImportError as e:
        echo_error(f"Failed to import plugin modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to configure plugin: {e}")
        return 1
