from __future__ import annotations

from rig.types.index import TypeIndex
from rig.types.model import Type


class TypeResolver:
    """Resolves a type name to a declared Type, scoped to either a single
    package or the whole repository. No import resolution: only names
    declared directly in the repository can be resolved - a future
    milestone that models imports would extend this, not replace it.
    """

    def __init__(self, index: TypeIndex) -> None:
        self._index = index

    def resolve_in_package(self, package: str, name: str) -> Type | None:
        for candidate in self._index.by_name(name):
            if candidate.package == package:
                return candidate
        return None

    def resolve_in_repository(self, name: str) -> Type | None:
        # If more than one package declares the same name, the lowest-id
        # match wins deterministically - disambiguating by caller context
        # is cross-package resolution, explicitly out of scope here.
        candidates = self._index.by_name(name)
        return candidates[0] if candidates else None
