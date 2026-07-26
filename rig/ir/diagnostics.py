from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from rig.ir.model import SourceLocation


class IRDiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, kw_only=True)
class IRDiagnostic:
    message: str
    severity: IRDiagnosticSeverity = IRDiagnosticSeverity.WARNING
    location: SourceLocation | None = None
