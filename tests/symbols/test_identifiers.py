from __future__ import annotations

from pathlib import Path

from rig.symbols.identifiers import (
    file_scope_id,
    package_scope_id,
    package_symbol_id,
    repository_scope_id,
    symbol_id,
)
from tests.symbols.conftest import REPOSITORY_ID


def test_repository_scope_id_is_deterministic() -> None:
    assert repository_scope_id(REPOSITORY_ID) == repository_scope_id(REPOSITORY_ID)


def test_package_scope_id_differs_by_package_name() -> None:
    a = package_scope_id(REPOSITORY_ID, "pkg1")
    b = package_scope_id(REPOSITORY_ID, "pkg2")
    assert a != b


def test_file_scope_id_differs_by_path() -> None:
    a = file_scope_id(REPOSITORY_ID, Path("a.go"))
    b = file_scope_id(REPOSITORY_ID, Path("b.go"))
    assert a != b


def test_package_symbol_id_is_deterministic() -> None:
    assert package_symbol_id(REPOSITORY_ID, "pkg1") == package_symbol_id(REPOSITORY_ID, "pkg1")


def test_symbol_id_differs_by_occurrence() -> None:
    scope = package_scope_id(REPOSITORY_ID, "pkg1")
    first = symbol_id(scope, "function", "Foo", occurrence=0)
    second = symbol_id(scope, "function", "Foo", occurrence=1)
    assert first != second


def test_symbol_id_never_equals_a_graph_style_declaration_id() -> None:
    from rig.ir.identifiers import declaration_id, file_id

    fid = file_id(REPOSITORY_ID, Path("a.go"))
    decl_id = declaration_id(fid, "function", "Foo")
    scope = package_scope_id(REPOSITORY_ID, "pkg1")
    sid = symbol_id(scope, "function", "Foo")

    assert sid != decl_id
    assert sid.startswith("symbol:")
    assert decl_id.startswith("declaration:")
