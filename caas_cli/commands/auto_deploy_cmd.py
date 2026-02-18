"""
Auto Deploy Command

Full automation workflow: requirement → production in one command.
"""

import subprocess
from pathlib import Path

import click

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_success,
    handle_keyboard_interrupt,
)


@click.command(name="auto-deploy")
@click.argument("requirement", type=str)
@click.option(
    "--target",
    type=click.Choice(["docker", "kubernetes", "k8s", "local"]),
    default="docker",
    help="Deployment target (default: docker)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="./generated",
    help="Output directory (default: ./generated)",
)
@click.option(
    "--skip-tests", is_flag=True, help="Skip test execution and code quality checks"
)
@click.option("--skip-docker", is_flag=True, help="Skip Docker build step")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without executing"
)
@handle_keyboard_interrupt
def auto_deploy(requirement, target, output, skip_tests, skip_docker, verbose, dry_run):
    """
    Full automation workflow: requirement to production

    \b
    PURPOSE:
    ═══════════════════════════════════════════════════════════════════════════
    One-command deployment from natural language requirement to production.

    Executes the complete CAAS workflow:
    1. Environment validation
    2. Code generation
    3. Dependency installation
    4. Test execution
    5. Code quality checks
    6. Docker build
    7. Deployment

    \b
    DEPLOYMENT TARGETS:
    ═══════════════════════════════════════════════════════════════════════════
    • docker       - Deploy with Docker Compose (default)
    • kubernetes   - Deploy to Kubernetes cluster
    • local        - Run locally (development mode)

    \b
    WORKFLOW STEPS:
    ═══════════════════════════════════════════════════════════════════════════
    1. 📋 Validate Environment
       - Python version (3.11+)
       - Required packages
       - API keys (OPENAI_API_KEY)
       - Docker/K8s installation
       - Disk space (5+ GB)

    2. 🔧 Generate Code
       - Full CAAS 6-Phase workflow
       - All phases (0-5)
       - Production-ready code

    3. 📦 Install Dependencies
       - Create virtual environment
       - Install requirements.txt
       - Install test dependencies

    4. 🧪 Run Tests
       - Execute pytest
       - Generate coverage report (HTML)
       - Verify 80%+ coverage

    5. ✅ Code Quality Checks
       - black (code formatter)
       - pylint (linter, 7.0+ score)
       - mypy (type checker)

    6. 🐳 Docker Build
       - Build Docker image
       - Start containers
       - Run health checks
       - Run integration tests

    7. 🚢 Deploy
       - Deploy to target environment
       - Verify deployment
       - Show access URLs

    \b
    USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Basic deployment to Docker:
       $ caas auto-deploy "Build a blog system"

    \b
    2️⃣  Deploy to Kubernetes:
       $ caas auto-deploy "E-commerce platform" --target kubernetes

    \b
    3️⃣  Local development mode:
       $ caas auto-deploy "Task manager" --target local

    \b
    4️⃣  Skip tests for faster iteration:
       $ caas auto-deploy "API server" --skip-tests

    \b
    5️⃣  Custom output directory:
       $ caas auto-deploy "Chat bot" -o ./my-project

    \b
    6️⃣  Dry run (show what would happen):
       $ caas auto-deploy "Blog system" --dry-run

    \b
    7️⃣  Verbose mode:
       $ caas auto-deploy "Trading system" --verbose

    \b
    ENVIRONMENT VARIABLES:
    ═══════════════════════════════════════════════════════════════════════════
    OPENAI_API_KEY        - OpenAI API key (required)
    DEPLOY_TARGET         - Override deployment target
    OUTPUT_DIR            - Override output directory
    SKIP_TESTS            - Skip tests (true/false)
    VERBOSE               - Verbose output (true/false)

    \b
    ERROR HANDLING:
    ═══════════════════════════════════════════════════════════════════════════
    • Automatic rollback on failure
    • Cleanup of partially created resources
    • Detailed error messages
    • Exit codes: 0=success, 1=failure

    \b
    REQUIREMENTS:
    ═══════════════════════════════════════════════════════════════════════════
    • Python 3.11+
    • OPENAI_API_KEY set
    • 5+ GB disk space
    • (Optional) Docker for containerization
    • (Optional) kubectl for K8s deployment

    \b
    TYPICAL OUTPUT:
    ═══════════════════════════════════════════════════════════════════════════
    🚀 CAAS Full Automation Workflow
    ────────────────────────────────────────
    📋 Step 1/7: Validating Environment... ✅
    🔧 Step 2/7: Generating Code...        ✅
    📦 Step 3/7: Installing Dependencies...✅
    🧪 Step 4/7: Running Tests...          ✅
    ✅ Step 5/7: Code Quality Checks...    ✅
    🐳 Step 6/7: Building Docker...        ✅
    🚢 Step 7/7: Deploying...              ✅

    🎉 Deployment successful!

    \b
    TROUBLESHOOTING:
    ═══════════════════════════════════════════════════════════════════════════
    • Environment validation fails:
      → Run: python scripts/validate_env.py
      → Fix issues listed in output

    • Tests fail:
      → Check: {output}/htmlcov/index.html
      → Fix failing tests and retry

    • Docker build fails:
      → Check: docker logs
      → Review Dockerfile

    • Deployment fails:
      → Check logs: docker-compose logs
      → Verify API keys in .env

    \b
    SEE ALSO:
    ═══════════════════════════════════════════════════════════════════════════
    caas generate        - Generate code only
    caas validate        - Validate design
    caas test            - Run tests only
    """
    try:
        echo_info("Starting full automation workflow...")
        echo_info(f"Requirement: {requirement}")
        echo_info(f"Target: {target}")
        echo_info(f"Output: {output}")
        click.echo()

        # Find the auto_deploy.sh script
        # Try relative to the CLI module first
        script_paths = [
            Path(__file__).parent.parent.parent / "scripts" / "auto_deploy.sh",
            Path.cwd() / "scripts" / "auto_deploy.sh",
            Path("/home/fomalhaut/Projects/caas/scripts/auto_deploy.sh"),
        ]

        script_path = None
        for path in script_paths:
            if path.exists():
                script_path = path
                break

        if not script_path:
            echo_error("auto_deploy.sh script not found!")
            echo_info("Expected locations:")
            for path in script_paths:
                echo_info(f"  - {path}")
            return 1

        # Build command
        cmd = [str(script_path), requirement, "--target", target, "--output", output]

        if skip_tests:
            cmd.append("--skip-tests")
        if skip_docker:
            cmd.append("--skip-docker")
        if verbose:
            cmd.append("--verbose")
        if dry_run:
            cmd.append("--dry-run")

        # Execute automation script
        if verbose:
            echo_info(f"Executing: {' '.join(cmd)}")
            click.echo()

        result = subprocess.run(cmd, env={**subprocess.os.environ}, cwd=str(Path.cwd()))

        # Check result
        if result.returncode == 0:
            click.echo()
            echo_success("Full automation workflow completed successfully!")
            return 0
        else:
            click.echo()
            echo_error(f"Automation workflow failed with exit code {result.returncode}")
            return 1

    except FileNotFoundError as e:
        echo_error(f"Script execution failed: {e}")
        echo_info("Make sure auto_deploy.sh is in the scripts/ directory")
        return 1
    except KeyboardInterrupt:
        echo_error("Automation workflow interrupted by user")
        return 1
    except Exception as e:
        echo_error(f"Unexpected error: {e}")
        import traceback

        if verbose:
            echo_error(traceback.format_exc())
        return 1
