# Contract: Document Format (Markdown & HTML)

**Purpose**: Define the saved document format structure for editor files

**Location**: User-created files in document directories (e.g., `~/Documents/campaigns/`)

**Formats**: `.md` (Markdown) and `.html` (HTML export)

---

## Markdown Format (`.md`)

**Purpose**: Human-readable, version-control-friendly source format

**Structure**:
```markdown
---
# YAML Frontmatter (optional)
title: "Newsletter 2026-05-19"
profile_used: "cambristi"
created_at: "2026-05-19T14:30:00Z"
modified_at: "2026-05-19T15:45:00Z"
---

# Newsletter Title

Body text with **bold** and *italic*.

[Link text](https://example.com)

- Bullet point 1
- Bullet point 2

1. Numbered list item 1
2. Numbered list item 2

![Alt text](image.jpg)

---

## Section Title

More content below.
```

### Frontmatter Fields (Optional)

- `title` (str): Document title
- `profile_used` (str): Profile name at time of creation
- `created_at` (str): ISO 8601 timestamp when created
- `modified_at` (str): ISO 8601 timestamp of last save
- `custom_fields` (any): User-defined metadata (preserved in roundtrip)

### Markdown Syntax Supported

- Headings (`#`, `##`, etc.)
- Bold (`**text**`), Italic (`*text*`)
- Links (`[text](url)`)
- Images (`![alt](src)`)
- Lists (bullet `-` and numbered `1.`)
- Blockquotes (`> quote`)
- Horizontal rules (`---`)
- Code blocks (triple backticks)
- Inline code (backticks)

### Roundtrip Guarantee

- Editor reads `.md` → Quill Delta → User edits → Quill Delta → saves `.md`
- Markdown syntax preserved in roundtrip (WYSIWYG editor maintains structure)
- Hyperlinks preserved from paste operations in Delta format

---

## HTML Format (`.html`)

**Purpose**: Export format for sending/publishing; generated automatically on save

**Structure**:
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Newsletter 2026-05-19</title>
  <style>
    /* Quill Snow theme styles + inline styles */
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto; }
    a { color: #1e90ff; text-decoration: underline; }
    /* ... */
  </style>
</head>
<body>
  <h1>Newsletter Title</h1>
  <p>Body text with <strong>bold</strong> and <em>italic</em>.</p>
  <p><a href="https://example.com">Link text</a></p>
  <ul>
    <li>Bullet point 1</li>
    <li>Bullet point 2</li>
  </ul>
  <ol>
    <li>Numbered list item 1</li>
    <li>Numbered list item 2</li>
  </ol>
  <img src="image.jpg" alt="Alt text">
  <hr>
  <h2>Section Title</h2>
  <p>More content below.</p>
</body>
</html>
```

### HTML Specifications

- Doctype: HTML5
- Charset: UTF-8
- Responsive meta viewport
- Self-contained: All styles embedded (inline or `<style>`)
- Link preservation: `<a href="...">text</a>` for all hyperlinks
- Image handling: `<img src="...">` for inline images
- Class-free semantics: No CSS framework classes (for email compatibility)

### HTML Generation

- Source: Quill.js Delta format
- Conversion: Delta → HTML via Quill's HTML clipboard export + html2text
- Inline styles preserved from editor formatting
- External styles embedded (Quill Snow theme)

---

## Synchronization Contract

### On Editor Open (`python src/editor.py file.md`)

1. Read `.md` file
2. Parse YAML frontmatter (if present)
3. Extract markdown body
4. Convert markdown → Quill Delta
5. Load Delta into Quill editor
6. Display in editor UI

### On Editor Save (`File → Save` or Ctrl+S)

1. Extract Quill Delta from editor
2. Convert Delta → Markdown (body text)
3. Preserve/update YAML frontmatter (profile_used, modified_at)
4. Write `.md` file
5. Convert Delta → HTML
6. Write `.html` file

### File Naming Convention

- Both files share same base name: `document-name.md` and `document-name.html`
- Location: User-selected directory (respects `default_document_path` if profile set)
- No automatic filename generation; user chooses name in Save dialog

---

## Backward Compatibility

✓ Existing `.md` files without frontmatter remain valid  
✓ `.html` exports readable by email clients and browsers  
✓ Profile selection optional; editor works without it  
✓ No changes to document format when switching profiles  

---

## Link Preservation Guarantee

**Requirement**: Hyperlinks copied from external sources and pasted into editor are preserved through save/reload cycle

**Test Case**:
1. External source: `https://example.com` (link)
2. Copy → Paste into editor
3. Editor shows clickable link in WYSIWYG view
4. Save document
5. Read `.md`: Markdown link syntax present: `[example.com](https://example.com)`
6. Read `.html`: HTML link present: `<a href="https://example.com">example.com</a>`
7. Reopen `.md` in editor → Link remains clickable

**Result**: ✓ PASS if links survive all roundtrips (copy → paste → save → reload → view)

---

## Image Handling Contract

**Inline Images**: Base64-encoded in Delta for portability  
**External Images**: File path preserved as-is in `src` attribute  
**Relative Paths**: Supported (relative to document directory)

---

## Edge Cases

| Case | Behavior |
|------|----------|
| Paste URL without formatting | Auto-linkified to `[url](url)` in markdown |
| Paste HTML with multiple links | All links preserved in roundtrip |
| Edit link in WYSIWYG view | Link text and URL both editable |
| Delete link from middle of text | Text remains, link removed |
| Copy link, paste multiple times | Each paste creates separate link object |
| Large images (>5MB) | Embedded as base64 (editor may slow down) |
