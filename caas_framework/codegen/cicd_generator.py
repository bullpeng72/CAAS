"""
CI/CD Pipeline Generator

Generates CI/CD pipeline configurations for different platforms.
Supports GitHub Actions, GitLab CI, and Jenkins.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class CICDConfig:
    """CI/CD configuration"""

    platform: str = "github_actions"  # github_actions, gitlab_ci, jenkins
    python_version: str = "3.11"
    run_tests: bool = True
    run_linting: bool = True
    build_docker: bool = True
    deploy_enabled: bool = False
    deploy_target: str = "docker"


class CICDGenerator:
    """
    CI/CD Pipeline Generator

    Generates pipeline configurations for various CI/CD platforms.
    """

    def generate_all(self, config: CICDConfig) -> Dict[str, str]:
        """
        Generate CI/CD pipeline files.

        Args:
            config: CI/CD configuration

        Returns:
            Dict[str, str]: Pipeline configuration files
        """
        files = {}

        if config.platform == "github_actions":
            files.update(self._generate_github_actions(config))
        elif config.platform == "gitlab_ci":
            files.update(self._generate_gitlab_ci(config))
        elif config.platform == "jenkins":
            files.update(self._generate_jenkins(config))

        return files

    def _generate_github_actions(self, config: CICDConfig) -> Dict[str, str]:
        """Generate GitHub Actions workflows"""
        files = {}

        # Main CI workflow
        files[
            ".github/workflows/ci.yml"
        ] = f"""name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: ["{config.python_version}"]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{{{ matrix.python-version }}}}
      uses: actions/setup-python@v4
      with:
        python-version: ${{{{ matrix.python-version }}}}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

{"    - name: Run linting" if config.run_linting else "# Linting disabled"}
{"      run: |" if config.run_linting else ""}
{"        pip install black flake8 mypy" if config.run_linting else ""}
{"        black --check ." if config.run_linting else ""}
{"        flake8 ." if config.run_linting else ""}
{"        mypy src/" if config.run_linting else ""}

{"    - name: Run tests" if config.run_tests else "# Tests disabled"}
{"      run: |" if config.run_tests else ""}
{"        pytest tests/ -v --cov=src --cov-report=xml" if config.run_tests else ""}

{"    - name: Upload coverage" if config.run_tests else ""}
{"      uses: codecov/codecov-action@v3" if config.run_tests else ""}
{"      with:" if config.run_tests else ""}
{"        file: ./coverage.xml" if config.run_tests else ""}
"""

        # Build and push Docker image
        if config.build_docker:
            files[
                ".github/workflows/docker-build.yml"
            ] = """name: Docker Build

on:
  push:
    branches: [ main ]
    tags:
      - 'v*'

jobs:
  docker:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Log in to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ secrets.DOCKER_USERNAME }}/my-app

    - name: Build and push
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
"""

        # Deployment workflow
        if config.deploy_enabled:
            files[
                ".github/workflows/deploy.yml"
            ] = f"""name: Deploy

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Deploy to {config.deploy_target}
      run: |
        echo "Deploying to {config.deploy_target}..."
        # Add your deployment commands here
"""

        return files

    def _generate_gitlab_ci(self, config: CICDConfig) -> Dict[str, str]:
        """Generate GitLab CI configuration"""
        files = {}

        # Coverage regex pattern (extracted to avoid f-string backslash issue)
        coverage_pattern = r"'/(?i)total.*? (100(?:\.0+)?\%|[1-9]?\d(?:\.\d+)?\%)$/'"

        files[
            ".gitlab-ci.yml"
        ] = f"""
image: python:{config.python_version}

stages:
  - lint
  - test
  - build
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip
    - venv/

before_script:
  - python -m venv venv
  - source venv/bin/activate
  - pip install -r requirements.txt

{"lint:" if config.run_linting else "# Linting disabled"}
{"  stage: lint" if config.run_linting else ""}
{"  script:" if config.run_linting else ""}
{"    - pip install black flake8 mypy" if config.run_linting else ""}
{"    - black --check ." if config.run_linting else ""}
{"    - flake8 ." if config.run_linting else ""}
{"    - mypy src/" if config.run_linting else ""}

{"test:" if config.run_tests else "# Tests disabled"}
{"  stage: test" if config.run_tests else ""}
{"  script:" if config.run_tests else ""}
{"    - pip install pytest pytest-cov" if config.run_tests else ""}
{"    - pytest tests/ --cov=src --cov-report=xml --cov-report=html" if config.run_tests else ""}
{f"  coverage: {coverage_pattern}" if config.run_tests else ""}
{"  artifacts:" if config.run_tests else ""}
{"    reports:" if config.run_tests else ""}
{"      coverage_report:" if config.run_tests else ""}
{"        coverage_format: cobertura" if config.run_tests else ""}
{"        path: coverage.xml" if config.run_tests else ""}

{"docker-build:" if config.build_docker else "# Docker build disabled"}
{"  stage: build" if config.build_docker else ""}
{"  image: docker:latest" if config.build_docker else ""}
{"  services:" if config.build_docker else ""}
{"    - docker:dind" if config.build_docker else ""}
{"  before_script:" if config.build_docker else ""}
{"    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY" if config.build_docker else ""}
{"  script:" if config.build_docker else ""}
{"    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_REF_SLUG ." if config.build_docker else ""}
{"    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_REF_SLUG" if config.build_docker else ""}
{"  only:" if config.build_docker else ""}
{"    - main" if config.build_docker else ""}
{"    - tags" if config.build_docker else ""}

{"deploy:" if config.deploy_enabled else "# Deployment disabled"}
{"  stage: deploy" if config.deploy_enabled else ""}
{"  script:" if config.deploy_enabled else ""}
{"    - echo 'Deploying to {config.deploy_target}...'" if config.deploy_enabled else ""}
{"  only:" if config.deploy_enabled else ""}
{"    - tags" if config.deploy_enabled else ""}
"""

        return files

    def _generate_jenkins(self, config: CICDConfig) -> Dict[str, str]:
        """Generate Jenkinsfile"""
        files = {}

        files[
            "Jenkinsfile"
        ] = f"""
pipeline {{
    agent any

    environment {{
        PYTHON_VERSION = '{config.python_version}'
    }}

    stages {{
        stage('Setup') {{
            steps {{
                sh 'python -m venv venv'
                sh '. venv/bin/activate && pip install -r requirements.txt'
            }}
        }}

        {"stage('Lint') {" if config.run_linting else "// Linting disabled"}
        {"    steps {" if config.run_linting else ""}
        {"        sh '. venv/bin/activate && pip install black flake8 mypy'" if config.run_linting else ""}
        {"        sh '. venv/bin/activate && black --check .'" if config.run_linting else ""}
        {"        sh '. venv/bin/activate && flake8 .'" if config.run_linting else ""}
        {"        sh '. venv/bin/activate && mypy src/'" if config.run_linting else ""}
        {"    }" if config.run_linting else ""}
        {"}" if config.run_linting else ""}

        {"stage('Test') {" if config.run_tests else "// Tests disabled"}
        {"    steps {" if config.run_tests else ""}
        {"        sh '. venv/bin/activate && pytest tests/ --cov=src --cov-report=xml'" if config.run_tests else ""}
        {"    }" if config.run_tests else ""}
        {"    post {" if config.run_tests else ""}
        {"        always {" if config.run_tests else ""}
        {"            junit 'test-results.xml'" if config.run_tests else ""}
        {"            cobertura 'coverage.xml'" if config.run_tests else ""}
        {"        }" if config.run_tests else ""}
        {"    }" if config.run_tests else ""}
        {"}" if config.run_tests else ""}

        {"stage('Build Docker') {" if config.build_docker else "// Docker build disabled"}
        {"    steps {" if config.build_docker else ""}
        {"        sh 'docker build -t my-app:latest .'" if config.build_docker else ""}
        {"    }" if config.build_docker else ""}
        {"}" if config.build_docker else ""}

        {"stage('Deploy') {" if config.deploy_enabled else "// Deployment disabled"}
        {"    when {" if config.deploy_enabled else ""}
        {"        branch 'main'" if config.deploy_enabled else ""}
        {"    }" if config.deploy_enabled else ""}
        {"    steps {" if config.deploy_enabled else ""}
        {"        echo 'Deploying to {config.deploy_target}...'" if config.deploy_enabled else ""}
        {"    }" if config.deploy_enabled else ""}
        {"}" if config.deploy_enabled else ""}
    }}

    post {{
        always {{
            cleanWs()
        }}
    }}
}}
"""

        return files
