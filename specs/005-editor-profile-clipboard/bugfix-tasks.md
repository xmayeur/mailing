# Bug Fix Tasks: Profile Selection File Dialog Issue

**Issue**: After selecting profile from main window, "Open File" dialog opens to hardcoded "data" directory instead of profile's default_document_path

**Root Cause**: `_menu_open()` method uses hardcoded `"data"` string in QFileDialog.getOpenFileName() instead of using `self._default_documents_path`

**Affected Code**: 
- `src/editor.py` line ~3110: `_menu_open()` method
- `src/editor.py` line ~3118: `_open_template()` method (also affected)

---

## Bug Fix Tasks

### Fix 1: Update _menu_open() to use default_document_path

- [ ] BF001 Fix _menu_open() to use self._default_documents_path in QFileDialog.getOpenFileName() in src/editor.py
  - Current: `QFileDialog.getOpenFileName(..., "data", ...)`
  - Fixed: `QFileDialog.getOpenFileName(..., self._default_documents_path, ...)`
  - Ensure fallback to "data" if path is invalid

### Fix 2: Update _open_template() to use default_document_path

- [ ] BF002 Fix _open_template() to use self._default_documents_path instead of hardcoded path in src/editor.py
  - Current: `template_path = _BASE / "data" / "template.md"`
  - Consider: Should use self._default_documents_path + "template.md" OR keep "data" for templates?
  - Recommendation: Keep template loading from "data", but file dialog should use default_document_path

### Fix 3: Test profile selection file dialog

- [ ] BF003 Manual test: Select profile → Click "Open File" → Verify dialog opens to profile's default_document_path

---

## Implementation

### Code Change for BF001

File: `src/editor.py`, method `_menu_open()`

**Before**:
```python
def _menu_open(self) -> None:
    if not self._ask_save_if_dirty():
        return
    path, _ = QFileDialog.getOpenFileName(
        self,
        "Open File",
        "data",  # ← BUG: hardcoded
        "Supported files (*.md *.html *.htm);;Markdown (*.md);;HTML (*.html *.htm);;All Files (*)",
    )
    if path:
        self.open_file(path)
```

**After**:
```python
def _menu_open(self) -> None:
    if not self._ask_save_if_dirty():
        return
    # Use profile's default_document_path; fallback to "data" if not set
    default_dir = self._default_documents_path if self._default_documents_path else "data"
    path, _ = QFileDialog.getOpenFileName(
        self,
        "Open File",
        default_dir,  # ← FIXED: uses profile's default path
        "Supported files (*.md *.html *.htm);;Markdown (*.md);;HTML (*.html *.htm);;All Files (*)",
    )
    if path:
        self.open_file(path)
```

---

## Status

These are minimal bug fixes to unblock profile selection feature (US1).  
Once fixed, US1 (Profile Selection) will be fully functional and ready for testing.
