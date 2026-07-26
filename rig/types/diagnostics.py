from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from rig.ir.model import SourceLocation


class TypeDiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, kw_only=True)
class TypeDiagnostic:
    message: str
    severity: TypeDiagnosticSeverity = TypeDiagnosticSeverity.WARNING
    location: SourceLocation | None = None
