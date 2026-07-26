from __future__ import annotations

from rig.references.identifiers import reference_id


def test_reference_id_is_deterministic() -> None:
    assert reference_id("f1", "function", 10, 20) == reference_id("f1", "function", 10, 20)


def test_reference_id_differs_by_file() -> None:
    assert reference_id("f1", "function", 10, 20) != reference_id("f2", "function", 10, 20)


def test_reference_id_differs_by_kind() -> None:
    assert reference_id("f1", "function", 10, 20) != reference_id("f1", "type", 10, 20)


def test_reference_id_differs_by_byte_span() -> None:
    assert reference_id("f1", "function", 10, 20) != reference_id("f1", "function", 10, 21)


def test_reference_id_has_stable_prefix() -> None:
    assert reference_id("f1", "function", 10, 20).startswith("reference:")
