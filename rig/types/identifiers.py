from __future__ import annotations

import hashlib

# Deliberately self-contained (mirrors rig.ir.identifiers / rig.symbols.identifiers
# / rig.references.identifiers rather than importing any of them) - type
# identity is its own namespace, independently reasoned, the same way every
# other package's identifier scheme is.

_SEPARATOR = "\x1f"


def _digest(*parts: str) -> str:
    joined = _SEPARATOR.join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def type_id(declaration_id: str) -> str:
    # A TypeDeclaration maps to exactly one Type, unlike symbols (which
    # disambiguate same-name declarations with an `occurrence` counter) -
    # the declaration id alone is already unique per type declaration.
    return f"type:{_digest(declaration_id)}"
