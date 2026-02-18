"""
Fix Runtime Error Command

Automatically analyze and fix runtime errors in generated code.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import click

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_progress,
    echo_success,
    echo_warning,
    handle_keyboard_interrupt,
)


@click.command()
@click.option(
    "--project",
    "-p",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    help="Path to project directory",
)
@click.option(
    "--error-log",
    "-e",
    type=click.Path(exists=True),
    help="Path to error log file (if not provided, paste error in prompt)",
)
@click.option(
    "--apply",
    "-a",
    is_flag=True,
    help="Automatically apply the fix (without this flag, only shows the fix)",
)
@click.option(
    "--backup",
    "-b",
    is_flag=True,
    default=True,
    help="Create backup before applying fix (default: True)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Save fix report to JSON file",
)
@handle_keyboard_interrupt
def fix_runtime_error(project, error_log, apply, backup, output):
    """
    Automatically analyze and fix runtime errors

    Analyzes Python runtime errors (ImportError, NameError, AttributeError, etc.)
    and generates automatic fixes with explanations. Can optionally apply fixes
    directly to the code.

    \b
    SUPPORTED ERROR TYPES:
    ═══════════════════════════════════════════════════════════════════════════
    • ImportError / ModuleNotFoundError - Missing imports
    • NameError - Undefined variables
    • AttributeError - Missing attributes/methods
    • TypeError - Type mismatches
    • KeyError - Missing dictionary keys
    • IndexError - List index out of range
    • ValueError - Invalid values
    • SyntaxError - Python syntax errors

    \b
    FIX PROCESS:
    ═══════════════════════════════════════════════════════════════════════════
    1. Parse error log and extract error information
    2. Analyze root cause using LLM
    3. Generate code fix with explanation
    4. Optionally apply fix to affected file(s)
    5. Suggest verification steps

    \b
    USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Analyze error from log file (preview only):
       $ caas fix-runtime-error --project ./generated_project \\
           --error-log error.log

    \b
    2️⃣  Apply fix automatically with backup:
       $ caas fix-runtime-error -p ./project -e error.log --apply --backup

    \b
    3️⃣  Paste error interactively:
       $ caas fix-runtime-error -p ./project
       # Then paste the error traceback when prompted

    \b
    4️⃣  Fix and save report:
       $ caas fix-runtime-error -p ./project -e error.log --apply \\
           --output fix_report.json

    \b
    SAFETY FEATURES:
    ═══════════════════════════════════════════════════════════════════════════
    • Preview mode by default (--apply required to modify files)
    • Automatic backup creation before applying fixes
    • Confidence score for each fix
    • Manual review recommended for low-confidence fixes

    \b
    NEXT STEPS AFTER FIXING:
    ═══════════════════════════════════════════════════════════════════════════
    • Run tests: pytest tests/ -v
    • Verify functionality: python main.py
    • Check for similar errors in other files
    • Re-run 'caas validate' to ensure correctness
    """
    from caas_framework.agents.code_analysis_agent import CodeAnalysisAgent
    from caas_framework.config.loader import load_config
    from caas_framework.plugins.llm.factory import create_llm_plugin

    echo_progress("Initializing Code Analysis Agent...")

    try:
        # Load configuration
        config = load_config()

        # Get error log
        if error_log:
            echo_progress(f"Reading error log from {error_log}...")
            with open(error_log, "r") as f:
                error_text = f.read()
        else:
            echo_info("\n📋 Paste your error traceback below (Ctrl+D or Ctrl+Z when done):")
            echo_info("=" * 70)
            error_lines = []
            try:
                while True:
                    line = input()
                    error_lines.append(line)
            except EOFError:
                pass
            error_text = "\n".join(error_lines)
            echo_info("=" * 70 + "\n")

        if not error_text.strip():
            echo_error("No error log provided")
            raise click.Abort()

        # Create LLM plugin
        llm_plugin = create_llm_plugin(
            provider=config.llm.provider,
            model=config.llm.model,
            api_key=config.llm.api_key,
            api_base=config.llm.api_base,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )

        # Create Code Analysis Agent
        agent = CodeAnalysisAgent(llm_plugin=llm_plugin)

        # Analyze error
        echo_progress("Analyzing runtime error...")
        project_path = Path(project)

        fix_result = asyncio.run(
            agent.analyze_runtime_error(error_log=error_text, project_path=project_path)
        )

        # Display analysis
        echo_success(f"\n{'='*70}")
        echo_success("RUNTIME ERROR ANALYSIS")
        echo_success(f"{'='*70}\n")

        error_info = fix_result.error_info

        # Error details
        echo_error(f"🔴 Error Type: {error_info.error_type}")
        echo_error(f"📝 Message: {error_info.error_message}")
        echo_info(f"📁 File: {error_info.file_path}")
        if error_info.line_number:
            echo_info(f"📍 Line: {error_info.line_number}")
        echo_info(f"🏷️  Category: {error_info.category}")
        echo_info(f"⚠️  Severity: {error_info.severity}\n")

        # Root cause
        echo_success("🔍 ROOT CAUSE ANALYSIS:")
        echo_info(f"  {fix_result.root_cause}\n")

        # Fix strategy
        echo_success("🛠️  FIX STRATEGY:")
        echo_info(f"  {fix_result.fix_strategy}\n")

        # Code fixes
        if fix_result.fixes:
            echo_success(f"💡 PROPOSED FIX ({len(fix_result.fixes)} change(s)):\n")

            for i, fix in enumerate(fix_result.fixes, 1):
                echo_info(f"Fix #{i}:")
                echo_info(f"  File: {fix.file_path}")
                echo_info(f"  Confidence: {fix.confidence * 100:.0f}%")
                echo_info(f"  Explanation: {fix.explanation}\n")

                if fix.confidence < 0.6:
                    echo_warning("  ⚠️  Low confidence - manual review recommended\n")

                # Show code diff
                echo_info("  Original Code:")
                for line in fix.original_code.split("\n")[:10]:
                    echo_error(f"    - {line}")

                echo_info("\n  Fixed Code:")
                for line in fix.fixed_code.split("\n")[:10]:
                    echo_success(f"    + {line}")

                echo_info("")

            # Apply fixes
            if apply:
                echo_progress("\nApplying fixes...")

                for fix in fix_result.fixes:
                    file_path = project_path / fix.file_path

                    if not file_path.exists():
                        echo_error(f"  ❌ File not found: {fix.file_path}")
                        continue

                    # Create backup
                    if backup:
                        backup_path = file_path.with_suffix(file_path.suffix + ".backup")
                        backup_path.write_text(file_path.read_text())
                        echo_info(f"  💾 Backup created: {backup_path}")

                    # Apply fix
                    try:
                        content = file_path.read_text()
                        # Simple replacement (in production, use more sophisticated patching)
                        new_content = content.replace(fix.original_code, fix.fixed_code)
                        file_path.write_text(new_content)
                        echo_success(f"  ✅ Fixed: {fix.file_path}")
                    except Exception as e:
                        echo_error(f"  ❌ Failed to apply fix: {e}")

                echo_success("\n✨ Fixes applied successfully!")

            else:
                echo_warning("\n⚠️  Preview mode - use --apply to modify files")

        else:
            echo_error("❌ Could not generate fix automatically")
            echo_info("   Manual intervention required")

        # Test command
        if fix_result.test_command:
            echo_success("\n🧪 VERIFICATION:")
            echo_info(f"  Run: {fix_result.test_command}")

        # Additional notes
        if fix_result.additional_notes:
            echo_success("\n📌 NOTES:")
            for note in fix_result.additional_notes:
                echo_info(f"  • {note}")

        # Save report
        if output:
            report = {
                "analysis_type": "runtime_error",
                "project_path": str(project_path),
                "timestamp": datetime.now().isoformat(),
                "error_info": error_info.dict(),
                "root_cause": fix_result.root_cause,
                "fix_strategy": fix_result.fix_strategy,
                "fixes": [f.dict() for f in fix_result.fixes],
                "test_command": fix_result.test_command,
                "applied": apply,
            }

            with open(output, "w") as f:
                json.dump(report, f, indent=2)

            echo_success(f"\n📄 Report saved to: {output}")

        # Summary
        echo_success(f"\n{'='*70}")
        if apply:
            echo_success("✅ Fix applied - verify with tests")
        else:
            echo_info("ℹ️  Preview completed - use --apply to fix")
        echo_success(f"{'='*70}\n")

    except FileNotFoundError as e:
        echo_error(f"File not found: {e}")
        raise click.Abort()
    except Exception as e:
        echo_error(f"Error analysis failed: {e}")
        import traceback

        echo_error(traceback.format_exc())
        raise click.Abort()
