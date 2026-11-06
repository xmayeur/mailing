"""Structural checks for first-party stylesheets (spec FR-006).

A stripped or hand-mangled stylesheet can silently degrade the editor UI.
The check walks a payload where comments, strings, and url() spans are
removed first, so braces that appear inside content values (for example
``content: "}"``) cannot produce false positives; then rule-block braces
must open and close in order and balance at end of file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.support.repo_files import REPO_ROOT, inventory_class_files

STYLESHEETS = inventory_class_files("first-party-css")


def _payload(text: str) -> str:
    """Remove comments, quoted strings, and url() spans (r = replacement-free tokens)."""
    out: list[str] = []
    i = 0
    length = len(text)
    while i < length:
        char = text[i]
        if char == "/" and text[i : i + 2] == "/*":
            end = text.find("*/", i + 2)
            i = length if end < 0 else end + 2
        elif char in {"'", '"'}:
            quote = char
            i += 1
            while i < length and text[i] != quote:
                i += 2 if text[i] == "\\" else 1
            i += 1
        elif text[i : i + 4].lower() == "url(":
            end = text.find(")", i)
            i = length if end < 0 else end + 1
        else:
            out.append(char)
            i += 1
    return "".join(out)


def _brace_error(payload: str) -> tuple[int, int] | None:
    """Return (line, depth) of an imbalance, or None if rule blocks balance."""
    depth = 0
    for idx, char in enumerate(payload):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                line = payload.count("\n", 0, idx) + 1
                return (line, depth)
    if depth != 0:
        return (payload.count("\n") + 1, depth)
    return None


def test_first_party_stylesheets_exist() -> None:
    """Sanity: the inventory enumerates the stylesheet surface, not nothing."""
    assert STYLESHEETS, "no tracked first-party stylesheets matched the inventory patterns"


@pytest.mark.parametrize(
    "stylesheet",
    STYLESHEETS,
    ids=lambda s: str(s.relative_to(REPO_ROOT)),
)
def test_stylesheet_rule_blocks_balance(stylesheet: Path) -> None:
    """Rule braces open and close in order and balance at end of file."""
    rel = stylesheet.relative_to(REPO_ROOT)
    payload = _payload(stylesheet.read_text(encoding="utf-8"))
    error = _brace_error(payload)
    assert error is None, (
        f"{rel} has unbalanced rule blocks "
        f"(line {error[0]}, brace depth {error[1]}); the file may be truncated or stripped"
    )
