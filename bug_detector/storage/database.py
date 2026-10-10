"""SQLite database initialization and connection management."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Union
from bug_detector.exceptions import StorageError

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    source_code TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    is_syntax_valid INTEGER NOT NULL,
    syntax_error_json TEXT,
    findings_json TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    ai_review_json TEXT,
    duration_ms REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_code_hash ON reviews(code_hash);
"""


def ensure_db_directory(db_path: Union[str, Path]) -> Path:
    """Ensure parent directory for SQLite database exists.
    
    Args:
        db_path: Path to SQLite database file.
        
    Returns:
        Resolved Path object.
    """
    try:
        path = Path(db_path).resolve()
        if path.name != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        return path
    except OSError as err:
        raise StorageError(f"Failed to create directory for database at '{db_path}': {err}") from err


def init_db(db_path: Union[str, Path]) -> None:
    """Initialize database tables and indices if not already present.
    
    Args:
        db_path: Path to SQLite database file.
        
    Raises:
        StorageError: If database initialization fails.
    """
    try:
        path = ensure_db_directory(db_path)
        with sqlite3.connect(str(path)) as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
    except (sqlite3.Error, OSError) as err:
        raise StorageError(f"Failed to initialize SQLite database at {db_path}: {err}") from err


@contextmanager
def get_connection(db_path: Union[str, Path]) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections with foreign keys and dict-like row access.
    
    Args:
        db_path: Path to SQLite database file.
        
    Yields:
        sqlite3.Connection configured with sqlite3.Row factory.
        
    Raises:
        StorageError: On connection failure or unhandled SQL errors.
    """
    path = ensure_db_directory(db_path)
    conn = None
    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except (sqlite3.Error, OSError) as err:
        if conn:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
        raise StorageError(f"Database operation failed: {err}") from err
    finally:
        if conn:
            conn.close()
