from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

PropertyScalar = str | int | bool | float
PropertyValue = PropertyScalar | tuple[PropertyScalar, ...]


def _normalize_scalar(value: Any) -> PropertyScalar:
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, int, float)):
        return value
    raise TypeError(f"unsupported property list element type: {type(value).__name__}")


def _normalize_value(value: Any) -> PropertyValue:
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, int, float)):
        return value
    if isinstance(value, (list, tuple)):
        return tuple(_normalize_scalar(item) for item in value)
    raise TypeError(f"unsupported property value type: {type(value).__name__}")


@dataclass(frozen=True, slots=True)
class Properties:
    """Immutable string-keyed property bag attached to a Node or Edge.

    Values are restricted to str/int/bool/float, or tuples of those, so a
    Properties instance is always hashable and JSON-serializable.
    """

    _items: tuple[tuple[str, PropertyValue], ...] = field(default_factory=tuple)

    @classmethod
    def of(cls, **values: Any) -> Properties:
        return cls.from_mapping(values)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> Properties:
        normalized = tuple(sorted((key, _normalize_value(value)) for key, value in mapping.items()))
        return cls(_items=normalized)

    def get(self, key: str, default: PropertyValue | None = None) -> PropertyValue | None:
        for item_key, item_value in self._items:
            if item_key == key:
                return item_value
        return default

    def with_property(self, key: str, value: Any) -> Properties:
        merged = dict(self._items)
        merged[key] = _normalize_value(value)
        return Properties(_items=tuple(sorted(merged.items())))

    def items(self) -> tuple[tuple[str, PropertyValue], ...]:
        return self._items

    def as_dict(self) -> dict[str, PropertyValue]:
        return dict(self._items)

    def __getitem__(self, key: str) -> PropertyValue:
        for item_key, item_value in self._items:
            if item_key == key:
                return item_value
        raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        return any(item_key == key for item_key, _ in self._items)

    def __iter__(self) -> Iterator[str]:
        return (item_key for item_key, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)
