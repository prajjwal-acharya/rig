from __future__ import annotations

from pathlib import Path

from rig.ir.model import SourceLocation
from rig.references.index import ReferenceIndex
from rig.references.model import ReferenceKind, ResolvedReference, UnresolvedReference
from rig.references.visitor import ReferenceVisitor, iter_references


def _location() -> SourceLocation:
    return SourceLocation(
        relative_path=Path("a.go"), start_line=0, start_column=0, end_line=0, end_column=3
    )


def _index() -> ReferenceIndex:
    index = ReferenceIndex()
    index.add_reference(
        ResolvedReference(
            id="r1",
            identifier="Foo",
            kind=ReferenceKind.FUNCTION,
            file_id="f1",
            location=_location(),
            symbol_id="s1",
        )
    )
    index.add_reference(
        UnresolvedReference(
            id="r2",
            identifier="Bar",
            kind=ReferenceKind.VARIABLE,
            file_id="f1",
            location=_location(),
        )
    )
    return index


def test_iter_references_yields_every_reference() -> None:
    assert {r.id for r in iter_references(_index())} == {"r1", "r2"}


def test_base_visitor_is_a_safe_no_op() -> None:
    ReferenceVisitor().visit_index(_index())  # must not raise


class RecordingVisitor(ReferenceVisitor):
    def __init__(self) -> None:
        self.resolved: list[str] = []
        self.unresolved: list[str] = []

    def visit_resolved(self, reference: ResolvedReference) -> None:
        self.resolved.append(reference.identifier)

    def visit_unresolved(self, reference: UnresolvedReference) -> None:
        self.unresolved.append(reference.identifier)


def test_visitor_dispatches_resolved_and_unresolved_separately() -> None:
    visitor = RecordingVisitor()

    visitor.visit_index(_index())

    assert visitor.resolved == ["Foo"]
    assert visitor.unresolved == ["Bar"]
