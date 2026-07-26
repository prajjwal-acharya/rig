from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Capability:
    provides: str
    consumes: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
