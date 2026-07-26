from __future__ import annotations

from pathlib import Path

from rig.languages import DEFAULT_REGISTRY
from rig.languages.pipeline import LanguageAnnotatedFile
from rig.parsers.manager import ParserManager
from rig.parsers.model import ParseContext
from rig.parsers.pipeline import parse_repository_files
from rig.parsers.treesitter.factory import build_default_registry
from rig.parsers.treesitter.tree import SyntaxTree
from rig.scanner.models import DiscoveredFile
from tests.parsers.treesitter.conftest import GO_LANGUAGE, VALID_GO_SOURCE


def test_manager_dispatches_go_source_to_the_real_treesitter_parser() -> None:
    manager = ParserManager(build_default_registry())
    context = ParseContext(path=Path("main.go"), language=GO_LANGUAGE, source=VALID_GO_SOURCE)

    result = manager.parse(context)

    assert result.success is True
    assert result.parser_id == "tree-sitter-go"
    assert isinstance(result.syntax_tree, SyntaxTree)
    assert result.syntax_tree.root.type == "source_file"
    assert result.elapsed_seconds >= 0.0


def test_manager_still_dispatches_python_to_its_stub_unchanged() -> None:
    python_language = DEFAULT_REGISTRY.lookup_extension(".py")
    assert python_language is not None

    manager = ParserManager(build_default_registry())
    context = ParseContext(path=Path("app.py"), language=python_language, source="print('hi')")

    result = manager.parse(context)

    assert result.success is True
    assert result.parser_id == "stub-python"
    assert result.syntax_tree is None


def test_full_pipeline_from_scanner_output_to_parse_result(tmp_path: Path) -> None:
    (tmp_path / "main.go").write_text(VALID_GO_SOURCE)

    manager = ParserManager(build_default_registry())
    annotated = [
        LanguageAnnotatedFile(
            file=DiscoveredFile(relative_path=Path("main.go")), language=GO_LANGUAGE
        )
    ]

    parsed = parse_repository_files(tmp_path, annotated, manager)

    assert len(parsed) == 1
    result = parsed[0].result
    assert result.success is True
    assert result.parser_id == "tree-sitter-go"
    assert isinstance(result.syntax_tree, SyntaxTree)
    assert result.syntax_tree.root.type == "source_file"
