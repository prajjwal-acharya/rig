from __future__ import annotations

from abc import ABC, abstractmethod

from rig.languages.model import Language
from rig.parsers.model import ParseContext, ParseResult


class Parser(ABC):
    @property
    @abstractmethod
    def language(self) -> Language: ...

    @property
    @abstractmethod
    def parser_id(self) -> str: ...

    @property
    def parser_version(self) -> str | None:
        return None

    @abstractmethod
    def parse(self, context: ParseContext) -> ParseResult: ...
