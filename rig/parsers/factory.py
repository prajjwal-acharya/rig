from __future__ import annotations

from rig.parsers.registry import ParserRegistry

# Neutral entry point for building a ready-to-use parser registry. Which
# backend (Tree-sitter today, potentially ANTLR or a native parser later)
# actually implements the parsers is an internal detail of the parser package:
# callers ask `rig.parsers` for a registry and never name a backend, so the
# backend can be swapped without touching any consumer.


def build_default_parser_registry() -> ParserRegistry:
    """Return a parser registry covering every language RIG can currently
    parse. Backend selection lives entirely inside the parser package."""

    from rig.parsers.treesitter.factory import build_default_registry

    return build_default_registry()
