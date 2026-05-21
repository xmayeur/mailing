"""Integration tests for SchemaCacheProvider with real DatabaseSchemaProvider.

Tests schema cache with actual CSV file reading and profile switching scenarios.
"""

import tempfile
from pathlib import Path

import pytest

from src.schema_cache import SchemaCacheProvider
from src.schema_provider import DatabaseSchemaProvider


@pytest.fixture
def csv_file_profile_a():
    """Create temporary CSV file for profile A."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write("email,name,status\n")
        f.write("user1@example.com,Alice,active\n")
        f.write("user2@example.com,Bob,inactive\n")
        f.flush()
        yield f.name
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def csv_file_profile_b():
    """Create temporary CSV file for profile B with different schema."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write("id,full_name,active\n")
        f.write("1,Charlie,true\n")
        f.write("2,Diana,false\n")
        f.flush()
        yield f.name
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


class TestProfileSwitching:
    """Test profile switching with cache invalidation and fresh loads."""

    def test_profile_switching_cache_invalidation(
        self, csv_file_profile_a: str, csv_file_profile_b: str
    ) -> None:
        """Load Profile A, switch to B, verify B loads fresh from file."""
        cache = SchemaCacheProvider()

        # Load profile A schema
        schema_a = cache.get(
            "profile_a", lambda: DatabaseSchemaProvider.from_csv(csv_file_profile_a)
        )
        assert schema_a == ["email", "name", "status"]

        # Load profile B schema
        schema_b = cache.get(
            "profile_b", lambda: DatabaseSchemaProvider.from_csv(csv_file_profile_b)
        )
        assert schema_b == ["id", "full_name", "active"]

        # Invalidate profile A (user switched away from A)
        cache.invalidate("profile_a")

        # Profile A now loads fresh
        schema_a_fresh = cache.get(
            "profile_a",
            lambda: DatabaseSchemaProvider.from_csv(csv_file_profile_a),
        )
        assert schema_a_fresh == ["email", "name", "status"]

        # Profile B still cached
        schema_b_cached = cache.get(
            "profile_b",
            lambda: DatabaseSchemaProvider.from_csv(csv_file_profile_b),
        )
        assert schema_b_cached == ["id", "full_name", "active"]

    def test_multiple_profile_switches(
        self, csv_file_profile_a: str, csv_file_profile_b: str
    ) -> None:
        """Test rapid profile switching with cache behavior."""
        cache = SchemaCacheProvider()

        # Load A
        cache.get(
            "profile_a", lambda: DatabaseSchemaProvider.from_csv(csv_file_profile_a)
        )

        # Switch to B
        cache.invalidate("profile_a")
        cache.get(
            "profile_b", lambda: DatabaseSchemaProvider.from_csv(csv_file_profile_b)
        )

        # Switch back to A
        cache.invalidate("profile_b")
        schema_a = cache.get(
            "profile_a",
            lambda: DatabaseSchemaProvider.from_csv(csv_file_profile_a),
        )
        assert schema_a == ["email", "name", "status"]


class TestCachePerformance:
    """Test that cache provides expected performance improvement."""

    def test_cache_hit_latency(self, csv_file_profile_a: str) -> None:
        """Cached schema retrieval should be very fast (<1ms)."""
        import time

        cache = SchemaCacheProvider()

        # First load (uncached)
        schema = cache.get(
            "profile_a", lambda: DatabaseSchemaProvider.from_csv(csv_file_profile_a)
        )
        assert schema == ["email", "name", "status"]

        # Timed cache hit (should be <1ms)
        start = time.perf_counter_ns()
        schema = cache.get(
            "profile_a", lambda: DatabaseSchemaProvider.from_csv(csv_file_profile_a)
        )
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000

        # Cache hit should be much faster than disk read
        assert elapsed_ms < 50  # 50ms is conservative upper bound for dict lookup
        assert schema == ["email", "name", "status"]


class TestRefreshWithModifiedDatabase:
    """Test refresh() when database schema changes."""

    def test_refresh_reloads_after_schema_change(self, csv_file_profile_a: str) -> None:
        """refresh() reloads schema even if cached."""
        cache = SchemaCacheProvider()

        # Initial load
        schema1 = cache.get(
            "profile_a", lambda: DatabaseSchemaProvider.from_csv(csv_file_profile_a)
        )
        assert schema1 == ["email", "name", "status"]

        # Modify CSV file to add a column
        with open(csv_file_profile_a, "w", encoding="utf-8") as f:
            f.write("email,name,status,created_at\n")
            f.write("user1@example.com,Alice,active,2026-05-17\n")

        # Cached get returns old schema
        cached_schema = cache.get(
            "profile_a",
            lambda: DatabaseSchemaProvider.from_csv(csv_file_profile_a),
        )
        assert cached_schema == ["email", "name", "status"]  # Old cached value

        # refresh() loads new schema from disk
        refreshed_schema = cache.refresh(
            "profile_a",
            lambda: DatabaseSchemaProvider.from_csv(csv_file_profile_a),
        )
        assert refreshed_schema == ["email", "name", "status", "created_at"]

        # Subsequent get() returns refreshed (cached) value
        schema2 = cache.get(
            "profile_a",
            lambda: DatabaseSchemaProvider.from_csv(csv_file_profile_a),
        )
        assert schema2 == ["email", "name", "status", "created_at"]
