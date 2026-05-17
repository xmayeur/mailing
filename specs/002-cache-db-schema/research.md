# Research: Database Schema Caching Unknowns (Phase 0)

**Date**: 2026-05-17  
**Status**: Complete  
**Goal**: Resolve technical unknowns from plan.md before Phase 1 design

---

## Unknown 1: Profile Identity Mechanism

**Question**: How is profile name accessed in editor.py and sendMail.py contexts?

**Research Process**:
- Examined sendMail.py argument parsing (args.profile)
- Examined config.yml loading (yaml.safe_load, args.conf[args.profile])
- Checked editor.py for profile references
- Reviewed existing schema_provider.py usage patterns

**Findings**:
- **sendMail.py**: Profile loaded via `args.profile` string → `args.conf[args.profile]` dict
- **editor.py**: Currently no profile concept; editor.py is standalone WYSIWYG for composing HTML
- **Profile identity**: Profile name is a string key in config.yml (e.g., "default", "cambristi")
- **Current usage**: sendMail.py uses profile to fetch database source (CSV path or Google Sheets ID), SMTP config, filter rules

**Decision**: Profile identity MUST be string name, keyed by args.profile or config profile name. No object identity.

---

## Unknown 2: Cache Ownership

**Question**: Who owns cache instance—application singleton, window-scoped, or global?

**Research Process**:
- Examined editor.py EditorWindow class structure
- Checked sendMail.py main flow (single process_profile call)
- Reviewed existing singleton patterns in codebase
- Assessed cache lifetime vs application lifetime

**Findings**:
- **sendMail.py**: Single CLI invocation per process, one profile per run → cache scope = process lifetime
- **editor.py**: PyQt6 QMainWindow, typically single instance per session (can open multiple docs, one window)
- **No existing singletons** in codebase for session management
- **Cache data**: List of strings (field names) ~1-5 KB per profile, <1MB typical total

**Decision**: Cache should be:
1. **In sendMail.py usage**: Instantiate SchemaCacheProvider once per process in main(), pass to process_profile()
2. **In editor.py usage** (future): Instantiate once in EditorWindow.__init__(), store as instance variable
3. **NOT a global singleton**: Explicit dependency injection allows testing and multiple instances if needed

---

## Unknown 3: Thread Safety

**Question**: Is sendMail.py single-threaded or do filter validation / record loading run async?

**Research Process**:
- Searched for Thread, threading, async, await keywords in sendMail.py and editor.py
- Examined file I/O operations (no thread pools, no async I/O)
- Reviewed network I/O for Google Sheets (via gspread, blocking calls)
- Assessed PyQt6 event loop (single-threaded Qt main loop)

**Findings**:
- **sendMail.py**: Fully synchronous/blocking, no threading or async
- **editor.py**: PyQt6 single-threaded (Qt event loop is serial)
- **Existing I/O**: CSV file reads, Google Sheets API calls are all blocking (expected for this scale)
- **No concurrent profile switches**: Single active profile per session (serial, not parallel)

**Decision**: Cache does NOT require thread safety locks. Simple dict operations are safe in single-threaded context. If future work adds async, revisit with thread-safe dict or locks.

---

## Unknown 4: Refresh API Requirements (Bonus)

**Question**: Should cache expose refresh() method or is profile change only invalidation?

**Research Process**:
- Reviewed spec.md User Story 2 (manual refresh)
- Examined filter editor use cases (database might change during session)
- Checked existing refresh patterns in codebase

**Findings**:
- **US2 requirement**: Manual refresh needed if database schema changes while same profile active
- **No automatic polling**: Assume user initiates refresh if needed
- **API pattern**: Existing code uses simple function calls (DatabaseSchemaProvider.from_csv), not callbacks

**Decision**: Cache API should expose:
- `get(profile_name, loader_func)` → fetch from cache or call loader_func and cache
- `invalidate(profile_name)` → clear cache for profile (or entire cache if None)
- `refresh(profile_name, loader_func)` → force reload from loader_func, update cache
- No background polling or auto-invalidation timers

---

## Summary Table

| Unknown | Finding | Decision |
|---------|---------|----------|
| **Profile Identity** | String name from config.yml (args.profile) | Cache keyed by string profile name |
| **Cache Ownership** | Single instance per process/window needed | Dependency injection in sendMail.py/editor.py |
| **Thread Safety** | Single-threaded (no async, no threads) | Simple dict, no locks required |
| **Refresh API** | User-initiated refresh needed (US2) | Implement get(), invalidate(), refresh() methods |

---

## Implications for Design

1. **SchemaCacheProvider class**:
   - Simple stateful wrapper: `__init__()` → initialize cache dict
   - Methods: `get()`, `invalidate()`, `refresh()` (no thread safety needed)
   - Dependency injection pattern: instantiate in application main, pass to functions

2. **Integration points**:
   - sendMail.py: Create cache in main(), pass to functions that need schema
   - editor.py: Create cache in EditorWindow.__init__(), use for filter validation (future)

3. **Testing**:
   - No async mocking needed
   - Can use simple mock DatabaseSchemaProvider
   - Cache behavior easily testable with in-memory dicts

---

**Next Step**: Proceed to Phase 1 Design (data-model.md, schema_cache.py skeleton)
