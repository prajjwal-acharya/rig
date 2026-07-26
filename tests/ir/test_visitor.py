from __future__ import annotations

from pathlib import Path

from rig.ir.model import (
    File,
    FunctionDeclaration,
    ImportDeclaration,
    SourceLocation,
    TypeDeclaration,
    VariableDeclaration,
)
from rig.ir.repository import RepositoryIRBuilder
from rig.ir.visitor import IRVisitor, iter_declarations, iter_files


def _location() -> SourceLocation:
    return SourceLocation(
        relative_path=Path("main.go"), start_line=0, start_column=0, end_line=0, end_column=1
    )


def _sample_repository():
    builder = RepositoryIRBuilder(Path("/repos/example"))
    builder.add_file(
        File(
            id="f1",
            relative_path=Path("main.go"),
            language_id="go",
            package_name="mypkg",
            declarations=(
                FunctionDeclaration(id="d1", name="Foo", location=_location()),
                TypeDeclaration(id="d2", name="Widget", location=_location()),
                VariableDeclaration(id="d3", name="x", location=_location()),
                ImportDeclaration(id="d4", name="fmt", location=_location()),
            ),
        )
    )
    return builder.build()


def test_iter_files_yields_every_file() -> None:
    repository = _sample_repository()

    files = list(iter_files(repository))

    assert [f.relative_path.as_posix() for f in files] == ["main.go"]


def test_iter_declarations_yields_every_declaration_across_files() -> None:
    repository = _sample_repository()

    declarations = list(iter_declarations(repository))

    assert [d.name for d in declarations] == ["Foo", "Widget", "x", "fmt"]


class RecordingVisitor(IRVisitor):
    def __init__(self) -> None:
        self.functions: list[str] = []
        self.types: list[str] = []
        self.variables: list[str] = []
        self.imports: list[str] = []

    def visit_function(self, declaration: FunctionDeclaration) -> None:
        self.functions.append(declaration.name)

    def visit_type(self, declaration: TypeDeclaration) -> None:
        self.types.append(declaration.name)

    def visit_variable(self, declaration: VariableDeclaration) -> None:
        self.variables.append(declaration.name)

    def visit_import(self, declaration: ImportDeclaration) -> None:
        self.imports.append(declaration.name)


def test_visitor_dispatches_to_the_correct_method_per_kind() -> None:
    repository = _sample_repository()
    visitor = RecordingVisitor()

    visitor.visit_repository(repository)

    assert visitor.functions == ["Foo"]
    assert visitor.types == ["Widget"]
    assert visitor.variables == ["x"]
    assert visitor.imports == ["fmt"]


def test_base_visitor_methods_are_safe_no_ops() -> None:
    repository = _sample_repository()
    visitor = IRVisitor()

    visitor.visit_repository(repository)  # must not raise


def test_visitor_can_be_invoked_directly_on_a_single_file() -> None:
    repository = _sample_repository()
    visitor = RecordingVisitor()

    visitor.visit_file(repository.files[0])

    assert visitor.functions == ["Foo"]
