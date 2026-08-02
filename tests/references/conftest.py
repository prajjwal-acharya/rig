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

REPO_ROOT = Path("/repos/example")


def _require_language(extension: str) -> Language:
    language = DEFAULT_REGISTRY.lookup_extension(extension)
    if language is None:
        raise RuntimeError(f"{extension!r} is missing from the default language catalog")
    return language


GO_LANGUAGE = _require_language(".go")

_backend = TreeSitterBackend()


def make_parsed_file(relative_path: str, source: str) -> ParsedFile:
    tree = _backend.parse(GO_GRAMMAR, source.encode("utf-8"))
    result = ParseResult.ok(parser_id="tree-sitter-go", language=GO_LANGUAGE, syntax_tree=tree)
    return ParsedFile(
        file=DiscoveredFile(relative_path=Path(relative_path)),
        language=GO_LANGUAGE,
        result=result,
    )


def build_repository_and_symbols(
    sources: dict[str, str],
) -> tuple[RepositoryIR, SymbolTable, list[ParsedFile]]:
    parsed_files = [make_parsed_file(path, source) for path, source in sources.items()]
    ir_registry = IRBuilderRegistry([GoIRBuilder()])
    repository = build_repository_ir(REPO_ROOT, parsed_files, ir_registry)
    symbols = GoSymbolTableBuilder().build(repository)
    return repository, symbols, parsed_files
