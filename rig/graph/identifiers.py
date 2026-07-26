from __future__ import annotations

import hashlib

# Node identifiers are NOT minted here - a Node reuses the IR object's own
# `.id` (declaration_id/file_id/package_id/repository_id) directly. This
# module only generates identifiers for edges, which have no IR-level
# equivalent to reuse.

_SEPARATOR = "\x1f"


def _digest(*parts: str) -> str:
    joined = _SEPARATOR.join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def edge_id(source: str, target: str, relationship: str, occurrence: int = 0) -> str:
    return f"edge:{_digest(source, target, relationship, str(occurrence))}"
