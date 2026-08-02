from __future__ import annotations

from pathlib import Path

from rig.frontends.go import GoIRBuilder
from rig.graph.builders.structural import StructuralGraphBuilder
from rig.graph.model import RelationshipType
from rig.ir.builder import IRBuilderRegistry
from rig.ir.repository import build_repository_ir
from rig.languages import DEFAULT_REGISTRY
from rig.languages.pipeline import LanguageAnnotatedFile
from rig.parsers.manager import ParserManager
from rig.parsers.pipeline import parse_repository_files
from rig.parsers.treesitter.factory import build_default_registry as build_parser_registry
from rig.references.builder import ReferenceGraphBuilder
from rig.references.model import ResolvedReference
from rig.references.resolver import GoReferenceResolver
from rig.scanner.models import DiscoveredFile
from rig.symbols.builder import GoSymbolTableBuilder


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_full_pipeline_from_scanner_to_enriched_graph(tmp_path: Path) -> None:
    _write(
        tmp_path / "pkg1" / "a.go",
        "package pkg1\n\n"
        "func helper() int {\n\treturn 1\n}\n\n"
        "func Foo() int {\n\treturn helper()\n}\n\n"
        "type Widget struct{}\n\n"
        "func UseWidget() Widget {\n\treturn Widget{}\n}\n",
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
    reference_index = GoReferenceResolver().resolve(repository, symbols)

    resolved_functions = [
        r
        for r in reference_index.references()
        if isinstance(r, ResolvedReference) and r.identifier == "helper"
    ]
    assert len(resolved_functions) == 1

    resolved_types = [
        r
        for r in reference_index.references()
        if isinstance(r, ResolvedReference) and r.identifier == "Widget"
    ]
    assert len(resolved_types) == 2  # function result type + composite literal

    structural_graph = StructuralGraphBuilder().build(repository)
    enriched_graph = ReferenceGraphBuilder().build(reference_index, symbols, structural_graph)

    references_edges = [
        e for e in enriched_graph.edges if e.relationship == RelationshipType.REFERENCES
    ]
    assert len(references_edges) >= 2

    node_ids = {n.id for n in enriched_graph.nodes}
    for edge in references_edges:
        assert edge.source in node_ids
        assert edge.target in node_ids

    assert len(enriched_graph.nodes) == len(structural_graph.nodes)
    assert not any(e.relationship == RelationshipType.REFERENCES for e in structural_graph.edges)
