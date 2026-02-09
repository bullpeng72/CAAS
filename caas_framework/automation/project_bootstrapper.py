"""
Project Bootstrapper - Automates project setup and initialization

Provides automated project directory creation, file writing, git initialization,
virtual environment setup, dependency installation, and README generation.
"""

import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from caas_framework.automation.cicd_generator import CICDGenerator

from caas_framework.utils.logger import get_logger

logger = get_logger(__name__)



@dataclass
class TestResult:
    """Result of running tests"""

    passed: bool
    output: str


@dataclass
class BootstrapResult:
    """Result of project bootstrap operation"""

    project_dir: Path
    files_created: int
    git_initialized: bool
    dependencies_installed: bool
    tests_passed: Optional[bool] = None


class ProjectBootstrapper:
    """Automated project setup and initialization"""

    def bootstrap(
        self,
        generated_files: Dict[str, str],
        project_name: str,
        base_dir: Optional[Path] = None,
        auto_git: bool = True,
        auto_venv: bool = True,
        auto_install: bool = True,
        auto_test: bool = False,
        auto_cicd: bool = False,
        include_docker: bool = False,
        verbose: bool = True,
    ) -> BootstrapResult:
        """
        Bootstrap a complete project from generated code files

        Args:
            generated_files: Dictionary of {filename: content} for all files
            project_name: Name of the project directory to create
            base_dir: Base directory to create project in (default: current directory)
            auto_git: Whether to initialize git repository
            auto_venv: Whether to create virtual environment
            auto_install: Whether to install dependencies
            auto_test: Whether to run tests after setup
            auto_cicd: Whether to generate CI/CD configuration (GitHub Actions)
            include_docker: Whether to include Docker configuration (requires auto_cicd=True)
            verbose: Whether to print progress messages

        Returns:
            BootstrapResult with operation details
        """
        base_dir = base_dir or Path.cwd()
        project_dir = base_dir / project_name

        if verbose:
            logger.info(f"\n{'=' * 70}")
            logger.info(f"🚀 Bootstrapping Project: {project_name}")
            logger.info(f"{'=' * 70}\n")
        # 1. Create project directory
        project_dir.mkdir(exist_ok=True)
        if verbose:
            logger.info(f"📁 Created project directory: {project_dir}")
        # 2. Write all generated files
        files_written = self._write_files(project_dir, generated_files, verbose)

        # 3. Initialize git repository
        git_initialized = False
        if auto_git:
            git_initialized = self._init_git(project_dir, verbose)

        # 4. Create virtual environment
        if auto_venv:
            self._create_venv(project_dir, verbose)

        # 5. Install dependencies
        dependencies_installed = False
        if auto_install and auto_venv:
            dependencies_installed = self._install_dependencies(project_dir, verbose)

        # 6. Run tests
        test_result = None
        if auto_test and auto_venv:
            test_result = self._run_tests(project_dir, verbose)

        # 7. Generate README
        self._generate_readme(project_dir, generated_files, verbose)

        # 8. Generate CI/CD configuration
        if auto_cicd:
            self._generate_cicd(project_dir, include_docker, verbose)

        # 9. Print completion message
        if verbose:
            self._print_completion(project_dir, project_name)

        return BootstrapResult(
            project_dir=project_dir,
            files_created=files_written,
            git_initialized=git_initialized,
            dependencies_installed=dependencies_installed,
            tests_passed=test_result.passed if test_result else None,
        )

    def _write_files(
        self, project_dir: Path, files: Dict[str, str], verbose: bool
    ) -> int:
        """Write all generated files to project directory"""
        files_written = 0

        for filename, content in files.items():
            # Skip metadata fields (those starting with _)
            if filename.startswith("_"):
                continue

            file_path = project_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            files_written += 1

            if verbose:
                logger.info(f"  ✅ {filename}")
        if verbose:
            logger.info(f"\n📝 Saved {files_written} files")
        return files_written

    def _init_git(self, project_dir: Path, verbose: bool) -> bool:
        """Initialize git repository with .gitignore and initial commit"""
        try:
            # Initialize git
            subprocess.run(
                ["git", "init"], cwd=project_dir, check=True, capture_output=True
            )

            # Create .gitignore
            gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment
.env
.env.local
.env.*.local

# Testing
.pytest_cache/
.coverage
htmlcov/

# OS
.DS_Store
Thumbs.db
"""
            gitignore_path = project_dir / ".gitignore"
            gitignore_path.write_text(gitignore_content)

            # Add all files
            subprocess.run(
                ["git", "add", "."], cwd=project_dir, check=True, capture_output=True
            )

            # Initial commit
            subprocess.run(
                ["git", "commit", "-m", "Initial commit from CAAS"],
                cwd=project_dir,
                check=True,
                capture_output=True,
            )

            if verbose:
                logger.info("✅ Git initialized with first commit")
            return True

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            if verbose:
                logger.error(f"⚠️  Git initialization failed: {e}")
            return False

    def _create_venv(self, project_dir: Path, verbose: bool):
        """Create Python virtual environment"""
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", "venv"],
                cwd=project_dir,
                check=True,
                capture_output=True,
            )

            if verbose:
                logger.info("✅ Virtual environment created")
        except subprocess.CalledProcessError as e:
            if verbose:
                logger.error(f"⚠️  Virtual environment creation failed: {e}")
    def _install_dependencies(self, project_dir: Path, verbose: bool) -> bool:
        """Install dependencies from requirements.txt"""
        requirements_path = project_dir / "requirements.txt"

        if not requirements_path.exists():
            if verbose:
                logger.warning("⚠️  No requirements.txt found, skipping dependency installation")
            return False

        try:
            # Determine venv python path based on OS
            if sys.platform == "win32":
                venv_python = project_dir / "venv" / "Scripts" / "python.exe"
            else:
                venv_python = project_dir / "venv" / "bin" / "python"

            if not venv_python.exists():
                if verbose:
                    logger.warning("⚠️  Virtual environment python not found")
                return False

            # Upgrade pip
            subprocess.run(
                [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
                cwd=project_dir,
                check=True,
                capture_output=True,
            )

            # Install requirements
            subprocess.run(
                [str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"],
                cwd=project_dir,
                check=True,
                capture_output=True,
            )

            if verbose:
                logger.info("✅ Dependencies installed from requirements.txt")
            return True

        except subprocess.CalledProcessError as e:
            if verbose:
                logger.error(f"⚠️  Dependency installation failed: {e}")
            return False

    def _run_tests(self, project_dir: Path, verbose: bool) -> Optional[TestResult]:
        """Run pytest if available"""
        try:
            # Determine venv python path
            if sys.platform == "win32":
                venv_python = project_dir / "venv" / "Scripts" / "python.exe"
            else:
                venv_python = project_dir / "venv" / "bin" / "python"

            # Run pytest
            result = subprocess.run(
                [str(venv_python), "-m", "pytest", "-v"],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )

            test_result = TestResult(
                passed=result.returncode == 0, output=result.stdout + result.stderr
            )

            if verbose:
                if test_result.passed:
                    logger.info("✅ All tests passed")
                else:
                    logger.error("⚠️  Some tests failed")
            return test_result

        except (subprocess.CalledProcessError, FileNotFoundError):
            if verbose:
                logger.warning("⚠️  pytest not found, skipping tests")
            return None

    def _generate_readme(self, project_dir: Path, files: Dict[str, str], verbose: bool):
        """Generate README.md with project information"""

        # Get description from metadata if available
        description = files.get("_description", "CrewAI-based automation system")

        # Build file list (exclude metadata fields)
        file_list = []
        for filename in sorted(files.keys()):
            if not filename.startswith("_"):
                file_list.append(f"- `{filename}`")

        readme_content = f"""# {project_dir.name}

Generated by CAAS (CrewAI Automatic Coder System)

## Overview

{description}

## Installation

1. Create and activate virtual environment:

```bash
python -m venv venv

# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\\Scripts\\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Project Structure

```
{project_dir.name}/
├── main.py          # Entry point
├── agents.py        # Agent definitions
├── tasks.py         # Task definitions
├── requirements.txt # Dependencies
└── README.md        # This file
```

## Generated Files

{chr(10).join(file_list)}

## Testing

If pytest is installed:

```bash
pytest
```

## Environment Variables

Create a `.env` file with required API keys:

```
OPENAI_API_KEY=your_api_key_here
```

---

*Generated by CAAS on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        readme_path = project_dir / "README.md"
        readme_path.write_text(readme_content)

        if verbose:
            logger.info("✅ README.md generated")
    def _print_completion(self, project_dir: Path, project_name: str):
        """Print completion message with next steps"""
        activate_cmd = (
            "venv\\Scripts\\activate"
            if sys.platform == "win32"
            else "source venv/bin/activate"
        )

        logger.info(f"\n{'=' * 70}")
        logger.info("✅ PROJECT READY!")
        logger.info(f"{'=' * 70}")
        logger.info(f"Location: {project_dir}")
        logger.info("\nTo start:")
        logger.info(f"  cd {project_name}")
        logger.info(f"  {activate_cmd}")
        logger.info("  python main.py")
        logger.info(f"{'=' * 70}\n")
    def _generate_cicd(self, project_dir: Path, include_docker: bool, verbose: bool):
        """Generate CI/CD configuration"""
        cicd_generator = CICDGenerator()

        cicd_generator.generate_all(
            project_dir=project_dir,
            include_docker=include_docker,
            include_coverage=True,
            verbose=verbose,
        )
