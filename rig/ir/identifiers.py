from __future__ import annotations

import hashlib
from pathlib import Path

_SEPARATOR = "\x1f"


def _digest(*parts: str) -> str:
    joined = _SEPARATOR.join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def repository_id(root: Path) -> str:
    return f"repository:{_digest(str(root))}"


def file_id(repository_id_: str, relative_path: Path) -> str:
    return f"file:{_digest(repository_id_, relative_path.as_posix())}"


def package_id(repository_id_: str, package_name: str) -> str:
    return f"package:{_digest(repository_id_, package_name)}"


def declaration_id(file_id_: str, kind: str, name: str, occurrence: int = 0) -> str:
    # `occurrence` disambiguates otherwise-identical (kind, name) pairs within
    # one file - malformed or duplicate source must not collide identifiers.
    return f"declaration:{_digest(file_id_, kind, name, str(occurrence))}"
