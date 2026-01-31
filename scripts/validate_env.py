#!/usr/bin/env python3
"""
Environment Validation Tool

Pre-flight checks before running CAAS automation workflow.
Validates Python version, packages, API keys, Docker, and Kubernetes.
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class ValidationStatus(Enum):
    """Validation result status"""
    PASSED = "✅"
    FAILED = "❌"
    WARNING = "⚠️"
    SKIPPED = "⏭️"


@dataclass
class ValidationResult:
    """Single validation check result"""
    name: str
    status: ValidationStatus
    message: str
    details: Optional[str] = None
    required: bool = True


class EnvironmentValidator:
    """
    Environment validator for CAAS automation workflow

    Validates:
    - Python version (3.11+)
    - Required packages
    - API keys (OPENAI_API_KEY, etc.)
    - Docker installation
    - Kubernetes installation (optional)
    """

    def __init__(self, skip_optional: bool = False):
        """
        Initialize validator.

        Args:
            skip_optional: Skip optional checks (Docker, K8s)
        """
        self.skip_optional = skip_optional
        self.results: List[ValidationResult] = []

    def validate_all(self) -> bool:
        """
        Run all validation checks.

        Returns:
            bool: True if all required checks passed
        """
        print("🔍 CAAS Environment Validation")
        print("=" * 60)
        print()

        # Run all checks
        self.check_python_version()
        self.check_required_packages()
        self.check_api_keys()

        if not self.skip_optional:
            self.check_docker()
            self.check_kubernetes()

        self.check_disk_space()
        self.check_network_connectivity()

        # Print results
        print()
        print("=" * 60)
        print("📊 Validation Results")
        print("=" * 60)
        print()

        passed_count = 0
        failed_count = 0
        warning_count = 0

        for result in self.results:
            status_icon = result.status.value
            required_text = "[REQUIRED]" if result.required else "[OPTIONAL]"

            print(f"{status_icon} {result.name} {required_text}")
            print(f"   {result.message}")

            if result.details:
                print(f"   Details: {result.details}")

            print()

            if result.status == ValidationStatus.PASSED:
                passed_count += 1
            elif result.status == ValidationStatus.FAILED:
                if result.required:
                    failed_count += 1
            elif result.status == ValidationStatus.WARNING:
                warning_count += 1

        # Summary
        print("=" * 60)
        print("📈 Summary")
        print("=" * 60)
        print(f"✅ Passed:   {passed_count}")
        print(f"❌ Failed:   {failed_count}")
        print(f"⚠️  Warnings: {warning_count}")
        print()

        # Determine overall result
        required_failures = [r for r in self.results
                           if r.status == ValidationStatus.FAILED and r.required]

        if required_failures:
            print("❌ Environment validation FAILED")
            print()
            print("Required fixes:")
            for result in required_failures:
                print(f"  - {result.name}: {result.message}")
            print()
            return False
        else:
            print("✅ Environment validation PASSED")
            if warning_count > 0:
                print(f"⚠️  {warning_count} warnings - review recommended")
            print()
            return True

    def check_python_version(self) -> None:
        """Check Python version (3.11+)"""
        try:
            version = sys.version_info
            version_str = f"{version.major}.{version.minor}.{version.micro}"

            if version.major == 3 and version.minor >= 11:
                self.results.append(ValidationResult(
                    name="Python Version",
                    status=ValidationStatus.PASSED,
                    message=f"Python {version_str} installed",
                    required=True
                ))
            elif version.major == 3 and version.minor >= 9:
                self.results.append(ValidationResult(
                    name="Python Version",
                    status=ValidationStatus.WARNING,
                    message=f"Python {version_str} - recommended 3.11+",
                    details="CAAS works best with Python 3.11+",
                    required=False
                ))
            else:
                self.results.append(ValidationResult(
                    name="Python Version",
                    status=ValidationStatus.FAILED,
                    message=f"Python {version_str} - requires 3.11+",
                    details="Upgrade: pyenv install 3.11 && pyenv global 3.11",
                    required=True
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                name="Python Version",
                status=ValidationStatus.FAILED,
                message=f"Error checking Python version: {e}",
                required=True
            ))

    def check_required_packages(self) -> None:
        """Check required Python packages"""
        required_packages = [
            ("click", "CLI framework"),
            ("pydantic", "Data validation"),
            ("crewai", "CrewAI framework"),
            ("openai", "OpenAI API"),
            ("python-dotenv", "Environment variables"),
            ("pytest", "Testing framework"),
            ("rich", "Terminal formatting")
        ]

        missing_packages = []
        installed_packages = []

        for package, description in required_packages:
            try:
                __import__(package.replace("-", "_"))
                installed_packages.append(package)
            except ImportError:
                missing_packages.append((package, description))

        if not missing_packages:
            self.results.append(ValidationResult(
                name="Required Packages",
                status=ValidationStatus.PASSED,
                message=f"All {len(required_packages)} packages installed",
                details=", ".join(installed_packages),
                required=True
            ))
        else:
            missing_list = ", ".join([p[0] for p in missing_packages])
            self.results.append(ValidationResult(
                name="Required Packages",
                status=ValidationStatus.FAILED,
                message=f"{len(missing_packages)} packages missing",
                details=f"Install: pip install {missing_list}",
                required=True
            ))

    def check_api_keys(self) -> None:
        """Check for required API keys"""
        api_keys = [
            ("OPENAI_API_KEY", True, "OpenAI API"),
            ("ANTHROPIC_API_KEY", False, "Anthropic API"),
            ("GOOGLE_API_KEY", False, "Google API")
        ]

        missing_required = []
        missing_optional = []

        for key_name, required, description in api_keys:
            key_value = os.environ.get(key_name)

            if key_value:
                # Mask the key for security
                masked_value = key_value[:8] + "..." + key_value[-4:] if len(key_value) > 12 else "***"
                self.results.append(ValidationResult(
                    name=f"API Key: {key_name}",
                    status=ValidationStatus.PASSED,
                    message=f"{description} key found",
                    details=f"Value: {masked_value}",
                    required=required
                ))
            else:
                if required:
                    missing_required.append(key_name)
                    self.results.append(ValidationResult(
                        name=f"API Key: {key_name}",
                        status=ValidationStatus.FAILED,
                        message=f"{description} key missing",
                        details=f"Set: export {key_name}=your_key_here",
                        required=True
                    ))
                else:
                    missing_optional.append(key_name)
                    self.results.append(ValidationResult(
                        name=f"API Key: {key_name}",
                        status=ValidationStatus.SKIPPED,
                        message=f"{description} key not set (optional)",
                        required=False
                    ))

    def check_docker(self) -> None:
        """Check Docker installation"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                self.results.append(ValidationResult(
                    name="Docker",
                    status=ValidationStatus.PASSED,
                    message="Docker installed",
                    details=version,
                    required=False
                ))

                # Check if Docker daemon is running
                daemon_check = subprocess.run(
                    ["docker", "ps"],
                    capture_output=True,
                    timeout=5
                )

                if daemon_check.returncode != 0:
                    self.results.append(ValidationResult(
                        name="Docker Daemon",
                        status=ValidationStatus.WARNING,
                        message="Docker installed but daemon not running",
                        details="Start: sudo systemctl start docker",
                        required=False
                    ))
            else:
                self.results.append(ValidationResult(
                    name="Docker",
                    status=ValidationStatus.WARNING,
                    message="Docker not found",
                    details="Install: https://docs.docker.com/get-docker/",
                    required=False
                ))
        except FileNotFoundError:
            self.results.append(ValidationResult(
                name="Docker",
                status=ValidationStatus.WARNING,
                message="Docker not installed",
                details="Install: https://docs.docker.com/get-docker/",
                required=False
            ))
        except subprocess.TimeoutExpired:
            self.results.append(ValidationResult(
                name="Docker",
                status=ValidationStatus.WARNING,
                message="Docker check timeout",
                required=False
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                name="Docker",
                status=ValidationStatus.WARNING,
                message=f"Docker check error: {e}",
                required=False
            ))

    def check_kubernetes(self) -> None:
        """Check Kubernetes (kubectl) installation"""
        try:
            result = subprocess.run(
                ["kubectl", "version", "--client"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                self.results.append(ValidationResult(
                    name="Kubernetes",
                    status=ValidationStatus.PASSED,
                    message="kubectl installed",
                    details="Kubernetes CLI available",
                    required=False
                ))
            else:
                self.results.append(ValidationResult(
                    name="Kubernetes",
                    status=ValidationStatus.SKIPPED,
                    message="kubectl not found (optional)",
                    required=False
                ))
        except FileNotFoundError:
            self.results.append(ValidationResult(
                name="Kubernetes",
                status=ValidationStatus.SKIPPED,
                message="kubectl not installed (optional)",
                required=False
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                name="Kubernetes",
                status=ValidationStatus.SKIPPED,
                message=f"kubectl check skipped: {e}",
                required=False
            ))

    def check_disk_space(self) -> None:
        """Check available disk space"""
        try:
            import shutil

            total, used, free = shutil.disk_usage("/")

            free_gb = free // (2**30)  # Convert to GB

            if free_gb >= 10:
                self.results.append(ValidationResult(
                    name="Disk Space",
                    status=ValidationStatus.PASSED,
                    message=f"{free_gb} GB available",
                    required=True
                ))
            elif free_gb >= 5:
                self.results.append(ValidationResult(
                    name="Disk Space",
                    status=ValidationStatus.WARNING,
                    message=f"{free_gb} GB available - recommended 10+ GB",
                    required=False
                ))
            else:
                self.results.append(ValidationResult(
                    name="Disk Space",
                    status=ValidationStatus.FAILED,
                    message=f"{free_gb} GB available - requires 5+ GB",
                    details="Free up disk space before continuing",
                    required=True
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                name="Disk Space",
                status=ValidationStatus.WARNING,
                message=f"Could not check disk space: {e}",
                required=False
            ))

    def check_network_connectivity(self) -> None:
        """Check network connectivity to OpenAI API"""
        try:
            import socket

            # Try to connect to OpenAI API
            socket.create_connection(("api.openai.com", 443), timeout=5)

            self.results.append(ValidationResult(
                name="Network Connectivity",
                status=ValidationStatus.PASSED,
                message="Can reach api.openai.com",
                required=True
            ))
        except socket.timeout:
            self.results.append(ValidationResult(
                name="Network Connectivity",
                status=ValidationStatus.FAILED,
                message="Connection timeout to api.openai.com",
                details="Check firewall/proxy settings",
                required=True
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                name="Network Connectivity",
                status=ValidationStatus.WARNING,
                message=f"Network check failed: {e}",
                required=False
            ))

    def export_results_json(self, output_file: str = "validation_results.json") -> None:
        """Export validation results to JSON"""
        results_dict = {
            "results": [
                {
                    "name": r.name,
                    "status": r.status.name,
                    "message": r.message,
                    "details": r.details,
                    "required": r.required
                }
                for r in self.results
            ],
            "summary": {
                "total": len(self.results),
                "passed": len([r for r in self.results if r.status == ValidationStatus.PASSED]),
                "failed": len([r for r in self.results if r.status == ValidationStatus.FAILED and r.required]),
                "warnings": len([r for r in self.results if r.status == ValidationStatus.WARNING])
            }
        }

        with open(output_file, "w") as f:
            json.dump(results_dict, f, indent=2)

        print(f"📄 Results exported to: {output_file}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="CAAS Environment Validation Tool"
    )
    parser.add_argument(
        "--skip-optional",
        action="store_true",
        help="Skip optional checks (Docker, K8s)"
    )
    parser.add_argument(
        "--export-json",
        type=str,
        help="Export results to JSON file"
    )

    args = parser.parse_args()

    # Run validation
    validator = EnvironmentValidator(skip_optional=args.skip_optional)
    success = validator.validate_all()

    # Export if requested
    if args.export_json:
        validator.export_results_json(args.export_json)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
