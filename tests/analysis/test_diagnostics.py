from __future__ import annotations

from rig.analysis.diagnostics import AnalysisDiagnostic, AnalysisDiagnosticSeverity


def test_diagnostic_defaults() -> None:
    diagnostic = AnalysisDiagnostic(message="something", category="general")

    assert diagnostic.severity == AnalysisDiagnosticSeverity.WARNING
    assert diagnostic.location is None
    assert diagnostic.symbol_id is None
    assert diagnostic.reference_id is None


def test_diagnostic_accepts_all_fields() -> None:
    diagnostic = AnalysisDiagnostic(
        message="cyclic dependency",
        category="dependency-cycle",
        severity=AnalysisDiagnosticSeverity.ERROR,
        symbol_id="symbol:function:abc",
        reference_id="reference:abc",
    )

    assert diagnostic.severity == AnalysisDiagnosticSeverity.ERROR
    assert diagnostic.symbol_id == "symbol:function:abc"
    assert diagnostic.reference_id == "reference:abc"
