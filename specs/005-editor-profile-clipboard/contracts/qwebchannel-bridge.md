# Contract: QWebChannel Bridge Interface

**Purpose**: Define the JavaScript ↔ Python communication interface for clipboard and editor events

**Format**: JSON RPC-style calls via PyQt6 QWebChannel

**Location**: 
- Python side: `src/editor.py` (EditorWidget class)
- JavaScript side: `editor_assets/editor.html` + Quill initialization

## Python → JavaScript Signals

### `qtBridge.profileChanged(profile_name, document_path)`

**Purpose**: Notify editor that active profile has changed

**Signature**:
```python
# Python emits:
qtBridge.profileChanged.emit(profile_name="cambristi", document_path="/path/to/docs")
```

**JavaScript handling** (in editor.html):
```javascript
// Receive profile change notification
window.qtBridge.profileChanged.connect((profileName, docPath) => {
  console.log(`Profile changed to: ${profileName} at ${docPath}`);
  // Update editor UI if needed (optional)
  updateEditorProfile(profileName);
});
```

**Parameters**:
- `profile_name` (str): Name of selected profile (e.g., "cambristi")
- `document_path` (str): default_document_path for that profile (may be empty if not set)

---

## JavaScript → Python Slots

### `qtBridge.pasteDetected()`

**Purpose**: Notify Python when user pastes content; Python processes clipboard

**Current behavior** (existing): Signal fired on Ctrl+V in Quill editor

**Enhancement for this feature**: Include clipboard analysis
```javascript
// Existing in editor.html - no change to slot name
quill.on('selection-change', function(range, oldRange, source) {
  if (source === 'user') {
    // Existing: qtBridge.textChanged(delta_string);
    // New: Also analyze clipboard on paste
    analyzeClipboard();
  }
});

function analyzeClipboard() {
  // JavaScript can read text/plain from clipboard via Clipboard API
  // Send analysis results to Python via new slot
  navigator.clipboard.readText().then(text => {
    qtBridge.clipboardTextAvailable.emit(text);
  }).catch(() => {
    // Fallback: Python handles clipboard via PyQt6 QClipboard
  });
}
```

### `qtBridge.clipboardAnalyzed(content_type, has_urls, url_list)`

**Purpose**: Pass clipboard analysis results from Python back to JavaScript for URL linkification

**Signature**:
```python
# Python analyzes and emits:
qtBridge.clipboardAnalyzed.emit(
  content_type="plain_text",
  has_urls=True,
  url_list=["https://example.com", "https://docs.python.org"]
)
```

**JavaScript handling**:
```javascript
window.qtBridge.clipboardAnalyzed.connect((contentType, hasUrls, urlList) => {
  if (contentType === 'plain_text' && hasUrls) {
    // Insert pasted text with URLs already linkified
    insertPastedTextWithLinks(urlList);
  } else if (contentType === 'html_rich') {
    // Quill handles HTML paste natively - no action needed
  } else {
    // Plain text without URLs - insert as-is
    insertPlainText();
  }
});
```

---

## Clipboard Analysis Contract

### Input: Raw Clipboard Data

**Source**: PyQt6 QClipboard or JavaScript Clipboard API

**Contents**:
- `text` (str): Plain text content
- `html` (str | None): HTML format (if available)
- `mime_type` (str): Content-Type (e.g., "text/html", "text/plain")

### Output: Clipboard Analysis Result

```json
{
  "content_type": "html_rich",  // One of: html_rich, plain_text, markdown
  "has_urls": true,
  "detected_urls": [
    "https://example.com",
    "https://docs.example.org/api"
  ],
  "has_existing_links": true,
  "raw_html": "<p>Check <a href=\"https://example.com\">this link</a></p>",
  "raw_text": "Check this link https://example.com"
}
```

**Fields**:
- `content_type` (str): "html_rich" | "plain_text" | "markdown"
- `has_urls` (bool): Plain-text URLs detected
- `detected_urls` (list[str]): Parsed URLs from content
- `has_existing_links` (bool): HTML link markup present
- `raw_html` (str | null): Original HTML if available
- `raw_text` (str): Plain text version

---

## URL Detection Algorithm

**Regex Pattern**:
```regex
https?://[^\s<>"{}|\\^`\[\]]+
ftp://[^\s<>"{}|\\^`\[\]]+
```

**Detection Strategy**:
1. Extract plain text from clipboard
2. Apply regex to find URLs starting with http://, https://, ftp://
3. Return list of matched URLs
4. Only apply linkification if content_type == "plain_text" AND no existing HTML links

**Edge Cases Handled**:
- Multiple URLs in single paste: All detected and linkified individually
- URLs at end of text (no trailing space): Handled by regex
- Markdown link syntax `[text](url)`: Not linkified (already a link)
- HTML link already present: Not double-converted

---

## Error Handling

**Python → JavaScript**:
- If clipboard read fails: Silent fallback to Quill native paste
- If URL detection errors: Log warning, insert content as-is

**JavaScript → Python**:
- If paste event timing fails: Quill's native paste handler takes over
- If Clipboard API unavailable: Use QMimeData from Qt

---

## Backward Compatibility

✓ Existing editor.html and editor.py functionality unchanged  
✓ New signals don't break existing slot connections  
✓ Profile change notifications optional (editor works without them)  
✓ Clipboard analysis failures degrade gracefully to native Quill paste  
