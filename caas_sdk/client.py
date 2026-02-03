"""
CAAS Python SDK Client

Main client for interacting with CAAS API.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Optional

import httpx

from caas_sdk.exceptions import (
    APIError,
    AuthenticationError,
    CAASError,
    NetworkError,
    RateLimitError,
    TimeoutError,
)
from caas_sdk.models import (
    GenerationConfig,
    GenerationResult,
    Project,
    ProjectStatus,
)


class BaseClient:
    """Base client with common functionality"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:8000",
        timeout: int = 300,
    ):
        """
        Initialize CAAS client.

        Args:
            api_key: API key for authentication
            base_url: Base URL of CAAS API
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["X-API-Key"] = self.api_key

        return headers

    def _handle_error(self, response: httpx.Response):
        """Handle API error response"""
        if response.status_code == 401:
            raise AuthenticationError("Authentication failed. Check your API key.")
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise RateLimitError(
                f"Rate limit exceeded. Retry after {retry_after} seconds.",
                retry_after=retry_after,
            )
        elif response.status_code >= 400:
            try:
                error_data = response.json()
                message = error_data.get("detail", response.text)
            except (json.JSONDecodeError, ValueError):
                message = response.text

            raise APIError(f"API error: {message}", status_code=response.status_code)


class CAAS(BaseClient):
    """
    CAAS Python SDK (Sync)

    Usage:
        client = CAAS(api_key="your_api_key")
        project = client.create_project(
            requirement="Build a task management app"
        )
        result = client.get_result(project.project_id)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:8000",
        timeout: int = 300,
    ):
        """Initialize sync CAAS client"""
        super().__init__(api_key, base_url, timeout)
        self.client = httpx.Client(timeout=timeout)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def create_project(
        self,
        requirement: str,
        domain: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ) -> Project:
        """
        Create new project.

        Args:
            requirement: Natural language requirement
            domain: Optional domain hint
            config: Generation configuration

        Returns:
            Project: Created project
        """
        if config is None:
            config = GenerationConfig(requirement=requirement, domain=domain)
        else:
            config.requirement = requirement
            if domain:
                config.domain = domain

        try:
            response = self.client.post(
                f"{self.base_url}/api/v1/projects",
                json={
                    "requirement": config.requirement,
                    "domain": config.domain,
                    "deployment_target": config.deployment_target,
                    "workflow_type": config.workflow_type,
                    "enable_validation": config.enable_validation,
                    "enable_auto_fix": config.enable_auto_fix,
                    "enable_tests": config.enable_tests,
                    "metadata": config.metadata,
                },
                headers=self._get_headers(),
            )

            if response.status_code != 200:
                self._handle_error(response)

            data = response.json()

            return Project(**data)

        except httpx.TimeoutException:
            raise TimeoutError("Request timed out")
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error: {e}")

    def get_project(self, project_id: str) -> Project:
        """
        Get project by ID.

        Args:
            project_id: Project ID

        Returns:
            Project: Project details
        """
        try:
            response = self.client.get(
                f"{self.base_url}/api/v1/projects/{project_id}",
                headers=self._get_headers(),
            )

            if response.status_code != 200:
                self._handle_error(response)

            data = response.json()

            # Extract project from response wrapper
            project_data = data.get("project", data)
            return Project(**project_data)

        except httpx.TimeoutException:
            raise TimeoutError("Request timed out")
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error: {e}")

    def get_result(self, project_id: str) -> GenerationResult:
        """
        Get generation result.

        Args:
            project_id: Project ID

        Returns:
            GenerationResult: Generation result
        """
        try:
            response = self.client.get(
                f"{self.base_url}/api/v1/projects/{project_id}/result",
                headers=self._get_headers(),
            )

            if response.status_code != 200:
                self._handle_error(response)

            data = response.json()

            return GenerationResult(**data)

        except httpx.TimeoutException:
            raise TimeoutError("Request timed out")
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error: {e}")

    def wait_for_completion(
        self, project_id: str, poll_interval: int = 2, max_wait: int = 300
    ) -> GenerationResult:
        """
        Wait for project completion.

        Args:
            project_id: Project ID
            poll_interval: Polling interval in seconds
            max_wait: Maximum wait time in seconds

        Returns:
            GenerationResult: Generation result
        """
        start_time = time.time()

        while time.time() - start_time < max_wait:
            project = self.get_project(project_id)

            if project.status == ProjectStatus.COMPLETED:
                return self.get_result(project_id)
            elif project.status == ProjectStatus.FAILED:
                raise CAASError(f"Generation failed: {project.error_message}")

            time.sleep(poll_interval)

        raise TimeoutError(f"Project did not complete within {max_wait} seconds")

    def download_code(self, project_id: str, output_dir: str):
        """
        Download generated code.

        Args:
            project_id: Project ID
            output_dir: Output directory
        """
        result = self.get_result(project_id)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for file_path, content in result.files.items():
            file_full_path = output_path / file_path
            file_full_path.parent.mkdir(parents=True, exist_ok=True)
            file_full_path.write_text(content)

    def list_projects(self, status: Optional[str] = None, limit: int = 100) -> list:
        """
        List all projects.

        Args:
            status: Filter by status (generating, completed, failed)
            limit: Maximum number of projects

        Returns:
            List of projects (dict)
        """
        try:
            params = {"limit": limit}
            if status:
                params["status"] = status

            response = self.client.get(
                f"{self.base_url}/api/v1/projects",
                params=params,
                headers=self._get_headers(),
            )

            if response.status_code != 200:
                self._handle_error(response)

            data = response.json()
            return data.get("projects", [])

        except httpx.TimeoutException:
            raise TimeoutError("Request timed out")
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error: {e}")

    def generate(
        self,
        requirement: str,
        domain: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
        wait: bool = True,
    ) -> GenerationResult:
        """
        High-level generate method.

        Args:
            requirement: Natural language requirement
            domain: Optional domain hint
            config: Generation configuration
            wait: Wait for completion

        Returns:
            GenerationResult: Generation result
        """
        project = self.create_project(requirement, domain, config)

        if wait:
            return self.wait_for_completion(project.project_id)
        else:
            return GenerationResult(project_id=project.project_id, success=False)


class AsyncCAAS(BaseClient):
    """
    CAAS Python SDK (Async)

    Usage:
        async with AsyncCAAS(api_key="your_api_key") as client:
            project = await client.create_project(
                requirement="Build a task management app"
            )
            result = await client.get_result(project.project_id)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:8000",
        timeout: int = 300,
    ):
        """Initialize async CAAS client"""
        super().__init__(api_key, base_url, timeout)
        self.client = httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()

    async def create_project(
        self,
        requirement: str,
        domain: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ) -> Project:
        """Create new project (async)"""
        if config is None:
            config = GenerationConfig(requirement=requirement, domain=domain)

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/projects",
                json={
                    "requirement": config.requirement,
                    "domain": config.domain,
                    "deployment_target": config.deployment_target,
                    "metadata": config.metadata,
                },
                headers=self._get_headers(),
            )

            if response.status_code != 200:
                self._handle_error(response)

            data = response.json()

            return Project(**data)

        except httpx.TimeoutException:
            raise TimeoutError("Request timed out")
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error: {e}")

    async def get_project(self, project_id: str) -> Project:
        """Get project by ID (async)"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/projects/{project_id}",
                headers=self._get_headers(),
            )

            if response.status_code != 200:
                self._handle_error(response)

            data = response.json()

            return Project(**data)

        except httpx.TimeoutException:
            raise TimeoutError("Request timed out")
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error: {e}")

    async def get_result(self, project_id: str) -> GenerationResult:
        """Get generation result (async)"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/projects/{project_id}/result",
                headers=self._get_headers(),
            )

            if response.status_code != 200:
                self._handle_error(response)

            data = response.json()

            return GenerationResult(**data)

        except httpx.TimeoutException:
            raise TimeoutError("Request timed out")
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error: {e}")

    async def wait_for_completion(
        self, project_id: str, poll_interval: int = 2, max_wait: int = 300
    ) -> GenerationResult:
        """Wait for project completion (async)"""
        start_time = time.time()

        while time.time() - start_time < max_wait:
            project = await self.get_project(project_id)

            if project.status == ProjectStatus.COMPLETED:
                return await self.get_result(project_id)
            elif project.status == ProjectStatus.FAILED:
                raise CAASError(f"Generation failed: {project.error_message}")

            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Project did not complete within {max_wait} seconds")

    async def generate(
        self,
        requirement: str,
        domain: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
        wait: bool = True,
    ) -> GenerationResult:
        """High-level generate method (async)"""
        project = await self.create_project(requirement, domain, config)

        if wait:
            return await self.wait_for_completion(project.project_id)
        else:
            return GenerationResult(project_id=project.project_id, success=False)
