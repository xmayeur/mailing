"""FR-012 self-audit: the coverage inventory is valid, and every tracked
non-Python asset maps to a covered class or a documented exclusion.

This is the drift alarm: a new asset class that appears without a deliberate
cover-or-exclude decision fails the gate naming the file.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.unit.support.repo_files import (
    REPO_ROOT,
    classify_tracked_file,
    inventory_class_files,
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

    unclassified = sorted(
        rel
        for rel in require_git()
        if not rel.endswith(".py") and classify_tracked_file(rel, inventory) == ("unclassified", "")
    )
    assert not unclassified, (
        "tracked non-Python assets that no class covers and no exclusion documents "
        f"(add a cover-or-exclude decision to {INVENTORY_PATH.relative_to(REPO_ROOT)}):\n"
        + "\n".join(f"  {rel}" for rel in unclassified)
    )


def test_exclusions_win_over_class_matches(tmp_path: Path) -> None:
    """FR-009 precedence: a file under an excluded tree is never a class asset (T025)."""
    registry = tmp_path / "inventory.json"
    registry.write_text(
        json.dumps(
            {
                "version": "1",
                "classes": [
                    {
                        "id": "declarative-configs",
                        "description": "x",
                        "patterns": ["*.json"],
                        "defect_classes": ["unparseable-content"],
                        "owning_test": "tests/unit/test_x.py",
                    }
                ],
                "exclusions": [{"pattern": "release/*", "family": "release-bundle", "reason": "FR-009"}],
            }
        ),
        encoding="utf-8",
    )
    inventory = strict_json_loads(registry.read_text(encoding="utf-8"))

    status, matched = classify_tracked_file("release/vendored/config.json", inventory)
    assert (status, matched) == ("excluded", "release/*")

    status, matched = classify_tracked_file("configs/own.json", inventory)
    assert (status, matched) == ("covered", "declarative-configs")

    status, _ = classify_tracked_file("mystery.xyz", inventory)
    assert status == "unclassified"


def test_class_enumeration_never_returns_excluded_files() -> None:
    """Every class enumeration is disjoint from the exclusion ledger (T025)."""
    exclusion_patterns = [entry["pattern"] for entry in load_inventory()["exclusions"]]
    for cls in load_inventory()["classes"]:
        for asset in inventory_class_files(cls["id"]):
            rel = asset.relative_to(REPO_ROOT).as_posix()
            assert not matches_any(rel, exclusion_patterns), (
                f"{rel} is listed in class {cls['id']} but matches exclusion patterns; "
                "exclusion precedence (FR-009) is broken"
            )


def test_shipped_vendor_classes_are_parse_or_existence_only() -> None:
    """Vendor semantics (T026): JS parse-checked, CSS existence-checked, never linted."""
    inventory = {cls["id"]: cls for cls in load_inventory()["classes"]}
    assert inventory["shipped-vendor-js"]["defect_classes"] == ["syntax-corruption"]
    assert inventory["shipped-vendor-css"]["defect_classes"] == ["missing-reference"]

    vendor_css = inventory_class_files("shipped-vendor-css")
    assert [f.name for f in vendor_css] == ["quill.snow.css"], "vendor stylesheet surface drifted"

    html = (REPO_ROOT / "src" / "editor_assets" / "editor.html").read_text(encoding="utf-8")
    vendor_assets = [f.name for f in inventory_class_files("shipped-vendor-js")]
    vendor_assets += [f.name for f in vendor_css]
    for asset in vendor_assets:
        assert f'"{asset}"' in html, f"editor.html no longer references shipped asset {asset}"
