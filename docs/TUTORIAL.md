# sendMail Editor Tutorial

Welcome to the sendMail Editor tutorial. This guide covers how to use the standalone WYSIWYG newsletter editor to create, edit, and manage HTML newsletters.

## Table of Contents

- [Getting Started](#getting-started)
- [Launching the Editor](#launching-the-editor)
- [Creating a New Newsletter](#creating-a-new-newsletter)
- [Opening Existing Documents](#opening-existing-documents)
- [Editing Content](#editing-content)
- [Working with Filters](#working-with-filters)
- [Managing Profiles](#managing-profiles)
- [Saving Your Work](#saving-your-work)
- [Sending via sendMail](#sending-via-sendmail)
- [Tips and Tricks](#tips-and-tricks)

## Getting Started

### Prerequisites

**For source installation:**
- Python 3.10 or later
- PySide6 and QtWebEngine (installed via the repository's dependencies)

**For pre-built executable:**
- No installation required, just download and run

### Installation

**Option 1: From source (development)**

```bash
git clone https://github.com/xmayeur/mailing.git
cd mailing
python src/editor.py
```

**Option 2: Pre-built executable (macOS/Windows)**

Download the latest `sendMailEditor` binary from [GitHub Releases](https://github.com/xmayeur/mailing/releases) and run it directly.

## Launching the Editor

### From Command Line

Launch a blank editor:

```bash
python src/editor.py
```

Open an existing file:

```bash
python src/editor.py path/to/your/newsletter.md
python src/editor.py path/to/your/newsletter.html
```

### Using the Standalone Binary (macOS/Windows)

Download from GitHub Releases and run:

```bash
# macOS
./sendMailEditor.app/Contents/MacOS/sendMailEditor

# Windows
sendMailEditor.exe
```

## Creating a New Newsletter

1. Launch the editor with no arguments
2. You'll see a blank document with the rich text editor in the center
3. Start typing or paste content into the editor
4. Use the formatting toolbar to style your text:
   - **Bold**, *Italic*, ~~Strikethrough~~
   - Heading sizes (H1, H2, H3, etc.)
   - Lists (bullet and numbered)
   - Links and images
   - Blockquotes
   - Code blocks

## Opening Existing Documents

The editor can open both Markdown and HTML files for editing:

```bash
# Open a Markdown file for editing
python src/editor.py newsletters/2026-05-17.md

# Open an HTML file for editing
python src/editor.py newsletters/template.html
```

The editor automatically detects the format and renders it in the rich text editor. You can make changes and save as HTML.

## Editing Content

### Text Formatting

Use the Quill editor toolbar to format text:

1. **Emphasis**: Select text and click Bold (B) or Italic (I)
2. **Headings**: Select text and choose heading size from dropdown
3. **Lists**: Click the bullet list or number list button
4. **Links**: Select text, click the link button, enter URL
5. **Images**: Click the image button and choose from your computer

### Inserting Images

1. Click the image button in the toolbar
2. Select an image from your computer
3. The image is automatically embedded as base64 for HTML export

### HTML Preview

The editor shows a live preview of the generated HTML. This helps you see how the newsletter will look when sent.

## Working with Filters

The editor includes advanced filtering capabilities for conditional content delivery.

### Opening the Send Dialog

1. Click **File** → **Send...** or use Ctrl+Enter (or Cmd+Enter on macOS)
2. This opens the Send Dialog with filter options
3. The dialog shows your current sendMail profiles

Note: Ctrl+S (Cmd+S) saves the newsletter; it does not open the send dialog.

### Setting Up Filters

The send dialog uses a **visual filter builder**: each filter row is a
combination of a field dropdown, an operator dropdown, and a value input.

1. Click **Add Row** to add a filter row
2. Pick a **field** from the dropdown (populated from your database schema)
3. Pick an **operator** (e.g. *is equal to*, *is not empty*, *one of*)
4. Enter the expected **value** (a larger text box appears for list operators)
5. Click **Apply Filter** to activate the filter
6. Click **Reset Filter** to fall back to the profile's configured filter
7. The editor validates the filter in real-time; a status line under the
   builder shows errors (red) or validity (green)

When the **Test** checkbox is enabled, the dialog edits the profile's
`filter_test` rules instead of `filter`.

### Database Preview

1. Enter a subscriber database path (CSV or Excel) via the **Database**
   **Browse** button, or leave it empty to use the profile's Google Sheets
2. Matching records load automatically (a **Retry** button appears if loading fails)
3. The editor shows matching records based on your filter
4. See exactly which subscribers will receive the filtered content

### Valid Filter Fields

Filter fields depend on your subscriber database schema. Common fields include:

- `country`
- `email`
- `subscription_level`
- `name`
- Custom fields from your CSV/Google Sheets

## Managing Profiles

### Adding sendMail Profiles

The editor reads profiles from your `config.yml`. Each top-level key is a
profile name:

```yaml
newsletter:
  sender: newsletters@example.com
  sendername: "Example Newsletters"
  max_mails_per_hour: 100
  filter:
    subscription_level: premium
```

### Selecting a Profile

1. Open the Send Dialog (File → Send...)
2. The **Profile** dropdown shows all available profiles
3. Select the profile to use for sending
4. The filter fields are validated against that profile's database

### Profile Configuration

Profiles are managed in your sendMail configuration file:

```bash
# Edit your configuration
python src/editor.py
# Then: Settings → Edit Config...
```

## Saving Your Work

The editor saves your content as **HTML files**, ready for sending with sendMail.

### HTML Format

The output format includes:

- Rendered HTML markup
- Embedded images as base64
- Styling and formatting preserved
- Complete `<!DOCTYPE>` document with stylesheet

### Save Behavior

1. **New documents**: Save with your chosen filename

   ```bash
   # File → Save As, choose name and location
   # Creates: newsletters/my-newsletter.html
   ```

2. **Existing documents**: Updated in place when you save

### Manual Save

Use **File** → **Save** (Ctrl+S / Cmd+S) to save current edits, or **File** → **Save As** (Ctrl+Shift+S) to save with a new filename.

## Sending via sendMail

Once your newsletter is ready:

1. **Save the newsletter** in the editor
2. **Note the HTML file path** (e.g., `newsletters/2026-05-17.html`)
3. **Send via sendMail**:

```bash
python src/sendMail.py --profile newsletter \
  -s "May Newsletter 2026" \
  newsletters/2026-05-17.html
```

### With Filters

Filters are not passed on the command line. They come either from the
profile's `filter` key in `config.yml`, or from a filter applied in the
editor's Send Dialog. To send to a filtered group:

1. Set the filter in `config.yml` (profile `filter` key), or set it in the
   editor's Send Dialog before sending
2. Send as usual:

```bash
python src/sendMail.py --profile newsletter \
  -s "Premium Subscribers Newsletter" \
  newsletters/2026-05-17.html
```

Use `-t` to send in test mode (applies the profile's `filter_test` rules):

```bash
python src/sendMail.py --profile newsletter -t \
  -s "Test Send" \
  newsletters/2026-05-17.html
```

### Using Database Preview Filter

1. Set up the filter in the editor's Send Dialog and click **Apply Filter**
2. The preview shows exactly which records match
3. Send directly from the dialog — the applied filter is used for the send

## Tips and Tricks

### Templates

Create reusable newsletter templates:

```bash
# Create a template and save it
python src/editor.py
# Edit content and save as: templates/base-newsletter.html

# Create new newsletter from template
cp templates/base-newsletter.html newsletters/2026-05-20.html
python src/editor.py newsletters/2026-05-20.html
```

### Batch Processing

For recurring newsletters:

```bash
# Create a weekly newsletter (save as HTML when done)
python src/editor.py

# Send when ready (use the saved HTML file)
python src/sendMail.py --profile newsletter \
  -s "Weekly Update" \
  newsletters/weekly-$(date +%Y-%m-%d).html
```

### Filter Testing

Before sending to your full list:

1. Create a test filter in the editor and use database preview to see matching records
2. Configure the profile's `filter_test` rules in `config.yml`
3. Test with a small group first:

```bash
python src/sendMail.py --profile newsletter \
  -s "Test Newsletter" \
  -t \
  newsletters/test.html
```

### Image Best Practices

1. **Size appropriately**: Compress images before inserting
2. **Alt text**: Always provide alt text for accessibility
3. **Responsive**: The editor scales images to fit email widths
4. **Test rendering**: Preview in the HTML pane before sending

### Markdown Tips

The editor supports full GitHub-flavored Markdown:

- Tables
- Code blocks with syntax highlighting
- Links and references
- Inline HTML (for advanced formatting)

### Google Sheets Integration

To use Google Sheets for subscriber lists:

1. Set up Google Sheets credentials in sendMail config
2. In the editor, select your Google Sheets database
3. Use database preview to verify filters work correctly

## Common Tasks

### Create and Send a Simple Newsletter

```bash
# 1. Create new newsletter in the editor
python src/editor.py

# 2. Edit content in the GUI and save as newsletters/announcement.html

# 3. Send to all subscribers
python src/sendMail.py --profile default \
  -s "Important Announcement" \
  newsletters/announcement.html
```

### Send to Filtered Group

```bash
# 1. Create and edit newsletter, save as newsletters/premium-offer.html

# 2. Set up filter in editor's Send Dialog (or in the profile's
#    "filter" key in config.yml)
# Filter: subscription_level is equal to premium

# 3. Test with preview
# (Verify matching records in database preview)

# 4. Send to filtered group
python src/sendMail.py --profile default \
  -s "Exclusive Premium Offer" \
  newsletters/premium-offer.html
```

### Create Newsletter from Template

```bash
# Copy template
cp templates/newsletter-template.html newsletters/2026-05-18.html

# Open in editor
python src/editor.py newsletters/2026-05-18.html

# Customize content and save, then send
python src/sendMail.py --profile newsletter \
  -s "Weekly Newsletter" \
  newsletters/2026-05-18.html
```

## Troubleshooting

### Editor Won't Launch

- Verify PySide6 is installed (it comes with the repository's dependencies)
- Check Python version: `python --version` (requires 3.10+)
- On Linux without display: Use xvfb or set `QT_QPA_PLATFORM=offscreen`

### Filter Not Validating

- Pick field names from the dropdown so they match your database schema
- Check the error message shown under the filter builder
- Operators requiring a value must have one (e.g. *is equal to*)
- For `filter`/`filter_test` keys edited in config.yml, check YAML syntax
  (proper indentation with spaces, not tabs)

### Images Not Embedding

- Check image file path is correct
- Large images may be scaled down for email compatibility
- Some email clients strip images - always provide alt text

### sendMail Command Not Found

- Ensure sendMail is installed: `pip install sendMail`
- Or use full path: `python src/sendMail.py`

## See Also

- [sendMail Main Documentation](../README.md)
- [Profiles Configuration Guide](PROFILES.md)
