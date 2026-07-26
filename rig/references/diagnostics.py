from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from rig.ir.model import SourceLocation


class ReferenceDiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, kw_only=True)
class ReferenceDiagnostic:
    message: str
    severity: ReferenceDiagnosticSeverity = ReferenceDiagnosticSeverity.WARNING
    location: SourceLocation | None = None
