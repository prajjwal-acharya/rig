from __future__ import annotations

from rig.types.diagnostics import TypeDiagnostic, TypeDiagnosticSeverity
from tests.types.conftest import location


def test_default_severity_is_warning() -> None:
    diagnostic = TypeDiagnostic(message="oops")

    assert diagnostic.severity == TypeDiagnosticSeverity.WARNING
    assert diagnostic.location is None


def test_diagnostic_can_carry_a_location() -> None:
    loc = location("a.go")
    diagnostic = TypeDiagnostic(
        message="duplicate type", severity=TypeDiagnosticSeverity.ERROR, location=loc
    )

    assert diagnostic.location == loc
    assert diagnostic.severity == TypeDiagnosticSeverity.ERROR
