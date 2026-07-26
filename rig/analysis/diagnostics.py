from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from rig.ir.model import SourceLocation


class AnalysisDiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, kw_only=True)
class AnalysisDiagnostic:
    message: str
    category: str
    severity: AnalysisDiagnosticSeverity = AnalysisDiagnosticSeverity.WARNING
    location: SourceLocation | None = None
    symbol_id: str | None = None
    reference_id: str | None = None
