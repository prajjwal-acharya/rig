from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ScopeKind(str, Enum):
    REPOSITORY = "repository"
    PACKAGE = "package"
    FILE = "file"


@dataclass(frozen=True, kw_only=True)
class Scope:
    # Common base for all scope kinds below - not instantiated directly,
    # construct a concrete subclass instead. `symbol_ids` holds only the
    # names declared directly in this scope (not inherited from a parent).
    id: str
    name: str
    kind: ScopeKind
    parent_id: str | None = None
    symbol_ids: tuple[tuple[str, str], ...] = ()

    def lookup_local(self, name: str) -> str | None:
        for item_name, item_symbol_id in self.symbol_ids:
            if item_name == name:
                return item_symbol_id
        return None

    def names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.symbol_ids)

    def as_dict(self) -> dict[str, str]:
        return dict(self.symbol_ids)


@dataclass(frozen=True, kw_only=True)
class RepositoryScope(Scope):
    kind: ScopeKind = field(default=ScopeKind.REPOSITORY, init=False)


@dataclass(frozen=True, kw_only=True)
class PackageScope(Scope):
    kind: ScopeKind = field(default=ScopeKind.PACKAGE, init=False)


@dataclass(frozen=True, kw_only=True)
class FileScope(Scope):
    kind: ScopeKind = field(default=ScopeKind.FILE, init=False)
