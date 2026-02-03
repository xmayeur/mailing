# sendMail Documentation

This directory contains the Sphinx documentation for the sendMail project.

## Building the Documentation

### Prerequisites

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Build HTML Documentation

To build the HTML documentation locally:

```bash
cd docs
make html
```

The generated HTML files will be in `_build/html/`. Open `_build/html/index.html` in your browser to view the documentation.

### Other Build Formats

Sphinx supports multiple output formats:

- **HTML**: `make html` - Standard HTML documentation
- **PDF**: `make latexpdf` - PDF via LaTeX (requires LaTeX installation)
- **EPUB**: `make epub` - EPUB format for e-readers
- **Man pages**: `make man` - Unix manual pages
- **Plain text**: `make text` - Plain text output

### Clean Build

To remove all build artifacts:

```bash
make clean
```

## ReadTheDocs Theme

This documentation uses the [ReadTheDocs Sphinx Theme](https://sphinx-rtd-theme.readthedocs.io/), which provides:

- Responsive mobile-friendly design
- Clean, professional appearance
- Easy navigation with collapsible sidebar
- Search functionality
- Customizable theme options

## Configuration

The main configuration file is `conf.py`, which includes:

- Project metadata (name, author, version)
- Sphinx extensions (autodoc, napoleon, viewcode, etc.)
- Theme configuration and options
- Module mocking for dependencies

## Structure

- `index.rst` - Main documentation page
- `sendMail.rst` - sendMail module API reference
- `googleDriveLib.rst` - Google Drive library API reference
- `makeHtml.rst` - HTML utility documentation
- `decode_spam_cause.rst` - Spam detection utility documentation
- `conf.py` - Sphinx configuration
- `Makefile` - Build commands (Unix/Mac)
- `make.bat` - Build commands (Windows)

## ReadTheDocs Hosting

This project includes a `.readthedocs.yaml` configuration file in the repository root for hosting on ReadTheDocs.io. The configuration specifies:

- Python version (3.11)
- Ubuntu build environment
- Documentation requirements
- Sphinx configuration path

To host on ReadTheDocs:

1. Create an account at https://readthedocs.org/
2. Import your repository
3. The documentation will build automatically on each commit

## Viewing the Documentation

After building, open the documentation in your browser:

```bash
open _build/html/index.html  # macOS
xdg-open _build/html/index.html  # Linux
start _build/html/index.html  # Windows
```
