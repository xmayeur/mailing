"""Structural tests for non-Python editor assets and CI workflow files.

The Python quality gates (black, ruff, vulture, pyright, mypy, flake8) and
SonarCloud all ignore src/editor_assets/ and .github/workflows/, so the
editor's inline JavaScript and the workflow YAML would otherwise be
completely unverified until a human opens the app or a push is made.
These tests keep that surface syntactically checked on every pytest run,
including the pre-commit hook.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_HTML = REPO_ROOT / "src" / "editor_assets" / "editor.html"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_editor_html_javascript_is_syntactically_valid() -> None:
    """Every inline <script> block in editor.html must parse with node --check.

    Quill and qwebchannel load from external files; the editor bootstrap and
    all feature logic live in one big inline block. A malformed block (e.g.
    an unclosed handler or duplicated fixture) is what broke nothing at
    commit time yet would have crashed the editor at start-up.
    """
    html = EDITOR_HTML.read_text(encoding="utf-8")
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
    """Every workflow file must be parseable YAML, not just well-indented text.

    A malformed workflow either fails as a startup_failure in the Actions
    UI (easy to miss) or silently drops the intended run.
    """
    workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    assert workflow_files, "no workflow files found under .github/workflows"

    for workflow in workflow_files:
        try:
            yaml.safe_load(workflow.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise AssertionError(f"{workflow.name} is not valid YAML: {exc}") from exc
