"""
Base Plugin Interface

All plugins (LLM, Vector DB, Graph DB) inherit from Plugin base class.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Type


class PluginType(str, Enum):
    """Plugin types"""

    LLM = "llm"
    VECTORDB = "vectordb"
    GRAPHDB = "graphdb"
    TOOL = "tool"


class Plugin(ABC):
    """
    Base plugin interface

    All plugins must implement:
    - initialize(): Setup plugin
    - health_check(): Verify plugin is working
    - close(): Cleanup resources
    """

    def __init__(self, name: str, plugin_type: PluginType, config: Dict[str, Any]):
        self.name = name
        self.plugin_type = plugin_type
        self.config = config
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize plugin (connect, authenticate, etc.)"""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if plugin is healthy"""

    @abstractmethod
    async def close(self) -> None:
        """Close connections and cleanup"""

    @property
    def is_initialized(self) -> bool:
        """Check if plugin is initialized"""
        return self._initialized

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, type={self.plugin_type})>"


class PluginRegistry:
    """
    Central plugin registry

    Manages plugin lifecycle:
    - Registration
    - Initialization
    - Discovery
    - Cleanup
    """

    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_classes: Dict[str, Type[Plugin]] = {}

    def register_plugin_class(self, name: str, plugin_class: Type[Plugin]) -> None:
        """
        Register a plugin class

        Args:
            name: Plugin name (e.g., "openai", "neo4j")
            plugin_class: Plugin class
        """
        self._plugin_classes[name] = plugin_class

    def register_plugin(self, plugin: Plugin) -> None:
        """
        Register a plugin instance

        Args:
            plugin: Plugin instance
        """
        self._plugins[plugin.name] = plugin

    async def initialize_plugin(
        self, name: str, plugin_type: PluginType, config: Dict[str, Any]
    ) -> Plugin:
        """
        Initialize a plugin by name

        Args:
            name: Plugin name
            plugin_type: Plugin type
            config: Plugin configuration

        Returns:
            Initialized plugin instance

        Raises:
            ValueError: If plugin not found
        """
        if name not in self._plugin_classes:
            raise ValueError(f"Plugin '{name}' not registered")

        plugin_class = self._plugin_classes[name]
        plugin = plugin_class(name=name, config=config)

        await plugin.initialize()
        self._plugins[name] = plugin

        return plugin

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get plugin by name"""
        return self._plugins.get(name)

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[Plugin]:
        """Get all plugins of a specific type"""
        return [
            plugin
            for plugin in self._plugins.values()
            if plugin.plugin_type == plugin_type
        ]

    async def close_all(self) -> None:
        """Close all plugins"""
        for plugin in self._plugins.values():
            await plugin.close()

        self._plugins.clear()

    def list_available_plugin_names(self) -> List[str]:
        """List names of all registered plugin classes"""
        return list(self._plugin_classes.keys())

    def list_available_plugins(self) -> List[Dict[str, str]]:
        """List all registered plugins with metadata (name, type, version, status)."""
        result = []
        # Include registered class names (not yet instantiated)
        for name, cls in self._plugin_classes.items():
            plugin_type = getattr(cls, "plugin_type", PluginType.LLM)
            result.append({
                "name": name,
                "type": plugin_type.value if hasattr(plugin_type, "value") else str(plugin_type),
                "version": getattr(cls, "version", "N/A"),
                "status": "registered",
                "description": getattr(cls, "__doc__", "").strip().split("\n")[0] if cls.__doc__ else "",
            })
        # Include live instances
        for name, plugin in self._plugins.items():
            existing = next((p for p in result if p["name"] == name), None)
            if existing:
                existing["status"] = "active" if plugin.is_initialized else "inactive"
            else:
                plugin_type = plugin.plugin_type
                result.append({
                    "name": name,
                    "type": plugin_type.value if hasattr(plugin_type, "value") else str(plugin_type),
                    "version": getattr(plugin, "version", "N/A"),
                    "status": "active" if plugin.is_initialized else "inactive",
                    "description": "",
                })
        return result

    def __repr__(self) -> str:
        return f"<PluginRegistry(plugins={len(self._plugins)}, classes={len(self._plugin_classes)})>"


# Global registry
_global_registry = PluginRegistry()


def get_plugin_registry() -> PluginRegistry:
    """Get global plugin registry"""
    return _global_registry
