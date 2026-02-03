"""
Tests for ProjectBootstrapper

Tests automated project setup and initialization functionality.
"""

import subprocess
from pathlib import Path

import pytest

from caas_framework.automation import BootstrapResult, ProjectBootstrapper, TestResult


@pytest.fixture
def temp_base_dir(tmp_path):
    """Temporary base directory for testing"""
    return tmp_path


@pytest.fixture
def sample_generated_files():
    """Sample generated files for testing"""
    return {
        "main.py": """from crewai import Crew, Process
from agents import create_agents
from tasks import create_tasks

def main():
    agents = create_agents()
    tasks = create_tasks(agents)
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential
    )
    result = crew.kickoff()
    return result

if __name__ == "__main__":
    main()
""",
        "agents.py": """from crewai import Agent

def create_agents():
    agents = {}
    agents["researcher"] = Agent(
        role="Research Specialist",
        goal="Gather information",
        backstory="Expert researcher"
    )
    return agents
""",
        "tasks.py": """from crewai import Task

def create_tasks(agents):
    tasks = []
    tasks.append(Task(
        description="Research the topic",
        expected_output="Research report",
        agent=agents["researcher"]
    ))
    return tasks
""",
        "requirements.txt": """crewai>=0.28.0
python-dotenv>=1.0.0
""",
        ".env.example": """OPENAI_API_KEY=your_api_key_here
""",
        "_description": "A research automation system",
    }


class TestBootstrapResult:
    """Test BootstrapResult dataclass"""

    def test_bootstrap_result_creation(self):
        """Test creating BootstrapResult"""
        result = BootstrapResult(
            project_dir=Path("/test/project"),
            files_created=5,
            git_initialized=True,
            dependencies_installed=True,
            tests_passed=None,
        )

        assert result.project_dir == Path("/test/project")
        assert result.files_created == 5
        assert result.git_initialized is True
        assert result.dependencies_installed is True
        assert result.tests_passed is None


class TestTestResult:
    """Test TestResult dataclass"""

    def test_test_result_creation(self):
        """Test creating TestResult"""
        result = TestResult(passed=True, output="All tests passed")

        assert result.passed is True
        assert result.output == "All tests passed"


class TestProjectBootstrapper:
    """Test ProjectBootstrapper class"""

    def test_bootstrapper_creation(self):
        """Test creating ProjectBootstrapper"""
        bootstrapper = ProjectBootstrapper()
        assert bootstrapper is not None

    def test_bootstrap_basic(self, temp_base_dir, sample_generated_files):
        """Test basic project bootstrap without extras"""
        bootstrapper = ProjectBootstrapper()

        result = bootstrapper.bootstrap(
            generated_files=sample_generated_files,
            project_name="test_project",
            base_dir=temp_base_dir,
            auto_git=False,
            auto_venv=False,
            auto_install=False,
            auto_test=False,
            verbose=False,
        )

        # Check result
        assert isinstance(result, BootstrapResult)
        assert result.project_dir == temp_base_dir / "test_project"
        assert result.files_created == 5  # Excludes _description
        assert result.git_initialized is False
        assert result.dependencies_installed is False
        assert result.tests_passed is None

        # Check directory created
        assert result.project_dir.exists()
        assert result.project_dir.is_dir()

    def test_bootstrap_creates_files(self, temp_base_dir, sample_generated_files):
        """Test that bootstrap creates all files"""
        bootstrapper = ProjectBootstrapper()

        result = bootstrapper.bootstrap(
            generated_files=sample_generated_files,
            project_name="test_project",
            base_dir=temp_base_dir,
            auto_git=False,
            auto_venv=False,
            auto_install=False,
            verbose=False,
        )

        project_dir = result.project_dir

        # Check files exist
        assert (project_dir / "main.py").exists()
        assert (project_dir / "agents.py").exists()
        assert (project_dir / "tasks.py").exists()
        assert (project_dir / "requirements.txt").exists()
        assert (project_dir / ".env.example").exists()

        # Check file contents
        main_content = (project_dir / "main.py").read_text()
        assert "from crewai import Crew" in main_content
        assert "def main():" in main_content

    def test_bootstrap_skips_metadata(self, temp_base_dir, sample_generated_files):
        """Test that bootstrap skips metadata fields"""
        bootstrapper = ProjectBootstrapper()

        result = bootstrapper.bootstrap(
            generated_files=sample_generated_files,
            project_name="test_project",
            base_dir=temp_base_dir,
            auto_git=False,
            auto_venv=False,
            verbose=False,
        )

        project_dir = result.project_dir

        # _description should not be created as a file
        assert not (project_dir / "_description").exists()

    def test_bootstrap_with_git(self, temp_base_dir, sample_generated_files):
        """Test bootstrap with git initialization"""
        # Skip if git is not available
        try:
            subprocess.run(["git", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("git not available")

        bootstrapper = ProjectBootstrapper()

        result = bootstrapper.bootstrap(
            generated_files=sample_generated_files,
            project_name="test_project",
            base_dir=temp_base_dir,
            auto_git=True,
            auto_venv=False,
            auto_install=False,
            verbose=False,
        )

        project_dir = result.project_dir

        # Check git initialized
        assert result.git_initialized is True
        assert (project_dir / ".git").exists()
        assert (project_dir / ".gitignore").exists()

        # Check .gitignore content
        gitignore_content = (project_dir / ".gitignore").read_text()
        assert "__pycache__/" in gitignore_content
        assert "venv/" in gitignore_content
        assert ".env" in gitignore_content

    def test_bootstrap_with_venv(self, temp_base_dir, sample_generated_files):
        """Test bootstrap with virtual environment creation"""
        bootstrapper = ProjectBootstrapper()

        result = bootstrapper.bootstrap(
            generated_files=sample_generated_files,
            project_name="test_project",
            base_dir=temp_base_dir,
            auto_git=False,
            auto_venv=True,
            auto_install=False,
            verbose=False,
        )

        project_dir = result.project_dir

        # Check venv created
        assert (project_dir / "venv").exists()
        assert (project_dir / "venv").is_dir()

    def test_bootstrap_generates_readme(self, temp_base_dir, sample_generated_files):
        """Test that bootstrap generates README.md"""
        bootstrapper = ProjectBootstrapper()

        result = bootstrapper.bootstrap(
            generated_files=sample_generated_files,
            project_name="test_project",
            base_dir=temp_base_dir,
            auto_git=False,
            auto_venv=False,
            verbose=False,
        )

        project_dir = result.project_dir
        readme_path = project_dir / "README.md"

        # Check README exists
        assert readme_path.exists()

        # Check README content
        readme_content = readme_path.read_text()
        assert "test_project" in readme_content
        assert "CAAS" in readme_content
        assert "Installation" in readme_content
        assert "Usage" in readme_content
        assert "python main.py" in readme_content
        assert "A research automation system" in readme_content  # From _description

    def test_write_files_method(self, temp_base_dir):
        """Test _write_files method directly"""
        bootstrapper = ProjectBootstrapper()
        project_dir = temp_base_dir / "test_project"
        project_dir.mkdir()

        files = {
            "test.py": "print('hello')",
            "subdir/test2.py": "print('world')",
            "_metadata": "should be skipped",
        }

        files_written = bootstrapper._write_files(project_dir, files, verbose=False)

        # Should write 2 files (skip _metadata)
        assert files_written == 2
        assert (project_dir / "test.py").exists()
        assert (project_dir / "subdir" / "test2.py").exists()
        assert not (project_dir / "_metadata").exists()

    def test_generate_readme_method(self, temp_base_dir):
        """Test _generate_readme method directly"""
        bootstrapper = ProjectBootstrapper()
        project_dir = temp_base_dir / "test_project"
        project_dir.mkdir()

        files = {
            "main.py": "code",
            "agents.py": "code",
            "_description": "Test project description",
        }

        bootstrapper._generate_readme(project_dir, files, verbose=False)

        readme_path = project_dir / "README.md"
        assert readme_path.exists()

        content = readme_path.read_text()
        assert "test_project" in content
        assert "main.py" in content
        assert "agents.py" in content
        assert "_description" not in content  # Metadata not listed as file
        assert "Test project description" in content  # But used in description

    def test_bootstrap_existing_directory(self, temp_base_dir, sample_generated_files):
        """Test bootstrap into existing directory"""
        project_dir = temp_base_dir / "test_project"
        project_dir.mkdir()

        # Create a file that shouldn't be overwritten
        existing_file = project_dir / "existing.txt"
        existing_file.write_text("existing content")

        bootstrapper = ProjectBootstrapper()

        result = bootstrapper.bootstrap(
            generated_files=sample_generated_files,
            project_name="test_project",
            base_dir=temp_base_dir,
            auto_git=False,
            auto_venv=False,
            verbose=False,
        )

        # Should succeed and create new files
        assert result.files_created == 5
        assert (project_dir / "main.py").exists()

        # Existing file should still exist
        assert existing_file.exists()
        assert existing_file.read_text() == "existing content"

    def test_bootstrap_nested_directories(self, temp_base_dir):
        """Test bootstrap with nested directory structure"""
        files = {
            "main.py": "code",
            "src/agents.py": "code",
            "src/tasks.py": "code",
            "tests/test_main.py": "code",
            "_description": "Test",
        }

        bootstrapper = ProjectBootstrapper()

        result = bootstrapper.bootstrap(
            generated_files=files,
            project_name="test_project",
            base_dir=temp_base_dir,
            auto_git=False,
            auto_venv=False,
            verbose=False,
        )

        project_dir = result.project_dir

        # Check nested files created
        assert (project_dir / "main.py").exists()
        assert (project_dir / "src" / "agents.py").exists()
        assert (project_dir / "src" / "tasks.py").exists()
        assert (project_dir / "tests" / "test_main.py").exists()

    def test_bootstrap_verbose_output(
        self, temp_base_dir, sample_generated_files, capsys
    ):
        """Test that verbose mode produces output"""
        bootstrapper = ProjectBootstrapper()

        result = bootstrapper.bootstrap(
            generated_files=sample_generated_files,
            project_name="test_project",
            base_dir=temp_base_dir,
            auto_git=False,
            auto_venv=False,
            verbose=True,
        )

        captured = capsys.readouterr()

        # Check for expected output
        assert "Bootstrapping Project" in captured.out
        assert "test_project" in captured.out
        assert "PROJECT READY" in captured.out

    def test_bootstrap_default_base_dir(
        self, sample_generated_files, tmp_path, monkeypatch
    ):
        """Test bootstrap with default base directory (cwd)"""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        bootstrapper = ProjectBootstrapper()

        result = bootstrapper.bootstrap(
            generated_files=sample_generated_files,
            project_name="test_project",
            auto_git=False,
            auto_venv=False,
            verbose=False,
        )

        # Should use current directory
        assert result.project_dir == tmp_path / "test_project"
        assert result.project_dir.exists()

    def test_bootstrap_with_cicd(self, tmp_path, sample_generated_files):
        """Test bootstrap with CI/CD generation"""
        bootstrapper = ProjectBootstrapper()

        result = bootstrapper.bootstrap(
            generated_files=sample_generated_files,
            project_name="test_project",
            base_dir=tmp_path,
            auto_git=False,
            auto_venv=False,
            auto_cicd=True,
            include_docker=False,
            verbose=False,
        )

        project_dir = result.project_dir

        # Should have GitHub Actions workflow
        assert (project_dir / ".github" / "workflows" / "ci.yml").exists()

    def test_bootstrap_with_cicd_and_docker(self, tmp_path, sample_generated_files):
        """Test bootstrap with CI/CD and Docker"""
        bootstrapper = ProjectBootstrapper()

        result = bootstrapper.bootstrap(
            generated_files=sample_generated_files,
            project_name="test_project",
            base_dir=tmp_path,
            auto_git=False,
            auto_venv=False,
            auto_cicd=True,
            include_docker=True,
            verbose=False,
        )

        project_dir = result.project_dir

        # Should have CI/CD files
        assert (project_dir / ".github" / "workflows" / "ci.yml").exists()
        assert (project_dir / "Dockerfile").exists()
        assert (project_dir / "docker-compose.yml").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
