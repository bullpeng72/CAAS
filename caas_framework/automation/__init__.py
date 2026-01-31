"""
Automation module for CAAS

Provides automated project setup and bootstrapping functionality.
"""

from caas_framework.automation.project_bootstrapper import (
    ProjectBootstrapper,
    BootstrapResult,
    TestResult
)
from caas_framework.automation.cicd_generator import CICDGenerator

__all__ = [
    'ProjectBootstrapper',
    'BootstrapResult',
    'TestResult',
    'CICDGenerator'
]
