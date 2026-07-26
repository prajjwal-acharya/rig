from __future__ import annotations

import dataclasses

import pytest

from rig.symbols.model import (
    ConstantSymbol,
    FunctionSymbol,
    PackageSymbol,
    SymbolKind,
    TypeSymbol,
    VariableSymbol,
)


def test_function_symbol_kind_is_set_automatically() -> None:
    symbol = FunctionSymbol(id="s1", name="Foo", declaration_id="d1")
    assert symbol.kind == SymbolKind.FUNCTION


def test_type_symbol_kind_is_set_automatically() -> None:
    symbol = TypeSymbol(id="s1", name="Widget", declaration_id="d1")
    assert symbol.kind == SymbolKind.TYPE


def test_variable_symbol_kind_is_set_automatically() -> None:
    symbol = VariableSymbol(id="s1", name="x", declaration_id="d1")
    assert symbol.kind == SymbolKind.VARIABLE


def test_constant_symbol_kind_is_set_automatically() -> None:
    symbol = ConstantSymbol(id="s1", name="MaxRetries", declaration_id="d1")
    assert symbol.kind == SymbolKind.CONSTANT


def test_package_symbol_kind_is_set_automatically() -> None:
    symbol = PackageSymbol(id="s1", name="pkg1", declaration_id="d1")
    assert symbol.kind == SymbolKind.PACKAGE


def test_kind_cannot_be_overridden_at_construction() -> None:
    with pytest.raises(TypeError):
        FunctionSymbol(id="s1", name="Foo", kind=SymbolKind.TYPE, declaration_id="d1")  # type: ignore[call-arg]


def test_symbols_are_immutable() -> None:
    symbol = FunctionSymbol(id="s1", name="Foo", declaration_id="d1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        symbol.name = "Bar"  # type: ignore[misc]


def test_function_symbol_defaults() -> None:
    symbol = FunctionSymbol(id="s1", name="Foo", declaration_id="d1")
    assert symbol.parameter_count == 0
    assert symbol.is_exported is False


def test_type_symbol_defaults() -> None:
    symbol = TypeSymbol(id="s1", name="Widget", declaration_id="d1")
    assert symbol.underlying_kind == "unknown"


def test_package_symbol_defaults() -> None:
    symbol = PackageSymbol(id="s1", name="pkg1", declaration_id="d1")
    assert symbol.file_ids == ()


def test_symbols_are_hashable() -> None:
    a = FunctionSymbol(id="s1", name="Foo", declaration_id="d1")
    b = FunctionSymbol(id="s1", name="Foo", declaration_id="d1")
    assert a == b
    assert hash(a) == hash(b)
