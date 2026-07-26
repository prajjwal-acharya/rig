from __future__ import annotations

from rig.types.builder import GoTypeBuilder
from rig.types.model import AliasType, InterfaceType, NamedType, StructType
from tests.types.conftest import build_repository, build_symbols, make_file, make_type


def test_struct_is_indexed() -> None:
    decl = make_type("Point", "a.go", underlying_kind="struct")
    file = make_file("a.go", package_name="pkg1", declarations=[decl])
    repository = build_repository(file)
    symbols = build_symbols(repository)

    index = GoTypeBuilder().build(repository, symbols)

    type_ = index.by_declaration(decl.id)
    assert isinstance(type_, StructType)
    assert type_.name == "Point"
    assert type_.package == "pkg1"


def test_interface_is_indexed() -> None:
    decl = make_type("Shape", "a.go", underlying_kind="interface")
    file = make_file("a.go", package_name="pkg1", declarations=[decl])
    repository = build_repository(file)
    symbols = build_symbols(repository)

    index = GoTypeBuilder().build(repository, symbols)

    type_ = index.by_declaration(decl.id)
    assert isinstance(type_, InterfaceType)


def test_alias_is_indexed() -> None:
    decl = make_type("ID", "a.go", underlying_kind="alias")
    file = make_file("a.go", package_name="pkg1", declarations=[decl])
    repository = build_repository(file)
    symbols = build_symbols(repository)

    index = GoTypeBuilder().build(repository, symbols)

    type_ = index.by_declaration(decl.id)
    assert isinstance(type_, AliasType)


def test_named_type_is_indexed_for_other_underlying_kinds() -> None:
    decl = make_type("Celsius", "a.go", underlying_kind="other")
    file = make_file("a.go", package_name="pkg1", declarations=[decl])
    repository = build_repository(file)
    symbols = build_symbols(repository)

    index = GoTypeBuilder().build(repository, symbols)

    type_ = index.by_declaration(decl.id)
    assert isinstance(type_, NamedType)


def test_unknown_underlying_kind_falls_back_to_named_type() -> None:
    decl = make_type("Mystery", "a.go", underlying_kind="unknown")
    file = make_file("a.go", package_name="pkg1", declarations=[decl])
    repository = build_repository(file)
    symbols = build_symbols(repository)

    index = GoTypeBuilder().build(repository, symbols)

    assert isinstance(index.by_declaration(decl.id), NamedType)


def test_type_is_linked_to_its_symbol() -> None:
    decl = make_type("Point", "a.go")
    file = make_file("a.go", package_name="pkg1", declarations=[decl])
    repository = build_repository(file)
    symbols = build_symbols(repository)

    index = GoTypeBuilder().build(repository, symbols)

    type_ = index.by_declaration(decl.id)
    assert type_ is not None
    symbol = symbols.get_symbol(type_.symbol_id)
    assert symbol is not None
    assert symbol.declaration_id == decl.id


def test_duplicate_type_in_same_package_is_indexed_with_a_diagnostic() -> None:
    point1 = make_type("Point", "a.go", occurrence=0)
    point2 = make_type("Point", "a.go", occurrence=1)
    file = make_file("a.go", package_name="pkg1", declarations=[point1, point2])
    repository = build_repository(file)
    symbols = build_symbols(repository)

    index = GoTypeBuilder().build(repository, symbols)

    matches = index.by_name("Point")
    assert len(matches) == 2
    assert matches[0].id != matches[1].id

    diagnostics = index.diagnostics()
    assert len(diagnostics) == 1
    assert "duplicate type" in diagnostics[0].message
    assert "Point" in diagnostics[0].message
    assert "pkg1" in diagnostics[0].message


def test_duplicate_across_two_files_in_the_same_package_is_detected() -> None:
    point1 = make_type("Point", "a.go")
    point2 = make_type("Point", "b.go")
    file1 = make_file("a.go", package_name="pkg1", declarations=[point1])
    file2 = make_file("b.go", package_name="pkg1", declarations=[point2])
    repository = build_repository(file1, file2)
    symbols = build_symbols(repository)

    index = GoTypeBuilder().build(repository, symbols)

    assert len(index.by_name("Point")) == 2
    assert len(index.diagnostics()) == 1


def test_no_diagnostic_for_the_same_name_in_different_packages() -> None:
    point1 = make_type("Point", "pkg1/a.go")
    point2 = make_type("Point", "pkg2/b.go")
    file1 = make_file("pkg1/a.go", package_name="pkg1", declarations=[point1])
    file2 = make_file("pkg2/b.go", package_name="pkg2", declarations=[point2])
    repository = build_repository(file1, file2)
    symbols = build_symbols(repository)

    index = GoTypeBuilder().build(repository, symbols)

    assert len(index.by_name("Point")) == 2
    assert index.diagnostics() == ()


def test_orphan_file_types_are_still_indexed_without_duplicate_diagnostics() -> None:
    point1 = make_type("Point", "orphan1.go")
    point2 = make_type("Point", "orphan2.go")
    file1 = make_file("orphan1.go", package_name=None, declarations=[point1])
    file2 = make_file("orphan2.go", package_name=None, declarations=[point2])
    repository = build_repository(file1, file2)
    symbols = build_symbols(repository)

    index = GoTypeBuilder().build(repository, symbols)

    assert len(index.by_name("Point")) == 2
    assert all(t.package is None for t in index.by_name("Point"))
    assert index.diagnostics() == ()


def test_empty_repository_produces_empty_index() -> None:
    repository = build_repository()
    symbols = build_symbols(repository)

    index = GoTypeBuilder().build(repository, symbols)

    assert len(index) == 0


def test_type_ids_are_deterministic_across_repeated_builds() -> None:
    decl = make_type("Point", "a.go")
    file = make_file("a.go", package_name="pkg1", declarations=[decl])
    repository = build_repository(file)
    symbols = build_symbols(repository)

    first = GoTypeBuilder().build(repository, symbols)
    second = GoTypeBuilder().build(repository, symbols)

    assert [t.id for t in first.types()] == [t.id for t in second.types()]


def test_metadata_counts_each_kind() -> None:
    struct_decl = make_type("Point", "a.go", underlying_kind="struct")
    interface_decl = make_type("Shape", "a.go", underlying_kind="interface")
    alias_decl = make_type("ID", "a.go", underlying_kind="alias")
    named_decl = make_type("Celsius", "a.go", underlying_kind="other")
    file = make_file(
        "a.go",
        package_name="pkg1",
        declarations=[struct_decl, interface_decl, alias_decl, named_decl],
    )
    repository = build_repository(file)
    symbols = build_symbols(repository)

    index = GoTypeBuilder().build(repository, symbols)
    stats = index.statistics()

    assert stats["total_types"] == 4
    assert stats["structs"] == 1
    assert stats["interfaces"] == 1
    assert stats["aliases"] == 1
    assert stats["named_types"] == 1
