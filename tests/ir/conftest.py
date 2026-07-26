from __future__ import annotations

from rig.parsers.treesitter.backend import TreeSitterBackend
from rig.parsers.treesitter.grammars.go import GO_GRAMMAR
from rig.parsers.treesitter.tree import SyntaxTree


def go_tree(source: str) -> SyntaxTree:
    backend = TreeSitterBackend()
    return backend.parse(GO_GRAMMAR, source.encode("utf-8"))
