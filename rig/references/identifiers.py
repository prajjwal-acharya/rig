from __future__ import annotations

import hashlib

# Deliberately self-contained (mirrors rig.ir.identifiers / rig.graph.identifiers
# / rig.symbols.identifiers rather than importing any of them) - reference
# identity is a distinct namespace from IR, graph, and symbol ids.

_SEPARATOR = "\x1f"


def _digest(*parts: str) -> str:
    joined = _SEPARATOR.join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def reference_id(file_id: str, kind: str, start_byte: int, end_byte: int) -> str:
    # A (file, kind, byte span) triple is already naturally unique - two
    # distinct source occurrences can never share the same span.
    return f"reference:{_digest(file_id, kind, str(start_byte), str(end_byte))}"
