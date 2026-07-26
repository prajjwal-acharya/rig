from __future__ import annotations

from rig.symbols.model import Symbol
from rig.symbols.table import SymbolTable


class SymbolResolver:
    """Resolves a name starting from a given scope, walking up the parent
    chain (e.g. file scope -> package scope -> repository scope). The chain
    is strictly vertical - it never reaches a sibling file's or package's
    scope, so this can never perform cross-package resolution.
    """

    def __init__(self, table: SymbolTable) -> None:
        self._table = table

    def resolve(self, scope_id: str, name: str) -> Symbol | None:
        scope = self._table.get_scope(scope_id)
        while scope is not None:
            found_id = scope.lookup_local(name)
            if found_id is not None:
                return self._table.get_symbol(found_id)
            scope = self._table.get_scope(scope.parent_id) if scope.parent_id else None
        return None
