"""Shell script checks: syntax parsing and static lint for repo-authored scripts.

Every file in the automation-scripts inventory class (scripts/*.sh, the local
git hook entry, and the root-level operational script) must parse under
``bash -n`` — line endings normalized so CRLF checkouts on Windows cannot
false-fail — and pass shellcheck at the severity that covers spec FR-004's
defect classes: unquoted expansions, unset variable use, masked failures.
"""

from __future__ import annotations

from pathlib import Path

from tests.unit.support import repo_files
from tests.unit.support.repo_files import bash_syntax_check, inventory_class_files, run_shellcheck


def _scripts() -> list[Path]:
    scripts = inventory_class_files("automation-scripts")
    assert scripts, "no tracked shell scripts matched the inventory patterns"
    return scripts


def test_shell_scripts_are_syntactically_valid() -> None:
    """Each repo-authored shell script parses; the syntax check runs everywhere with bash."""
    for script in _scripts():
        result = bash_syntax_check(script.read_text(encoding="utf-8"))
        assert result.returncode == 0, (
            f"{script.relative_to(repo_files.REPO_ROOT)} has a shell syntax error "
            f"(bash -n) after line-ending normalization:\n{result.stderr}"
        )


def test_shell_scripts_pass_shellcheck() -> None:
    """Static analysis at the FR-004 defect severity fails naming file and finding.

    Each script is linted through its committed LF content (stdin), so a
    CRLF checkout on Windows cannot manufacture SC1017 noise; every verdict
    is tied to the file that produced it.
    """
    findings_by_file: list[str] = []
    for script, result in run_shellcheck(_scripts()):
        if result.returncode != 0:
            findings_by_file.append(f"{script}:\n{result.stdout.strip()}")
    assert not findings_by_file, (
        "shellcheck flagged repo-authored scripts (unquoted expansions, unset "
        "variable use, masked failures, or parse defects):\n\n" + "\n\n".join(findings_by_file)
    )
