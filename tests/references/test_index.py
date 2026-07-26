from __future__ import annotations

from pathlib import Path

import pytest

from rig.ir.model import SourceLocation
from rig.references.diagnostics import ReferenceDiagnostic
from rig.references.index import DuplicateReferenceError, ReferenceIndex
from rig.references.model import ReferenceKind, ResolvedReference, UnresolvedReference


def _location() -> SourceLocation:
    return SourceLocation(
        relative_path=Path("a.go"), start_line=0, start_column=0, end_line=0, end_column=3
    )


def _resolved(rid: str, identifier: str, file_id: str, symbol_id: str) -> ResolvedReference:
    return ResolvedReference(
        id=rid,
        identifier=identifier,
        kind=ReferenceKind.FUNCTION,
        file_id=file_id,
        location=_location(),
        symbol_id=symbol_id,
    )


def test_add_and_get_reference() -> None:
    index = ReferenceIndex()
    reference = _resolved("r1", "Foo", "f1", "s1")

    index.add_reference(reference)

    assert index.get("r1") is reference


def test_get_missing_returns_none() -> None:
    index = ReferenceIndex()
    assert index.get("missing") is None


def test_duplicate_reference_id_raises() -> None:
    index = ReferenceIndex()
    index.add_reference(_resolved("r1", "Foo", "f1", "s1"))

    with pytest.raises(DuplicateReferenceError):
        index.add_reference(_resolved("r1", "Foo", "f1", "s1"))


def test_by_symbol_returns_all_references_to_that_symbol() -> None:
    index = ReferenceIndex()
    index.add_reference(_resolved("r1", "Foo", "f1", "s1"))
    index.add_reference(_resolved("r2", "Foo", "f2", "s1"))
    index.add_reference(_resolved("r3", "Bar", "f1", "s2"))

    results = index.by_symbol("s1")

    assert {r.id for r in results} == {"r1", "r2"}


def test_by_file_returns_all_references_in_that_file() -> None:
    index = ReferenceIndex()
    index.add_reference(_resolved("r1", "Foo", "f1", "s1"))
    index.add_reference(_resolved("r2", "Bar", "f1", "s2"))
    index.add_reference(_resolved("r3", "Baz", "f2", "s3"))

    results = index.by_file("f1")

    assert {r.id for r in results} == {"r1", "r2"}


def test_by_identifier_returns_all_matching_occurrences() -> None:
    index = ReferenceIndex()
    index.add_reference(_resolved("r1", "Foo", "f1", "s1"))
    index.add_reference(_resolved("r2", "Foo", "f2", "s1"))

    results = index.by_identifier("Foo")

    assert {r.id for r in results} == {"r1", "r2"}


def test_unresolved_reference_not_indexed_by_symbol() -> None:
    index = ReferenceIndex()
    index.add_reference(
        UnresolvedReference(
            id="r1",
            identifier="Foo",
            kind=ReferenceKind.FUNCTION,
            file_id="f1",
            location=_location(),
        )
    )

    assert index.by_symbol("anything") == ()
    assert index.by_file("f1")[0].id == "r1"


def test_references_are_sorted_by_id() -> None:
    index = ReferenceIndex()
    index.add_reference(_resolved("r2", "Bar", "f1", "s1"))
    index.add_reference(_resolved("r1", "Foo", "f1", "s1"))

    assert [r.id for r in index.references()] == ["r1", "r2"]


def test_diagnostics_accumulate() -> None:
    index = ReferenceIndex()
    diagnostic = ReferenceDiagnostic(message="unresolved reference to 'x'")

    index.add_diagnostic(diagnostic)

    assert index.diagnostics() == (diagnostic,)


def test_len_and_contains() -> None:
    index = ReferenceIndex()
    index.add_reference(_resolved("r1", "Foo", "f1", "s1"))

    assert len(index) == 1
    assert "r1" in index
    assert "missing" not in index


def test_empty_index() -> None:
    index = ReferenceIndex()

    assert len(index) == 0
    assert index.references() == ()
    assert index.diagnostics() == ()
    assert index.by_symbol("anything") == ()
    assert index.by_file("anything") == ()
    assert index.by_identifier("anything") == ()
