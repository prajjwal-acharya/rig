from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from rig.ir.identifiers import declaration_id, file_id, repository_id
from rig.ir.model import Declaration, File, SourceLocation, TypeDeclaration
from rig.ir.repository import RepositoryIR, RepositoryIRBuilder
from rig.symbols.builder import GoSymbolTableBuilder
from rig.symbols.table import SymbolTable

REPO_ROOT = Path("/repos/example")
REPOSITORY_ID = repository_id(REPO_ROOT)


def location(relative_path: str = "main.go") -> SourceLocation:
    return SourceLocation(
        relative_path=Path(relative_path), start_line=0, start_column=0, end_line=0, end_column=1
    )


def make_type(
    name: str,
    relative_path: str = "main.go",
    *,
    underlying_kind: str = "struct",
    occurrence: int = 0,
) -> TypeDeclaration:
    fid = file_id(REPOSITORY_ID, Path(relative_path))
    return TypeDeclaration(
        id=declaration_id(fid, "type", name, occurrence),
        name=name,
        location=location(relative_path),
        underlying_kind=underlying_kind,
        is_exported=True,
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


def build_symbols(repository: RepositoryIR) -> SymbolTable:
    return GoSymbolTableBuilder().build(repository)
