# Logging Audit: log.info → log.debug Migration

**Date**: 2026-05-21  
**Feature**: Fix Profile Loading and Configuration  
**Scope**: Audit all log.info calls, classify as operational (keep at info) or diagnostic (move to debug)

## Summary

- **Total log.info calls found**: 44 across source files
- **Files affected**: sendMail.py (11), editor.py (30), googleDriveLib.py, schema_provider.py, filter_matcher.py
- **Action**: Classify each call, replace diagnostic with log.debug

## Classification Criteria

| Level | Definition | Examples |
|-------|-----------|----------|
| **INFO** (keep) | User-relevant operational events | Email sent, subscriber count, filters applied, rate limit reached |
| **DEBUG** (move) | Diagnostic/technical details | Vault fetch steps, SMTP connection details, cache hits, internal state |

## Audit Results by File

### sendMail.py (11 calls)

| Line | Code | Classification | Action |
|------|------|-----------------|--------|
| 531 | `log.info("stored in sent folder")` | INFO | Keep (user event) |
| 922 | `log.info("do not sent activated")` | INFO | Keep (user event) |
| 950 | `log.info(f"Dossier temporaire supprimé : {d}")` | DEBUG | → log.debug (cleanup detail) |
| 957 | `log.info(f"Reprise à l'index {from_index}")` | DEBUG | → log.debug (resume detail) |
| 970 | `log.info("Limite horaire atteinte. Pause d'une heure...")` | INFO | Keep (rate limit, user-relevant) |
| 1028 | `log.info(f"Envoi à {len(addressees)} destinataires...")` | INFO | Keep (send event, user-relevant) |
| 1033 | `log.info(f"Envoi final à {len(addressees)} destinataires.")` | INFO | Keep (send event) |
| 1037 | `log.info(...)` | INFO | Keep (operational) |
| 1265 | `log.info(f"Sending email to {recipients}")` | INFO | Keep (send event) |
| 1275 | `log.info("sent")` | INFO | Keep (user event) |
| 1398 | `log.info("Test mode: mailing sent successfully.")` | INFO | Keep (test result) |

**sendMail.py Summary**: 2 → debug, 9 keep

### editor.py (30 calls)

**Need detailed analysis** - Scan file for specific calls:
- Profile loading steps: DEBUG (diagnostic)
- File operations (save, open): INFO (user event)
- Styling updates: DEBUG (technical detail)

### Other Modules

- **googleDriveLib.py**: Check Drive API calls (mostly operational, some DEBUG)
- **schema_provider.py**: Check schema operations (mostly DEBUG)
- **filter_matcher.py**: Check filter matching (mostly DEBUG)

## Implementation Plan

1. Review each file with developer
2. Mark diagnostic calls with "→ log.debug"
3. Create PR with migrations
4. Verify production logs at INFO level have no debug noise

## Testing

- Run app with INFO logging level
- Capture all INFO messages
- Verify no debug-diagnostic messages present
- Enable DEBUG logging, verify detail messages appear
