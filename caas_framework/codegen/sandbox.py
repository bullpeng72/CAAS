"""
Code Execution Sandbox

Secure sandbox environment for executing and testing generated code.
"""

import tempfile
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import docker

from caas_framework.utils.logger import get_logger

logger = get_logger("sandbox")


class SandboxType(str, Enum):
    """Sandbox types"""

    DOCKER = "docker"
    PROCESS = "process"  # Subprocess-based (less secure)
    VIRTUAL_ENV = "venv"  # Virtual environment-based


@dataclass
class SandboxConfig:
    """Sandbox configuration"""

    sandbox_type: SandboxType = SandboxType.DOCKER
    timeout: int = 30  # seconds
    memory_limit: str = "512m"  # Docker memory limit
    cpu_limit: float = 1.0  # Docker CPU limit
    network_enabled: bool = False  # Disable network by default
    python_version: str = "3.11"


@dataclass
class ExecutionResult:
    """Sandbox execution result"""

    success: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    execution_time: float = 0.0
    error_message: Optional[str] = None


class DockerSandbox:
    """
    Docker-based Sandbox

    Provides isolated, secure environment for code execution.
    """

    def __init__(self, config: SandboxConfig):
        """
        Initialize Docker sandbox.

        Args:
            config: Sandbox configuration
        """
        self.config = config

        try:
            self.docker_client = docker.from_env()
            self.available = True
            logger.info("Docker sandbox initialized")
        except Exception as e:
            logger.warning(f"Docker not available: {e}")
            self.available = False

    def execute(
        self, files: Dict[str, str], command: str, entry_point: str = "main.py"
    ) -> ExecutionResult:
        """
        Execute code in Docker container.

        Args:
            files: Files to execute
            command: Command to run
            entry_point: Entry point file

        Returns:
            ExecutionResult: Execution result
        """
        if not self.available:
            return ExecutionResult(
                success=False, exit_code=-1, error_message="Docker is not available"
            )

        start_time = time.time()

        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write files
            for file_path, content in files.items():
                file_full_path = temp_path / file_path
                file_full_path.parent.mkdir(parents=True, exist_ok=True)
                file_full_path.write_text(content)

            # Create Dockerfile
            dockerfile = self._create_dockerfile()
            (temp_path / "Dockerfile").write_text(dockerfile)

            # Create requirements.txt (extract from files if needed)
            requirements = self._extract_requirements(files)
            if requirements:
                (temp_path / "requirements.txt").write_text("\n".join(requirements))

            try:
                # Build image
                logger.info("Building Docker image...")
                image, build_logs = self.docker_client.images.build(
                    path=str(temp_path), tag=f"caas-sandbox:{int(time.time())}", rm=True
                )

                # Run container
                logger.info(f"Running command: {command}")
                container = self.docker_client.containers.run(
                    image.id,
                    command=command,
                    remove=True,
                    mem_limit=self.config.memory_limit,
                    cpu_period=100000,
                    cpu_quota=int(100000 * self.config.cpu_limit),
                    network_disabled=not self.config.network_enabled,
                    detach=True,
                )

                # Wait for completion with timeout
                try:
                    result = container.wait(timeout=self.config.timeout)
                    exit_code = result["StatusCode"]

                    # Get logs
                    stdout = container.logs(stdout=True, stderr=False).decode("utf-8")
                    stderr = container.logs(stdout=False, stderr=True).decode("utf-8")

                    execution_time = time.time() - start_time

                    return ExecutionResult(
                        success=(exit_code == 0),
                        exit_code=exit_code,
                        stdout=stdout,
                        stderr=stderr,
                        execution_time=execution_time,
                    )

                except Exception as e:
                    # Timeout or other error
                    try:
                        container.stop(timeout=1)
                        container.remove()
                    except (docker.errors.APIError, docker.errors.NotFound) as cleanup_error:
                        # Container cleanup failed (already stopped/removed)
                        pass

                    return ExecutionResult(
                        success=False,
                        exit_code=-1,
                        error_message=f"Execution timeout or error: {e}",
                        execution_time=time.time() - start_time,
                    )

                finally:
                    # Cleanup image
                    try:
                        self.docker_client.images.remove(image.id, force=True)
                    except (docker.errors.APIError, docker.errors.ImageNotFound) as cleanup_error:
                        # Image cleanup failed (already removed)
                        pass

            except docker.errors.BuildError as e:
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    error_message=f"Docker build failed: {e}",
                    execution_time=time.time() - start_time,
                )

            except Exception as e:
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    error_message=f"Docker execution failed: {e}",
                    execution_time=time.time() - start_time,
                )

    def _create_dockerfile(self) -> str:
        """Create Dockerfile for sandbox"""
        return f"""
FROM python:{self.config.python_version}-slim

# Install dependencies
RUN pip install --no-cache-dir crewai pydantic fastapi uvicorn

# Copy code
WORKDIR /app
COPY . .

# Install requirements if present
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Set non-root user for security
RUN useradd -m -u 1000 sandbox
USER sandbox

# Default command
CMD ["python", "main.py"]
"""

    def _extract_requirements(self, files: Dict[str, str]) -> List[str]:
        """Extract required packages from files"""
        # Simple extraction - look for common imports
        import ast

        requirements = set()

        for file_path, content in files.items():
            if not file_path.endswith(".py"):
                continue

            try:
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module = alias.name.split(".")[0]
                            if self._is_third_party(module):
                                requirements.add(module)

                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module = node.module.split(".")[0]
                            if self._is_third_party(module):
                                requirements.add(module)

            except (SyntaxError, ValueError, UnicodeDecodeError) as e:
                # Failed to parse file - skip it
                continue

        return list(requirements)

    def _is_third_party(self, module: str) -> bool:
        """Check if module is third-party (not stdlib)"""
        stdlib_modules = {
            "abc",
            "ast",
            "asyncio",
            "collections",
            "dataclasses",
            "datetime",
            "enum",
            "functools",
            "itertools",
            "json",
            "logging",
            "math",
            "os",
            "pathlib",
            "random",
            "re",
            "subprocess",
            "sys",
            "tempfile",
            "time",
            "typing",
            "uuid",
        }

        return module not in stdlib_modules


class Sandbox:
    """
    Main Sandbox Manager

    Provides unified interface for different sandbox types.
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        """
        Initialize sandbox.

        Args:
            config: Sandbox configuration
        """
        self.config = config or SandboxConfig()

        # Initialize sandbox based on type
        if self.config.sandbox_type == SandboxType.DOCKER:
            self.backend = DockerSandbox(self.config)
        else:
            # Fallback to process-based sandbox
            logger.warning("Docker sandbox not available, using process-based")
            self.backend = None

        logger.info(f"Sandbox initialized: type={self.config.sandbox_type}")

    def execute(
        self, files: Dict[str, str], command: Optional[str] = None, entry_point: str = "main.py"
    ) -> ExecutionResult:
        """
        Execute code in sandbox.

        Args:
            files: Files to execute
            command: Command to run (default: python entry_point)
            entry_point: Entry point file

        Returns:
            ExecutionResult: Execution result
        """
        if command is None:
            command = f"python {entry_point}"

        if self.backend:
            return self.backend.execute(files, command, entry_point)
        else:
            return self._execute_subprocess(files, command, entry_point)

    def _execute_subprocess(
        self, files: Dict[str, str], command: str, entry_point: str
    ) -> ExecutionResult:
        """
        Fallback: Execute in subprocess (less secure).

        Args:
            files: Files to execute
            command: Command to run
            entry_point: Entry point file

        Returns:
            ExecutionResult: Execution result
        """
        import subprocess

        start_time = time.time()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write files
            for file_path, content in files.items():
                file_full_path = temp_path / file_path
                file_full_path.parent.mkdir(parents=True, exist_ok=True)
                file_full_path.write_text(content)

            try:
                # Execute command
                result = subprocess.run(
                    command.split(),
                    cwd=temp_path,
                    capture_output=True,
                    text=True,
                    timeout=self.config.timeout,
                )

                execution_time = time.time() - start_time

                return ExecutionResult(
                    success=(result.returncode == 0),
                    exit_code=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    execution_time=execution_time,
                )

            except subprocess.TimeoutExpired:
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    error_message="Execution timeout",
                    execution_time=time.time() - start_time,
                )

            except Exception as e:
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    error_message=f"Execution error: {e}",
                    execution_time=time.time() - start_time,
                )


def execute_in_sandbox(
    files: Dict[str, str],
    command: Optional[str] = None,
    entry_point: str = "main.py",
    timeout: int = 30,
) -> ExecutionResult:
    """
    Convenient function to execute code in sandbox.

    Args:
        files: Files to execute
        command: Command to run
        entry_point: Entry point file
        timeout: Execution timeout

    Returns:
        ExecutionResult: Execution result
    """
    config = SandboxConfig(timeout=timeout)
    sandbox = Sandbox(config)

    return sandbox.execute(files, command, entry_point)
