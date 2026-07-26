from __future__ import annotations

from pathlib import Path

from rig.analysis import (
    Analysis,
    AnalysisContext,
    AnalysisManager,
    AnalysisRegistry,
    AnalysisResult,
    Capability,
)
from rig.graph.builders.structural import StructuralGraphBuilder
from rig.ir.builder import IRBuilderRegistry
from rig.ir.builders.go import GoIRBuilder
from rig.ir.repository import build_repository_ir
from rig.languages import DEFAULT_REGISTRY
from rig.languages.pipeline import LanguageAnnotatedFile
from rig.parsers.manager import ParserManager
from rig.parsers.pipeline import parse_repository_files
from rig.parsers.treesitter.factory import build_default_registry as build_parser_registry
from rig.references.resolver import GoReferenceResolver
from rig.scanner.models import DiscoveredFile
from rig.symbols.builder import GoSymbolTableBuilder


class FunctionCountingAnalysis(Analysis):
    """A stand-in for a real semantic analysis, used only to prove the
    framework wires real RepositoryIR/SymbolTable/ReferenceIndex/Graph
    through AnalysisContext correctly end-to-end."""

    @property
    def analysis_id(self) -> str:
        return "function-counter"

    @property
    def display_name(self) -> str:
        return "Function Counter"

    @property
    def required_capabilities(self) -> frozenset[Capability]:
        return frozenset({Capability.IR, Capability.SYMBOL_TABLE, Capability.REFERENCE_INDEX})

    def execute(self, context: AnalysisContext) -> AnalysisResult:
        from rig.symbols.model import FunctionSymbol

        assert context.symbols is not None
        function_count = sum(1 for s in context.symbols.symbols() if isinstance(s, FunctionSymbol))
        return AnalysisResult.ok(
            analysis_id="ignored",
            repository_id="ignored",
            artifacts={"function_count": function_count},
        )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_full_pipeline_through_analysis_manager(tmp_path: Path) -> None:
    _write(
        tmp_path / "pkg1" / "a.go",
        "package pkg1\n\nfunc helper() {}\n\nfunc Foo() {\n\thelper()\n}\n",
    )

    go_language = DEFAULT_REGISTRY.lookup_extension(".go")
    assert go_language is not None
    annotated = [
        LanguageAnnotatedFile(
            file=DiscoveredFile(relative_path=Path("pkg1/a.go")), language=go_language
        )
    ]

    parser_manager = ParserManager(build_parser_registry())
    parsed = parse_repository_files(tmp_path, annotated, parser_manager)

    ir_registry = IRBuilderRegistry([GoIRBuilder()])
    repository = build_repository_ir(tmp_path, parsed, ir_registry)

    symbols = GoSymbolTableBuilder().build(repository)
    references = GoReferenceResolver(parsed).resolve(repository, symbols)
    graph = StructuralGraphBuilder().build(repository)

    context = AnalysisContext(
        repository=repository, symbols=symbols, references=references, graph=graph
    )

    manager = AnalysisManager(AnalysisRegistry([FunctionCountingAnalysis()]))
    results = manager.execute_all(context)

    assert len(results) == 1
    result = results[0]
    assert result.success is True
    assert result.analysis_id == "function-counter"
    assert result.repository_id == repository.id
    assert result.artifacts["function_count"] == 2
    assert result.started_at is not None
    assert result.duration_seconds >= 0.0


def test_missing_capability_is_caught_before_touching_real_data(tmp_path: Path) -> None:
    _write(tmp_path / "a.go", "package p\n\nfunc Foo() {}\n")

    go_language = DEFAULT_REGISTRY.lookup_extension(".go")
    assert go_language is not None
    annotated = [
        LanguageAnnotatedFile(file=DiscoveredFile(relative_path=Path("a.go")), language=go_language)
    ]
    parser_manager = ParserManager(build_parser_registry())
    parsed = parse_repository_files(tmp_path, annotated, parser_manager)
    ir_registry = IRBuilderRegistry([GoIRBuilder()])
    repository = build_repository_ir(tmp_path, parsed, ir_registry)

    # Deliberately omit symbols/references - FunctionCountingAnalysis
    # requires SYMBOL_TABLE and REFERENCE_INDEX capabilities.
    context = AnalysisContext(repository=repository)

    manager = AnalysisManager(AnalysisRegistry([FunctionCountingAnalysis()]))
    result = manager.execute_one("function-counter", context)

    assert result.success is False
    assert len(result.diagnostics) == 2
