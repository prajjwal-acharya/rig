from __future__ import annotations

from rig.analysis.capability import Capability
from rig.analysis.context import AnalysisContext
from rig.analysis.manager import AnalysisManager
from rig.analysis.registry import AnalysisRegistry
from rig.graph.model import Graph
from rig.references.index import ReferenceIndex
from rig.symbols.table import SymbolTable
from tests.analysis.conftest import FailingAnalysis, FakeAnalysis, make_repository


def test_execute_one_runs_a_registered_analysis() -> None:
    manager = AnalysisManager(AnalysisRegistry([FakeAnalysis()]))
    context = AnalysisContext(repository=make_repository())

    result = manager.execute_one("fake", context)

    assert result.success is True
    assert result.analysis_id == "fake"
    assert result.repository_id == context.repository.id


def test_execute_one_missing_analysis_returns_failed_result() -> None:
    manager = AnalysisManager(AnalysisRegistry())
    context = AnalysisContext(repository=make_repository())

    result = manager.execute_one("missing", context)

    assert result.success is False
    assert "no analysis registered" in result.diagnostics[0].message


def test_manager_overwrites_identity_fields_regardless_of_what_analysis_returns() -> None:
    manager = AnalysisManager(AnalysisRegistry([FakeAnalysis("real-id")]))
    context = AnalysisContext(repository=make_repository())

    result = manager.execute_one("real-id", context)

    # FakeAnalysis.execute() deliberately returns "ignored-by-manager" for
    # both fields - the manager must override them with the real values.
    assert result.analysis_id == "real-id"
    assert result.repository_id == context.repository.id


def test_manager_sets_analysis_version() -> None:
    manager = AnalysisManager(AnalysisRegistry([FakeAnalysis(version="2.3.4")]))
    context = AnalysisContext(repository=make_repository())

    result = manager.execute_one("fake", context)

    assert result.analysis_version == "2.3.4"


def test_manager_records_timing() -> None:
    manager = AnalysisManager(AnalysisRegistry([FakeAnalysis()]))
    context = AnalysisContext(repository=make_repository())

    result = manager.execute_one("fake", context)

    assert result.started_at is not None
    assert result.completed_at is not None
    assert result.duration_seconds >= 0.0
    assert result.completed_at >= result.started_at


def test_context_is_propagated_to_the_analysis() -> None:
    analysis = FakeAnalysis()
    manager = AnalysisManager(AnalysisRegistry([analysis]))
    context = AnalysisContext(repository=make_repository(), symbols=SymbolTable())

    manager.execute_one("fake", context)

    assert analysis.executed_with is context


def test_missing_capability_prevents_execution() -> None:
    analysis = FakeAnalysis(required_capabilities=frozenset({Capability.SYMBOL_TABLE}))
    manager = AnalysisManager(AnalysisRegistry([analysis]))
    context = AnalysisContext(repository=make_repository())  # no symbols

    result = manager.execute_one("fake", context)

    assert result.success is False
    assert "missing required capability: symbol_table" in result.diagnostics[0].message
    assert analysis.executed_with is None  # execute() was never called


def test_capability_present_allows_execution() -> None:
    analysis = FakeAnalysis(required_capabilities=frozenset({Capability.SYMBOL_TABLE}))
    manager = AnalysisManager(AnalysisRegistry([analysis]))
    context = AnalysisContext(repository=make_repository(), symbols=SymbolTable())

    result = manager.execute_one("fake", context)

    assert result.success is True
    assert analysis.executed_with is context


def test_import_graph_capability_maps_to_the_graph_field() -> None:
    analysis = FakeAnalysis(required_capabilities=frozenset({Capability.IMPORT_GRAPH}))
    manager = AnalysisManager(AnalysisRegistry([analysis]))

    without_graph = AnalysisContext(repository=make_repository())
    with_graph = AnalysisContext(repository=make_repository(), graph=Graph())

    assert manager.execute_one("fake", without_graph).success is False
    assert manager.execute_one("fake", with_graph).success is True


def test_multiple_missing_capabilities_are_all_reported() -> None:
    analysis = FakeAnalysis(
        required_capabilities=frozenset({Capability.SYMBOL_TABLE, Capability.GRAPH})
    )
    manager = AnalysisManager(AnalysisRegistry([analysis]))
    context = AnalysisContext(repository=make_repository())

    result = manager.execute_one("fake", context)

    assert len(result.diagnostics) == 2


def test_analysis_exception_is_isolated() -> None:
    manager = AnalysisManager(AnalysisRegistry([FailingAnalysis()]))
    context = AnalysisContext(repository=make_repository())

    result = manager.execute_one("failing", context)

    assert result.success is False
    assert "boom during execute" in result.diagnostics[0].message


def test_one_failing_analysis_does_not_block_others() -> None:
    manager = AnalysisManager(AnalysisRegistry([FailingAnalysis(), FakeAnalysis("good")]))
    context = AnalysisContext(repository=make_repository())

    results = manager.execute_all(context)

    assert len(results) == 2
    by_id = {r.analysis_id: r for r in results}
    assert by_id["failing"].success is False
    assert by_id["good"].success is True


def test_execute_all_runs_every_registered_analysis_by_default() -> None:
    manager = AnalysisManager(
        AnalysisRegistry([FakeAnalysis("a"), FakeAnalysis("b"), FakeAnalysis("c")])
    )
    context = AnalysisContext(repository=make_repository())

    results = manager.execute_all(context)

    assert [r.analysis_id for r in results] == ["a", "b", "c"]


def test_execute_all_can_run_a_subset_by_id() -> None:
    manager = AnalysisManager(
        AnalysisRegistry([FakeAnalysis("a"), FakeAnalysis("b"), FakeAnalysis("c")])
    )
    context = AnalysisContext(repository=make_repository())

    results = manager.execute_all(context, analysis_ids=["c", "a"])

    assert [r.analysis_id for r in results] == ["c", "a"]


def test_execute_all_on_empty_registry_returns_empty_tuple() -> None:
    manager = AnalysisManager(AnalysisRegistry())
    context = AnalysisContext(repository=make_repository())

    assert manager.execute_all(context) == ()


def test_execution_order_is_deterministic_across_repeated_runs() -> None:
    manager = AnalysisManager(AnalysisRegistry([FakeAnalysis("zeta"), FakeAnalysis("alpha")]))
    context = AnalysisContext(repository=make_repository())

    first = [r.analysis_id for r in manager.execute_all(context)]
    second = [r.analysis_id for r in manager.execute_all(context)]

    assert first == second == ["alpha", "zeta"]


def test_reference_index_capability_is_validated() -> None:
    analysis = FakeAnalysis(required_capabilities=frozenset({Capability.REFERENCE_INDEX}))
    manager = AnalysisManager(AnalysisRegistry([analysis]))

    without_index = AnalysisContext(repository=make_repository())
    with_index = AnalysisContext(repository=make_repository(), references=ReferenceIndex())

    assert manager.execute_one("fake", without_index).success is False
    assert manager.execute_one("fake", with_index).success is True


def test_ir_capability_is_always_satisfied() -> None:
    analysis = FakeAnalysis(required_capabilities=frozenset({Capability.IR}))
    manager = AnalysisManager(AnalysisRegistry([analysis]))
    context = AnalysisContext(repository=make_repository())

    result = manager.execute_one("fake", context)

    assert result.success is True
