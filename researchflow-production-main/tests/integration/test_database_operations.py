"""
Integration tests for database CRUD operations.
Connects to Postgres (DATABASE_URL); uses a dedicated test table.
Skips when database is not reachable (e.g. in CI unit-only job).
Run from repo root with Postgres: PYTHONPATH=services/worker pytest tests/integration/test_database_operations.py -v
"""

import os
from contextlib import contextmanager

import pytest

# Prefer sqlalchemy if available (worker has it); else skip DB tests
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://ros:ros@localhost:5432/ros",
)
TEST_TABLE = "_test_crud_integration"


@pytest.fixture(scope="module")
def db_engine():
    """Create engine and skip if DB unreachable."""
    if not HAS_SQLALCHEMY:
        pytest.skip("sqlalchemy not installed")
    try:
        # postgresql:// needs psycopg2; if missing, engine creation may still succeed
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        pytest.skip(f"Database not reachable: {e}")


@contextmanager
def _test_table(engine: "Engine"):
    """Create test table, yield, then drop."""
    with engine.connect() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {TEST_TABLE} (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                value INTEGER DEFAULT 0
            )
        """))
        conn.commit()
    try:
        yield
    finally:
        with engine.connect() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {TEST_TABLE}"))
            conn.commit()


@pytest.mark.integration
class TestDatabaseOperations:
    """CRUD integration tests against Postgres."""

    def test_create_and_read(self, db_engine):
        """Insert a row and read it back."""
        with _test_table(db_engine):
            with db_engine.connect() as conn:
                conn.execute(
                    text(f"INSERT INTO {TEST_TABLE} (name, value) VALUES (:name, :value)"),
                    {"name": "test-row", "value": 42},
                )
                conn.commit()
                row = conn.execute(
                    text(f"SELECT id, name, value FROM {TEST_TABLE} WHERE name = :name"),
                    {"name": "test-row"},
                ).fetchone()
                assert row is not None
                assert row[1] == "test-row"
                assert row[2] == 42

    def test_update(self, db_engine):
        """Update a row and verify."""
        with _test_table(db_engine):
            with db_engine.connect() as conn:
                conn.execute(
                    text(f"INSERT INTO {TEST_TABLE} (name, value) VALUES (:name, :value)"),
                    {"name": "update-me", "value": 1},
                )
                conn.commit()
                conn.execute(
                    text(f"UPDATE {TEST_TABLE} SET value = :v WHERE name = :name"),
                    {"v": 99, "name": "update-me"},
                )
                conn.commit()
                row = conn.execute(
                    text(f"SELECT value FROM {TEST_TABLE} WHERE name = :name"),
                    {"name": "update-me"},
                ).fetchone()
                assert row is not None
                assert row[0] == 99

    def test_delete(self, db_engine):
        """Delete a row and verify it is gone."""
        with _test_table(db_engine):
            with db_engine.connect() as conn:
                conn.execute(
                    text(f"INSERT INTO {TEST_TABLE} (name, value) VALUES (:name, :value)"),
                    {"name": "delete-me", "value": 0},
                )
                conn.commit()
                conn.execute(
                    text(f"DELETE FROM {TEST_TABLE} WHERE name = :name"),
                    {"name": "delete-me"},
                )
                conn.commit()
                row = conn.execute(
                    text(f"SELECT id FROM {TEST_TABLE} WHERE name = :name"),
                    {"name": "delete-me"},
                ).fetchone()
                assert row is None
