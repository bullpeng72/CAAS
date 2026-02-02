"""
CI/CD Generator - Automatic CI/CD Pipeline Configuration

Generates GitHub Actions workflows and Docker configuration for automated
testing, deployment, and continuous integration.
"""

from pathlib import Path


class CICDGenerator:
    """Automatic CI/CD pipeline configuration generator"""

    def generate_github_actions(
        self,
        project_dir: Path,
        python_version: str = "3.11",
        include_docker: bool = False,
        include_coverage: bool = True,
        verbose: bool = True,
    ) -> Path:
        """
        Generate GitHub Actions CI workflow

        Args:
            project_dir: Project directory
            python_version: Python version to use (default: 3.11)
            include_docker: Whether to include Docker build step
            include_coverage: Whether to include coverage reporting
            verbose: Whether to print progress messages

        Returns:
            Path to the generated workflow file
        """
        workflows_dir = project_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        ci_workflow_path = workflows_dir / "ci.yml"

        # Build workflow content
        workflow_content = self._build_ci_workflow(
            python_version=python_version,
            include_docker=include_docker,
            include_coverage=include_coverage,
        )

        ci_workflow_path.write_text(workflow_content)

        if verbose:
            print(f"✅ GitHub Actions CI workflow generated: {ci_workflow_path}")

        return ci_workflow_path

    def _build_ci_workflow(
        self, python_version: str, include_docker: bool, include_coverage: bool
    ) -> str:
        """Build GitHub Actions CI workflow YAML content"""

        workflow = f"""name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python {python_version}
      uses: actions/setup-python@v4
      with:
        python-version: {python_version}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: |
        {"pytest --cov=. --cov-report=xml --cov-report=term" if include_coverage else "pytest"}
"""

        if include_coverage:
            workflow += """
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: false
"""

        if include_docker:
            workflow += """
  docker:
    runs-on: ubuntu-latest
    needs: test

    steps:
    - uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Build Docker image
      run: docker build -t app:latest .

    - name: Test Docker image
      run: docker run --rm app:latest python -c "print('Docker image works!')"
"""

        return workflow

    def generate_docker_files(
        self,
        project_dir: Path,
        base_image: str = "python:3.11-slim",
        port: int = 8000,
        verbose: bool = True,
    ) -> tuple[Path, Path]:
        """
        Generate Dockerfile and docker-compose.yml

        Args:
            project_dir: Project directory
            base_image: Base Docker image
            port: Port to expose
            verbose: Whether to print progress messages

        Returns:
            Tuple of (Dockerfile path, docker-compose.yml path)
        """
        # Generate Dockerfile
        dockerfile_path = project_dir / "Dockerfile"
        dockerfile_content = f"""FROM {base_image}

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE {port}

# Run application
CMD ["python", "main.py"]
"""
        dockerfile_path.write_text(dockerfile_content)

        # Generate docker-compose.yml
        docker_compose_path = project_dir / "docker-compose.yml"
        docker_compose_content = f"""version: '3.8'

services:
  app:
    build: .
    ports:
      - "{port}:{port}"
    environment:
      - ENV=production
    volumes:
      - .:/app
    restart: unless-stopped
"""
        docker_compose_path.write_text(docker_compose_content)

        if verbose:
            print(f"✅ Dockerfile generated: {dockerfile_path}")
            print(f"✅ docker-compose.yml generated: {docker_compose_path}")

        return dockerfile_path, docker_compose_path

    def generate_all(
        self,
        project_dir: Path,
        python_version: str = "3.11",
        include_docker: bool = True,
        include_coverage: bool = True,
        docker_port: int = 8000,
        verbose: bool = True,
    ) -> dict[str, Path]:
        """
        Generate complete CI/CD configuration

        Args:
            project_dir: Project directory
            python_version: Python version
            include_docker: Include Docker configuration
            include_coverage: Include coverage reporting
            docker_port: Port for Docker
            verbose: Print progress messages

        Returns:
            Dictionary of generated file paths
        """
        generated_files = {}

        # GitHub Actions workflow
        ci_workflow = self.generate_github_actions(
            project_dir=project_dir,
            python_version=python_version,
            include_docker=include_docker,
            include_coverage=include_coverage,
            verbose=verbose,
        )
        generated_files["ci_workflow"] = ci_workflow

        # Docker files
        if include_docker:
            dockerfile, docker_compose = self.generate_docker_files(
                project_dir=project_dir, port=docker_port, verbose=verbose
            )
            generated_files["dockerfile"] = dockerfile
            generated_files["docker_compose"] = docker_compose

        return generated_files
