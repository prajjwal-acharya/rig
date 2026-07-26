from __future__ import annotations

from pathlib import Path

from rig.ir.diagnostics import IRDiagnostic, IRDiagnosticSeverity
from rig.ir.model import SourceLocation


def test_diagnostic_defaults_to_warning_severity() -> None:
    diagnostic = IRDiagnostic(message="something is off")

    assert diagnostic.severity == IRDiagnosticSeverity.WARNING
    assert diagnostic.location is None


def test_diagnostic_accepts_explicit_severity_and_location() -> None:
    location = SourceLocation(
        relative_path=Path("main.go"), start_line=1, start_column=0, end_line=1, end_column=3
    )
    diagnostic = IRDiagnostic(
        message="unsupported construct", severity=IRDiagnosticSeverity.ERROR, location=location
    )

    assert diagnostic.severity == IRDiagnosticSeverity.ERROR
    assert diagnostic.location is location
