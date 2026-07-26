from __future__ import annotations

from rig.types.identifiers import type_id


def test_type_id_is_deterministic() -> None:
    assert type_id("declaration:abc") == type_id("declaration:abc")


def test_type_id_differs_by_declaration() -> None:
    assert type_id("declaration:abc") != type_id("declaration:xyz")


def test_type_id_has_a_stable_prefix() -> None:
    assert type_id("declaration:abc").startswith("type:")
