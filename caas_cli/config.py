"""
CLI Configuration Management
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any


class CLIConfig:
    """CLI configuration manager"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize CLI config.

        Args:
            config_path: Path to config file (default: ~/.caas/config.json)
        """
        if config_path is None:
            config_path = Path.home() / ".caas" / "config.json"

        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self._load()

    def _load(self):
        """Load config from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self._config = json.load(f)
            except Exception as e:
                click.echo(f"Warning: Failed to load config: {e}", err=True)
                self._config = {}
        else:
            self._config = self._default_config()

    def _save(self):
        """Save config to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w') as f:
            json.dump(self._config, f, indent=2)

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration"""
        return {
            "api_url": "http://localhost:8000",
            "api_key": None,
            "default_domain": None,
            "default_deployment": "docker",
            "enable_validation": True,
            "enable_auto_fix": True,
            "enable_tests": True,
            "use_expert_agents": True,
            "output_dir": "./generated",
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """Set config value"""
        self._config[key] = value
        self._save()

    def get_all(self) -> Dict[str, Any]:
        """Get all config"""
        return self._config.copy()

    def reset(self):
        """Reset to default config"""
        self._config = self._default_config()
        self._save()


def get_config() -> CLIConfig:
    """Get CLI config instance"""
    return CLIConfig()


# Make click available
import click
