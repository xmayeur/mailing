# Data Model: Editor Workflow Improvements

**Feature**: `003-editor-workflow-improvements`  
**Generated**: 2026-05-18

---

## Entities

### Configuration Profile

**Description**: YAML configuration block for a send profile in `config.yml`

**Fields**:
- `default_documents_path` (string, optional): Absolute path to the user's preferred document folder. Per-profile (each profile has its own remembered folder).
- `smtp_host`, `smtp_port`, `from_address`, etc. (existing fields): Unchanged

**Validation Rules**:
- Path must be readable and writable by the editor process
- Path may not exist; falls back to OS default if missing (no error)
- Path is validated on editor startup; invalid paths do NOT block initialization

**Lifecycle**:
- **Creation**: Initialized to empty string `""` when profile is created
- **Update**: Set to the directory of the last **successfully** saved/opened file
- **Fallback**: If path is invalid/missing on load, replaced with OS-specific default (Documents on Windows, home on macOS/Linux)

**Example**:
```yaml
newsletter:
  sender: newsletters@example.com
  default_documents_path: "/Users/xavier/projects/newsletters"  # per-profile
  database: "subscribers.csv"
  # ... other profile settings
```

---

### Template File Metadata

**Description**: State tracking for files opened in read-only template mode

**Fields**:
- `_is_template` (boolean, internal state): True if the opened file is a template file
- `_template_filename` (string, internal state): Original template filename for logging

**Validation Rules**:
- Template detection: Filename contains `.template` (e.g., `template.html`, `newsletter-template.md`) OR matches `template.*` pattern
- Detection is case-insensitive on all platforms
- If multiple patterns match, first matching rule applies

**Lifecycle**:
- **Detection**: On `EditorWindow.open_file()`, check filename against template patterns
- **Enforcement**: If template detected, set `_is_template = True` and disable Save action
- **Preservation**: All edits remain in memory; Save As creates new file without modifying original template

---

### Filter Validation State

**Description**: Transient state for filter field responsiveness optimization

**Fields**:
- `_validation_timer` (QTimer, internal): Debounce timer for filter validation
- `_last_filter_text` (string, internal): Previous filter text for comparison

**Behavior**:
- Debounce timeout: 50ms (reduced from 200ms)
- Validation runs after user pauses typing for 50ms
- Validation feedback shown non-intrusively without blocking user input

**Lifecycle**:
- **Init**: Timer initialized in `_SendDialog.__init__()`
- **Update**: On each character input, restart timer (cancel previous timeout)
- **Trigger**: After 50ms of inactivity, validation runs and UI updates

---

## Configuration Atomicity (FR-011)

**Strategy**: Atomic config writes to prevent data corruption

**Implementation Approach**:
1. Use temporary file + rename pattern:
   - Write new config to `config.yml.tmp` in same directory
   - On success, atomically rename `.tmp` → `config.yml` (single filesystem operation)
   - On failure, leave original `config.yml` untouched; `.tmp` cleaned up

2. Error Handling:
   - If write fails (disk full, permissions, etc.), catch exception and log warning
   - Restore previous config state implicitly (no changes written to `.tmp` on error)
   - User is notified but editor continues (config read-only state until next successful save)

3. Validation:
   - Before writing, validate YAML syntax
   - On read, handle corrupted YAML gracefully (use defaults)

---

## Relationships & Dependencies

```
Profile
  ├─ default_documents_path (string)
  ├─ other settings (sender, database, etc.)
  └─ [linked to] EditorWindow state

EditorWindow
  ├─ _is_template (boolean)
  ├─ _file_path (string)
  ├─ _css_path (string)
  └─ [triggers] _SendDialog

_SendDialog
  ├─ _validation_timer (QTimer)
  ├─ filter_text_edit (QPlainTextEdit)
  ├─ filter_status_label (QLabel)
  └─ [reads] Profile (default_documents_path, selected profile)
```

---

## Data Volume & Scale

**Configuration File**:
- Size: < 10 KB (typical profile config)
- Profiles per config: 1-20 (typical)
- Update frequency: Once per file save/open
- Atomic write overhead: Negligible (single filesystem rename)

**Filter Validation**:
- No new data storage
- Debounce timer fires ~50ms intervals during typing
- Timers cleaned up on dialog close

---

## State Transitions

### Editor File Load State

```
[Startup]
  ↓
[Load config] → [Load default_documents_path]
  ↓
[Path valid?] → YES → [Use remembered path]
             → NO  → [Use OS default, log warning]
  ↓
[Editor ready] → [User opens file or uses Save As]
  ↓
[File loaded] → [Update default_documents_path to file's folder] (if successful save/open)
```

### Template File Detection State

```
[open_file(path)]
  ↓
[Matches template pattern?]
  → NO  → [Normal editor mode]
  → YES → [Read-only template mode]
            ├─ _is_template = true
            ├─ Title shows "[Read-Only Template]"
            ├─ Save action disabled
            └─ Save As enabled
```

---

## Constraints & Assumptions

- YAML config syntax remains unchanged; no breaking changes to existing profiles
- Per-profile storage means each profile maintains independent folder memory
- Atomic writes use rename (works on Windows/macOS/Linux)
- Template detection uses simple string matching (no regex overhead)
- Filter validation timer reset on every keystroke (no accumulated state)

