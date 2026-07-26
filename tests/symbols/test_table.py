from __future__ import annotations

import pytest

from rig.symbols.diagnostics import SymbolDiagnostic
from rig.symbols.model import FunctionSymbol
from rig.symbols.scope import PackageScope
from rig.symbols.table import DuplicateScopeError, DuplicateSymbolError, SymbolTable


def test_add_and_get_symbol() -> None:
    table = SymbolTable()
    symbol = FunctionSymbol(id="s1", name="Foo", declaration_id="d1")

    table.add_symbol(symbol)

    assert table.get_symbol("s1") is symbol


def test_get_symbol_missing_returns_none() -> None:
    table = SymbolTable()
    assert table.get_symbol("missing") is None


def test_duplicate_symbol_id_raises() -> None:
    table = SymbolTable()
    table.add_symbol(FunctionSymbol(id="s1", name="Foo", declaration_id="d1"))

    with pytest.raises(DuplicateSymbolError):
        table.add_symbol(FunctionSymbol(id="s1", name="Foo", declaration_id="d1"))


def test_add_and_get_scope() -> None:
    table = SymbolTable()
    scope = PackageScope(id="sc1", name="pkg1")

    table.add_scope(scope)

    assert table.get_scope("sc1") is scope


def test_get_scope_missing_returns_none() -> None:
    table = SymbolTable()
    assert table.get_scope("missing") is None


def test_duplicate_scope_id_raises() -> None:
    table = SymbolTable()
    table.add_scope(PackageScope(id="sc1", name="pkg1"))

    with pytest.raises(DuplicateScopeError):
        table.add_scope(PackageScope(id="sc1", name="pkg1"))


def test_symbols_are_returned_sorted_by_id() -> None:
    table = SymbolTable()
    table.add_symbol(FunctionSymbol(id="s2", name="Bar", declaration_id="d2"))
    table.add_symbol(FunctionSymbol(id="s1", name="Foo", declaration_id="d1"))

    assert [s.id for s in table.symbols()] == ["s1", "s2"]


def test_scopes_are_returned_sorted_by_id() -> None:
    table = SymbolTable()
    table.add_scope(PackageScope(id="sc2", name="pkg2"))
    table.add_scope(PackageScope(id="sc1", name="pkg1"))

    assert [s.id for s in table.scopes()] == ["sc1", "sc2"]


def test_diagnostics_accumulate() -> None:
    table = SymbolTable()
    diagnostic = SymbolDiagnostic(message="duplicate thing")

    table.add_diagnostic(diagnostic)

    assert table.diagnostics() == (diagnostic,)


def test_len_reflects_symbol_count() -> None:
    table = SymbolTable()
    table.add_symbol(FunctionSymbol(id="s1", name="Foo", declaration_id="d1"))
    table.add_symbol(FunctionSymbol(id="s2", name="Bar", declaration_id="d2"))

    assert len(table) == 2


def test_contains_reflects_symbol_ids() -> None:
    table = SymbolTable()
    table.add_symbol(FunctionSymbol(id="s1", name="Foo", declaration_id="d1"))

    assert "s1" in table
    assert "missing" not in table


def test_empty_table() -> None:
    table = SymbolTable()
    assert len(table) == 0
    assert table.symbols() == ()
    assert table.scopes() == ()
    assert table.diagnostics() == ()
