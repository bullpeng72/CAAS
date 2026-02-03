"""Port allocation and management for generated services.

This module provides centralized port management to prevent conflicts between
CAAS services and generated projects.
"""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set

from pydantic import BaseModel


class PortAllocation(BaseModel):
    """Represents a port allocation."""

    port: int
    service_name: str
    project_name: str
    allocated_at: str


class PortManager:
    """Manages port allocation for generated services.

    Reserved Ports:
    - 8000: FastAPI backend
    - 8501: Streamlit UI
    - 3000: Web UI
    - 50051: gRPC

    Frontend Port Range: 8600-8699
    """

    # Reserved ports that cannot be allocated
    RESERVED_PORTS: Set[int] = {8000, 8501, 3000, 50051}

    # Port range for generated frontends
    FRONTEND_PORT_START = 8600
    FRONTEND_PORT_END = 8699

    def __init__(self, registry_path: Optional[str] = None):
        """Initialize the port manager.

        Args:
            registry_path: Path to the port registry file. If None, uses ~/.caas/port_registry.json
        """
        if registry_path is None:
            caas_dir = Path.home() / ".caas"
            caas_dir.mkdir(exist_ok=True)
            registry_path = str(caas_dir / "port_registry.json")

        self.registry_path = registry_path
        self._lock = threading.Lock()
        self._ensure_registry_exists()

    def _ensure_registry_exists(self):
        """Create the registry file if it doesn't exist."""
        if not os.path.exists(self.registry_path):
            with open(self.registry_path, "w") as f:
                json.dump({}, f)

    def _load_registry(self) -> Dict[int, PortAllocation]:
        """Load the port registry from disk."""
        with open(self.registry_path, "r") as f:
            content = f.read()
            if not content or content.strip() == "":
                return {}
            data = json.loads(content)
            return {
                int(port): PortAllocation(**allocation)
                for port, allocation in data.items()
            }

    def _save_registry(self, registry: Dict[int, PortAllocation]):
        """Save the port registry to disk."""
        data = {
            str(port): allocation.model_dump() for port, allocation in registry.items()
        }
        with open(self.registry_path, "w") as f:
            json.dump(data, f, indent=2)

    def is_port_available(self, port: int) -> bool:
        """Check if a port is available for allocation.

        Args:
            port: The port number to check

        Returns:
            True if the port is available, False otherwise
        """
        # Reserved ports are never available
        if port in self.RESERVED_PORTS:
            return False

        with self._lock:
            registry = self._load_registry()
            return port not in registry

    def allocate_port(
        self,
        service_name: str,
        project_name: str = "default",
        preferred_port: Optional[int] = None,
    ) -> int:
        """Allocate a port for a service.

        Args:
            service_name: Name of the service (e.g., "frontend", "backend")
            project_name: Name of the project
            preferred_port: Preferred port number. If None, auto-allocates from range.

        Returns:
            The allocated port number

        Raises:
            ValueError: If the preferred port is reserved or already allocated
            RuntimeError: If no ports are available in the range
        """
        with self._lock:
            registry = self._load_registry()

            # If preferred port specified, try to use it
            if preferred_port is not None:
                if preferred_port in self.RESERVED_PORTS:
                    raise ValueError(
                        f"Port {preferred_port} is reserved and cannot be allocated. "
                        f"Reserved ports: {sorted(self.RESERVED_PORTS)}"
                    )

                if preferred_port in registry:
                    raise ValueError(
                        f"Port {preferred_port} is already allocated to "
                        f"{registry[preferred_port].service_name} "
                        f"in project {registry[preferred_port].project_name}"
                    )

                port = preferred_port
            else:
                # Auto-allocate from the frontend port range
                port = self._find_available_port(registry)

            # Allocate the port
            allocation = PortAllocation(
                port=port,
                service_name=service_name,
                project_name=project_name,
                allocated_at=datetime.now().isoformat(),
            )
            registry[port] = allocation
            self._save_registry(registry)

            return port

    def _find_available_port(self, registry: Dict[int, PortAllocation]) -> int:
        """Find an available port in the frontend port range.

        Args:
            registry: The current port registry

        Returns:
            An available port number

        Raises:
            RuntimeError: If no ports are available in the range
        """
        for port in range(self.FRONTEND_PORT_START, self.FRONTEND_PORT_END + 1):
            if port not in registry and port not in self.RESERVED_PORTS:
                return port

        raise RuntimeError(
            f"No available ports in range {self.FRONTEND_PORT_START}-{self.FRONTEND_PORT_END}. "
            f"Please release some ports or expand the range."
        )

    def release_port(self, port: int) -> bool:
        """Release a previously allocated port.

        Args:
            port: The port number to release

        Returns:
            True if the port was released, False if it wasn't allocated
        """
        with self._lock:
            registry = self._load_registry()

            if port not in registry:
                return False

            del registry[port]
            self._save_registry(registry)
            return True

    def list_allocations(self) -> Dict[int, PortAllocation]:
        """Get all current port allocations.

        Returns:
            Dictionary mapping port numbers to their allocations
        """
        with self._lock:
            return self._load_registry()

    def get_allocation(self, port: int) -> Optional[PortAllocation]:
        """Get the allocation for a specific port.

        Args:
            port: The port number

        Returns:
            The port allocation if it exists, None otherwise
        """
        with self._lock:
            registry = self._load_registry()
            return registry.get(port)

    def release_project_ports(self, project_name: str) -> int:
        """Release all ports allocated to a project.

        Args:
            project_name: Name of the project

        Returns:
            Number of ports released
        """
        with self._lock:
            registry = self._load_registry()
            ports_to_release = [
                port
                for port, allocation in registry.items()
                if allocation.project_name == project_name
            ]

            for port in ports_to_release:
                del registry[port]

            if ports_to_release:
                self._save_registry(registry)

            return len(ports_to_release)
