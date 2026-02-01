"""
Environment Variable Manager

Utility functions for managing .env files and environment variables.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv, set_key, unset_key


class EnvManager:
    """Manager for .env file operations"""

    def __init__(self, env_file: Optional[Path] = None):
        """
        Initialize EnvManager

        Args:
            env_file: Path to .env file (defaults to project root/.env)
        """
        if env_file is None:
            # Find project root .env file
            current = Path(__file__).resolve()
            project_root = current.parent.parent.parent  # app/utils -> app -> project
            env_file = project_root / ".env"

        self.env_file = env_file
        self.env_example_file = env_file.parent / ".env.example"

        # Load existing .env
        if self.env_file.exists():
            load_dotenv(self.env_file)

    def get_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable value

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Value or default
        """
        return os.getenv(key, default)

    def set_value(self, key: str, value: str) -> bool:
        """
        Set environment variable in .env file

        Args:
            key: Environment variable name
            value: Value to set

        Returns:
            bool: True if successful
        """
        try:
            # Create .env file if it doesn't exist
            if not self.env_file.exists():
                self.env_file.touch()

            # Set the key-value pair
            set_key(str(self.env_file), key, value)

            # Also set in current process
            os.environ[key] = value

            return True
        except Exception as e:
            print(f"Error setting {key}: {e}")
            return False

    def unset_value(self, key: str) -> bool:
        """
        Remove environment variable from .env file

        Args:
            key: Environment variable name

        Returns:
            bool: True if successful
        """
        try:
            if not self.env_file.exists():
                return True

            unset_key(str(self.env_file), key)

            # Also remove from current process
            os.environ.pop(key, None)

            return True
        except Exception as e:
            print(f"Error unsetting {key}: {e}")
            return False

    def get_all_values(self) -> Dict[str, str]:
        """
        Get all environment variables from .env file

        Returns:
            Dictionary of env var name to value
        """
        env_vars = {}

        if not self.env_file.exists():
            return env_vars

        with open(self.env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Parse key=value
                match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$', line)
                if match:
                    key, value = match.groups()
                    # Remove quotes if present
                    value = value.strip('\'"')
                    env_vars[key] = value

        return env_vars

    def is_key_set(self, key: str) -> bool:
        """
        Check if an environment variable is set and non-empty

        Args:
            key: Environment variable name

        Returns:
            bool: True if set and non-empty
        """
        value = self.get_value(key)
        return value is not None and value.strip() != ""

    def validate_keys(self, required_keys: List[str]) -> Tuple[List[str], List[str]]:
        """
        Validate that required keys are set

        Args:
            required_keys: List of required environment variable names

        Returns:
            Tuple of (missing_keys, empty_keys)
        """
        missing_keys = []
        empty_keys = []

        for key in required_keys:
            value = self.get_value(key)

            if value is None:
                missing_keys.append(key)
            elif value.strip() == "":
                empty_keys.append(key)

        return missing_keys, empty_keys

    def bulk_set(self, key_values: Dict[str, str]) -> Tuple[int, List[str]]:
        """
        Set multiple environment variables at once

        Args:
            key_values: Dictionary of key-value pairs

        Returns:
            Tuple of (success_count, failed_keys)
        """
        success_count = 0
        failed_keys = []

        for key, value in key_values.items():
            if self.set_value(key, value):
                success_count += 1
            else:
                failed_keys.append(key)

        return success_count, failed_keys

    def get_example_values(self) -> Dict[str, str]:
        """
        Get example values from .env.example file

        Returns:
            Dictionary of env var name to example value
        """
        example_vars = {}

        if not self.env_example_file.exists():
            return example_vars

        with open(self.env_example_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Parse key=value
                match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$', line)
                if match:
                    key, value = match.groups()
                    # Keep example values as-is (don't strip quotes)
                    example_vars[key] = value

        return example_vars

    def get_missing_from_example(self) -> List[str]:
        """
        Get environment variables that are in .env.example but not in .env

        Returns:
            List of missing environment variable names
        """
        example_vars = self.get_example_values()
        current_vars = self.get_all_values()

        missing = []
        for key in example_vars.keys():
            if key not in current_vars:
                missing.append(key)

        return missing

    def copy_from_example(self, keys: Optional[List[str]] = None) -> int:
        """
        Copy environment variables from .env.example to .env

        Args:
            keys: Specific keys to copy (if None, copies all missing keys)

        Returns:
            Number of keys copied
        """
        example_vars = self.get_example_values()
        current_vars = self.get_all_values()

        if keys is None:
            keys = self.get_missing_from_example()

        copied = 0
        for key in keys:
            if key in example_vars and key not in current_vars:
                if self.set_value(key, example_vars[key]):
                    copied += 1

        return copied

    def backup(self, backup_path: Optional[Path] = None) -> Path:
        """
        Create a backup of the .env file

        Args:
            backup_path: Path for backup file (defaults to .env.backup)

        Returns:
            Path to backup file
        """
        if backup_path is None:
            backup_path = self.env_file.parent / ".env.backup"

        if self.env_file.exists():
            import shutil
            shutil.copy2(self.env_file, backup_path)

        return backup_path

    def restore(self, backup_path: Optional[Path] = None) -> bool:
        """
        Restore .env file from backup

        Args:
            backup_path: Path to backup file (defaults to .env.backup)

        Returns:
            bool: True if successful
        """
        if backup_path is None:
            backup_path = self.env_file.parent / ".env.backup"

        if not backup_path.exists():
            return False

        try:
            import shutil
            shutil.copy2(backup_path, self.env_file)
            # Reload environment
            load_dotenv(self.env_file, override=True)
            return True
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False

    def export_to_dict(self) -> Dict[str, str]:
        """
        Export all environment variables as a dictionary

        Returns:
            Dictionary of all env vars
        """
        return self.get_all_values()

    def import_from_dict(self, env_dict: Dict[str, str], overwrite: bool = False) -> int:
        """
        Import environment variables from a dictionary

        Args:
            env_dict: Dictionary of key-value pairs
            overwrite: Whether to overwrite existing values

        Returns:
            Number of keys imported
        """
        imported = 0
        current_vars = self.get_all_values()

        for key, value in env_dict.items():
            # Skip if exists and not overwriting
            if key in current_vars and not overwrite:
                continue

            if self.set_value(key, value):
                imported += 1

        return imported

    def get_commented_keys(self) -> List[str]:
        """
        Get list of commented-out environment variable keys

        Returns:
            List of commented environment variable names
        """
        commented = []

        if not self.env_file.exists():
            return commented

        with open(self.env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # Check for commented key=value
                if line.startswith('#'):
                    # Remove comment marker and whitespace
                    uncommented = line.lstrip('#').strip()
                    match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*=', uncommented)
                    if match:
                        key = match.group(1)
                        commented.append(key)

        return commented


# Global instance
_default_env_manager: Optional[EnvManager] = None


def get_env_manager() -> EnvManager:
    """Get or create the default EnvManager instance"""
    global _default_env_manager
    if _default_env_manager is None:
        _default_env_manager = EnvManager()
    return _default_env_manager
