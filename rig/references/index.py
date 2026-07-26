from __future__ import annotations

import threading
from collections.abc import Iterable

from rig.references.diagnostics import ReferenceDiagnostic
from rig.references.model import Reference, ResolvedReference


class DuplicateReferenceError(ValueError):
    pass


class ReferenceIndex:
    """Thread-safe, repository-wide index of references.

    O(1) lookup by id, and O(1) amortized lookup by symbol/file/identifier
    (each backed by its own dict of reference ids, built incrementally as
    references are added). Iteration is always sorted by id, so output is
    deterministic regardless of insertion order.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._references: dict[str, Reference] = {}
        self._by_symbol: dict[str, list[str]] = {}
        self._by_file: dict[str, list[str]] = {}
        self._by_identifier: dict[str, list[str]] = {}
        self._diagnostics: list[ReferenceDiagnostic] = []

    def add_reference(self, reference: Reference) -> None:
        with self._lock:
            if reference.id in self._references:
                raise DuplicateReferenceError(f"reference already present: {reference.id!r}")
            self._references[reference.id] = reference
            self._by_file.setdefault(reference.file_id, []).append(reference.id)
            self._by_identifier.setdefault(reference.identifier, []).append(reference.id)
            if isinstance(reference, ResolvedReference):
                self._by_symbol.setdefault(reference.symbol_id, []).append(reference.id)

    def add_diagnostic(self, diagnostic: ReferenceDiagnostic) -> None:
        with self._lock:
            self._diagnostics.append(diagnostic)

    def get(self, reference_id: str) -> Reference | None:
        return self._references.get(reference_id)

    def by_symbol(self, symbol_id: str) -> tuple[Reference, ...]:
        return self._sorted(self._by_symbol.get(symbol_id, ()))

    def by_file(self, file_id: str) -> tuple[Reference, ...]:
        return self._sorted(self._by_file.get(file_id, ()))

    def by_identifier(self, identifier: str) -> tuple[Reference, ...]:
        return self._sorted(self._by_identifier.get(identifier, ()))

    def references(self) -> tuple[Reference, ...]:
        return self._sorted(self._references.keys())

    def diagnostics(self) -> tuple[ReferenceDiagnostic, ...]:
        return tuple(self._diagnostics)

    def _sorted(self, reference_ids: Iterable[str]) -> tuple[Reference, ...]:
        return tuple(self._references[rid] for rid in sorted(reference_ids))

    def __len__(self) -> int:
        return len(self._references)

    def __contains__(self, reference_id: str) -> bool:
        return reference_id in self._references
