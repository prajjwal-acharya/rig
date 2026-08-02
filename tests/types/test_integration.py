from __future__ import annotations

from pathlib import Path

from rig.frontends.go import GoIRBuilder
from rig.ir.builder import IRBuilderRegistry
from rig.ir.repository import RepositoryIR, build_repository_ir
from rig.languages import DEFAULT_REGISTRY
from rig.languages.model import Language
from rig.parsers.model import ParseResult
from rig.parsers.pipeline import ParsedFile
from rig.parsers.treesitter.backend import TreeSitterBackend
from rig.parsers.treesitter.grammars.go import GO_GRAMMAR
from rig.scanner.models import DiscoveredFile
from rig.symbols.builder import GoSymbolTableBuilder
from rig.symbols.table import SymbolTable
from rig.types.builder import GoTypeBuilder
from rig.types.model import AliasType, InterfaceType, NamedType, StructType
from rig.types.resolver import TypeResolver

REPO_ROOT = Path("/repos/example")


def _go_language() -> Language:
    language = DEFAULT_REGISTRY.lookup_extension(".go")
    assert language is not None
    return language


_GO_LANGUAGE = _go_language()
_backend = TreeSitterBackend()


def _make_parsed_file(relative_path: str, source: str) -> ParsedFile:
    tree = _backend.parse(GO_GRAMMAR, source.encode("utf-8"))
    result = ParseResult.ok(parser_id="tree-sitter-go", language=_GO_LANGUAGE, syntax_tree=tree)
    return ParsedFile(
        file=DiscoveredFile(relative_path=Path(relative_path)),
        language=_GO_LANGUAGE,
        result=result,
    )


def _build_repository_and_symbols(sources: dict[str, str]) -> tuple[RepositoryIR, SymbolTable]:
    parsed_files = [_make_parsed_file(path, source) for path, source in sources.items()]
    ir_registry = IRBuilderRegistry([GoIRBuilder()])
    repository = build_repository_ir(REPO_ROOT, parsed_files, ir_registry)
    symbols = GoSymbolTableBuilder().build(repository)
    return repository, symbols


def test_full_pipeline_indexes_every_kind_of_type() -> None:
    source = (
        "package pkg1\n\n"
        "type Point struct {\n\tX int\n\tY int\n}\n\n"
        "type Shape interface {\n\tArea() float64\n}\n\n"
        "type ID = int\n\n"
        "type Celsius float64\n"
    )
    repository, symbols = _build_repository_and_symbols({"a.go": source})

    index = GoTypeBuilder().build(repository, symbols)

    stats = index.statistics()
    assert stats["total_types"] == 4
    assert stats["structs"] == 1
    assert stats["interfaces"] == 1
    assert stats["aliases"] == 1
    assert stats["named_types"] == 1

    point = index.by_name("Point")[0]
    assert isinstance(point, StructType)
    shape = index.by_name("Shape")[0]
    assert isinstance(shape, InterfaceType)
    identifier = index.by_name("ID")[0]
    assert isinstance(identifier, AliasType)
    celsius = index.by_name("Celsius")[0]
    assert isinstance(celsius, NamedType)


def test_full_pipeline_cross_file_duplicate_detection() -> None:
    repository, symbols = _build_repository_and_symbols(
        {
            "pkg1/a.go": "package pkg1\n\ntype Point struct {\n\tX int\n}\n",
            "pkg1/b.go": "package pkg1\n\ntype Point struct {\n\tY int\n}\n",
        }
    )

    index = GoTypeBuilder().build(repository, symbols)

    assert len(index.by_name("Point")) == 2
    assert len(index.diagnostics()) == 1


def test_full_pipeline_resolver_scoped_to_package() -> None:
    repository, symbols = _build_repository_and_symbols(
        {
            "pkg1/a.go": "package pkg1\n\ntype Point struct {\n\tX int\n}\n",
            "pkg2/b.go": "package pkg2\n\ntype Point struct {\n\tY int\n}\n",
        }
    )

    index = GoTypeBuilder().build(repository, symbols)
    resolver = TypeResolver(index)

    pkg1_point = resolver.resolve_in_package("pkg1", "Point")
    pkg2_point = resolver.resolve_in_package("pkg2", "Point")

    assert pkg1_point is not None and pkg1_point.package == "pkg1"
    assert pkg2_point is not None and pkg2_point.package == "pkg2"


def test_full_pipeline_type_links_to_real_symbol_and_declaration() -> None:
    source = "package pkg1\n\ntype Point struct {\n\tX int\n}\n"
    repository, symbols = _build_repository_and_symbols({"a.go": source})

    index = GoTypeBuilder().build(repository, symbols)
    point = index.by_name("Point")[0]

    symbol = symbols.get_symbol(point.symbol_id)
    assert symbol is not None
    assert symbol.declaration_id == point.declaration_id

    declarations = [
        d for f in repository.files for d in f.declarations if d.id == point.declaration_id
    ]
    assert len(declarations) == 1
    assert declarations[0].name == "Point"


def test_full_pipeline_is_deterministic_across_repeated_builds() -> None:
    source = (
        "package pkg1\n\n"
        "type Point struct {\n\tX int\n}\n\n"
        "type Shape interface {\n\tArea() float64\n}\n"
    )
    repository, symbols = _build_repository_and_symbols({"a.go": source})

    first = GoTypeBuilder().build(repository, symbols)
    second = GoTypeBuilder().build(repository, symbols)

    assert [t.id for t in first.types()] == [t.id for t in second.types()]
