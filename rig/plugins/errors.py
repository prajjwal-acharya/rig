from __future__ import annotations


class PluginError(Exception):
    pass


class InvalidManifestError(PluginError):
    pass


class DuplicatePluginError(PluginError):
    pass


class PluginNotFoundError(PluginError):
    pass


class IncompatiblePluginError(PluginError):
    pass
