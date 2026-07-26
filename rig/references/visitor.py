from __future__ import annotations

from collections.abc import Iterator

from rig.references.index import ReferenceIndex
from rig.references.model import Reference, ResolvedReference, UnresolvedReference


def iter_references(index: ReferenceIndex) -> Iterator[Reference]:
    yield from index.references()


class ReferenceVisitor:
    """Base visitor over a ReferenceIndex. Subclass and override only the
    `visit_*` methods you care about. Future analyses (call graph, dependency
    analysis, dead code detection, rename refactoring, impact analysis,
    query execution) should consume references through this layer rather
    than traversing syntax trees directly.
    """

    def visit_index(self, index: ReferenceIndex) -> None:
        for reference in index.references():
            self.visit_reference(reference)

    def visit_reference(self, reference: Reference) -> None:
        if isinstance(reference, ResolvedReference):
            self.visit_resolved(reference)
        elif isinstance(reference, UnresolvedReference):
            self.visit_unresolved(reference)

    def visit_resolved(self, reference: ResolvedReference) -> None:
        pass

    def visit_unresolved(self, reference: UnresolvedReference) -> None:
        pass
