from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from rig.plugins.errors import IncompatiblePluginError, InvalidManifestError
from rig.plugins.types import PluginType

CURRENT_API_VERSION = "1.0"

_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_API_VERSION_PATTERN = re.compile(r"^\d+\.\d+$")


@dataclass(frozen=True)
class PluginManifest:
    name: str
    version: str
    type: PluginType
    api_version: str
    description: str = ""
    author: str = ""
    min_rig_version: str | None = None
    max_tested_rig_version: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PluginManifest:
        try:
            name = str(data["name"])
            version = str(data["version"])
            plugin_type = PluginType(data["type"])
            api_version = str(data["api_version"])
        except KeyError as exc:
            raise InvalidManifestError(f"manifest is missing required field: {exc}") from exc
        except ValueError as exc:
            raise InvalidManifestError(f"manifest has an invalid field: {exc}") from exc

        return cls(
            name=name,
            version=version,
            type=plugin_type,
            api_version=api_version,
            description=str(data.get("description", "")),
            author=str(data.get("author", "")),
            min_rig_version=_optional_str(data.get("min_rig_version")),
            max_tested_rig_version=_optional_str(data.get("max_tested_rig_version")),
        )


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def validate_manifest(manifest: PluginManifest) -> None:
    errors = []
    if not _NAME_PATTERN.match(manifest.name):
        errors.append(f"invalid plugin name: {manifest.name!r}")
    if not _SEMVER_PATTERN.match(manifest.version):
        errors.append(f"invalid plugin version: {manifest.version!r} (expected MAJOR.MINOR.PATCH)")
    if not _API_VERSION_PATTERN.match(manifest.api_version):
        errors.append(f"invalid api_version: {manifest.api_version!r} (expected MAJOR.MINOR)")

    if errors:
        raise InvalidManifestError("; ".join(errors))


def check_api_compatibility(
    manifest: PluginManifest, supported_api_version: str = CURRENT_API_VERSION
) -> None:
    plugin_major = manifest.api_version.split(".")[0]
    supported_major = supported_api_version.split(".")[0]
    if plugin_major != supported_major:
        raise IncompatiblePluginError(
            f"plugin {manifest.name!r} declares api_version {manifest.api_version!r}, "
            f"incompatible with supported api_version {supported_api_version!r}"
        )
