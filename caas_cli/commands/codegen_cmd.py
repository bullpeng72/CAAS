"""
Codegen Command

Generate specific code components independently
"""


import click

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_progress,
    echo_success,
    handle_keyboard_interrupt,
    load_json,
    save_files,
)


@click.command()
@click.option(
    "--component",
    type=click.Choice(["tests", "deployment", "frontend", "docs", "cicd", "all"]),
    required=True,
    help="Component to generate",
)
@click.option(
    "--agents",
    type=click.Path(exists=True),
    required=True,
    help="Path to agents.json file",
)
@click.option(
    "--tasks",
    type=click.Path(exists=True),
    required=True,
    help="Path to tasks.json file",
)
@click.option(
    "--golden-data",
    type=click.Path(exists=True),
    help="Path to golden_data.json (recommended for better generation)",
)
@click.option(
    "--deployment-target",
    type=click.Choice(["docker", "kubernetes", "terraform"]),
    default="docker",
    help="Deployment target (for deployment component)",
)
@click.option(
    "--frontend-framework",
    type=click.Choice(["streamlit", "react"]),
    default="streamlit",
    help="Frontend framework (for frontend component)",
)
@click.option(
    "--cicd-platform",
    type=click.Choice(["github_actions", "gitlab_ci", "jenkins"]),
    default="github_actions",
    help="CI/CD platform (for cicd component)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="./codegen_output",
    help="Output directory (default: ./codegen_output)",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed generation output")
@handle_keyboard_interrupt
async def codegen(
    component,
    agents,
    tasks,
    golden_data,
    deployment_target,
    frontend_framework,
    cicd_platform,
    output,
    verbose,
):
    """
    Generate specific code components independently

    \b
    AVAILABLE COMPONENTS:
    ═══════════════════════════════════════════════════════════════════════════
    • tests         - Generate unit & integration tests
    • deployment    - Generate Docker/Kubernetes/Terraform configs
    • frontend      - Generate Streamlit or React UI
    • docs          - Generate API documentation
    • cicd          - Generate CI/CD pipelines (GitHub Actions/GitLab CI/Jenkins)
    • all           - Generate all components

    \b
    USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Generate tests only:
       $ caas codegen --component tests \\
           --agents agents.json --tasks tasks.json

    \b
    2️⃣  Generate Docker deployment configs:
       $ caas codegen --component deployment \\
           --agents agents.json --tasks tasks.json \\
           --deployment-target docker

    \b
    3️⃣  Generate Kubernetes configs:
       $ caas codegen --component deployment \\
           --agents agents.json --tasks tasks.json \\
           --deployment-target kubernetes

    \b
    4️⃣  Generate Streamlit frontend:
       $ caas codegen --component frontend \\
           --agents agents.json --tasks tasks.json \\
           --frontend-framework streamlit

    \b
    5️⃣  Generate CI/CD pipeline (GitHub Actions):
       $ caas codegen --component cicd \\
           --agents agents.json --tasks tasks.json \\
           --cicd-platform github_actions

    \b
    6️⃣  Generate CI/CD pipeline (GitLab CI):
       $ caas codegen --component cicd \\
           --agents agents.json --tasks tasks.json \\
           --cicd-platform gitlab_ci

    \b
    7️⃣  Generate all components:
       $ caas codegen --component all \\
           --agents agents.json --tasks tasks.json \\
           --golden-data golden_data.json \\
           --output ./my_output

    \b
    8️⃣  Generate with verbose output:
       $ caas codegen --component tests \\
           --agents agents.json --tasks tasks.json -v
    """
    try:
        echo_info(f"Generating {component} component...")
        click.echo()

        # Load agents and tasks
        echo_progress("Loading specifications...")
        agents_list = load_json(agents)
        tasks_list = load_json(tasks)

        # Load golden data if provided
        golden_data_dict = None
        if golden_data:
            golden_data_dict = load_json(golden_data)
            if verbose:
                echo_info(
                    f"Loaded Golden Data with {len(golden_data_dict.get('features', []))} features"
                )

        # Generate component
        files = {}

        if component == "tests":
            files = await _generate_tests(
                agents_list, tasks_list, golden_data_dict, verbose
            )
        elif component == "deployment":
            files = await _generate_deployment(
                agents_list, tasks_list, deployment_target, verbose
            )
        elif component == "frontend":
            files = await _generate_frontend(
                agents_list, tasks_list, frontend_framework, verbose
            )
        elif component == "docs":
            files = await _generate_docs(
                agents_list, tasks_list, golden_data_dict, verbose
            )
        elif component == "cicd":
            files = await _generate_cicd(cicd_platform, verbose)
        elif component == "all":
            files = await _generate_all(
                agents_list,
                tasks_list,
                golden_data_dict,
                deployment_target,
                frontend_framework,
                cicd_platform,
                verbose,
            )

        # Save generated files
        if files:
            click.echo()
            echo_progress(f"Saving generated files to {output}...")
            save_files(output, files)

            click.echo()
            echo_success("Code generation completed!")
            echo_info(f"Output directory: {output}")

            # Show next steps
            click.echo()
            click.echo(click.style("Next steps:", bold=True))
            click.echo(f"  1. cd {output}")
            click.echo("  2. Review generated files")
            if component in ["tests", "all"]:
                click.echo("  3. Run tests: pytest")
            if component in ["deployment", "all"]:
                click.echo(f"  3. Deploy with {deployment_target}")
        else:
            echo_error("No files generated")
            return 1

    except ImportError as e:
        echo_error(f"Failed to import codegen modules: {e}")
        echo_info("Make sure caas-framework is installed: pip install -e .")
        return 1
    except Exception as e:
        echo_error(f"Code generation error: {e}")
        import traceback

        if verbose:
            echo_error(traceback.format_exc())
        return 1


async def _generate_tests(agents_list, tasks_list, golden_data, verbose):
    """Generate tests"""
    from caas_framework.codegen.tdd_test_generator import TestGenerator

    echo_progress("Generating tests...")

    generator = TestGenerator()
    tests = generator.generate_all_tests(agents_list, tasks_list)

    if verbose:
        click.echo()
        echo_info(f"Generated {len(tests)} test files")
        for file_path in tests.keys():
            click.echo(f"  • {file_path}")

    return tests


async def _generate_deployment(agents_list, tasks_list, deployment_target, verbose):
    """Generate deployment configs"""
    from caas_framework.codegen.deployment_generator import (
        DeploymentConfig,
        DeploymentGenerator,
    )

    echo_progress(f"Generating {deployment_target} deployment configs...")

    generator = DeploymentGenerator()
    config = DeploymentConfig(
        target=deployment_target,
        project_name="crewai_project",
        agents=agents_list,
        tasks=tasks_list,
    )

    files = generator.generate_all(config)

    if verbose:
        click.echo()
        echo_info(f"Generated {len(files)} deployment files")
        for file_path in files.keys():
            click.echo(f"  • {file_path}")

    return files


async def _generate_frontend(agents_list, tasks_list, frontend_framework, verbose):
    """Generate frontend"""
    from caas_framework.codegen.frontend_generator import FrontendGenerator

    echo_progress(f"Generating {frontend_framework} frontend...")

    generator = FrontendGenerator()
    files = generator.generate(
        agents=agents_list, tasks=tasks_list, framework=frontend_framework
    )

    if verbose:
        click.echo()
        echo_info(f"Generated {len(files)} frontend files")
        for file_path in files.keys():
            click.echo(f"  • {file_path}")

    return files


async def _generate_docs(agents_list, tasks_list, golden_data, verbose):
    """Generate documentation"""
    from caas_framework.codegen.doc_generator import DocsGenerator

    echo_progress("Generating documentation...")

    generator = DocsGenerator()
    docs = generator.generate_all_docs(
        agents=agents_list, tasks=tasks_list, golden_data=golden_data
    )

    if verbose:
        click.echo()
        echo_info(f"Generated {len(docs)} documentation files")
        for file_path in docs.keys():
            click.echo(f"  • {file_path}")

    return docs


async def _generate_cicd(cicd_platform, verbose):
    """Generate CI/CD pipeline"""
    from caas_framework.codegen.cicd_generator import CICDConfig, CICDGenerator

    echo_progress(f"Generating {cicd_platform} CI/CD pipeline...")

    config = CICDConfig(platform=cicd_platform)
    generator = CICDGenerator()
    files = generator.generate_all(config)

    if verbose:
        click.echo()
        echo_info(f"Generated {len(files)} CI/CD files")
        for file_path in files.keys():
            click.echo(f"  • {file_path}")

    return files


async def _generate_all(
    agents_list,
    tasks_list,
    golden_data,
    deployment_target,
    frontend_framework,
    cicd_platform,
    verbose,
):
    """Generate all components"""
    echo_progress("Generating all components...")

    all_files = {}

    # Tests
    echo_info("1/5 Generating tests...")
    tests = await _generate_tests(agents_list, tasks_list, golden_data, verbose)
    all_files.update(tests)

    # Deployment
    echo_info("2/5 Generating deployment configs...")
    deployment = await _generate_deployment(
        agents_list, tasks_list, deployment_target, verbose
    )
    all_files.update(deployment)

    # Frontend
    echo_info("3/5 Generating frontend...")
    frontend = await _generate_frontend(
        agents_list, tasks_list, frontend_framework, verbose
    )
    all_files.update(frontend)

    # CI/CD
    echo_info("4/5 Generating CI/CD pipeline...")
    cicd = await _generate_cicd(cicd_platform, verbose)
    all_files.update(cicd)

    # Docs
    echo_info("5/5 Generating documentation...")
    docs = await _generate_docs(agents_list, tasks_list, golden_data, verbose)
    all_files.update(docs)

    if verbose:
        click.echo()
        echo_info(f"Total files generated: {len(all_files)}")

    return all_files
