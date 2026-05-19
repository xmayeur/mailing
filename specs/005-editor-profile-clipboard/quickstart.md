# Phase 1: Quick Start Implementation Guide

**Feature**: Editor Profile & Clipboard Enhancements  
**Branch**: `005-editor-profile-clipboard`  
**Reference**: [data-model.md](data-model.md) | [research.md](research.md)

---

## Overview

Three independent features, each testable standalone:

1. **Profile Selector** (P1): Dropdown in main window to select email profiles and auto-load default document path
2. **Hyperlink Preservation** (P1): Copy/paste with HTML link markup intact
3. **URL Auto-Linkify** (P2): Detect and linkify plain-text URLs on paste

---

## Feature 1: Profile Selector in Main Window

### What Gets Modified

**File**: `src/editor.py`

**Class**: `EditorWidget` (main editor window)

### Steps to Implement

1. **Load profiles on startup**:
   ```python
   from yaml import safe_load
   
   def load_profiles_from_config(config_path="config.yml"):
       """Load email profiles from config.yml"""
       with open(config_path) as f:
           config = safe_load(f)
       return config.get("profiles", {})
   ```

2. **Add profile dropdown to UI**:
   - Create `QComboBox` widget in main window toolbar
   - Populate with profile names from config
   - Position in toolbar (horizontal layout)
   - Connect to `on_profile_selected()` slot

3. **Handle profile selection**:
   ```python
   def on_profile_selected(self, profile_name):
       """Update active profile and file browser path"""
       self.active_profile = self.profiles[profile_name]
       default_path = self.active_profile.get("default_document_path")
       if default_path:
           # Set file browser root to default_path
           self.file_browser.setRootPath(default_path)
           self.file_browser.expand(self.file_browser.rootIndex())
       # Save session: self.save_editor_session()
   ```

4. **Persist profile selection**:
   ```python
   def save_editor_session(self):
       """Save active profile to .claude/editor-session.json"""
       session = {
           "active_profile_name": self.active_profile.get("name"),
           "active_profile_default_path": self.active_profile.get("default_document_path")
       }
       # Write to ~/.claude/editor-session.json
   
   def load_editor_session(self):
       """Restore active profile from session file"""
       # Read session file, restore active_profile
   ```

### Testing

- [ ] Dropdown shows all profiles from config.yml
- [ ] Selecting profile updates file browser path
- [ ] Profile persists across editor restart
- [ ] Works with profiles missing `default_document_path`
- [ ] Graceful fallback if path doesn't exist

---

## Feature 2: Hyperlink Preservation on Copy/Paste

### What Gets Modified

**File**: `editor_assets/editor.html` (Quill event handlers)  
**File**: `src/editor.py` (QWebChannel bridge)

### Steps to Implement

1. **Detect paste events with rich content**:
   ```javascript
   // In editor.html, hook Quill paste event:
   quill.on('text-change', function(delta, oldDelta, source) {
     if (source === 'user') {
       // Check clipboard for HTML content
       analyzeClipboardContent();
     }
   });
   
   async function analyzeClipboardContent() {
     try {
       // Try to read HTML from clipboard
       const html = await navigator.clipboard.read();
       for (let item of html) {
         if (item.types.includes('text/html')) {
           const blob = await item.getType('text/html');
           const htmlString = await blob.text();
           // Pass to Python for processing
           qtBridge.clipboardAnalyzed.emit('html_rich', true, []);
         }
       }
     } catch (e) {
       // Fallback: Let Quill handle native paste
     }
   }
   ```

2. **Leverage Quill native HTML paste**:
   - Quill v2 already converts HTML to Delta on paste
   - Link markup is preserved: `<a href="url">text</a>` → Delta with link attribute
   - No custom parsing needed; Quill handles it

3. **Test link preservation**:
   - Copy text with link from browser → Paste into editor
   - Verify link remains clickable in Quill view
   - Save document → Check `.md` has markdown link `[text](url)`
   - Reopen document → Link still clickable

### Testing

- [ ] Copy hyperlinked text from web page → Paste preserves link
- [ ] Copy mixed text + hyperlinks → All links preserved
- [ ] Save → Link appears as markdown in `.md` file
- [ ] Reopen → Link still functional in editor
- [ ] Paste already-linked content → No double conversion

---

## Feature 3: Auto-Linkify Plain-Text URLs

### What Gets Modified

**File**: `src/editor.py` (ClipboardProcessor class)

### Steps to Implement

1. **Create URL detection function**:
   ```python
   import re
   
   def detect_urls_in_text(text):
       """Find http(s)/ftp URLs in plain text"""
       url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+|ftp://[^\s<>"{}|\\^`\[\]]+'
       return re.findall(url_pattern, text)
   ```

2. **Analyze clipboard on paste**:
   ```python
   class ClipboardProcessor:
       def analyze_paste(self, raw_text, raw_html):
           """Determine content type and detect URLs"""
           if raw_html and '<a' in raw_html:
               # Already has links, don't linkify
               return {
                   'content_type': 'html_rich',
                   'has_urls': False,
                   'detected_urls': []
               }
           
           urls = detect_urls_in_text(raw_text)
           
           if urls and not self._is_markdown_link(raw_text):
               return {
                   'content_type': 'plain_text',
                   'has_urls': True,
                   'detected_urls': urls
               }
           
           return {
               'content_type': 'plain_text',
               'has_urls': False,
               'detected_urls': []
           }
       
       def _is_markdown_link(self, text):
           """Check if text already in markdown link format [text](url)"""
           return bool(re.search(r'\[.+\]\(.+\)', text))
   ```

3. **Handle linkification in Quill**:
   ```javascript
   // In editor.html paste handler:
   qtBridge.clipboardAnalyzed.connect((contentType, hasUrls, urlList) => {
     if (contentType === 'plain_text' && hasUrls && urlList.length > 0) {
       // Insert text with links
       insertTextWithLinks(pastedText, urlList);
     }
   });
   
   function insertTextWithLinks(text, urlList) {
     let index = 0;
     for (let url of urlList) {
       const urlIndex = text.indexOf(url, index);
       if (urlIndex !== -1) {
         // Insert text before URL
         quill.insertText(text.substring(index, urlIndex));
         // Insert URL as link
         quill.insertText(url, { link: url });
         index = urlIndex + url.length;
       }
     }
     // Insert remaining text
     quill.insertText(text.substring(index));
   }
   ```

### Testing

- [ ] Paste plain URL (e.g., https://example.com) → Becomes clickable link
- [ ] Paste multiple URLs → Each linkified separately
- [ ] Paste markdown-formatted link → Not double-converted
- [ ] Paste already-rich content with links → Links preserved as-is
- [ ] Save & reopen → Links remain functional

---

## Integration Points

### Profile → File Browser

```python
# EditorWidget main window
self.profile_selector.selectionChanged.connect(self.on_profile_selected)
# on_profile_selected updates file_browser root directory
```

### Paste → Document

```javascript
// Quill paste event → ClipboardProcessor → EditorPasteHandler → Quill Delta
quill.on('editor-change', (delta, oldDelta, source) => {
  if (source === 'user') {
    analyzeClipboard();  // → qtBridge.clipboardAnalyzed.emit(...)
  }
});
```

### Document Save → Session

```python
# When document saved
self.save_editor_session()
# Persists: active_profile_name, active_profile_default_path, active_document_path
```

---

## Development Checklist

- [ ] Load profiles from config.yml on startup
- [ ] Add profile selector QComboBox to toolbar
- [ ] Handle profile selection and update file browser
- [ ] Persist/restore profile selection across sessions
- [ ] Test rich paste with HTML links
- [ ] Implement URL detection regex
- [ ] Handle plain-text URL linkification
- [ ] Test roundtrip: paste → save → reload
- [ ] Verify markdown/HTML output formats
- [ ] Edge case: mixed content, broken links, missing paths
- [ ] Run pytest suite with new tests
- [ ] Manual testing in editor GUI

---

## Configuration Example

In `config.yml`, enable profile-specific document paths:

```yaml
profiles:
  cambristi:
    default_document_path: /Users/xavier/Documents/cambristi_campaigns
    smtp_host: smtp.gmail.com
    smtp_port: 587
    smtp_user: cambristi@example.com
    smtp_password: secret

  newsletter:
    default_document_path: ~/Dropbox/newsletters
    smtp_host: smtp.sendgrid.net
    smtp_port: 587
    smtp_user: sendgrid_user
    smtp_password: key_xyz
```

Editor automatically loads these paths and user can switch profiles via dropdown.

---

## Files Modified Summary

| File | Changes |
|------|---------|
| `src/editor.py` | Add ConfigLoader, ClipboardProcessor, EditorPasteHandler; extend EditorWidget with profile dropdown and session persistence |
| `editor_assets/editor.html` | Add paste event analysis, URL detection signals, link insertion logic |
| `config.yml` | Optional: Add `default_document_path` to profiles (backward compatible) |
| `.claude/editor-session.json` | New: Persist active profile between sessions |

**New classes**: ConfigLoader, ClipboardProcessor, ClipboardOperation, EditorPasteHandler  
**New dependencies**: None (yaml, re, json already available)

---

## Deployment Strategy

### Phase 1 (P1 features)
1. Implement profile selector (feature 1)
2. Ensure rich paste works (feature 2 is mostly native Quill)
3. Manual testing in editor GUI
4. Commit to branch

### Phase 2 (P2 feature - optional initial rollout)
5. Add URL auto-linkify (feature 3)
6. Test integration
7. Optional: Ship P1 first, iterate on P2

### Testing & Release
8. Run full pytest suite
9. Manual GUI testing on macOS/Windows
10. Create PR for review
