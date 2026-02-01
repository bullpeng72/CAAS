"""
Deployment Generator

Generates deployment configurations (Docker, Kubernetes, docker-compose, etc.)
"""

from typing import Dict
from pydantic import BaseModel


class DeploymentConfig(BaseModel):
    """Deployment configuration"""
    target: str  # "docker", "kubernetes", "terraform"
    project_name: str
    has_database: bool = False
    has_api: bool = False
    has_ui: bool = False
    ui_port: int = 8600  # Configurable UI port (default: 8600)
    python_version: str = "3.11"


class DeploymentGenerator:
    """
    Deployment Generator

    Generates deployment files for various platforms.
    """

    def generate_dockerfile(self, config: DeploymentConfig) -> str:
        """
        Generate Dockerfile.

        Args:
            config: Deployment configuration

        Returns:
            str: Dockerfile content
        """
        dockerfile = f'''# Dockerfile for {config.project_name}

FROM python:{config.python_version}-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY main.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose port (if API exists)
'''
        if config.has_api:
            dockerfile += 'EXPOSE 8000\n\n'
            dockerfile += '# Run FastAPI application\nCMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]\n'
        else:
            dockerfile += '\n# Run CrewAI application\nCMD ["python", "main.py"]\n'

        return dockerfile

    def generate_docker_compose(self, config: DeploymentConfig) -> str:
        """
        Generate docker-compose.yml.

        Args:
            config: Deployment configuration

        Returns:
            str: docker-compose.yml content
        """
        compose = f'''version: '3.8'

services:
  app:
    build: .
    container_name: {config.project_name}
    restart: unless-stopped
'''

        if config.has_api:
            compose += '''    ports:
      - "8000:8000"
'''

        compose += '''    environment:
      - PYTHONUNBUFFERED=1
'''

        if config.has_database:
            compose += '''      - DATABASE_URL=${DATABASE_URL:-postgresql://user:password@db:5432/dbname}
    depends_on:
      - db
'''

        if config.has_ui:
            compose += '''    volumes:
      - ./src:/app/src
'''

        if config.has_database:
            compose += '''
  db:
    image: postgres:15-alpine
    container_name: {config.project_name}_db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-user}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-password}
      - POSTGRES_DB=${POSTGRES_DB:-dbname}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
'''

        return compose

    def generate_kubernetes_deployment(self, config: DeploymentConfig) -> str:
        """
        Generate Kubernetes deployment.yaml.

        Args:
            config: Deployment configuration

        Returns:
            str: deployment.yaml content
        """
        deployment = f'''apiVersion: apps/v1
kind: Deployment
metadata:
  name: {config.project_name}
  labels:
    app: {config.project_name}
spec:
  replicas: 3
  selector:
    matchLabels:
      app: {config.project_name}
  template:
    metadata:
      labels:
        app: {config.project_name}
    spec:
      containers:
      - name: {config.project_name}
        image: {config.project_name}:latest
        ports:
        - containerPort: 8000
        env:
        - name: PYTHONUNBUFFERED
          value: "1"
'''

        if config.has_database:
            deployment += '''        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: database-url
'''

        deployment += '''        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
'''

        return deployment

    def generate_kubernetes_service(self, config: DeploymentConfig) -> str:
        """
        Generate Kubernetes service.yaml.

        Args:
            config: Deployment configuration

        Returns:
            str: service.yaml content
        """
        service = f'''apiVersion: v1
kind: Service
metadata:
  name: {config.project_name}
spec:
  type: LoadBalancer
  selector:
    app: {config.project_name}
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
'''

        return service

    def generate_github_actions(self, config: DeploymentConfig) -> str:
        """
        Generate GitHub Actions CI/CD workflow.

        Args:
            config: Deployment configuration

        Returns:
            str: GitHub Actions workflow content
        """
        workflow = f'''name: CI/CD Pipeline

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

    - name: Set up Python {config.python_version}
      uses: actions/setup-python@v4
      with:
        python-version: {config.python_version}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r tests/requirements-test.txt

    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3

    - name: Build Docker image
      run: |
        docker build -t {config.project_name}:${{{{ github.sha }}}} .
        docker tag {config.project_name}:${{{{ github.sha }}}} {config.project_name}:latest

    - name: Push to registry
      run: |
        echo "Push to Docker registry here"

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - name: Deploy to production
      run: |
        echo "Deploy to production here"
'''

        return workflow

    def generate_makefile(self, config: DeploymentConfig) -> str:
        """
        Generate Makefile for common tasks.

        Args:
            config: Deployment configuration

        Returns:
            str: Makefile content
        """
        makefile = f'''# Makefile for {config.project_name}

.PHONY: install test run docker-build docker-run clean

install:
\tpip install -r requirements.txt

test:
\tpytest tests/ -v --cov=src

run:
\tpython main.py

docker-build:
\tdocker build -t {config.project_name}:latest .

docker-run:
\tdocker-compose up -d

docker-stop:
\tdocker-compose down

clean:
\tfind . -type d -name __pycache__ -exec rm -rf {{}} +
\tfind . -type f -name "*.pyc" -delete
\trm -rf .pytest_cache .coverage htmlcov

format:
\tblack src/ tests/
\tisort src/ tests/

lint:
\tflake8 src/ tests/
\tmypy src/

help:
\t@echo "Available commands:"
\t@echo "  install      - Install dependencies"
\t@echo "  test         - Run tests"
\t@echo "  run          - Run application"
\t@echo "  docker-build - Build Docker image"
\t@echo "  docker-run   - Run with docker-compose"
\t@echo "  docker-stop  - Stop docker-compose"
\t@echo "  clean        - Clean cache files"
\t@echo "  format       - Format code"
\t@echo "  lint         - Lint code"
'''

        return makefile

    def generate_all(
        self,
        config: DeploymentConfig
    ) -> Dict[str, str]:
        """
        Generate all deployment files.

        Args:
            config: Deployment configuration

        Returns:
            Dict[str, str]: Deployment file mapping (filename -> content)
        """
        files = {}

        # Docker
        files["Dockerfile"] = self.generate_dockerfile(config)
        files["docker-compose.yml"] = self.generate_docker_compose(config)
        files[".dockerignore"] = '''
__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.so
.env
.venv
env/
venv/
.git
.gitignore
.pytest_cache
.coverage
htmlcov/
*.log
'''

        # Kubernetes (if target is kubernetes)
        if config.target == "kubernetes":
            files["k8s/deployment.yaml"] = self.generate_kubernetes_deployment(config)
            files["k8s/service.yaml"] = self.generate_kubernetes_service(config)

        # CI/CD
        files[".github/workflows/ci-cd.yml"] = self.generate_github_actions(config)

        # Makefile
        files["Makefile"] = self.generate_makefile(config)

        # .env.example
        files[".env.example"] = '''
# Environment variables
# Copy this file to .env and fill in your actual values

# LLM Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Database (if applicable)
# Format: postgresql://username:password@host:port/database
DATABASE_URL=postgresql://your_db_user:your_db_password@localhost:5432/your_database
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_DB=your_database

# Application
DEBUG=false
LOG_LEVEL=INFO
'''

        return files
