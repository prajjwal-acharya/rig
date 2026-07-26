from __future__ import annotations

from pathlib import Path

from rig.ir.builder import IRBuilderRegistry
from rig.ir.builders.go import GoIRBuilder
from rig.ir.model import FunctionDeclaration, TypeDeclaration
from rig.ir.repository import build_repository_ir
from rig.ir.visitor import IRVisitor
from rig.languages import DEFAULT_REGISTRY
from rig.languages.pipeline import LanguageAnnotatedFile
from rig.parsers.manager import ParserManager
from rig.parsers.pipeline import parse_repository_files
from rig.parsers.treesitter.factory import build_default_registry
from rig.scanner.models import DiscoveredFile


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_full_pipeline_from_scanner_output_to_repository_ir(tmp_path: Path) -> None:
    _write(tmp_path / "pkg1" / "a.go", "package pkg1\n\nfunc Foo() {}\n")
    _write(tmp_path / "pkg1" / "b.go", "package pkg1\n\nfunc Bar() {}\nfunc Foo() {}\n")
    _write(tmp_path / "pkg2" / "c.go", "package pkg2\n\ntype Widget struct{}\n")

    go_language = DEFAULT_REGISTRY.lookup_extension(".go")
    assert go_language is not None

    files = [
        DiscoveredFile(relative_path=Path("pkg1/a.go")),
        DiscoveredFile(relative_path=Path("pkg1/b.go")),
        DiscoveredFile(relative_path=Path("pkg2/c.go")),
    ]
    annotated = [LanguageAnnotatedFile(file=f, language=go_language) for f in files]

    parser_manager = ParserManager(build_default_registry())
    parsed = parse_repository_files(tmp_path, annotated, parser_manager)

    ir_registry = IRBuilderRegistry([GoIRBuilder()])
    repository = build_repository_ir(tmp_path, parsed, ir_registry)

    assert {f.relative_path.as_posix() for f in repository.files} == {
        "pkg1/a.go",
        "pkg1/b.go",
        "pkg2/c.go",
    }
    assert {p.name for p in repository.packages} == {"pkg1", "pkg2"}
    assert any("duplicate function declaration" in d.message for d in repository.diagnostics)


def test_visitor_collects_declarations_from_the_full_pipeline(tmp_path: Path) -> None:
    _write(tmp_path / "main.go", "package main\n\nfunc Run() {}\n\ntype Config struct{}\n")

    go_language = DEFAULT_REGISTRY.lookup_extension(".go")
    assert go_language is not None

    annotated = [
        LanguageAnnotatedFile(
            file=DiscoveredFile(relative_path=Path("main.go")), language=go_language
        )
    ]
    parser_manager = ParserManager(build_default_registry())
    parsed = parse_repository_files(tmp_path, annotated, parser_manager)

    ir_registry = IRBuilderRegistry([GoIRBuilder()])
    repository = build_repository_ir(tmp_path, parsed, ir_registry)

    class Collector(IRVisitor):
        def __init__(self) -> None:
            self.functions: list[str] = []
            self.types: list[str] = []

        def visit_function(self, declaration: FunctionDeclaration) -> None:
            self.functions.append(declaration.name)

        def visit_type(self, declaration: TypeDeclaration) -> None:
            self.types.append(declaration.name)

    collector = Collector()
    collector.visit_repository(repository)

    assert collector.functions == ["Run"]
    assert collector.types == ["Config"]


def test_files_with_no_matching_ir_builder_are_skipped(tmp_path: Path) -> None:
    _write(tmp_path / "notes.txt", "just some text")

    text_language = DEFAULT_REGISTRY.lookup_extension(".txt")
    assert text_language is not None

    annotated = [
        LanguageAnnotatedFile(
            file=DiscoveredFile(relative_path=Path("notes.txt")), language=text_language
        )
    ]
    parser_manager = ParserManager(build_default_registry())
    parsed = parse_repository_files(tmp_path, annotated, parser_manager)

    ir_registry = IRBuilderRegistry([GoIRBuilder()])
    repository = build_repository_ir(tmp_path, parsed, ir_registry)

    assert repository.files == ()


def test_empty_repository_produces_empty_ir(tmp_path: Path) -> None:
    ir_registry = IRBuilderRegistry([GoIRBuilder()])

    repository = build_repository_ir(tmp_path, [], ir_registry)

    assert repository.files == ()
    assert repository.packages == ()
    assert repository.diagnostics == ()
