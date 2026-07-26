from __future__ import annotations

from rig.graph.identifiers import edge_id


def test_edge_id_is_deterministic() -> None:
    assert edge_id("a", "b", "CONTAINS") == edge_id("a", "b", "CONTAINS")


def test_edge_id_differs_by_source() -> None:
    assert edge_id("a", "c", "CONTAINS") != edge_id("b", "c", "CONTAINS")


def test_edge_id_differs_by_target() -> None:
    assert edge_id("a", "b", "CONTAINS") != edge_id("a", "c", "CONTAINS")


def test_edge_id_differs_by_relationship() -> None:
    assert edge_id("a", "b", "CONTAINS") != edge_id("a", "b", "DECLARES")


def test_edge_id_differs_by_occurrence() -> None:
    assert edge_id("a", "b", "CALLS", occurrence=0) != edge_id("a", "b", "CALLS", occurrence=1)


def test_edge_id_has_a_stable_prefix() -> None:
    assert edge_id("a", "b", "CONTAINS").startswith("edge:")
