from __future__ import annotations

from rig.analysis.capability import Capability


def test_capability_has_expected_members() -> None:
    expected = {"ir", "symbol_table", "reference_index", "graph", "import_graph"}
    assert {member.value for member in Capability} == expected
