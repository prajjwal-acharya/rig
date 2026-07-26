from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from rig.languages.model import Language


class DuplicateLanguageMappingError(ValueError):
    pass


class LanguageRegistry:
    def __init__(self, languages: Iterable[Language]) -> None:
        materialized = tuple(languages)
        by_extension: dict[str, Language] = {}
        by_filename: dict[str, Language] = {}

        for language in materialized:
            for extension in language.extensions:
                existing = by_extension.get(extension)
                if existing is not None and existing is not language:
                    raise DuplicateLanguageMappingError(
                        f"extension {extension!r} is claimed by both "
                        f"{existing.id!r} and {language.id!r}"
                    )
                by_extension[extension] = language

            for filename in language.filenames:
                existing = by_filename.get(filename)
                if existing is not None and existing is not language:
                    raise DuplicateLanguageMappingError(
                        f"filename {filename!r} is claimed by both "
                        f"{existing.id!r} and {language.id!r}"
                    )
                by_filename[filename] = language

        self._by_extension: Mapping[str, Language] = MappingProxyType(by_extension)
        self._by_filename: Mapping[str, Language] = MappingProxyType(by_filename)
        self._languages: tuple[Language, ...] = materialized

    def lookup_extension(self, extension: str) -> Language | None:
        return self._by_extension.get(extension)

    def lookup_filename(self, filename: str) -> Language | None:
        return self._by_filename.get(filename)

    def languages(self) -> tuple[Language, ...]:
        return self._languages

    def __len__(self) -> int:
        return len(self._languages)
