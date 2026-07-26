from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from rig.ir.model import SourceLocation
from rig.references.model import ReferenceKind, ResolvedReference, UnresolvedReference


def _location() -> SourceLocation:
    return SourceLocation(
        relative_path=Path("a.go"), start_line=0, start_column=0, end_line=0, end_column=3
    )


def test_resolved_reference_holds_symbol_id() -> None:
    reference = ResolvedReference(
        id="r1",
        identifier="Foo",
        kind=ReferenceKind.FUNCTION,
        file_id="f1",
        location=_location(),
        symbol_id="symbol:function:abc",
    )

    assert reference.symbol_id == "symbol:function:abc"


def test_unresolved_reference_has_a_reason() -> None:
    reference = UnresolvedReference(
        id="r1", identifier="Foo", kind=ReferenceKind.FUNCTION, file_id="f1", location=_location()
    )

    assert reference.reason == "no matching declaration in scope"


def test_references_are_immutable() -> None:
    reference = UnresolvedReference(
        id="r1", identifier="Foo", kind=ReferenceKind.FUNCTION, file_id="f1", location=_location()
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        reference.identifier = "Bar"  # type: ignore[misc]


def test_reference_kind_has_expected_members() -> None:
    expected = {"type", "function", "variable", "constant", "package"}
    assert {member.value for member in ReferenceKind} == expected


def test_references_are_hashable() -> None:
    a = UnresolvedReference(
        id="r1", identifier="Foo", kind=ReferenceKind.FUNCTION, file_id="f1", location=_location()
    )
    b = UnresolvedReference(
        id="r1", identifier="Foo", kind=ReferenceKind.FUNCTION, file_id="f1", location=_location()
    )

    assert a == b
    assert hash(a) == hash(b)
