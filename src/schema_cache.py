"""In-memory database schema cache for reducing redundant schema reads.

Provides SchemaCacheProvider to cache database field names (schema) keyed by
profile name. Eliminates repeated I/O when filter validation, record preview,
or field lookups need schema information.

Usage:
    cache = SchemaCacheProvider()
    schema = cache.get("profile_a", lambda: DatabaseSchemaProvider.from_csv("data.csv"))
    # Second call with same profile returns cached result
    schema = cache.get("profile_a", lambda: ...)  # <50ms cache hit

    # Invalidate cache on profile change
    cache.invalidate("profile_a")

    # Force reload if database schema changed
    cache.refresh("profile_a", loader_func)

Classes:
    SchemaCacheProvider: Session-scoped schema cache (in-memory, not persistent)
"""

from collections.abc import Callable


class SchemaCacheProvider:
    """In-memory database schema cache keyed by profile name.

    Caches field names extracted from CSV/Google Sheets databases to avoid
    redundant reads. Cache is session-scoped (in-memory only, no persistence).

    Thread Safety: Not thread-safe. Assumes single-threaded context
    (sendMail.py is fully synchronous; editor.py uses Qt single-threaded loop).

    Example:
        cache = SchemaCacheProvider()

        # First call loads schema and caches it
        schema = cache.get("profile_a",
                          lambda: DatabaseSchemaProvider.from_csv("data.csv"))
        # Returns: ["email", "name", "status"]

        # Second call returns cached result (<50ms)
        schema = cache.get("profile_a", lambda: ...)
        # Returns: ["email", "name", "status"] (from cache)

        # Invalidate on profile change
        cache.invalidate("profile_a")

        # Force reload
        cache.refresh("profile_a",
                     lambda: DatabaseSchemaProvider.from_csv("data.csv"))
    """

    def __init__(self) -> None:
        """Initialize empty schema cache."""
        self._cache: dict[str, list[str]] = {}
        self._current_profile: str | None = None

    def get(self, profile_name: str, loader: Callable[[], list[str]]) -> list[str]:
        """Fetch schema from cache. If not cached, call loader and cache result.

        Args:
            profile_name: Profile identifier (string key from config.yml)
            loader: Callable that returns list of field names.
                   Example: lambda: DatabaseSchemaProvider.from_csv("path.csv")

        Returns:
            List of field names (from cache if exists, from loader if not)

        Behavior:
            - First call with "profile_a" → calls loader(), caches, returns result
            - Second call with "profile_a" → returns cached result (no loader call)
            - Call with different profile → calls loader() for new profile, caches separately

        Raises:
            Any exception raised by loader() propagates to caller. Cache not updated.
        """
        if profile_name in self._cache:
            return self._cache[profile_name]

        schema = loader()
        self._cache[profile_name] = schema
        return schema

    def invalidate(self, profile_name: str | None = None) -> None:
        """Invalidate cache entry or entire cache.

        Args:
            profile_name: Profile to invalidate. If None, clears entire cache.

        Behavior:
            - invalidate("profile_a") → removes cache entry for "profile_a"
            - invalidate(None) or invalidate() → clears entire cache dict

        Raises:
            Nothing. Silently succeeds if profile_name not in cache.
        """
        if profile_name is None:
            self._cache.clear()
        else:
            self._cache.pop(profile_name, None)

    def refresh(self, profile_name: str, loader: Callable[[], list[str]]) -> list[str]:
        """Force reload schema from loader and update cache.

        Use when database schema changed while app is running and same profile
        is still active. Unlike get(), this always calls loader (bypasses cache).

        Args:
            profile_name: Profile identifier
            loader: Callable that returns list of field names

        Returns:
            Freshly loaded list of field names (replaces cached value)

        Raises:
            Any exception raised by loader() propagates to caller. Cache not updated.
        """
        schema = loader()
        self._cache[profile_name] = schema
        return schema
