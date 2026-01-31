"""
Persistence Backends

Pluggable persistence backends for workflow state.
"""

import json
import sqlite3
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel


class PersistenceBackend(ABC):
    """
    Abstract persistence backend.

    Defines interface for storing and retrieving workflow state.
    """

    @abstractmethod
    def save(self, key: str, data: Dict[str, Any]) -> bool:
        """Save data"""
        pass

    @abstractmethod
    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Load data"""
        pass

    @abstractmethod
    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data"""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        pass


class FilePersistenceBackend(PersistenceBackend):
    """
    File-based persistence backend.

    Stores data as JSON files in a directory.
    """

    def __init__(self, storage_dir: str = ".caas/persistence"):
        """
        Initialize file backend.

        Args:
            storage_dir: Directory for storing files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, data: Dict[str, Any]) -> bool:
        """Save data to file"""
        try:
            file_path = self.storage_dir / f"{key}.json"
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=str)

            return True
        except Exception:
            return False

    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Load data from file"""
        try:
            file_path = self.storage_dir / f"{key}.json"

            if not file_path.exists():
                return None

            with open(file_path, "r") as f:
                return json.load(f)
        except Exception:
            return None

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys"""
        pattern = f"{prefix}*.json" if prefix else "*.json"
        files = self.storage_dir.glob(pattern)

        return [f.stem for f in files]

    def delete(self, key: str) -> bool:
        """Delete file"""
        try:
            file_path = self.storage_dir / f"{key}.json"

            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False

    def exists(self, key: str) -> bool:
        """Check if file exists"""
        file_path = self.storage_dir / f"{key}.json"
        return file_path.exists()


class DatabasePersistenceBackend(PersistenceBackend):
    """
    SQLite database persistence backend.

    Stores data in a SQLite database.
    """

    def __init__(self, db_path: str = ".caas/persistence.db"):
        """
        Initialize database backend.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path

        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS persistence (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_key_prefix
            ON persistence (key)
        ''')

        conn.commit()
        conn.close()

    def save(self, key: str, data: Dict[str, Any]) -> bool:
        """Save data to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            data_json = json.dumps(data, default=str)
            now = datetime.utcnow().isoformat()

            cursor.execute('''
                INSERT OR REPLACE INTO persistence (key, data, updated_at)
                VALUES (?, ?, ?)
            ''', (key, data_json, now))

            conn.commit()
            conn.close()

            return True
        except Exception:
            return False

    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Load data from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT data FROM persistence WHERE key = ?
            ''', (key,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return json.loads(row[0])
            return None
        except Exception:
            return None

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if prefix:
                cursor.execute('''
                    SELECT key FROM persistence WHERE key LIKE ?
                ''', (f"{prefix}%",))
            else:
                cursor.execute('''
                    SELECT key FROM persistence
                ''')

            keys = [row[0] for row in cursor.fetchall()]
            conn.close()

            return keys
        except Exception:
            return []

    def delete(self, key: str) -> bool:
        """Delete from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                DELETE FROM persistence WHERE key = ?
            ''', (key,))

            deleted = cursor.rowcount > 0

            conn.commit()
            conn.close()

            return deleted
        except Exception:
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT 1 FROM persistence WHERE key = ? LIMIT 1
            ''', (key,))

            exists = cursor.fetchone() is not None
            conn.close()

            return exists
        except Exception:
            return False

    def cleanup_old(self, days: int = 30) -> int:
        """
        Delete old entries.

        Args:
            days: Delete entries older than this

        Returns:
            int: Number of entries deleted
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff = datetime.utcnow().timestamp() - (days * 24 * 3600)
            cutoff_str = datetime.fromtimestamp(cutoff).isoformat()

            cursor.execute('''
                DELETE FROM persistence WHERE updated_at < ?
            ''', (cutoff_str,))

            deleted = cursor.rowcount

            conn.commit()
            conn.close()

            return deleted
        except Exception:
            return 0


class MemoryPersistenceBackend(PersistenceBackend):
    """
    In-memory persistence backend.

    Stores data in memory (not persistent across restarts).
    """

    def __init__(self):
        """Initialize memory backend"""
        self.storage: Dict[str, Dict[str, Any]] = {}

    def save(self, key: str, data: Dict[str, Any]) -> bool:
        """Save to memory"""
        self.storage[key] = data.copy()
        return True

    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Load from memory"""
        return self.storage.get(key)

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys"""
        if prefix:
            return [k for k in self.storage.keys() if k.startswith(prefix)]
        return list(self.storage.keys())

    def delete(self, key: str) -> bool:
        """Delete from memory"""
        if key in self.storage:
            del self.storage[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return key in self.storage

    def clear(self):
        """Clear all data"""
        self.storage.clear()
