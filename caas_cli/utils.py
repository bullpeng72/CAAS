"""
CLI Utility Functions
"""

import sys
from typing import Optional

import click


def echo_success(message: str):
    """Print success message"""
    click.echo(click.style(f"✅ {message}", fg="green"))


def echo_error(message: str):
    """Print error message"""
    click.echo(click.style(f"❌ {message}", fg="red"), err=True)


def echo_warning(message: str):
    """Print warning message"""
    click.echo(click.style(f"⚠️  {message}", fg="yellow"))


def echo_info(message: str):
    """Print info message"""
    click.echo(click.style(f"ℹ️  {message}", fg="cyan"))


def echo_progress(message: str):
    """Print progress message"""
    click.echo(click.style(f"⏳ {message}", fg="blue"))


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Ask for user confirmation.

    Args:
        message: Confirmation message
        default: Default value

    Returns:
        bool: User's choice
    """
    return click.confirm(message, default=default)


def prompt_text(message: str, default: Optional[str] = None) -> str:
    """
    Prompt for text input.

    Args:
        message: Prompt message
        default: Default value

    Returns:
        str: User input
    """
    return click.prompt(message, default=default, type=str)


def prompt_choice(message: str, choices: list, default: Optional[str] = None) -> str:
    """
    Prompt for choice.

    Args:
        message: Prompt message
        choices: List of choices
        default: Default choice

    Returns:
        str: Selected choice
    """
    return click.prompt(
        message, type=click.Choice(choices, case_sensitive=False), default=default
    )


def print_table(headers: list, rows: list):
    """
    Print table.

    Args:
        headers: Table headers
        rows: Table rows
    """
    # Calculate column widths
    col_widths = [len(h) for h in headers]

    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Print header
    header_line = "  ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    click.echo(click.style(header_line, bold=True))
    click.echo("-" * len(header_line))

    # Print rows
    for row in rows:
        row_line = "  ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths))
        click.echo(row_line)


def print_json(data: dict):
    """Print JSON data"""
    import json

    click.echo(json.dumps(data, indent=2))


class ProgressBar:
    """Progress bar for long-running operations"""

    def __init__(self, total: int, label: str = "Progress"):
        """
        Initialize progress bar.

        Args:
            total: Total steps
            label: Progress bar label
        """
        self.bar = click.progressbar(
            length=total, label=label, show_percent=True, show_pos=True
        )

    def __enter__(self):
        self.bar.__enter__()
        return self

    def __exit__(self, *args):
        self.bar.__exit__(*args)

    def update(self, n: int = 1):
        """Update progress"""
        self.bar.update(n)


def handle_keyboard_interrupt(func):
    """Decorator to handle keyboard interrupt"""
    import asyncio
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Check if function is async
            if asyncio.iscoroutinefunction(func):
                return asyncio.run(func(*args, **kwargs))
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            echo_warning("\nOperation cancelled by user")
            sys.exit(1)

    return wrapper


def load_json(file_path: str):
    """
    Load JSON file with error handling.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data

    Raises:
        SystemExit: If file cannot be loaded
    """
    import json

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        echo_error(f"File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        echo_error(f"Invalid JSON in {file_path}: {e}")
        sys.exit(1)
    except Exception as e:
        echo_error(f"Failed to load {file_path}: {e}")
        sys.exit(1)


def save_json(file_path, data):
    """
    Save data to JSON file.

    Args:
        file_path: Output path (str or Path)
        data: Data to save (dict, list, or Pydantic model)
    """
    import json
    from pathlib import Path

    try:
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Handle Pydantic models
        if hasattr(data, "model_dump"):
            data = data.model_dump()
        elif hasattr(data, "dict"):
            data = data.dict()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        echo_success(f"Saved to: {file_path}")
    except Exception as e:
        echo_error(f"Failed to save {file_path}: {e}")
        sys.exit(1)


def save_files(output_dir, files_dict):
    """
    Save multiple files to output directory.

    Args:
        output_dir: Output directory path (str or Path)
        files_dict: Dict mapping file paths to content
    """
    from pathlib import Path

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    for file_path, content in files_dict.items():
        try:
            full_path = output_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to string if needed
            if isinstance(content, dict):
                import json

                content = json.dumps(content, indent=2, ensure_ascii=False)
            elif not isinstance(content, str):
                content = str(content)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            saved_count += 1
        except Exception as e:
            echo_warning(f"Failed to save {file_path}: {e}")

    echo_success(f"Saved {saved_count}/{len(files_dict)} files to {output_dir}")


def print_phase_banner(phase_num: int, phase_name: str):
    """
    Print BMAD phase banner.

    Args:
        phase_num: Phase number (0-5)
        phase_name: Phase name
    """
    click.echo()
    click.echo(click.style("═" * 70, fg="cyan"))
    click.echo(click.style(f"  Phase {phase_num}: {phase_name}", fg="cyan", bold=True))
    click.echo(click.style("═" * 70, fg="cyan"))
    click.echo()


def print_validation_results(result):
    """
    Print validation results with colors.

    Args:
        result: Validation result object
    """
    if hasattr(result, "is_valid"):
        if result.is_valid:
            echo_success("Validation passed!")
        else:
            echo_error("Validation failed!")

    if hasattr(result, "errors") and result.errors:
        click.echo()
        click.echo(click.style("Errors:", fg="red", bold=True))
        for error in result.errors:
            click.echo(f"  - {error}")

    if hasattr(result, "warnings") and result.warnings:
        click.echo()
        click.echo(click.style("Warnings:", fg="yellow", bold=True))
        for warning in result.warnings:
            click.echo(f"  - {warning}")

    if hasattr(result, "summary"):
        click.echo()
        click.echo(click.style("Summary:", bold=True))
        if isinstance(result.summary, dict):
            for key, value in result.summary.items():
                click.echo(f"  {key}: {value}")
        else:
            click.echo(f"  {result.summary}")


# Global session manager instance
_session_manager = None


def get_or_create_session_manager():
    """
    Get or create global SessionManager instance.

    Returns:
        SessionManager: Global session manager
    """
    global _session_manager

    if _session_manager is None:
        try:
            from pathlib import Path

            from caas_framework.session.manager import SessionManager

            # Store sessions in ~/.caas/sessions.json
            session_dir = Path.home() / ".caas"
            session_dir.mkdir(exist_ok=True)

            _session_manager = SessionManager(
                storage_path=session_dir / "sessions.json"
            )
        except ImportError:
            echo_error("Failed to import SessionManager from caas_framework")
            sys.exit(1)

    return _session_manager


async def initialize_framework(llm_provider: str = "openai", **config):
    """
    Initialize framework with common settings.

    Args:
        llm_provider: LLM provider name
        **config: Additional configuration

    Returns:
        CrewAIFramework: Initialized framework
    """
    try:
        from pathlib import Path

        from dotenv import load_dotenv

        from caas_framework import CrewAIFramework
        from caas_framework.config.settings import FrameworkConfig

        # Load .env file
        env_paths = [Path.cwd() / ".env", Path(__file__).parent.parent / ".env"]
        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path)
                break

        # Create config
        framework_config = FrameworkConfig(**config)

        # Initialize framework
        framework = CrewAIFramework(llm_provider=llm_provider, config=framework_config)

        await framework.initialize()
        echo_success("Framework initialized")

        return framework

    except ImportError as e:
        echo_error(f"Failed to import caas_framework: {e}")
        echo_info("Make sure caas-framework is installed: pip install -e .")
        sys.exit(1)
    except Exception as e:
        echo_error(f"Failed to initialize framework: {e}")
        sys.exit(1)
