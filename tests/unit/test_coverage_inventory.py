"""FR-012 self-audit: the coverage inventory is valid, and every tracked
non-Python asset maps to a covered class or a documented exclusion.

This is the drift alarm: a new asset class that appears without a deliberate
cover-or-exclude decision fails the gate naming the file.
"""

from __future__ import annotations

from pathlib import Path

from tests.unit.support.repo_files import (
    REPO_ROOT,
    matches_any,
    require_git,
    strict_json_loads,
)

INVENTORY_PATH = Path(__file__).parent / "coverage_inventory.json"

# NOTE (T027 hardening): assertions here currently validate registry shape and
# file mapping only. Owning-test existence enforcement lands once every
# owning test module exists.


def load_inventory() -> dict:
    """Load the registry through the strict loader, so it gates itself."""
    return strict_json_loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def class_patterns(inventory: dict) -> list[str]:
    return [pattern for cls in inventory["classes"] for pattern in cls["patterns"]]


def exclusion_patterns(inventory: dict) -> list[str]:
    return [entry["pattern"] for entry in inventory["exclusions"]]


def test_registry_is_strictly_valid() -> None:
    inventory = load_inventory()
    assert inventory["version"] == "1"
    assert isinstance(inventory["classes"], list) and inventory["classes"] != []
    assert isinstance(inventory["exclusions"], list)


def test_classes_are_wellformed() -> None:
    inventory = load_inventory()
    ids = [cls["id"] for cls in inventory["classes"]]
    assert len(ids) == len(set(ids)), "duplicate class ids in coverage inventory"
    for cls in inventory["classes"]:
        assert cls["description"].strip(), f"class {cls['id']} lacks description"
        assert cls["patterns"], f"class {cls['id']} has no patterns"
        assert cls["defect_classes"], f"class {cls['id']} has no defect classes"
        assert cls["owning_test"].endswith(".py"), f"class {cls['id']} has no owning test"


def test_exclusions_carry_a_reason() -> None:
    inventory = load_inventory()
    patterns = [entry["pattern"] for entry in inventory["exclusions"]]
    assert len(patterns) == len(set(patterns)), "duplicate exclusion patterns"
    for entry in inventory["exclusions"]:
        assert entry["reason"].strip(), f"exclusion {entry['pattern']} lacks a reason"
        assert entry["family"].strip(), f"exclusion {entry['pattern']} lacks a family"


def test_every_tracked_non_python_file_is_covered_or_excluded() -> None:
    inventory = load_inventory()
    covered = class_patterns(inventory)
    excluded = exclusion_patterns(inventory)

    unclassified = sorted(
        rel
        for rel in require_git()
        if not rel.endswith(".py") and not matches_any(rel, covered) and not matches_any(rel, excluded)
    )
    assert not unclassified, (
        "tracked non-Python assets that no class covers and no exclusion documents "
        f"(add a cover-or-exclude decision to {INVENTORY_PATH.relative_to(REPO_ROOT)}):\n"
        + "\n".join(f"  {rel}" for rel in unclassified)
    )
