from __future__ import annotations

from pathlib import Path

from rig.ir.builder import IRBuilderRegistry
from rig.ir.builders.go import GoIRBuilder
from rig.ir.repository import build_repository_ir
from rig.languages import DEFAULT_REGISTRY
from rig.languages.pipeline import LanguageAnnotatedFile
from rig.parsers.manager import ParserManager
from rig.parsers.pipeline import parse_repository_files
from rig.parsers.treesitter.factory import build_default_registry as build_parser_registry
from rig.scanner.models import DiscoveredFile
from rig.symbols.builder import GoSymbolTableBuilder
from rig.symbols.identifiers import file_scope_id
from rig.symbols.model import FunctionSymbol
from rig.symbols.resolver import SymbolResolver


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_full_pipeline_builds_symbol_table_and_resolves_across_files(tmp_path: Path) -> None:
    _write(
        tmp_path / "pkg1" / "a.go",
        "package pkg1\n\nfunc Foo() {}\nfunc Foo() {}\n\ntype Widget struct{}\n",
    )
    _write(tmp_path / "pkg1" / "b.go", "package pkg1\n\nfunc Bar() {}\n")

    go_language = DEFAULT_REGISTRY.lookup_extension(".go")
    assert go_language is not None
    files = [
        DiscoveredFile(relative_path=Path("pkg1/a.go")),
        DiscoveredFile(relative_path=Path("pkg1/b.go")),
    ]
    annotated = [LanguageAnnotatedFile(file=f, language=go_language) for f in files]

    parser_manager = ParserManager(build_parser_registry())
    parsed = parse_repository_files(tmp_path, annotated, parser_manager)
    ir_registry = IRBuilderRegistry([GoIRBuilder()])
    repository = build_repository_ir(tmp_path, parsed, ir_registry)

    table = GoSymbolTableBuilder().build(repository)

    function_names = sorted(s.name for s in table.symbols() if isinstance(s, FunctionSymbol))
    assert function_names == ["Bar", "Foo", "Foo"]
    assert len(table.diagnostics()) == 1
    assert "duplicate function symbol" in table.diagnostics()[0].message

    resolver = SymbolResolver(table)
    a_scope = file_scope_id(repository.id, Path("pkg1/a.go"))
    resolved = resolver.resolve(a_scope, "Bar")
    assert resolved is not None
    assert resolved.name == "Bar"

    assert resolver.resolve(a_scope, "DoesNotExist") is None


def test_symbol_table_is_deterministic_across_runs(tmp_path: Path) -> None:
    _write(tmp_path / "pkg1" / "a.go", "package pkg1\n\nfunc Foo() {}\nfunc Bar() {}\n")

    go_language = DEFAULT_REGISTRY.lookup_extension(".go")
    assert go_language is not None
    annotated = [
        LanguageAnnotatedFile(
            file=DiscoveredFile(relative_path=Path("pkg1/a.go")), language=go_language
        )
    ]

    def run_once():
        parser_manager = ParserManager(build_parser_registry())
        parsed = parse_repository_files(tmp_path, annotated, parser_manager)
        ir_registry = IRBuilderRegistry([GoIRBuilder()])
        repository = build_repository_ir(tmp_path, parsed, ir_registry)
        return GoSymbolTableBuilder().build(repository)

    first = run_once()
    second = run_once()

    assert [s.id for s in first.symbols()] == [s.id for s in second.symbols()]
    assert [s.id for s in first.scopes()] == [s.id for s in second.scopes()]
