"""FR-008 helper contract: absent tools yield visible skips with reasons, never passes.

A check whose support tool is unavailable must be reported as SKIPPED with an
explicit reason. These tests assert the guard behavior itself by simulating
absent tools (CI never has them absent, so the only way to pin the contract
is to force it).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.support import repo_files


def test_bash_absent_skips_with_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo_files, "_find_bash", lambda: None)
    with pytest.raises(pytest.skip.Exception, match="bash is not installed"):
        repo_files.bash_syntax_check("true")


def test_shellcheck_absent_skips_with_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo_files.shutil, "which", lambda name: None)
    with pytest.raises(pytest.skip.Exception, match="shellcheck is not installed"):
        repo_files.run_shellcheck([Path("scripts/build_doc.sh")])


def test_git_absent_skips_with_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo_files.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(OSError("no git")))
    with pytest.raises(pytest.skip.Exception, match="git unavailable"):
        repo_files.require_git()
