from __future__ import annotations

from rig.references.diagnostics import ReferenceDiagnostic, ReferenceDiagnosticSeverity


def test_diagnostic_defaults_to_warning_severity() -> None:
    diagnostic = ReferenceDiagnostic(message="unresolved reference to 'x'")

    assert diagnostic.severity == ReferenceDiagnosticSeverity.WARNING
    assert diagnostic.location is None


def test_diagnostic_accepts_explicit_severity() -> None:
    diagnostic = ReferenceDiagnostic(
        message="ambiguous", severity=ReferenceDiagnosticSeverity.ERROR
    )

    assert diagnostic.severity == ReferenceDiagnosticSeverity.ERROR
