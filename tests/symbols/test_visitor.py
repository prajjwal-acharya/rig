from __future__ import annotations

from rig.symbols.model import (
    ConstantSymbol,
    FunctionSymbol,
    PackageSymbol,
    TypeSymbol,
    VariableSymbol,
)
from rig.symbols.scope import PackageScope
from rig.symbols.table import SymbolTable
from rig.symbols.visitor import SymbolVisitor, iter_scopes, iter_symbols


def _table() -> SymbolTable:
    table = SymbolTable()
    table.add_symbol(PackageSymbol(id="s0", name="pkg1", declaration_id="d0"))
    table.add_symbol(FunctionSymbol(id="s1", name="Foo", declaration_id="d1"))
    table.add_symbol(TypeSymbol(id="s2", name="Widget", declaration_id="d2"))
    table.add_symbol(VariableSymbol(id="s3", name="x", declaration_id="d3"))
    table.add_symbol(ConstantSymbol(id="s4", name="Max", declaration_id="d4"))
    return table


def test_iter_symbols_yields_every_symbol() -> None:
    table = _table()
    assert {s.id for s in iter_symbols(table)} == {"s0", "s1", "s2", "s3", "s4"}


def test_iter_scopes_yields_every_scope() -> None:
    table = _table()
    table.add_scope(PackageScope(id="sc1", name="pkg1"))

    assert [s.id for s in iter_scopes(table)] == ["sc1"]


def test_base_visitor_is_a_safe_no_op() -> None:
    SymbolVisitor().visit_table(_table())  # must not raise


class RecordingVisitor(SymbolVisitor):
    def __init__(self) -> None:
        self.packages: list[str] = []
        self.functions: list[str] = []
        self.types: list[str] = []
        self.variables: list[str] = []
        self.constants: list[str] = []

    def visit_package(self, symbol: PackageSymbol) -> None:
        self.packages.append(symbol.name)

    def visit_function(self, symbol: FunctionSymbol) -> None:
        self.functions.append(symbol.name)

    def visit_type(self, symbol: TypeSymbol) -> None:
        self.types.append(symbol.name)

    def visit_variable(self, symbol: VariableSymbol) -> None:
        self.variables.append(symbol.name)

    def visit_constant(self, symbol: ConstantSymbol) -> None:
        self.constants.append(symbol.name)


def test_visitor_dispatches_to_the_correct_method_per_kind() -> None:
    visitor = RecordingVisitor()

    visitor.visit_table(_table())

    assert visitor.packages == ["pkg1"]
    assert visitor.functions == ["Foo"]
    assert visitor.types == ["Widget"]
    assert visitor.variables == ["x"]
    assert visitor.constants == ["Max"]


def test_constant_is_not_misdispatched_as_variable() -> None:
    # ConstantSymbol and VariableSymbol are siblings (both subclass Symbol
    # directly), so isinstance ordering must never conflate the two.
    visitor = RecordingVisitor()

    visitor.visit_table(_table())

    assert "Max" not in visitor.variables
    assert "x" not in visitor.constants
