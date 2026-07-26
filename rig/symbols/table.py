from __future__ import annotations

import threading

from rig.symbols.diagnostics import SymbolDiagnostic
from rig.symbols.model import Symbol
from rig.symbols.scope import Scope


class DuplicateSymbolError(ValueError):
    pass


class DuplicateScopeError(ValueError):
    pass


class SymbolTable:
    """Thread-safe registry of symbols and scopes for one repository.

    O(1) lookup by id. Insertion order does not matter - `symbols()` and
    `scopes()` always return their contents sorted by id, so iteration is
    deterministic regardless of how the table was populated.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._symbols: dict[str, Symbol] = {}
        self._scopes: dict[str, Scope] = {}
        self._diagnostics: list[SymbolDiagnostic] = []

    def add_symbol(self, symbol: Symbol) -> None:
        with self._lock:
            if symbol.id in self._symbols:
                raise DuplicateSymbolError(f"symbol already present: {symbol.id!r}")
            self._symbols[symbol.id] = symbol

    def add_scope(self, scope: Scope) -> None:
        with self._lock:
            if scope.id in self._scopes:
                raise DuplicateScopeError(f"scope already present: {scope.id!r}")
            self._scopes[scope.id] = scope

    def add_diagnostic(self, diagnostic: SymbolDiagnostic) -> None:
        with self._lock:
            self._diagnostics.append(diagnostic)

    def get_symbol(self, symbol_id: str) -> Symbol | None:
        return self._symbols.get(symbol_id)

    def get_scope(self, scope_id: str) -> Scope | None:
        return self._scopes.get(scope_id)

    def symbols(self) -> tuple[Symbol, ...]:
        return tuple(sorted(self._symbols.values(), key=lambda symbol: symbol.id))

    def scopes(self) -> tuple[Scope, ...]:
        return tuple(sorted(self._scopes.values(), key=lambda scope: scope.id))

    def diagnostics(self) -> tuple[SymbolDiagnostic, ...]:
        return tuple(self._diagnostics)

    def __len__(self) -> int:
        return len(self._symbols)

    def __contains__(self, symbol_id: str) -> bool:
        return symbol_id in self._symbols
