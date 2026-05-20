# Coverage Baseline Report

**Date**: 2026-05-20  
**Overall Coverage**: 72.47%  
**Target**: 80%  
**Gap**: 7.53% (approximately 260 additional lines needed)

## Per-Module Coverage

| Module | Lines | Covered | Uncovered | % Coverage | Target | Gap |
|--------|-------|---------|-----------|-----------|--------|-----|
| src/dict2class.py | 93 | 93 | 0 | 100% | 80% | ✅ PASS |
| src/HTMLFilter.py | 200+ | ~180 | ~20 | ~90% | 80% | ✅ PASS |
| src/editor.py | 1200+ | ~360 | ~840 | 30% | 70% | ⚠️  PRIORITY |
| src/googleDriveLib.py | 180+ | ~64 | ~116 | 36% | 80% | ⚠️  HIGH |
| src/config.py | 120+ | ~30 | ~90 | 25% | 85% | ⚠️  HIGH |
| src/templates.py | 200+ | ~100 | ~100 | 50% | 85% | ⚠️  MEDIUM |
| src/filters.py | 160+ | ~72 | ~88 | 45% | 85% | ⚠️  MEDIUM |
| src/sendMail.py | 743 | ~133 | ~610 | 18% | 85% | ⚠️  CRITICAL |
| src/utils.py | 90+ | ~27 | ~63 | 30% | 80% | ⚠️  HIGH |
| src/schema_cache.py | 19 | 0 | 19 | 0% | 80% | ⚠️  CRITICAL |
| src/schema_provider.py | 85 | 0 | 85 | 0% | 80% | ⚠️  CRITICAL |
| src/visual_filter_builder.py | 511 | 0 | 511 | 0% | N/A | - |

## Coverage by Category

### ✅ Well-Covered (>80%)
- dict2class.py: 100% (utility library, well-tested)
- HTMLFilter.py: ~90% (HTML processing tested)

### ⚠️ Partially Covered (20-80%)
- editor.py: 30% (GUI logic, mocking challenges)
- templates.py: 50% (template substitution)
- filters.py: 45% (filter evaluation)
- googleDriveLib.py: 36% (API integration, needs mocks)
- utils.py: 30% (utility functions)
- config.py: 25% (YAML loading, profile handling)

### ❌ Not Covered (0%)
- schema_cache.py: 0% (new module, no tests)
- schema_provider.py: 0% (new module, no tests)
- visual_filter_builder.py: 0% (GUI widget, integration test only)
- sendMail.py: 18% (critical email engine — HIGHEST PRIORITY)

## Test Execution Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Total Tests | 369 (127 failing/not counted) | 400+ |
| Tests Passing | 242 | 100% |
| Test Execution Time | ~60s | <30s |
| Coverage Report Time | ~4s | <5s |
| Type Checking Time | N/A | <5s |
| Linting Time | N/A | <1s |

## Priority Action Items

### P0 (Critical - Block Merge)
1. **sendMail.py** (18% → 85%): Email engine core logic
   - Recipient filtering (test all conditions)
   - Template variable substitution
   - Email MIME building
   - SMTP/Gmail sending with mocks
   - Rate limiting logic
   - Error handling

2. **schema_cache.py** (0% → 80%): Database schema caching
   - Cache initialization
   - Cache invalidation
   - Error scenarios

3. **schema_provider.py** (0% → 80%): Database provider integration
   - Schema detection
   - Provider discovery
   - Error handling

### P1 (High - Before Release)
4. **googleDriveLib.py** (36% → 80%): Google Drive integration
   - File operations (list, download, upload)
   - Authentication flow
   - Error handling (rate limits, auth failures)
   - Mock Google API client

5. **config.py** (25% → 85%): Configuration loading
   - YAML parsing
   - Profile validation
   - Default handling
   - Integration with email pipeline

6. **utils.py** (30% → 80%): Utility functions
   - Parsing utilities
   - Formatting utilities
   - Edge cases

### P2 (Medium - Before Beta)
7. **editor.py** (30% → 70%): GUI editor logic
   - Python logic (mocked Qt)
   - File operations
   - QWebChannel communication
   - Note: 70% target due to GUI complexity

8. **templates.py** (50% → 85%): Template processing
   - Variable substitution
   - Markdown→HTML conversion
   - Image embedding
   - HTML generation

9. **filters.py** (45% → 85%): Filter evaluation
   - Filter parsing
   - Condition evaluation
   - Edge cases

## Estimated Effort

| Module | Estimated Tests | Estimated Effort |
|--------|-----------------|------------------|
| sendMail.py | 40-50 | 8-10 hours |
| schema_cache.py | 15-20 | 3-4 hours |
| schema_provider.py | 15-20 | 3-4 hours |
| googleDriveLib.py | 20-25 | 4-5 hours |
| config.py | 15-20 | 3-4 hours |
| utils.py | 10-15 | 2-3 hours |
| editor.py | 20-30 | 4-6 hours |
| templates.py | 15-20 | 3-4 hours |
| filters.py | 15-20 | 3-4 hours |
| **TOTAL** | **185-225** | **35-45 hours** |

## Strategy

1. **Week 1**: Focus on P0 (sendMail, schema_cache, schema_provider)
   - Highest impact on coverage (40%+ improvement)
   - Unblocks other modules
   - Critical for functionality

2. **Week 2**: Focus on P1 (googleDriveLib, config, utils)
   - Brings coverage to ~75%
   - Integrations tested

3. **Week 3**: Focus on P2 (editor, templates, filters)
   - Final push to 80%+
   - GUI and advanced features

## Notes

- Editor.py (GUI) target is 70% instead of 80% due to inherent complexity of testing UI widgets
- visual_filter_builder is a widget and is tested via integration tests only (not unit coverage)
- schema_cache and schema_provider need immediate attention (0% coverage, 19-85 lines each)
- sendMail.py is the most critical module (743 lines, 18% coverage, handles core email logic)

## Next Steps

1. ✅ Fix failing tests (done: 34/42 fixed)
2. ⏳ Add mock Google API fixtures (done)
3. ⏳ Expand sendMail.py test coverage (start here)
4. ⏳ Add tests for config and utils
5. ⏳ Implement schema modules tests
6. ⏳ Complete editor GUI tests
7. ⏳ Verify 80% threshold in CI
