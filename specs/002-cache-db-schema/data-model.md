# Data Model: Schema Caching

**Date**: 2026-05-17  
**Status**: Design Complete  
**Goal**: Define SchemaCacheProvider class interface and cache data structure

---

## Entity: SchemaCacheProvider

**Purpose**: In-memory cache for database schema keyed by profile name. Eliminates redundant schema reads across filter validation, record preview, and field lookups.

**Scope**: Session-only (in-memory, no persistence to disk)

**Ownership**: Single instance per application session (created in main(), passed via dependency injection)

### Data Structure

```python
class SchemaCacheProvider:
    """In-memory database schema cache keyed by profile name."""
    
    # Internal state:
    # _cache: dict[str, list[str]]  # Maps profile_name → field_names
    # _current_profile: str | None  # Tracks active profile for invalidation logic
```

**Cache Entry**:
- **Key**: Profile name (string from config.yml, e.g., "default", "cambristi")
- **Value**: List of field names extracted from database (list[str], e.g., ["email", "name", "status"])
- **Memory**: Typical 50–300 fields per profile → ~1–5 KB per entry → <1 MB total (max ~100 profiles)

---

## Interface: Public Methods

### Method 1: get(profile_name, loader)

**Purpose**: Fetch schema from cache or call loader function and cache result.

**Signature**:
```python
def get(self, profile_name: str, loader: Callable[[], list[str]]) -> list[str]:
    """
    Fetch schema from cache. If not cached, call loader() and cache result.
    
    Args:
        profile_name: Profile identifier (string key from config.yml)
        loader: Callable that returns list[str] of field names
                Example: lambda: DatabaseSchemaProvider.from_csv("data.csv")
    
    Returns:
        List of field names (from cache if exists, from loader if not)
    
    Behavior:
        - First call with "profile_a" → calls loader(), caches result, returns it
        - Second call with "profile_a" → returns cached result (no loader call)
        - Call with different profile → calls loader() for new profile, caches separately
    """
```

**Use Cases**:
- Filter validation: `cache.get("profile_a", lambda: provider.from_csv("data.csv"))`
- Record preview: `cache.get("profile_b", lambda: provider.from_google_sheets(service, sheet_id))`

### Method 2: invalidate(profile_name=None)

**Purpose**: Clear cache entry for a profile or entire cache.

**Signature**:
```python
def invalidate(self, profile_name: str | None = None) -> None:
    """
    Invalidate cache entry. Clear entire cache if profile_name is None.
    
    Args:
        profile_name: Profile to invalidate. If None, clears entire cache.
    
    Behavior:
        - invalidate("profile_a") → removes cache entry for profile_a only
        - invalidate(None) or invalidate() → clears entire cache dict
    """
```

**Use Cases**:
- Profile switch detected: `cache.invalidate("profile_a")` (before loading profile_b)
- Application reset: `cache.invalidate()` (clear all)

### Method 3: refresh(profile_name, loader)

**Purpose**: Force reload schema from loader and update cache (for when database schema changed).

**Signature**:
```python
def refresh(self, profile_name: str, loader: Callable[[], list[str]]) -> list[str]:
    """
    Force reload schema from loader and update cache (bypassing cache hit).
    
    Args:
        profile_name: Profile identifier
        loader: Callable that returns list[str] of field names
    
    Returns:
        Freshly loaded list of field names (replaces cached value)
    
    Behavior:
        - Always calls loader() (ignores existing cache)
        - Updates cache with new result
        - Returns new schema
    
    Use Case: User detects database schema changed while app running
    """
```

**Use Cases**:
- Manual refresh after database edit: `cache.refresh("profile_a", loader_func)`

---

## Integration Points

### sendMail.py Integration

**Current Flow**:
```python
config = args.conf[args.profile]
database_path = config["database"]
schema = DatabaseSchemaProvider.detect_and_extract(database_path, ...)
```

**With Cache**:
```python
cache = SchemaCacheProvider()

def get_schema_for_profile(profile_name: str, profile_config: dict) -> list[str]:
    """Load schema for profile, using cache."""
    db_path = profile_config["database"]
    return cache.get(profile_name, 
                    lambda: DatabaseSchemaProvider.detect_and_extract(db_path, ...))

# In main() or process_profile():
schema = get_schema_for_profile(args.profile, config)
```

### editor.py Integration (Future)

**Current**: No profile concept (pure document editor)

**Future (with filter editor feature)**:
```python
class SendNewsletterWindow(QDialog):
    def __init__(self, ...):
        self._schema_cache = SchemaCacheProvider()
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
    
    def _on_profile_changed(self, profile_name: str):
        """Profile changed, invalidate cache and reload."""
        if profile_name and profile_name != self._current_profile:
            self._schema_cache.invalidate(self._current_profile)
            self._current_profile = profile_name
            self._validate_filter()
    
    def _validate_filter(self):
        """Validate filter using cached schema."""
        schema = self._schema_cache.get(
            self._current_profile,
            lambda: self._load_database_schema(self._current_profile)
        )
        # Use schema for field validation
```

---

## Non-Functional Requirements

| Requirement | Value | Justification |
|---|---|---|
| **Cache hit latency** | <50ms | Dict lookup + list copy is <1ms; acceptable for UI responsiveness |
| **First load (uncached)** | Unchanged | No optimization; reuses DatabaseSchemaProvider |
| **Memory footprint** | <1MB typical | 50–300 fields/profile, ~1–5 KB each, max ~100 profiles |
| **Scope** | Session-only (in-memory) | No disk persistence; simplifies implementation |
| **Thread safety** | Not required | Single-threaded (no async, no threading in sendMail/editor) |

---

## State Transitions

```
Initialization:
  SchemaCacheProvider() → _cache = {}, _current_profile = None

On first get("profile_a", loader):
  loader() called → returns ["col1", "col2", ...]
  _cache["profile_a"] = ["col1", "col2", ...]
  return ["col1", "col2", ...]

On second get("profile_a", loader):
  return _cache["profile_a"]  (no loader call)

On profile change (detected by editor):
  invalidate("profile_a")
  _cache.pop("profile_a", None)

On refresh("profile_a", loader):
  new_schema = loader()
  _cache["profile_a"] = new_schema
  return new_schema
```

---

## Error Handling

**When loader raises exception**:
- `get()`: Exception propagates to caller; cache not updated
- `refresh()`: Exception propagates to caller; cache not updated
- No silent failures or fallbacks (let errors surface)

**When cache has no entry**:
- `get()`: Calls loader (normal behavior)
- `invalidate()`: Silently succeeds (no error if entry doesn't exist)
- `refresh()`: Treats as first load (calls loader, caches result)

---

## Testing Strategy

**Unit Tests** (test_schema_cache.py):
- Cache hit: verify cached result returned on second call
- Cache miss: verify loader called on first call
- Invalidation: verify cache entry cleared
- Refresh: verify loader called even if cached

**Integration Tests** (test_schema_cache_integration.py):
- Profile switching: load profile A, switch to B, verify B loads fresh
- Performance: measure <50ms cache hit time

---

**Next Step**: Implement SchemaCacheProvider skeleton (src/schema_cache.py)
