from __future__ import annotations

from pathlib import Path

from rig.frontends.go import GoIRBuilder
from rig.graph.builders.imports import ImportGraphBuilder
from rig.graph.builders.structural import StructuralGraphBuilder
from rig.graph.model import RelationshipType
from rig.ir.builder import IRBuilderRegistry
from rig.ir.repository import build_repository_ir
from rig.languages import DEFAULT_REGISTRY
from rig.languages.pipeline import LanguageAnnotatedFile
from rig.parsers.manager import ParserManager
from rig.parsers.pipeline import parse_repository_files
from rig.parsers.treesitter.factory import build_default_registry as build_parser_registry
from rig.scanner.models import DiscoveredFile


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_full_pipeline_enriches_structural_graph_with_imports(tmp_path: Path) -> None:
    _write(
        tmp_path / "pkg1" / "a.go",
        'package pkg1\n\nimport (\n\t"fmt"\n\tf "fmt"\n\t. "strings"\n\t_ "net/http/pprof"\n)\n\n'
        'func Foo() { fmt.Println("hi") }\n',
    )
    _write(tmp_path / "pkg2" / "b.go", 'package pkg2\n\nimport "fmt"\n\nfunc Bar() {}\n')

    go_language = DEFAULT_REGISTRY.lookup_extension(".go")
    assert go_language is not None
    files = [
        DiscoveredFile(relative_path=Path("pkg1/a.go")),
        DiscoveredFile(relative_path=Path("pkg2/b.go")),
    ]
    annotated = [LanguageAnnotatedFile(file=f, language=go_language) for f in files]

    parser_manager = ParserManager(build_parser_registry())
    parsed = parse_repository_files(tmp_path, annotated, parser_manager)
    ir_registry = IRBuilderRegistry([GoIRBuilder()])
    repository = build_repository_ir(tmp_path, parsed, ir_registry)

    structural_graph = StructuralGraphBuilder().build(repository)
    enriched = ImportGraphBuilder().build(repository, structural_graph)

    import_nodes = [n for n in enriched.nodes if n.type == "Import"]
    import_paths = {n.properties["import_path"] for n in import_nodes}
    assert import_paths == {"fmt", "strings", "net/http/pprof"}
    # "fmt" (plain) and "f"="fmt" (aliased) are distinct nodes -> 4 total
    assert len(import_nodes) == 4

    imports_edges = [e for e in enriched.edges if e.relationship == RelationshipType.IMPORTS]
    assert len(imports_edges) == 5  # 4 from pkg1/a.go + 1 (shared "fmt") from pkg2/b.go

    assert enriched.metadata.statistics["import_count"] == 5
    assert enriched.metadata.statistics["import_node_count"] == 4
    assert enriched.metadata.statistics["import_edge_count"] == 5

    # structural graph itself must remain untouched
    assert not any(n.type == "Import" for n in structural_graph.nodes)
