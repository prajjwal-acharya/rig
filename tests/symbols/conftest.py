from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from rig.ir.identifiers import declaration_id, file_id, repository_id
from rig.ir.model import (
    Declaration,
    File,
    FunctionDeclaration,
    ImportDeclaration,
    SourceLocation,
    TypeDeclaration,
    VariableDeclaration,
)
from rig.ir.repository import RepositoryIR, RepositoryIRBuilder

REPO_ROOT = Path("/repos/example")
REPOSITORY_ID = repository_id(REPO_ROOT)


def location(relative_path: str = "main.go") -> SourceLocation:
    return SourceLocation(
        relative_path=Path(relative_path), start_line=0, start_column=0, end_line=0, end_column=1
    )


def make_function(
    name: str, relative_path: str = "main.go", *, occurrence: int = 0, is_exported: bool = True
) -> FunctionDeclaration:
    fid = file_id(REPOSITORY_ID, Path(relative_path))
    return FunctionDeclaration(
        id=declaration_id(fid, "function", name, occurrence),
        name=name,
        location=location(relative_path),
        parameter_count=1,
        is_exported=is_exported,
    )


def make_type(name: str, relative_path: str = "main.go") -> TypeDeclaration:
    fid = file_id(REPOSITORY_ID, Path(relative_path))
    return TypeDeclaration(
        id=declaration_id(fid, "type", name),
        name=name,
        location=location(relative_path),
        underlying_kind="struct",
        is_exported=True,
    )


def make_variable(
    name: str, relative_path: str = "main.go", *, is_constant: bool = False
) -> VariableDeclaration:
    fid = file_id(REPOSITORY_ID, Path(relative_path))
    return VariableDeclaration(
        id=declaration_id(fid, "variable", name),
        name=name,
        location=location(relative_path),
        is_constant=is_constant,
        is_exported=True,
    )


def make_import(name: str, relative_path: str = "main.go") -> ImportDeclaration:
    fid = file_id(REPOSITORY_ID, Path(relative_path))
    return ImportDeclaration(
        id=declaration_id(fid, "import", name),
        name=name,
        location=location(relative_path),
        import_path=name,
    )


def make_file(
    relative_path: str,
    *,
    package_name: str | None,
    declarations: Iterable[Declaration] = (),
) -> File:
    return File(
        id=file_id(REPOSITORY_ID, Path(relative_path)),
        relative_path=Path(relative_path),
        language_id="go",
        package_name=package_name,
        declarations=tuple(declarations),
    )


def build_repository(*files: File) -> RepositoryIR:
    builder = RepositoryIRBuilder(REPO_ROOT)
    for file in files:
        builder.add_file(file)
    return builder.build()
