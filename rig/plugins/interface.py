from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import ClassVar

from rig.plugins.capability import Capability
from rig.plugins.context import PluginContext
from rig.plugins.manifest import PluginManifest


class Plugin(ABC):
    # A ClassVar (not an abstract property) so discovery can read a plugin's
    # manifest straight off the class, before it is ever instantiated.
    manifest: ClassVar[PluginManifest]

    @abstractmethod
    def initialize(self, context: PluginContext) -> None: ...

    @abstractmethod
    def register(self) -> Sequence[Capability]: ...

    @abstractmethod
    def shutdown(self) -> None: ...
