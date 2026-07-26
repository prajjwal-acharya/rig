from __future__ import annotations

from rig.symbols.model import FunctionSymbol
from rig.symbols.resolver import SymbolResolver
from rig.symbols.scope import FileScope, PackageScope, RepositoryScope
from rig.symbols.table import SymbolTable


def _table_with_scopes() -> SymbolTable:
    table = SymbolTable()

    foo = FunctionSymbol(id="sym:foo", name="Foo", declaration_id="d1")
    bar = FunctionSymbol(id="sym:bar", name="Bar", declaration_id="d2")
    table.add_symbol(foo)
    table.add_symbol(bar)

    table.add_scope(RepositoryScope(id="scope:repo", name="repo", parent_id=None))
    table.add_scope(
        PackageScope(
            id="scope:pkg",
            name="pkg1",
            parent_id="scope:repo",
            symbol_ids=(("Foo", "sym:foo"), ("Bar", "sym:bar")),
        )
    )
    table.add_scope(
        FileScope(
            id="scope:file_a",
            name="a.go",
            parent_id="scope:pkg",
            symbol_ids=(("Foo", "sym:foo"),),
        )
    )
    table.add_scope(
        FileScope(
            id="scope:file_b",
            name="b.go",
            parent_id="scope:pkg",
            symbol_ids=(("Bar", "sym:bar"),),
        )
    )
    return table


def test_resolves_name_declared_in_the_same_file_scope() -> None:
    table = _table_with_scopes()
    resolver = SymbolResolver(table)

    resolved = resolver.resolve("scope:file_a", "Foo")

    assert resolved is not None
    assert resolved.name == "Foo"


def test_resolves_name_declared_in_a_sibling_file_via_package_scope() -> None:
    table = _table_with_scopes()
    resolver = SymbolResolver(table)

    # "Bar" is declared in b.go but not in a.go's own file scope - it must
    # still resolve via the shared package scope.
    resolved = resolver.resolve("scope:file_a", "Bar")

    assert resolved is not None
    assert resolved.name == "Bar"


def test_missing_name_resolves_to_none() -> None:
    table = _table_with_scopes()
    resolver = SymbolResolver(table)

    assert resolver.resolve("scope:file_a", "DoesNotExist") is None


def test_unknown_scope_id_resolves_to_none() -> None:
    table = _table_with_scopes()
    resolver = SymbolResolver(table)

    assert resolver.resolve("scope:unknown", "Foo") is None


def test_resolution_never_crosses_into_a_sibling_package() -> None:
    table = _table_with_scopes()
    table.add_scope(
        PackageScope(
            id="scope:other_pkg",
            name="pkg2",
            parent_id="scope:repo",
            symbol_ids=(("Baz", "sym:baz"),),
        )
    )
    resolver = SymbolResolver(table)

    # "Baz" belongs to a sibling package, reachable only via the repository
    # root, not via pkg1's own chain.
    assert resolver.resolve("scope:file_a", "Baz") is None


def test_resolve_at_package_scope_directly() -> None:
    table = _table_with_scopes()
    resolver = SymbolResolver(table)

    resolved = resolver.resolve("scope:pkg", "Foo")

    assert resolved is not None
    assert resolved.name == "Foo"
