from __future__ import annotations

from pathlib import Path

from rig.ir.diagnostics import IRDiagnosticSeverity
from rig.ir.identifiers import repository_id
from rig.ir.model import File, FunctionDeclaration, ImportDeclaration, SourceLocation
from rig.ir.repository import RepositoryIRBuilder


def _location(relative_path: Path) -> SourceLocation:
    return SourceLocation(
        relative_path=relative_path, start_line=0, start_column=0, end_line=0, end_column=1
    )


def _function(name: str, relative_path: Path) -> FunctionDeclaration:
    return FunctionDeclaration(id=f"fn:{name}", name=name, location=_location(relative_path))


def test_repository_id_matches_identifiers_module() -> None:
    root = Path("/repos/example")
    builder = RepositoryIRBuilder(root)

    assert builder.repository_id == repository_id(root)


def test_build_with_no_files_produces_empty_repository() -> None:
    builder = RepositoryIRBuilder(Path("/repos/example"))

    repository = builder.build()

    assert repository.files == ()
    assert repository.packages == ()
    assert repository.diagnostics == ()


def test_files_are_sorted_deterministically() -> None:
    builder = RepositoryIRBuilder(Path("/repos/example"))
    builder.add_file(File(id="b", relative_path=Path("b.go"), language_id="go"))
    builder.add_file(File(id="a", relative_path=Path("a.go"), language_id="go"))

    repository = builder.build()

    assert [f.relative_path.as_posix() for f in repository.files] == ["a.go", "b.go"]


def test_packages_are_grouped_by_name() -> None:
    builder = RepositoryIRBuilder(Path("/repos/example"))
    builder.add_file(
        File(id="a", relative_path=Path("a.go"), language_id="go", package_name="pkg1")
    )
    builder.add_file(
        File(id="b", relative_path=Path("b.go"), language_id="go", package_name="pkg1")
    )
    builder.add_file(
        File(id="c", relative_path=Path("c.go"), language_id="go", package_name="pkg2")
    )

    repository = builder.build()

    names = {p.name for p in repository.packages}
    assert names == {"pkg1", "pkg2"}
    pkg1 = next(p for p in repository.packages if p.name == "pkg1")
    assert set(pkg1.file_ids) == {"a", "b"}


def test_files_without_package_name_are_excluded_from_packages() -> None:
    builder = RepositoryIRBuilder(Path("/repos/example"))
    builder.add_file(File(id="a", relative_path=Path("a.go"), language_id="go", package_name=None))

    repository = builder.build()

    assert repository.packages == ()


def test_packages_are_sorted_deterministically() -> None:
    builder = RepositoryIRBuilder(Path("/repos/example"))
    builder.add_file(
        File(id="a", relative_path=Path("a.go"), language_id="go", package_name="zeta")
    )
    builder.add_file(
        File(id="b", relative_path=Path("b.go"), language_id="go", package_name="alpha")
    )

    repository = builder.build()

    assert [p.name for p in repository.packages] == ["alpha", "zeta"]


def test_diagnostics_from_add_file_are_preserved() -> None:
    from rig.ir.diagnostics import IRDiagnostic

    builder = RepositoryIRBuilder(Path("/repos/example"))
    diagnostic = IRDiagnostic(message="something odd")
    builder.add_file(File(id="a", relative_path=Path("a.go"), language_id="go"), [diagnostic])

    repository = builder.build()

    assert diagnostic in repository.diagnostics


def test_duplicate_declaration_in_same_package_produces_diagnostic() -> None:
    builder = RepositoryIRBuilder(Path("/repos/example"))
    builder.add_file(
        File(
            id="a",
            relative_path=Path("a.go"),
            language_id="go",
            package_name="pkg1",
            declarations=(_function("Foo", Path("a.go")),),
        )
    )
    builder.add_file(
        File(
            id="b",
            relative_path=Path("b.go"),
            language_id="go",
            package_name="pkg1",
            declarations=(_function("Foo", Path("b.go")),),
        )
    )

    repository = builder.build()

    messages = [d.message for d in repository.diagnostics]
    assert any("duplicate function declaration" in m and "Foo" in m for m in messages)
    assert all(d.severity == IRDiagnosticSeverity.WARNING for d in repository.diagnostics)


def test_no_duplicate_diagnostic_across_different_packages() -> None:
    builder = RepositoryIRBuilder(Path("/repos/example"))
    builder.add_file(
        File(
            id="a",
            relative_path=Path("a.go"),
            language_id="go",
            package_name="pkg1",
            declarations=(_function("Foo", Path("a.go")),),
        )
    )
    builder.add_file(
        File(
            id="b",
            relative_path=Path("b.go"),
            language_id="go",
            package_name="pkg2",
            declarations=(_function("Foo", Path("b.go")),),
        )
    )

    repository = builder.build()

    assert repository.diagnostics == ()


def test_repeated_imports_across_files_are_not_flagged_as_duplicates() -> None:
    builder = RepositoryIRBuilder(Path("/repos/example"))
    import_a = ImportDeclaration(id="i1", name="fmt", location=_location(Path("a.go")))
    import_b = ImportDeclaration(id="i2", name="fmt", location=_location(Path("b.go")))
    builder.add_file(
        File(
            id="a",
            relative_path=Path("a.go"),
            language_id="go",
            package_name="pkg1",
            declarations=(import_a,),
        )
    )
    builder.add_file(
        File(
            id="b",
            relative_path=Path("b.go"),
            language_id="go",
            package_name="pkg1",
            declarations=(import_b,),
        )
    )

    repository = builder.build()

    assert repository.diagnostics == ()


def test_build_is_deterministic_across_repeated_calls() -> None:
    builder = RepositoryIRBuilder(Path("/repos/example"))
    builder.add_file(
        File(id="a", relative_path=Path("a.go"), language_id="go", package_name="pkg1")
    )

    first = builder.build()
    second = builder.build()

    assert first == second
