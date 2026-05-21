"""Unit tests for SchemaCacheProvider (schema caching).

Tests cover:
- Cache hit: cached schema returned on second call
- Cache miss: loader called on first call
- Invalidation: cache entry cleared on invalidate
- Refresh: loader called on refresh even if cached
"""

import pytest

from src.schema_cache import SchemaCacheProvider


@pytest.fixture
def cache():
    """Fresh SchemaCacheProvider instance for each test."""
    return SchemaCacheProvider()


@pytest.fixture
def mock_loader_profile_a():
    """Mock loader for profile 'a' returning sample schema."""

    def loader() -> list[str]:
        return ["email", "name", "status"]

    return loader


@pytest.fixture
def mock_loader_profile_b():
    """Mock loader for profile 'b' returning different schema."""

    def loader() -> list[str]:
        return ["id", "full_name", "active"]

    return loader


@pytest.fixture
def counting_loader():
    """Loader that tracks call count."""
    call_count = {"count": 0}

    def loader() -> list[str]:
        call_count["count"] += 1
        return ["email", "name", "status"]

    loader.call_count = call_count  # type: ignore
    return loader


# ============================================================================
# Test Cases for User Story 1: Cache Loading
# ============================================================================


class TestCacheHit:
    """T009a: test_get_returns_cached_schema_on_second_call"""

    def test_get_returns_cached_schema_on_second_call(
        self, cache: SchemaCacheProvider, counting_loader
    ) -> None:
        """Second get() with same profile returns cached result without loader call."""
        # First call: loader called
        result1 = cache.get("profile_a", counting_loader)
        assert result1 == ["email", "name", "status"]
        assert counting_loader.call_count["count"] == 1

        # Second call: loader NOT called (result from cache)
        result2 = cache.get("profile_a", counting_loader)
        assert result2 == ["email", "name", "status"]
        assert counting_loader.call_count["count"] == 1  # Still 1, not 2

        # Results are logically equal (may not be same object due to caching)
        assert result1 == result2


class TestCacheMiss:
    """First call (cache miss) invokes loader"""

    def test_get_calls_loader_on_cache_miss(
        self, cache: SchemaCacheProvider, counting_loader
    ) -> None:
        """First get() call invokes loader (cache miss)."""
        result = cache.get("profile_a", counting_loader)
        assert result == ["email", "name", "status"]
        assert counting_loader.call_count["count"] == 1


class TestMultipleProfiles:
    """Different profiles cached independently"""

    def test_different_profiles_cached_separately(
        self,
        cache: SchemaCacheProvider,
        mock_loader_profile_a,
        mock_loader_profile_b,
    ) -> None:
        """Separate profiles have separate cache entries."""
        # Load profile A
        result_a = cache.get("profile_a", mock_loader_profile_a)
        assert result_a == ["email", "name", "status"]

        # Load profile B
        result_b = cache.get("profile_b", mock_loader_profile_b)
        assert result_b == ["id", "full_name", "active"]

        # Second call to A returns cached result
        result_a2 = cache.get("profile_a", mock_loader_profile_a)
        assert result_a2 == ["email", "name", "status"]


class TestInvalidation:
    """T010a, T010b: invalidate() clears cache"""

    def test_invalidate_clears_cache(
        self, cache: SchemaCacheProvider, counting_loader
    ) -> None:
        """invalidate(profile_name) clears cache for that profile."""
        # Load and cache
        result1 = cache.get("profile_a", counting_loader)
        assert counting_loader.call_count["count"] == 1

        # Invalidate
        cache.invalidate("profile_a")

        # Next get() calls loader again (cache cleared)
        result2 = cache.get("profile_a", counting_loader)
        assert counting_loader.call_count["count"] == 2  # Loader called again
        assert result1 == result2

    def test_profile_change_invalidates_old_profile(
        self,
        cache: SchemaCacheProvider,
        mock_loader_profile_a,
        mock_loader_profile_b,
        counting_loader,
    ) -> None:
        """Invalidating old profile when switching profiles."""
        # Load profile A
        cache.get("profile_a", mock_loader_profile_a)

        # Switch to profile B (invalidate A)
        cache.invalidate("profile_a")
        cache.get("profile_b", mock_loader_profile_b)

        # Profile A is no longer cached
        result_a = cache.get("profile_a", counting_loader)
        assert result_a == ["email", "name", "status"]


class TestInvalidateAll:
    """invalidate() with no args clears entire cache"""

    def test_invalidate_no_args_clears_all(
        self,
        cache: SchemaCacheProvider,
        mock_loader_profile_a,
        mock_loader_profile_b,
        counting_loader,
    ) -> None:
        """invalidate() (no args) clears entire cache."""
        # Cache both profiles
        cache.get("profile_a", mock_loader_profile_a)
        cache.get("profile_b", mock_loader_profile_b)

        # Clear all
        cache.invalidate()

        # Both profiles now call loaders
        cache.get("profile_a", counting_loader)
        cache.get("profile_b", counting_loader)


class TestLoaderExceptions:
    """Exceptions from loader propagate to caller"""

    def test_loader_exception_propagates(self, cache: SchemaCacheProvider) -> None:
        """If loader raises, exception propagates. Cache not updated."""

        def failing_loader() -> list[str]:
            raise ValueError("Database connection failed")

        with pytest.raises(ValueError, match="Database connection failed"):
            cache.get("profile_a", failing_loader)

        # Cache not updated (no entry for profile_a)
        # Next call with different loader will call it
        def working_loader() -> list[str]:
            return ["a", "b"]

        result = cache.get("profile_a", working_loader)
        assert result == ["a", "b"]


# ============================================================================
# Test Fixtures for User Story 2: Refresh
# ============================================================================


@pytest.fixture
def stateful_loader():
    """Loader that changes schema on subsequent calls (simulates database change)."""
    state = {"version": 1}

    def loader() -> list[str]:
        if state["version"] == 1:
            return ["email", "name", "status"]
        else:
            return ["email", "name", "status", "created_at"]

    loader.set_version = lambda v: state.update({"version": v})  # type: ignore
    return loader


class TestRefresh:
    """T017a, T017b: refresh() reloads and updates cache"""

    def test_refresh_reloads_schema(
        self, cache: SchemaCacheProvider, stateful_loader
    ) -> None:
        """refresh() always calls loader (bypasses cache)."""
        # Initial load
        result1 = cache.get("profile_a", stateful_loader)
        assert result1 == ["email", "name", "status"]

        # Change loader state (simulate database schema change)
        stateful_loader.set_version(2)  # type: ignore

        # Regular get() still returns cached (old) schema
        cached = cache.get("profile_a", stateful_loader)
        assert cached == ["email", "name", "status"]  # Old schema

        # refresh() loads new schema
        result2 = cache.refresh("profile_a", stateful_loader)
        assert result2 == ["email", "name", "status", "created_at"]  # New schema

    def test_refresh_updates_cache_with_new_schema(
        self, cache: SchemaCacheProvider, stateful_loader
    ) -> None:
        """After refresh(), subsequent get() returns refreshed schema."""
        # Load and cache
        cache.get("profile_a", stateful_loader)

        # Change database
        stateful_loader.set_version(2)  # type: ignore

        # Refresh
        refreshed = cache.refresh("profile_a", stateful_loader)
        assert refreshed == ["email", "name", "status", "created_at"]

        # Get now returns refreshed schema
        result = cache.get("profile_a", stateful_loader)
        assert result == ["email", "name", "status", "created_at"]
