"""Helpers to enumerate tracked repository assets and validate them safely.

The non-Python checks operate on files git tracks, which matches the spec's
"tracked" scope exactly: `git ls-files` excludes untracked build output and
local experiments, and is available wherever the quality gates run (clone
based CI, local checkouts).

Skipping semantics (spec FR-008): when a support tool is unavailable, the
check that needs it is skipped with an explicit reason — never silently
passed. Hosted CI provides every tool, so nothing skips there.
"""

from __future__ import annotations

import fnmatch
import functools
import json
import shutil
import subprocess
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]

SHELL_TIMEOUT_S = 30
SHELLCHECK_TIMEOUT_S = 120

YamlNode = Any  # yaml typing is incomplete in the test environment


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


INVENTORY_PATH = REPO_ROOT / "tests" / "unit" / "coverage_inventory.json"


def inventory_class_files(class_id: str) -> list[Path]:
    """Tracked files of one inventory class, exclusions applied (FR-009)."""
    inventory = strict_json_loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    exclusions = [entry["pattern"] for entry in inventory["exclusions"]]
    for cls in inventory["classes"]:
        if cls["id"] == class_id:
            return tracked_files(*cls["patterns"], exclude=exclusions)
    raise LookupError(f"unknown coverage inventory class: {class_id}")


def classify_tracked_file(rel: str, inventory: dict) -> tuple[str, str]:
    """Classify one tracked file: exclusion precedence per FR-009.

    Returns ("excluded", pattern) — exclusions win over class matches — else
    ("covered", class_id), else ("unclassified", ""). New asset classes that
    appear without a cover-or-exclude decision land here, which the
    self-audit turns into a failure naming the file.
    """
    for entry in inventory["exclusions"]:
        if matches_any(rel, [entry["pattern"]]):
            return ("excluded", entry["pattern"])
    for cls in inventory["classes"]:
        if matches_any(rel, cls["patterns"]):
            return ("covered", cls["id"])
    return ("unclassified", "")


class _StrictSafeLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys at any level."""


def _strict_construct_mapping(loader: Any, node: YamlNode, deep: bool = False) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(None, None, f"duplicate mapping key {key!r}", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_StrictSafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_construct_mapping)


def strict_yaml_load(text: str) -> Any:
    """Parse YAML, failing on unparseable content and duplicate keys at any level."""
    return yaml.load(text, Loader=_StrictSafeLoader)


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key, value in pairs:
        if key in mapping:
            raise ValueError(f"duplicate mapping key {key!r}")
        mapping[key] = value
    return mapping


def strict_json_loads(text: str) -> Any:
    """Parse JSON, failing on unparseable content and duplicate keys at any level."""
    return json.loads(text, object_pairs_hook=_reject_duplicate_json_keys)


GIT_BASH_LOCATIONS = (
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files\Git\usr\bin\bash.exe",
    r"C:\Program Files (x86)\Git\bin\bash.exe",
)


@functools.lru_cache(maxsize=1)
def _find_bash() -> str | None:
    """Resolve a working bash executable, probing candidates.

    On GitHub Windows runners ``shutil.which("bash")`` resolves to
    ``C:\\Windows\\System32\\bash.exe`` — the WSL stub, which exits nonzero
    with "Windows Subsystem for Linux has no installed distributions" and
    cannot parse anything. Probing candidates and falling back to Git for
    Windows bash keeps the syntax check running on every CI platform
    (FR-008) instead of silently shipping broken results.
    """
    candidates: list[str] = []
    found = shutil.which("bash")
    if found:
        candidates.append(found)
    if sys.platform == "win32":
        candidates.extend(GIT_BASH_LOCATIONS)
    for candidate in dict.fromkeys(candidates):
        try:
            probe = subprocess.run(
                [candidate, "-c", "exit 0"],
                capture_output=True,
                timeout=SHELL_TIMEOUT_S,
            )
        except OSError:
            continue
        if probe.returncode == 0:
            return candidate
    return None


def bash_syntax_check(script_text: str) -> subprocess.CompletedProcess[str]:
    """Parse shell script text with ``bash -n`` on line endings normalized to LF.

    CI may check LF-committed scripts out with CRLF endings (Windows
    autocrlf), and ``bash -n`` on CRLF text reports spurious syntax errors.
    Normalizing validates the committed content, not the local checkout mode.
    """
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is not installed: cannot run shell syntax check")
    normalized = script_text.replace("\r\n", "\n")
    return subprocess.run(
        [bash, "-n"],
        input=normalized,
        capture_output=True,
        text=True,
        timeout=SHELL_TIMEOUT_S,
    )


def run_shellcheck(files: list[Path]) -> subprocess.CompletedProcess[str]:
    """Run shellcheck through its absolute executable path; skip when absent.

    The absolute path (from ``shutil.which``) bypasses Windows executable
    resolution quirks — PATH aliases and System32 stubs — so the lint check
    runs the exact binary the environment provides, with UTF-8 decoding of
    its findings. If the platform ever returns no captured streams the check
    fails loudly with the full result instead of masking a silent pass
    (FR-008 forbids silent passes).

    Severity is ``info`` or worse (error, warning, info; style excluded):
    unquoted expansions (SC2086) and masked assignments (SC2155) are
    classified as info in shellcheck, and FR-004 names them as required
    defect classes — warning-only severity would miss them.
    """
    executable = shutil.which("shellcheck")
    if executable is None:
        pytest.skip("shellcheck is not installed: cannot run shell lint check")
    if not files:
        pytest.skip("no tracked files matched the shell check patterns")
    result = subprocess.run(
        [executable, "--severity=info", *(str(f) for f in files)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=SHELLCHECK_TIMEOUT_S,
    )
    if result.stdout is None or result.stderr is None:
        pytest.fail(
            f"shellcheck produced no captured output streams (executable={executable!r}, "
            f"result={result!r}): refusing to pass silently"
        )
    return result
