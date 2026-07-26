from __future__ import annotations

from enum import Enum


class Capability(str, Enum):
    IR = "ir"
    SYMBOL_TABLE = "symbol_table"
    REFERENCE_INDEX = "reference_index"
    GRAPH = "graph"
    IMPORT_GRAPH = "import_graph"
