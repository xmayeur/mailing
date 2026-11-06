"""Helpers to enumerate tracked repository assets.

The non-Python checks operate on files git tracks, which matches the spec's
"tracked" scope exactly: `git ls-files` excludes untracked build output and
local experiments, and is available wherever the quality gates run (clone
based CI, local checkouts).
"""

from __future__ import annotations

import fnmatch
import subprocess
from collections.abc import Iterable, Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def _git_ls_files() -> Iterator[str]:
    """Yield tracked, repo-relative POSIX paths; yield nothing when git cannot run."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=True,
            timeout=30,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return
    yield from (rel for rel in result.stdout.decode("utf-8").split("\0") if rel)


def require_git() -> list[str]:
    """Return tracked files, or skip the calling test with a reason when git cannot run."""
    files = list(_git_ls_files())
    if not files:
        pytest.skip("git unavailable or not a git repository: cannot enumerate tracked files")
    return files


def matches_any(path: str, patterns: Iterable[str]) -> bool:
    """fnmatch a repo-relative POSIX path against patterns (``*`` spans directories)."""
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def tracked_files(*patterns: str, exclude: Iterable[str] = ()) -> list[Path]:
    """Tracked files matching any pattern, minus exclusions, as absolute paths."""
    excluded = tuple(exclude)
    return [REPO_ROOT / rel for rel in require_git() if matches_any(rel, patterns) and not matches_any(rel, excluded)]
