"""Structural tests for non-Python editor assets and CI workflow files.

The Python quality gates (black, ruff, vulture, pyright, mypy, flake8) and
SonarCloud all ignore src/editor_assets/ and .github/workflows/, so the
editor's inline JavaScript and the workflow YAML would otherwise be
completely unverified until a human opens the app or a push is made.
These tests keep that surface checked on every pytest run, including the
pre-commit hook.

Editor bundle consistency (spec FR-003): every local reference in
editor.html resolves, the structural components needed to bootstrap are
present exactly once, shipped-vendor scripts still parse, and the object
names the Python host registers for the Qt WebChannel match the names the
page consumes.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

from tests.unit.support.repo_files import inventory_class_files, strict_yaml_load

REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_HTML = REPO_ROOT / "src" / "editor_assets" / "editor.html"
HOST_EDITOR_PY = REPO_ROOT / "src" / "editor.py"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

EXTERNAL_PREFIXES = ("http:", "https:", "data:", "mailto:", "#")


def _editor_html() -> str:
    return EDITOR_HTML.read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_editor_html_javascript_is_syntactically_valid() -> None:
    """Every inline <script> block in editor.html must parse with node --check.

    Quill and qwebchannel load from external files; the editor bootstrap and
    all feature logic live in one big inline block. A malformed block (e.g.
    an unclosed handler or duplicated fixture) is what broke nothing at
    commit time yet would have crashed the editor at start-up.
    """
    html = _editor_html()
    inline_scripts = re.findall(r"<script>(.*?)</script>", html, re.DOTALL | re.IGNORECASE)
    assert inline_scripts, "editor.html contains no inline <script> block"

    with tempfile.TemporaryDirectory() as tmp:
        for idx, script in enumerate(inline_scripts):
            temp_file = Path(tmp) / f"editor_inline_{idx}.js"
            temp_file.write_text(script, encoding="utf-8")
            result = subprocess.run(
                ["node", "--check", str(temp_file)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, (
                f"inline <script> #{idx} in editor.html is not valid JavaScript:\n" f"{result.stderr}"
            )


def test_github_workflows_are_valid_yaml() -> None:
    """Every workflow file must be strictly parseable YAML.

    A malformed workflow either fails as a startup_failure in the Actions
    UI (easy to miss) or silently drops the intended run. Duplicate keys are
    ambiguous and fail too: a pasted step key would silently override its
    predecessor.
    """
    workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    assert workflow_files, "no workflow files found under .github/workflows"

    for workflow in workflow_files:
        try:
            strict_yaml_load(workflow.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise AssertionError(f"{workflow.name} is not valid YAML: {exc}") from exc


def test_editor_html_local_references_resolve() -> None:
    """Every local script/stylesheet referenced by the markup must exist (FR-003)."""
    html = _editor_html()
    tag_refs = re.findall(
        r"<(?:script|link|img)\b[^>]*?\b(?:src|href)=\"([^\"]+)\"",
        html,
        re.IGNORECASE,
    )
    local_refs = [ref for ref in tag_refs if not ref.strip().lower().startswith(EXTERNAL_PREFIXES)]
    assert local_refs, "editor.html references no local script/stylesheet assets"

    missing = [ref for ref in local_refs if not (EDITOR_HTML.parent / ref).is_file()]
    assert not missing, (
        f"{EDITOR_HTML.relative_to(REPO_ROOT)} references local assets that do not exist "
        f"in {EDITOR_HTML.parent.relative_to(REPO_ROOT)}: {', '.join(sorted(missing))}"
    )


def test_editor_html_bootstrap_components_present() -> None:
    """Structural components required for the editor to bootstrap exist exactly once."""
    html = _editor_html()

    for component_id in ("editor-container", "toolbar"):
        assert f'id="{component_id}"' in html, f"editor.html is missing bootstrap component #{component_id}"

    for init_marker, description in (
        ("new QWebChannel(qt.webChannelTransport", "Qt WebChannel bootstrap"),
        ("new Quill(", "Quill editor bootstrap"),
    ):
        occurrences = html.count(init_marker)
        assert occurrences == 1, (
            f"editor.html must contain exactly one {description} marker " f"({init_marker!r}); found {occurrences}"
        )


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_shipped_vendor_scripts_are_syntactically_valid() -> None:
    """Shipped-vendor scripts (quill, qwebchannel) must parse — corruption breaks start-up."""
    vendor_files = inventory_class_files("shipped-vendor-js")
    assert vendor_files, "no shipped vendor scripts matched src/editor_assets/*.js"

    for vendor in vendor_files:
        result = subprocess.run(
            ["node", "--check", str(vendor)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"{vendor.relative_to(REPO_ROOT)} is not valid JavaScript:\n{result.stderr}"


def test_editor_bridge_object_names_match_host_registration() -> None:
    """QWebChannel object names: what src/editor.py registers must match what the page uses.

    registerObject("bridge", ...) in the Python host pairs with
    channel.objects.bridge in the page's inline script; a rename on either
    side silently breaks the editor at start-up.
    """
    host_source = HOST_EDITOR_PY.read_text(encoding="utf-8")
    registered = set(re.findall(r"registerObject\(\s*[\"']([^\"']+)[\"']", host_source))
    assert registered, f"{HOST_EDITOR_PY.relative_to(REPO_ROOT)} registers no WebChannel objects"

    page_source = _editor_html()
    referenced = set(re.findall(r"channel\.objects\.([A-Za-z_][A-Za-z0-9_]*)", page_source))

    unregistered = referenced - registered
    unused = registered - referenced
    assert not unregistered and not unused, (
        "editor WebChannel object names diverge between src/editor.py and editor.html: "
        f"page references unregistered objects {sorted(unregistered)}; "
        f"host registers unreferenced objects {sorted(unused)}"
    )


_PASTE_SAFE_ATTRS_DECLARATION = re.compile(r"_PASTE_SAFE_ATTRS\s*=\s*\[(.*?)\]", re.DOTALL)
_ATTRIBUTE_NAME = re.compile(r"[\"']([^\"']+)[\"']")

# Security-reviewed paste attribute allowlist (CodeQL alert #18 analysis):
# constant-name presentation attributes only. `style` is accepted: it is CSS
# (inert for script execution in Qt WebEngine), the mail pipeline strips
# inline styles at send time for CSP, and inserted nodes still pass through
# Quill's clipboard converter. Any change to this set must re-open the
# js/xss review for the paste size-restore path.
REVIEWED_SAFE_PASTE_ATTRIBUTES = frozenset({"colspan", "rowspan", "width", "height", "align", "valign", "style"})
FORBIDDEN_PASTE_ATTRIBUTES = frozenset({"src", "href", "xlink:href", "srcdoc", "data"})


def test_paste_attribute_allowlist_is_locked() -> None:
    """The paste size-restore path may only copy reviewed, inert attributes.

    The paste handler parses clipboard HTML and copies attributes onto live
    editor nodes; CodeQL flags that taint flow (js/xss, alert #18) and the
    reviewed mitigation is this constant-name allowlist plus Quill's
    clipboard converter. This pin makes the allowlist a gate: adding any
    attribute — above all event handlers or URL-bearing ones — fails the
    suite until the security review is consciously repeated here.
    """
    html = _editor_html()
    declaration = _PASTE_SAFE_ATTRS_DECLARATION.search(html)
    assert declaration, "editor.html no longer declares _PASTE_SAFE_ATTRS"

    declared = frozenset(name.lower() for name in _ATTRIBUTE_NAME.findall(declaration.group(1)))
    assert declared == REVIEWED_SAFE_PASTE_ATTRIBUTES, (
        "the paste attribute allowlist in editor.html diverges from the "
        "security-reviewed set (CodeQL alert #18 review): "
        f"unexpected additions {sorted(declared - REVIEWED_SAFE_PASTE_ATTRIBUTES)}, "
        f"missing {sorted(REVIEWED_SAFE_PASTE_ATTRIBUTES - declared)}"
    )
    assert not declared & FORBIDDEN_PASTE_ATTRIBUTES and not any(
        name.startswith("on") for name in declared
    ), "the paste attribute allowlist must never contain URL-bearing or event-handler attributes"
    assert "_PASTE_SAFE_ATTRS.forEach" in html, (
        "_copyAttributes must copy attributes through the _PASTE_SAFE_ATTRS "
        "allowlist loop, not by iterating source attributes directly"
    )
