from __future__ import annotations

import pytest

from rig.plugins.errors import IncompatiblePluginError, InvalidManifestError
from rig.plugins.manifest import PluginManifest, check_api_compatibility, validate_manifest
from rig.plugins.types import PluginType
from tests.plugins.conftest import make_manifest


def test_valid_manifest_passes_validation() -> None:
    validate_manifest(make_manifest())


def test_rejects_invalid_name() -> None:
    manifest = make_manifest(name="Not A Valid Name!")

    with pytest.raises(InvalidManifestError):
        validate_manifest(manifest)


def test_rejects_invalid_version() -> None:
    manifest = make_manifest(version="not-semver")

    with pytest.raises(InvalidManifestError):
        validate_manifest(manifest)


def test_rejects_invalid_api_version() -> None:
    manifest = make_manifest(api_version="one-point-oh")

    with pytest.raises(InvalidManifestError):
        validate_manifest(manifest)


def test_from_dict_builds_manifest() -> None:
    manifest = PluginManifest.from_dict(
        {
            "name": "python-parser",
            "version": "1.0.0",
            "type": "language",
            "api_version": "1.0",
            "description": "Python language parser",
        }
    )

    assert manifest.name == "python-parser"
    assert manifest.type == PluginType.LANGUAGE
    assert manifest.description == "Python language parser"


def test_from_dict_missing_required_field_raises() -> None:
    with pytest.raises(InvalidManifestError):
        PluginManifest.from_dict({"name": "incomplete", "version": "1.0.0"})


def test_from_dict_invalid_type_raises() -> None:
    with pytest.raises(InvalidManifestError):
        PluginManifest.from_dict(
            {
                "name": "bad-type",
                "version": "1.0.0",
                "type": "not-a-real-type",
                "api_version": "1.0",
            }
        )


def test_api_compatibility_matches_major_version() -> None:
    manifest = make_manifest(api_version="1.5")

    check_api_compatibility(manifest, supported_api_version="1.0")


def test_api_compatibility_rejects_mismatched_major_version() -> None:
    manifest = make_manifest(api_version="2.0")

    with pytest.raises(IncompatiblePluginError):
        check_api_compatibility(manifest, supported_api_version="1.0")
