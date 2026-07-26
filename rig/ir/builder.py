from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rig.ir.diagnostics import IRDiagnostic
from rig.ir.model import File


class DuplicateIRBuilderError(ValueError):
    pass


@dataclass(frozen=True, kw_only=True)
class FileBuildResult:
    file: File
    diagnostics: tuple[IRDiagnostic, ...] = ()


class IRBuilder(ABC):
    """Generic contract: consume a parsed syntax tree, produce IR.

    `tree` is intentionally typed `Any` here - same reserved-slot pattern as
    `ParseResult.syntax_tree` - so this framework never imports anything
    backend-specific (Tree-sitter or otherwise). Concrete builders narrow it
    to whatever their backend actually produces.
    """

    @property
    @abstractmethod
    def language_id(self) -> str: ...

    @abstractmethod
    def build_file(self, repository_id: str, relative_path: Path, tree: Any) -> FileBuildResult: ...


class IRBuilderRegistry:
    def __init__(self, builders: Iterable[IRBuilder] = ()) -> None:
        self._lock = threading.Lock()
        self._by_language_id: dict[str, IRBuilder] = {}
        for builder in builders:
            self.register(builder)

    def register(self, builder: IRBuilder) -> None:
        with self._lock:
            existing = self._by_language_id.get(builder.language_id)
            if existing is not None:
                raise DuplicateIRBuilderError(
                    f"a builder is already registered for language {builder.language_id!r}"
                )
            self._by_language_id[builder.language_id] = builder

    def lookup(self, language_id: str) -> IRBuilder | None:
        return self._by_language_id.get(language_id)

    def builders(self) -> tuple[IRBuilder, ...]:
        return tuple(self._by_language_id.values())

    def __len__(self) -> int:
        return len(self._by_language_id)

    def __contains__(self, language_id: str) -> bool:
        return language_id in self._by_language_id
