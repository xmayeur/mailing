# Data Model: Filter Editor with Database Preview

**Feature**: Filter Editor with Database Preview in Send Newsletter Window  
**Date**: 2026-05-17

## Entities & State

### Filter (YAML-formatted)

**Source**: `config.yml` profile settings  
**Type**: Dictionary with field-value conditions  
**Example**:
```yaml
status: is active
country: one of "BE", "FR"
email: is not empty
```

**Attributes**:
- `field`: Column name from database
- `operator`: Filter operation (see Supported Operations below)
- `value`: Target value for comparison
- `valid`: Boolean (syntax & field validation status)
- `session_active`: Boolean (overrides config.yml when true)

**Supported Filter Operations**:

| Category | Operations |
|----------|-----------|
| **Equality** | is, is not, is equal to, is not equal to |
| **Comparison** | gt (greater than), lt (less than), ge (greater or equal), le (less or equal) |
| **Text Matching** | contains, does not contain, starts with, ends with, matches (regex), does not match |
| **List Membership** | in, not in, one of, not one of |
| **Empty/Null** | is empty, is not empty |
| **Email-specific** | is bounced, is not bounced |

**Format**: `{field_name: "operator value"}` (YAML key-value pairs)

**Examples**:
```yaml
# Equality
email: is john@example.com
status: is not pending

# Text matching
name: contains John
domain: starts with mail.
country: ends with .uk
message: matches .*urgent.*

# List membership
id: in 1,2,3
role: one of admin,manager

# Empty
notes: is empty
address: is not empty
```

**State Transitions**:
```
[Original Config Filter] 
    ↓
[User edits in text field]
    ↓
[Validation passes/fails]
    ↓ (passes + clicks Apply)
[Session Filter - overrides config]
    ↓
[Send operation uses session filter]
```

### Database Record

**Source**: CSV or Google Sheets  
**Type**: List/row of field values  
**Example**: `["alice@test.com", "active", "Alice"]`

**Attributes**:
- `email`: Email address (required for send)
- `[field1]`: Custom field matching filter definitions
- `[field2]`: Additional fields as defined in database headers

### Validation Status

**Source**: `FilterValidator.get_validation_status()`  
**Attributes**:
- `is_valid`: boolean
- `syntax_errors`: list[str] (YAML parsing issues)
- `missing_fields`: list[str] (fields not in schema)

### Database Schema

**Source**: Database headers  
**Type**: List of field names  
**Example**: `["email", "status", "name", "country"]`

**Extraction**:
- CSV: First row headers
- Google Sheets: First row via gspread API

## Relationships

```
Config Profile
    │
    ├─ Filter (original, from config.yml)
    ├─ Database path (CSV or SHEETID)
    └─ Database Schema → [Field names...]

Session State (in _SendDialog)
    │
    ├─ _session_filter (overrides config filter)
    ├─ _current_profile (profile name)
    └─ Records Display [QTableWidget]
        └─ [Filtered Records] (matches current filter)
```

## Workflow Data Flow

### Filter Application Flow (Bug Fix Scope)

```
1. User edits filter text
   ↓
2. Validation runs (on text change, debounced 200ms)
   ├─ Parse YAML syntax
   ├─ Check field names against schema
   ↓
3. User clicks "Apply Filter" button
   ├─ Final validation (line 775-782)
   ├─ Parse YAML & store in _session_filter (line 787-789)
   ├─ [BUG FIX: Call filter_and_display_records()] ← MISSING
   ↓
4. Record preview updates
   ├─ FilterMatcher.filter_rows(all_records, filter, schema)
   ├─ _update_record_display(filtered_rows, headers, total)
   ↓
5. User sees filtered record list & count
```

## Validation Rules

**Filter Syntax**:
- Must be valid YAML mapping (key: value pairs)
- Each key = field name
- Each value = condition string (e.g., "is active", "in 'A','B'")

**Field Names**:
- Must exist in active database schema
- Case-sensitive match with column headers
- Error reported if field not found: "Fields not found: [field_name]"

**Empty Filter**:
- Valid state
- Means: show all records
- YAML parse result: `None` or `{}`

## State Validation

- Only one profile active at a time
- Session filter persists until dialog closes (or Reset clicked)
- Original filter from config.yml never modified
- Database records reloaded when profile changes
