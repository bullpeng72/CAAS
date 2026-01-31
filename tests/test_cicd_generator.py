"""
Tests for CICDGenerator

Tests automated CI/CD configuration generation.
"""

import pytest
from pathlib import Path
from caas_framework.automation import CICDGenerator


class TestCICDGenerator:
    """Test CI/CD configuration generator"""

    def test_generator_creation(self):
        """Test creating CICDGenerator"""
        generator = CICDGenerator()
        assert generator is not None

    def test_generate_github_actions_basic(self, tmp_path):
        """Test basic GitHub Actions workflow generation"""
        generator = CICDGenerator()

        workflow_path = generator.generate_github_actions(
            project_dir=tmp_path,
            python_version="3.11",
            verbose=False
        )

        # Check file was created
        assert workflow_path.exists()
        assert workflow_path.name == "ci.yml"
        assert workflow_path.parent.name == "workflows"

        # Check content
        content = workflow_path.read_text()
        assert "name: CI" in content
        assert "on:" in content
        assert "push:" in content
        assert "pull_request:" in content
        assert "python-version: 3.11" in content
        assert "pytest" in content

    def test_generate_github_actions_with_coverage(self, tmp_path):
        """Test GitHub Actions workflow with coverage"""
        generator = CICDGenerator()

        workflow_path = generator.generate_github_actions(
            project_dir=tmp_path,
            include_coverage=True,
            verbose=False
        )

        content = workflow_path.read_text()

        # Should include coverage steps
        assert "pytest --cov" in content
        assert "codecov" in content
        assert "coverage.xml" in content

    def test_generate_github_actions_without_coverage(self, tmp_path):
        """Test GitHub Actions workflow without coverage"""
        generator = CICDGenerator()

        workflow_path = generator.generate_github_actions(
            project_dir=tmp_path,
            include_coverage=False,
            verbose=False
        )

        content = workflow_path.read_text()

        # Should not include coverage
        assert "pytest --cov" not in content
        assert "codecov" not in content

    def test_generate_github_actions_with_docker(self, tmp_path):
        """Test GitHub Actions workflow with Docker build"""
        generator = CICDGenerator()

        workflow_path = generator.generate_github_actions(
            project_dir=tmp_path,
            include_docker=True,
            verbose=False
        )

        content = workflow_path.read_text()

        # Should include Docker job
        assert "docker:" in content
        assert "docker build" in content
        assert "docker run" in content

    def test_generate_github_actions_without_docker(self, tmp_path):
        """Test GitHub Actions workflow without Docker"""
        generator = CICDGenerator()

        workflow_path = generator.generate_github_actions(
            project_dir=tmp_path,
            include_docker=False,
            verbose=False
        )

        content = workflow_path.read_text()

        # Should not include Docker job
        assert "docker:" not in content
        assert "docker build" not in content

    def test_generate_github_actions_custom_python_version(self, tmp_path):
        """Test GitHub Actions workflow with custom Python version"""
        generator = CICDGenerator()

        workflow_path = generator.generate_github_actions(
            project_dir=tmp_path,
            python_version="3.10",
            verbose=False
        )

        content = workflow_path.read_text()
        assert "python-version: 3.10" in content

    def test_generate_dockerfile(self, tmp_path):
        """Test Dockerfile generation"""
        generator = CICDGenerator()

        dockerfile_path, _ = generator.generate_docker_files(
            project_dir=tmp_path,
            verbose=False
        )

        # Check file was created
        assert dockerfile_path.exists()
        assert dockerfile_path.name == "Dockerfile"

        # Check content
        content = dockerfile_path.read_text()
        assert "FROM python:3.11-slim" in content
        assert "WORKDIR /app" in content
        assert "COPY requirements.txt" in content
        assert "RUN pip install" in content
        assert "COPY . ." in content
        assert "CMD" in content

    def test_generate_docker_compose(self, tmp_path):
        """Test docker-compose.yml generation"""
        generator = CICDGenerator()

        _, docker_compose_path = generator.generate_docker_files(
            project_dir=tmp_path,
            verbose=False
        )

        # Check file was created
        assert docker_compose_path.exists()
        assert docker_compose_path.name == "docker-compose.yml"

        # Check content
        content = docker_compose_path.read_text()
        assert "version: '3.8'" in content
        assert "services:" in content
        assert "app:" in content
        assert "build: ." in content
        assert "ports:" in content
        assert "environment:" in content

    def test_generate_docker_custom_image(self, tmp_path):
        """Test Dockerfile with custom base image"""
        generator = CICDGenerator()

        dockerfile_path, _ = generator.generate_docker_files(
            project_dir=tmp_path,
            base_image="python:3.10-alpine",
            verbose=False
        )

        content = dockerfile_path.read_text()
        assert "FROM python:3.10-alpine" in content

    def test_generate_docker_custom_port(self, tmp_path):
        """Test Docker files with custom port"""
        generator = CICDGenerator()

        dockerfile_path, docker_compose_path = generator.generate_docker_files(
            project_dir=tmp_path,
            port=5000,
            verbose=False
        )

        dockerfile_content = dockerfile_path.read_text()
        assert "EXPOSE 5000" in dockerfile_content

        compose_content = docker_compose_path.read_text()
        assert "5000:5000" in compose_content

    def test_generate_all_minimal(self, tmp_path):
        """Test generating all CI/CD files (minimal)"""
        generator = CICDGenerator()

        generated = generator.generate_all(
            project_dir=tmp_path,
            include_docker=False,
            verbose=False
        )

        # Should have CI workflow
        assert 'ci_workflow' in generated
        assert generated['ci_workflow'].exists()

        # Should not have Docker files
        assert 'dockerfile' not in generated
        assert 'docker_compose' not in generated

    def test_generate_all_complete(self, tmp_path):
        """Test generating all CI/CD files (complete)"""
        generator = CICDGenerator()

        generated = generator.generate_all(
            project_dir=tmp_path,
            include_docker=True,
            include_coverage=True,
            verbose=False
        )

        # Should have all files
        assert 'ci_workflow' in generated
        assert 'dockerfile' in generated
        assert 'docker_compose' in generated

        # All files should exist
        assert generated['ci_workflow'].exists()
        assert generated['dockerfile'].exists()
        assert generated['docker_compose'].exists()

    def test_generate_all_returns_paths(self, tmp_path):
        """Test that generate_all returns correct paths"""
        generator = CICDGenerator()

        generated = generator.generate_all(
            project_dir=tmp_path,
            include_docker=True,
            verbose=False
        )

        # Check paths
        assert generated['ci_workflow'] == tmp_path / '.github' / 'workflows' / 'ci.yml'
        assert generated['dockerfile'] == tmp_path / 'Dockerfile'
        assert generated['docker_compose'] == tmp_path / 'docker-compose.yml'

    def test_generates_valid_yaml(self, tmp_path):
        """Test that generated YAML is valid"""
        import yaml

        generator = CICDGenerator()

        # Generate workflow
        workflow_path = generator.generate_github_actions(
            project_dir=tmp_path,
            verbose=False
        )

        # Parse YAML to verify it's valid
        content = workflow_path.read_text()
        parsed = yaml.safe_load(content)

        assert parsed is not None
        assert 'name' in parsed
        # YAML parses "on:" as boolean True
        assert True in parsed or 'on' in parsed
        assert 'jobs' in parsed

    def test_workflow_has_required_steps(self, tmp_path):
        """Test that workflow includes all required steps"""
        import yaml

        generator = CICDGenerator()

        workflow_path = generator.generate_github_actions(
            project_dir=tmp_path,
            include_coverage=True,
            verbose=False
        )

        content = workflow_path.read_text()
        parsed = yaml.safe_load(content)

        # Check test job exists
        assert 'test' in parsed['jobs']
        test_job = parsed['jobs']['test']

        # Check required steps
        step_names = [step.get('name', step.get('uses', '')) for step in test_job['steps']]

        assert any('checkout' in s for s in step_names)
        assert any('Python' in s for s in step_names)
        assert any('Install dependencies' in s for s in step_names)
        assert any('Run tests' in s for s in step_names)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
