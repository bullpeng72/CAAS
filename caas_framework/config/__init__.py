"""
Configuration Management

Supports multiple configuration sources:
- Python dict
- YAML file
- Environment variables
- .env file
"""

from caas_framework.config.settings import FrameworkConfig
from caas_framework.config.loader import ConfigLoader

__all__ = ["FrameworkConfig", "ConfigLoader"]
