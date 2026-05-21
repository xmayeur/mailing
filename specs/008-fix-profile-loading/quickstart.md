# Quickstart: Profile Loading and Configuration Fix

**Date**: 2026-05-21  
**Branch**: `008-fix-profile-loading`  
**Estimated scope**: 5-7 tasks, 3-5 days

## Feature Overview

Fix three interconnected issues:
1. **Editor**: Apply profile styling when opening files
2. **SMTP**: Load credentials from vault when profile selected
3. **Logging**: Replace debug-level info logs with debug level
4. **Bonus**: Enable filter persistence to profile config (P3, on request)

## Architecture Changes

### Profile Loading Flow (NEW)

```
[User selects profile] 
  → Profile name ("artscroises")
  → Lookup vault key in config.yml ("mailconfig: artscroisesmailing")
  → Call get_hc_secrets(vault_key)
  → Parse SMTP host/port/user/password from response
  → Cache in Profile object
  → [Editor] Load template styling
  → [SendMail] Use cached SMTP to connect
```

### Code Changes Summary

**sendMail.py**:
- Add method `Profile.load_smtp_from_vault()` to fetch SMTP params
- Call during profile selection, cache result
- Handle vault errors gracefully (specific error messages)
- Replace debug log.info → log.debug (5-10 calls)

**editor.py**:
- Add method `Editor.apply_profile_styling(profile)` to set CSS/template
- Call when profile is selected or file opened
- Preserve existing document content while changing styling
- Replace debug log.info → log.debug (3-5 calls)

**config.yml**:
- Add optional `filters:` section under each profile [future]
- Document vault_key format

**All modules** (logging):
- Audit log.info calls
- Move diagnostic logs to log.debug
- ~20-30 total changes across files

## Implementation Steps

1. **Tests first** (TDD):
   - Write tests for profile.load_smtp_from_vault()
   - Write tests for vault key error handling
   - Write tests for editor styling application
   - Write tests for filter save/restore

2. **Profile SMTP Loading**:
   - Implement vault_key → secrets fetch
   - Cache SMTP params in Profile
   - Add error handling for vault failures

3. **Editor Profile Styling**:
   - Load template file from profile
   - Apply CSS/HTML styling to editor content
   - Test with multiple profiles

4. **Logging Migration**:
   - Find all log.info calls
   - Categorize: diagnostic (→ debug) vs. operational (keep info)
   - Update calls (use regex replace where safe)

5. **Filter Persistence** (P3):
   - Add filters array to config.yml structure
   - Add save/restore methods to Profile
   - Write tests

6. **Integration Test**:
   - Full flow: select profile → open file → see styled content → send email
   - Verify SMTP connects with vault credentials
   - Verify logs at correct levels

## Testing Plan

### Unit Tests
```
tests/test_profile_loading.py
  - test_load_smtp_from_vault_success
  - test_load_smtp_from_vault_missing_key
  - test_load_smtp_from_vault_invalid_credentials
  
tests/test_editor_styling.py
  - test_apply_profile_styling
  - test_styling_preserves_content
  - test_switch_profiles_updates_styling

tests/test_filter_persistence.py
  - test_save_filter_to_profile
  - test_load_filter_from_profile
  - test_filter_persists_across_restart
```

### Integration Tests
```
tests/integration/test_smtp_sending_with_artscroises_profile.py
  - test_artscroises_profile_sends_email_successfully
  - test_smtp_error_provides_specific_feedback
```

### Manual Testing Checklist
- [ ] Editor opens file with artscroises profile styling
- [ ] Switching profiles in editor updates styling
- [ ] SendMail sends email with artscroises profile (no SMTP error)
- [ ] Test profile with invalid vault key shows clear error
- [ ] Production logs have no debug diagnostic messages at INFO level
- [ ] Save filter to profile config (request feature)
- [ ] Restart app, filter restored for profile

## Known Dependencies

- `get-hc-secrets` (existing): Vault integration
- `PyQt6` (existing): Editor GUI
- `pyyaml` (existing): Config file parsing
- `logging` (Python stdlib): Log level management

## Success Metrics

- ✅ Artscroises profile sends email without SMTP error
- ✅ Editor styling matches selected profile
- ✅ Log volume at INFO level reduced by 30-50% (diagnostic logs moved to DEBUG)
- ✅ All 5 user stories have passing acceptance tests
- ✅ No new dependencies required

## Known Risks

| Risk | Mitigation |
|------|-----------|
| Vault offline/slow | Cache SMTP params in session, show timeout error with retry |
| Wrong profile cached | Use profile name as cache key, invalidate on switch |
| Template file missing | Graceful fallback to default styling, warn user |
| Filter format incompatibility | Version config.yml, migration script if needed |
| Log.debug too verbose | Use structured logging with filters for DEBUG level |

## Rollback Plan

- Revert to previous commit
- Clear config.yml cache (app restart)
- Re-apply vault key configuration manually

## Next Steps

1. Approve quickstart → start `/speckit.tasks`
2. `/speckit.tasks` generates task breakdown
3. Implement tasks on branch `008-fix-profile-loading`
4. `/speckit.verify` to test completed work
5. Submit PR, merge to master
