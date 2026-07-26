from __future__ import annotations

from rig.symbols.builder import GoSymbolTableBuilder
from rig.symbols.identifiers import file_scope_id, package_scope_id, repository_scope_id
from rig.symbols.model import (
    ConstantSymbol,
    FunctionSymbol,
    PackageSymbol,
    TypeSymbol,
    VariableSymbol,
)
from rig.symbols.scope import FileScope, PackageScope, RepositoryScope
from tests.symbols.conftest import (
    build_repository,
    make_file,
    make_function,
    make_import,
    make_type,
    make_variable,
)


def test_package_is_indexed_as_a_symbol() -> None:
    file = make_file("a.go", package_name="pkg1")
    repository = build_repository(file)

    table = GoSymbolTableBuilder().build(repository)

    package_symbols = [s for s in table.symbols() if isinstance(s, PackageSymbol)]
    assert len(package_symbols) == 1
    assert package_symbols[0].name == "pkg1"
    assert package_symbols[0].file_ids == (file.id,)


def test_function_is_indexed() -> None:
    function = make_function("Foo", "a.go", is_exported=True)
    file = make_file("a.go", package_name="pkg1", declarations=[function])
    repository = build_repository(file)

    table = GoSymbolTableBuilder().build(repository)

    symbol = next(s for s in table.symbols() if isinstance(s, FunctionSymbol))
    assert symbol.name == "Foo"
    assert symbol.declaration_id == function.id
    assert symbol.is_exported is True
    assert symbol.parameter_count == 1


def test_type_is_indexed() -> None:
    type_decl = make_type("Widget", "a.go")
    file = make_file("a.go", package_name="pkg1", declarations=[type_decl])
    repository = build_repository(file)

    table = GoSymbolTableBuilder().build(repository)

    symbol = next(s for s in table.symbols() if isinstance(s, TypeSymbol))
    assert symbol.name == "Widget"
    assert symbol.underlying_kind == "struct"


def test_variable_is_indexed() -> None:
    variable = make_variable("GlobalX", "a.go", is_constant=False)
    file = make_file("a.go", package_name="pkg1", declarations=[variable])
    repository = build_repository(file)

    table = GoSymbolTableBuilder().build(repository)

    symbol = next(s for s in table.symbols() if isinstance(s, VariableSymbol))
    assert symbol.name == "GlobalX"


def test_constant_is_indexed() -> None:
    constant = make_variable("MaxRetries", "a.go", is_constant=True)
    file = make_file("a.go", package_name="pkg1", declarations=[constant])
    repository = build_repository(file)

    table = GoSymbolTableBuilder().build(repository)

    symbol = next(s for s in table.symbols() if isinstance(s, ConstantSymbol))
    assert symbol.name == "MaxRetries"
    assert not any(isinstance(s, VariableSymbol) for s in table.symbols())


def test_imports_are_not_indexed_as_symbols() -> None:
    imp = make_import("fmt", "a.go")
    file = make_file("a.go", package_name="pkg1", declarations=[imp])
    repository = build_repository(file)

    table = GoSymbolTableBuilder().build(repository)

    assert not any(s.declaration_id == imp.id for s in table.symbols())


def test_duplicate_declaration_names_are_both_indexed_with_a_diagnostic() -> None:
    foo1 = make_function("Foo", "a.go", occurrence=0)
    foo2 = make_function("Foo", "a.go", occurrence=1)
    file = make_file("a.go", package_name="pkg1", declarations=[foo1, foo2])
    repository = build_repository(file)

    table = GoSymbolTableBuilder().build(repository)

    function_symbols = [s for s in table.symbols() if isinstance(s, FunctionSymbol)]
    assert len(function_symbols) == 2
    assert function_symbols[0].id != function_symbols[1].id

    diagnostics = table.diagnostics()
    assert len(diagnostics) == 1
    assert "duplicate function symbol" in diagnostics[0].message
    assert "Foo" in diagnostics[0].message


def test_duplicate_across_two_files_in_the_same_package_is_detected() -> None:
    foo1 = make_function("Foo", "a.go")
    foo2 = make_function("Foo", "b.go")
    file1 = make_file("a.go", package_name="pkg1", declarations=[foo1])
    file2 = make_file("b.go", package_name="pkg1", declarations=[foo2])
    repository = build_repository(file1, file2)

    table = GoSymbolTableBuilder().build(repository)

    function_symbols = [s for s in table.symbols() if isinstance(s, FunctionSymbol)]
    assert len(function_symbols) == 2
    assert len(table.diagnostics()) == 1


def test_no_diagnostic_for_the_same_name_in_different_packages() -> None:
    foo1 = make_function("Foo", "pkg1/a.go")
    foo2 = make_function("Foo", "pkg2/b.go")
    file1 = make_file("pkg1/a.go", package_name="pkg1", declarations=[foo1])
    file2 = make_file("pkg2/b.go", package_name="pkg2", declarations=[foo2])
    repository = build_repository(file1, file2)

    table = GoSymbolTableBuilder().build(repository)

    assert table.diagnostics() == ()


def test_repository_scope_is_created() -> None:
    file = make_file("a.go", package_name="pkg1")
    repository = build_repository(file)

    table = GoSymbolTableBuilder().build(repository)

    repo_scope = table.get_scope(repository_scope_id(repository.id))
    assert isinstance(repo_scope, RepositoryScope)
    assert repo_scope.lookup_local("pkg1") is not None


def test_package_scope_is_created_with_parent_repository_scope() -> None:
    file = make_file("a.go", package_name="pkg1")
    repository = build_repository(file)

    table = GoSymbolTableBuilder().build(repository)

    pkg_scope = table.get_scope(package_scope_id(repository.id, "pkg1"))
    assert isinstance(pkg_scope, PackageScope)
    assert pkg_scope.parent_id == repository_scope_id(repository.id)


def test_file_scope_is_created_with_parent_package_scope() -> None:
    function = make_function("Foo", "a.go")
    file = make_file("a.go", package_name="pkg1", declarations=[function])
    repository = build_repository(file)

    table = GoSymbolTableBuilder().build(repository)

    file_scope = table.get_scope(file_scope_id(repository.id, file.relative_path))
    assert isinstance(file_scope, FileScope)
    assert file_scope.parent_id == package_scope_id(repository.id, "pkg1")
    assert file_scope.lookup_local("Foo") is not None


def test_package_scope_aggregates_symbols_from_all_member_files() -> None:
    foo = make_function("Foo", "pkg1/a.go")
    bar = make_function("Bar", "pkg1/b.go")
    file1 = make_file("pkg1/a.go", package_name="pkg1", declarations=[foo])
    file2 = make_file("pkg1/b.go", package_name="pkg1", declarations=[bar])
    repository = build_repository(file1, file2)

    table = GoSymbolTableBuilder().build(repository)

    pkg_scope = table.get_scope(package_scope_id(repository.id, "pkg1"))
    assert isinstance(pkg_scope, PackageScope)
    assert set(pkg_scope.names()) == {"Foo", "Bar"}


def test_orphan_file_without_package_is_scoped_to_repository() -> None:
    function = make_function("Foo", "orphan.go")
    file = make_file("orphan.go", package_name=None, declarations=[function])
    repository = build_repository(file)

    table = GoSymbolTableBuilder().build(repository)

    file_scope = table.get_scope(file_scope_id(repository.id, file.relative_path))
    assert isinstance(file_scope, FileScope)
    assert file_scope.parent_id == repository_scope_id(repository.id)


def test_orphan_files_with_the_same_declared_name_do_not_collide() -> None:
    foo1 = make_function("Foo", "orphan1.go")
    foo2 = make_function("Foo", "orphan2.go")
    file1 = make_file("orphan1.go", package_name=None, declarations=[foo1])
    file2 = make_file("orphan2.go", package_name=None, declarations=[foo2])
    repository = build_repository(file1, file2)

    table = GoSymbolTableBuilder().build(repository)

    function_symbols = [s for s in table.symbols() if isinstance(s, FunctionSymbol)]
    assert len(function_symbols) == 2
    assert function_symbols[0].id != function_symbols[1].id


def test_empty_repository_produces_empty_table_except_repository_scope() -> None:
    repository = build_repository()

    table = GoSymbolTableBuilder().build(repository)

    assert len(table) == 0
    assert len(table.scopes()) == 1
    assert isinstance(table.scopes()[0], RepositoryScope)


def test_symbol_ids_are_deterministic_across_repeated_builds() -> None:
    function = make_function("Foo", "a.go")
    file = make_file("a.go", package_name="pkg1", declarations=[function])
    repository = build_repository(file)

    first = GoSymbolTableBuilder().build(repository)
    second = GoSymbolTableBuilder().build(repository)

    assert [s.id for s in first.symbols()] == [s.id for s in second.symbols()]
    assert [s.id for s in first.scopes()] == [s.id for s in second.scopes()]


def test_multiple_packages_are_each_indexed_independently() -> None:
    foo = make_function("Foo", "pkg1/a.go")
    bar = make_function("Bar", "pkg2/b.go")
    file1 = make_file("pkg1/a.go", package_name="pkg1", declarations=[foo])
    file2 = make_file("pkg2/b.go", package_name="pkg2", declarations=[bar])
    repository = build_repository(file1, file2)

    table = GoSymbolTableBuilder().build(repository)

    package_symbols = {s.name for s in table.symbols() if isinstance(s, PackageSymbol)}
    assert package_symbols == {"pkg1", "pkg2"}
