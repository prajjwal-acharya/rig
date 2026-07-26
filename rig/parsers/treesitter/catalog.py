from __future__ import annotations

from rig.parsers.treesitter.grammar import GrammarRegistry
from rig.parsers.treesitter.grammars.go import GO_GRAMMAR

DEFAULT_GRAMMARS = (GO_GRAMMAR,)

DEFAULT_GRAMMAR_REGISTRY = GrammarRegistry(DEFAULT_GRAMMARS)
