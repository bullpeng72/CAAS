"""
Configuration Module

Re-exports settings from app.utils.config for backward compatibility.
"""

from caas_app.utils.config import settings, get_settings, reload_settings, Settings

__all__ = ["settings", "get_settings", "reload_settings", "Settings"]
