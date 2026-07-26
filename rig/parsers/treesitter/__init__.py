from rig.parsers.treesitter.backend import TreeSitterBackend
from rig.parsers.treesitter.catalog import DEFAULT_GRAMMAR_REGISTRY, DEFAULT_GRAMMARS
from rig.parsers.treesitter.errors import DuplicateGrammarError
from rig.parsers.treesitter.factory import build_default_registry, build_treesitter_parsers
from rig.parsers.treesitter.grammar import Grammar, GrammarRegistry
from rig.parsers.treesitter.parser import TreeSitterParser
from rig.parsers.treesitter.traversal import (
    iter_children,
    iter_descendants,
    iter_named_children,
    iter_named_descendants,
    iter_preorder,
)
from rig.parsers.treesitter.tree import Point, SyntaxNode, SyntaxTree

__all__ = [
    "DEFAULT_GRAMMARS",
    "DEFAULT_GRAMMAR_REGISTRY",
    "DuplicateGrammarError",
    "Grammar",
    "GrammarRegistry",
    "Point",
    "SyntaxNode",
    "SyntaxTree",
    "TreeSitterBackend",
    "TreeSitterParser",
    "build_default_registry",
    "build_treesitter_parsers",
    "iter_children",
    "iter_descendants",
    "iter_named_children",
    "iter_named_descendants",
    "iter_preorder",
]
