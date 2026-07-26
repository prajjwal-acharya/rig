from __future__ import annotations

from dataclasses import replace

from rig.graph.builder import GraphAccumulator
from rig.graph.identifiers import edge_id
from rig.graph.model import Edge, Graph, RelationshipType
from rig.references.index import ReferenceIndex
from rig.references.model import ResolvedReference
from rig.symbols.table import SymbolTable


class ReferenceGraphBuilder:
    """Enriches an existing Graph with REFERENCES edges, derived from a
    ReferenceIndex. Reuses existing File and Declaration/Package nodes -
    never creates a new node, only new edges. Does not mutate the input
    Graph.
    """

    def build(self, index: ReferenceIndex, symbols: SymbolTable, graph: Graph) -> Graph:
        seen_edges: set[tuple[str, str]] = set()
        new_edges: list[Edge] = []

        for reference in index.references():
            if not isinstance(reference, ResolvedReference):
                continue

            symbol = symbols.get_symbol(reference.symbol_id)
            if symbol is None:
                continue  # defensive: a dangling symbol id should never happen

            target_node_id = symbol.declaration_id
            key = (reference.file_id, target_node_id)
            if key in seen_edges:
                # Multiple references from the same file to the same target
                # collapse into a single edge - REFERENCES is a boolean
                # "this file references that declaration" fact, not a count.
                continue
            seen_edges.add(key)

            new_edges.append(
                Edge(
                    id=edge_id(
                        reference.file_id, target_node_id, RelationshipType.REFERENCES.value
                    ),
                    source=reference.file_id,
                    target=target_node_id,
                    relationship=RelationshipType.REFERENCES,
                )
            )

        resolved_count = _resolved_count(index)
        statistics = graph.metadata.statistics
        statistics = statistics.with_property("reference_count", len(index))
        statistics = statistics.with_property("resolved_reference_count", resolved_count)
        statistics = statistics.with_property(
            "unresolved_reference_count", len(index) - resolved_count
        )
        statistics = statistics.with_property("reference_edge_count", len(new_edges))
        metadata = replace(graph.metadata, statistics=statistics)

        accumulator = GraphAccumulator(metadata=metadata)
        for node in graph.nodes:
            accumulator.add_node(node)
        for edge in graph.edges:
            accumulator.add_edge(edge)
        for edge in new_edges:
            accumulator.add_edge(edge)

        return accumulator.build()


def _resolved_count(index: ReferenceIndex) -> int:
    return sum(1 for reference in index.references() if isinstance(reference, ResolvedReference))
