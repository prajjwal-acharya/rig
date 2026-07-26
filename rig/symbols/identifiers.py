from __future__ import annotations

import hashlib
from pathlib import Path

# Deliberately self-contained (mirrors rig.ir.identifiers / rig.graph.identifiers
# rather than importing either): symbol identity is a distinct namespace from
# both IR ids and graph node ids, by design - see the module docstring in
# model.py for why.

_SEPARATOR = "\x1f"


def _digest(*parts: str) -> str:
    joined = _SEPARATOR.join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def repository_scope_id(repository_id: str) -> str:
    return f"scope:repository:{_digest(repository_id)}"


def package_scope_id(repository_id: str, package_name: str) -> str:
    return f"scope:package:{_digest(repository_id, package_name)}"


def file_scope_id(repository_id: str, relative_path: Path) -> str:
    return f"scope:file:{_digest(repository_id, relative_path.as_posix())}"


def package_symbol_id(repository_id: str, package_name: str) -> str:
    return f"symbol:package:{_digest(repository_id, package_name)}"


def symbol_id(scope_id: str, kind: str, name: str, occurrence: int = 0) -> str:
    return f"symbol:{kind}:{_digest(scope_id, kind, name, str(occurrence))}"
