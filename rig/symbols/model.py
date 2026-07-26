from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# Symbol identity is deliberately its own namespace: a Symbol's `id` is never
# a graph node id and never an IR declaration id, even though it is derived
# from one. Today a graph Node happens to reuse a Declaration's id directly,
# so "reuse graph ids" would silently mean "reuse declaration ids" too - this
# model avoids that conflation so a future "graph node -> symbol" pointer is
# never confused with "this symbol's own identity".


class SymbolKind(str, Enum):
    PACKAGE = "package"
    FUNCTION = "function"
    TYPE = "type"
    VARIABLE = "variable"
    CONSTANT = "constant"


@dataclass(frozen=True, kw_only=True)
class Symbol:
    # Common base for all symbol kinds below - not instantiated directly,
    # construct a concrete subclass instead.
    id: str
    name: str
    kind: SymbolKind
    declaration_id: str
    is_exported: bool = False


@dataclass(frozen=True, kw_only=True)
class PackageSymbol(Symbol):
    kind: SymbolKind = field(default=SymbolKind.PACKAGE, init=False)
    file_ids: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class FunctionSymbol(Symbol):
    kind: SymbolKind = field(default=SymbolKind.FUNCTION, init=False)
    parameter_count: int = 0


@dataclass(frozen=True, kw_only=True)
class TypeSymbol(Symbol):
    kind: SymbolKind = field(default=SymbolKind.TYPE, init=False)
    underlying_kind: str = "unknown"


@dataclass(frozen=True, kw_only=True)
class VariableSymbol(Symbol):
    kind: SymbolKind = field(default=SymbolKind.VARIABLE, init=False)


@dataclass(frozen=True, kw_only=True)
class ConstantSymbol(Symbol):
    kind: SymbolKind = field(default=SymbolKind.CONSTANT, init=False)
