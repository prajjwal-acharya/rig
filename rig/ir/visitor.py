from __future__ import annotations

from collections.abc import Iterator

from rig.ir.model import (
    Declaration,
    File,
    FunctionDeclaration,
    ImportDeclaration,
    TypeDeclaration,
    VariableDeclaration,
)
from rig.ir.repository import RepositoryIR


def iter_files(repository: RepositoryIR) -> Iterator[File]:
    yield from repository.files


def iter_declarations(repository: RepositoryIR) -> Iterator[Declaration]:
    for file in repository.files:
        yield from file.declarations


class IRVisitor:
    """Base visitor over IR objects. Subclass and override only the
    `visit_*` methods you care about; the rest provide default traversal."""

    def visit_repository(self, repository: RepositoryIR) -> None:
        for file in repository.files:
            self.visit_file(file)

    def visit_file(self, file: File) -> None:
        for declaration in file.declarations:
            self.visit_declaration(declaration)

    def visit_declaration(self, declaration: Declaration) -> None:
        if isinstance(declaration, FunctionDeclaration):
            self.visit_function(declaration)
        elif isinstance(declaration, TypeDeclaration):
            self.visit_type(declaration)
        elif isinstance(declaration, VariableDeclaration):
            self.visit_variable(declaration)
        elif isinstance(declaration, ImportDeclaration):
            self.visit_import(declaration)

    def visit_function(self, declaration: FunctionDeclaration) -> None:
        pass

    def visit_type(self, declaration: TypeDeclaration) -> None:
        pass

    def visit_variable(self, declaration: VariableDeclaration) -> None:
        pass

    def visit_import(self, declaration: ImportDeclaration) -> None:
        pass
