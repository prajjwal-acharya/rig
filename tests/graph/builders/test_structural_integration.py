from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from rig.graph.builders.structural import StructuralGraphBuilder
from rig.graph.model import RelationshipType
from rig.graph.serialization import graph_to_dict
from rig.ir.builder import IRBuilderRegistry
from rig.ir.builders.go import GoIRBuilder
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


def test_full_pipeline_golden_graph_shape(tmp_path: Path) -> None:
    _write(
        tmp_path / "pkg1" / "a.go",
        'package pkg1\n\nimport "fmt"\n\nfunc Foo() {}\n\ntype Widget struct{}\n\n'
        "var GlobalX int\n\nconst MaxRetries = 3\n",
    )
    _write(tmp_path / "pkg2" / "b.go", "package pkg2\n\nfunc Bar() {}\n")

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

    builder = StructuralGraphBuilder(now=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    graph = builder.build(repository)

    node_types_by_id = {n.id: n.type for n in graph.nodes}
    type_counts: dict[str, int] = {}
    for node_type in node_types_by_id.values():
        type_counts[node_type] = type_counts.get(node_type, 0) + 1

    assert type_counts == {
        "Repository": 1,
        "Package": 2,
        "File": 2,
        "Function": 2,
        "Type": 1,
        "Variable": 1,
        "Constant": 1,
    }

    contains_count = sum(1 for e in graph.edges if e.relationship == RelationshipType.CONTAINS)
    declares_count = sum(1 for e in graph.edges if e.relationship == RelationshipType.DECLARES)
    # CONTAINS: repo->pkg1, repo->pkg2, pkg1->a.go, pkg2->b.go
    assert contains_count == 4
    # DECLARES: Foo, Widget, GlobalX, MaxRetries (a.go) + Bar (b.go)
    assert declares_count == 5

    assert graph.metadata.statistics["package_count"] == 2
    assert graph.metadata.statistics["file_count"] == 2
    assert graph.metadata.statistics["declaration_count"] == 5

    # The whole graph must be JSON-serializable without error.
    payload = graph_to_dict(graph)
    assert len(payload["nodes"]) == len(graph.nodes)
    assert len(payload["edges"]) == len(graph.edges)


def test_full_pipeline_is_deterministic_across_runs(tmp_path: Path) -> None:
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
        builder = StructuralGraphBuilder(now=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
        return builder.build(repository)

    first = run_once()
    second = run_once()

    assert first == second
