from __future__ import annotations

import pytest

from rig.types.diagnostics import TypeDiagnostic
from rig.types.index import DuplicateTypeError, TypeIndex
from rig.types.model import InterfaceType, StructType
from tests.types.conftest import location


def _struct(name: str = "Widget", *, tid: str = "type:1") -> StructType:
    return StructType(
        id=tid,
        declaration_id=f"declaration:{tid}",
        symbol_id=f"symbol:{tid}",
        name=name,
        package="pkg1",
        location=location(),
    )


def test_add_and_get() -> None:
    index = TypeIndex()
    type_ = _struct()

    index.add_type(type_)

    assert index.get(type_.id) is type_
    assert type_.id in index
    assert len(index) == 1


def test_get_missing_returns_none() -> None:
    index = TypeIndex()

    assert index.get("missing") is None


def test_duplicate_id_raises() -> None:
    index = TypeIndex()
    index.add_type(_struct(tid="type:1"))

    with pytest.raises(DuplicateTypeError):
        index.add_type(_struct(tid="type:1"))


def test_by_name_returns_all_matches_sorted_by_id() -> None:
    index = TypeIndex()
    index.add_type(_struct("Widget", tid="type:2"))
    index.add_type(_struct("Widget", tid="type:1"))

    matches = index.by_name("Widget")

    assert [t.id for t in matches] == ["type:1", "type:2"]


def test_by_name_missing_returns_empty_tuple() -> None:
    index = TypeIndex()

    assert index.by_name("Missing") == ()


def test_by_symbol_lookup() -> None:
    index = TypeIndex()
    type_ = _struct()
    index.add_type(type_)

    assert index.by_symbol(type_.symbol_id) is type_
    assert index.by_symbol("missing") is None


def test_by_declaration_lookup() -> None:
    index = TypeIndex()
    type_ = _struct()
    index.add_type(type_)

    assert index.by_declaration(type_.declaration_id) is type_
    assert index.by_declaration("missing") is None


def test_types_are_iterated_in_deterministic_id_order() -> None:
    index = TypeIndex()
    index.add_type(_struct("B", tid="type:2"))
    index.add_type(_struct("A", tid="type:1"))

    assert [t.id for t in index.types()] == ["type:1", "type:2"]


def test_diagnostics_accumulate() -> None:
    index = TypeIndex()
    diagnostic = TypeDiagnostic(message="duplicate type")

    index.add_diagnostic(diagnostic)

    assert index.diagnostics() == (diagnostic,)


def test_statistics_counts_by_kind() -> None:
    index = TypeIndex()
    index.add_type(_struct(tid="type:1"))
    index.add_type(
        InterfaceType(
            id="type:2",
            declaration_id="declaration:2",
            symbol_id="symbol:2",
            name="Shape",
            package="pkg1",
            location=location(),
        )
    )

    stats = index.statistics()

    assert stats["total_types"] == 2
    assert stats["structs"] == 1
    assert stats["interfaces"] == 1
    assert stats["aliases"] == 0
    assert stats["named_types"] == 0


def test_empty_index() -> None:
    index = TypeIndex()

    assert len(index) == 0
    assert index.types() == ()
    assert index.diagnostics() == ()
    assert index.statistics()["total_types"] == 0
