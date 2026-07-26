from __future__ import annotations

import importlib.metadata

import tree_sitter_go
from tree_sitter import Language as TSLanguage

from rig.parsers.treesitter.grammar import Grammar


def _package_version(distribution_name: str) -> str | None:
    try:
        return importlib.metadata.version(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        return None


GO_GRAMMAR = Grammar(
    language_id="go",
    ts_language=TSLanguage(tree_sitter_go.language()),
    parser_id="tree-sitter-go",
    version=_package_version("tree-sitter-go"),
)
