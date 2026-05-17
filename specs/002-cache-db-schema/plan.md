# Implementation Plan: Database Schema Caching

**Branch**: `002-cache-db-schema` | **Date**: 2026-05-17 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/002-cache-db-schema/spec.md`

**Note**: This plan implements session-scoped schema caching to eliminate redundant database reads when filter validation, field lookups, or record preview need schema information.

## Summary

Currently, database schema (field names) is loaded from CSV headers or Google Sheets on each request. For filter validation in the upcoming filter editor feature, this creates performance overhead when user rapidly switches profiles or edits filters. Implement in-memory schema cache keyed by profile name, invalidating only when profile changes. Cache scope is session-only (not persisted to disk).

## Technical Context

**Language/Version**: Python 3.12+ (project requirement)  
**Primary Dependencies**: PyYAML (config loading), gspread (Google Sheets), csv (stdlib)  
**Storage**: In-memory dict (session-scoped, no persistence)  
**Testing**: pytest (existing test suite, focus on caching behavior)  
**Target Platform**: Linux/macOS/Windows (CLI + PyQt6 editor)  
**Project Type**: Desktop application + CLI tool  
**Performance Goals**: Schema load from cache <50ms (vs typical uncached ~500ms+)  
**Constraints**: Session-only scope, profile-identified by name string, single active profile per session  
**Scale/Scope**: Typical profiles 50-300 fields, cache footprint <1MB per session

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution not yet defined for this project (template-only). Recommended principles to establish:
- Library-First: Schema caching should be a reusable utility, testable in isolation
- Test-First: TDD required — tests written before implementation
- Simplicity: No persistence layer, no polling, no background threads

No known violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/002-cache-db-schema/
├── plan.md              # This file
├── research.md          # Phase 0 (TBD)
├── data-model.md        # Phase 1 (TBD)
├── quickstart.md        # Phase 1 (TBD)
├── contracts/           # Phase 1 (TBD)
└── tasks.md             # Phase 2 (TBD)
```

### Source Code (repository root)

```text
src/
├── schema_provider.py       # Existing: DatabaseSchemaProvider class
├── schema_cache.py          # NEW: SchemaCacheProvider wrapper
├── sendMail.py              # Modified: Use schema cache for config profiles
└── editor.py                # Future: Use schema cache for filter validation
        
tests/
├── unit/
│   └── test_schema_cache.py # NEW: Cache hit/miss, invalidation tests
├── integration/
│   └── test_schema_cache_integration.py # NEW: E2E with editor
```

**Structure Decision**: Schema caching is a thin wrapper around existing DatabaseSchemaProvider. Add SchemaCacheProvider class to schema_provider.py or separate schema_cache.py module. Wrapper is stateful (holds cache dict), making it unsuitable as a static utility — instantiate once per application session and pass to components that need it.

## Phases

### Phase 0: Research *(outcomes: research.md)*

No critical unknowns. Confirm:
1. **Profile identity**: How is profile name accessed in editor.py and sendMail.py contexts?
2. **Cache ownership**: Who owns cache instance—application singleton, window-scoped, or global?
3. **Refresh API**: Should cache expose refresh() method or is profile change only invalidation?
4. **Thread safety**: Is sendMail.py single-threaded or do filter validation / record loading run async?

### Phase 1: Design & Implementation

**Prerequisites**: research.md complete

#### 1. Data Model (data-model.md)

Entity: **SchemaCache**
- **cache**: dict[str, list[str]] — maps profile_name → field_names
- **current_profile**: str | None — tracks active profile
- **Methods**:
  - get(profile_name: str, loader: Callable) → list[str] — fetch from cache or call loader
  - invalidate(profile_name: str | None) — clear entry or entire cache
  - refresh(profile_name: str, loader: Callable) → list[str] — force reload

#### 2. Contracts (if applicable)

No external API changes. Schema caching is internal optimization, not exposed to users.

#### 3. Quickstart (quickstart.md)

```python
# Before: Schema loaded every request
from src.schema_provider import DatabaseSchemaProvider

schema = DatabaseSchemaProvider.from_csv("data.csv")

# After: First call loads, subsequent calls cached
from src.schema_cache import SchemaCacheProvider

cache = SchemaCacheProvider()
schema = cache.get("profile_a", 
                   lambda: DatabaseSchemaProvider.from_csv("data.csv"))

# Profile change invalidates
cache.invalidate("profile_a")  # or cache.invalidate() for full clear

# Refresh if database changed
schema = cache.refresh("profile_a", 
                      lambda: DatabaseSchemaProvider.from_csv("data.csv"))
```

#### 4. Agent Context Update

Run: `.specify/scripts/bash/update-agent-context.sh claude`

Add to agent context:
- Schema caching pattern: in-memory dict keyed by profile name
- SchemaCacheProvider class location and interface
- Use sites: editor.py filter validation, sendMail.py profile handling

### Phase 2: Validation & Acceptance *(outcomes: implementation + tests)*

Will be planned by `/speckit.tasks` command after Phase 1 design approval.

## Complexity Tracking

No violations to justify. Caching is a simple wrapper, no repository pattern or multi-project complexity.

---

**Next Step**: Execute Phase 0 research to resolve unknowns, then Phase 1 design to finalize contracts and agent context.
