from __future__ import annotations

import threading
from collections.abc import Iterable, Mapping

from rig.types.diagnostics import TypeDiagnostic
from rig.types.model import Type, TypeKind


class DuplicateTypeError(ValueError):
    pass


class TypeIndex:
    """Thread-safe, repository-wide index of declared types.

    O(1) lookup by id, by symbol id, and by declaration id; O(1) amortized
    lookup by name (a dict of name -> type ids, since same-name types are
    tracked via diagnostics rather than rejected outright). Iteration is
    always sorted by id, so output is deterministic regardless of insertion
    order. Per-kind counts are maintained incrementally so `statistics()`
    stays O(1) regardless of index size.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._types: dict[str, Type] = {}
        self._by_name: dict[str, list[str]] = {}
        self._by_symbol: dict[str, str] = {}
        self._by_declaration: dict[str, str] = {}
        self._diagnostics: list[TypeDiagnostic] = []
        self._kind_counts: dict[TypeKind, int] = dict.fromkeys(TypeKind, 0)

    def add_type(self, type_: Type) -> None:
        with self._lock:
            if type_.id in self._types:
                raise DuplicateTypeError(f"type already present: {type_.id!r}")
            self._types[type_.id] = type_
            self._by_name.setdefault(type_.name, []).append(type_.id)
            self._by_symbol[type_.symbol_id] = type_.id
            self._by_declaration[type_.declaration_id] = type_.id
            self._kind_counts[type_.kind] += 1

    def add_diagnostic(self, diagnostic: TypeDiagnostic) -> None:
        with self._lock:
            self._diagnostics.append(diagnostic)

    def get(self, type_id: str) -> Type | None:
        return self._types.get(type_id)

    def by_name(self, name: str) -> tuple[Type, ...]:
        return self._sorted(self._by_name.get(name, ()))

    def by_symbol(self, symbol_id: str) -> Type | None:
        matched_id = self._by_symbol.get(symbol_id)
        return self._types.get(matched_id) if matched_id is not None else None

    def by_declaration(self, declaration_id: str) -> Type | None:
        matched_id = self._by_declaration.get(declaration_id)
        return self._types.get(matched_id) if matched_id is not None else None

    def types(self) -> tuple[Type, ...]:
        return self._sorted(self._types.keys())

    def diagnostics(self) -> tuple[TypeDiagnostic, ...]:
        return tuple(self._diagnostics)

    def statistics(self) -> Mapping[str, int]:
        return {
            "total_types": len(self._types),
            "structs": self._kind_counts[TypeKind.STRUCT],
            "interfaces": self._kind_counts[TypeKind.INTERFACE],
            "aliases": self._kind_counts[TypeKind.ALIAS],
            "named_types": self._kind_counts[TypeKind.NAMED],
        }

    def _sorted(self, type_ids: Iterable[str]) -> tuple[Type, ...]:
        return tuple(self._types[tid] for tid in sorted(type_ids))

    def __len__(self) -> int:
        return len(self._types)

    def __contains__(self, type_id: str) -> bool:
        return type_id in self._types
