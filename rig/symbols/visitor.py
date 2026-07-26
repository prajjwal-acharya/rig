from __future__ import annotations

from collections.abc import Iterator

from rig.symbols.model import (
    ConstantSymbol,
    FunctionSymbol,
    PackageSymbol,
    Symbol,
    TypeSymbol,
    VariableSymbol,
)
from rig.symbols.scope import Scope
from rig.symbols.table import SymbolTable


def iter_symbols(table: SymbolTable) -> Iterator[Symbol]:
    yield from table.symbols()


def iter_scopes(table: SymbolTable) -> Iterator[Scope]:
    yield from table.scopes()


class SymbolVisitor:
    """Base visitor over a SymbolTable. Subclass and override only the
    `visit_*` methods you care about; the rest provide default traversal.
    Future analyses should consume symbols through this layer rather than
    walking RepositoryIR directly.
    """

    def visit_table(self, table: SymbolTable) -> None:
        for symbol in table.symbols():
            self.visit_symbol(symbol)

    def visit_symbol(self, symbol: Symbol) -> None:
        if isinstance(symbol, PackageSymbol):
            self.visit_package(symbol)
        elif isinstance(symbol, FunctionSymbol):
            self.visit_function(symbol)
        elif isinstance(symbol, TypeSymbol):
            self.visit_type(symbol)
        elif isinstance(symbol, ConstantSymbol):
            self.visit_constant(symbol)
        elif isinstance(symbol, VariableSymbol):
            self.visit_variable(symbol)

    def visit_package(self, symbol: PackageSymbol) -> None:
        pass

    def visit_function(self, symbol: FunctionSymbol) -> None:
        pass

    def visit_type(self, symbol: TypeSymbol) -> None:
        pass

    def visit_variable(self, symbol: VariableSymbol) -> None:
        pass

    def visit_constant(self, symbol: ConstantSymbol) -> None:
        pass
