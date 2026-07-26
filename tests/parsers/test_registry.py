from __future__ import annotations

import pytest

from rig.parsers.errors import DuplicateParserError
from rig.parsers.registry import ParserRegistry
from tests.parsers.conftest import FAKE_LANGUAGE, OTHER_LANGUAGE, FakeParser


def test_register_and_lookup() -> None:
    registry = ParserRegistry()
    parser = FakeParser()

    registry.register(parser)

    assert registry.lookup(FAKE_LANGUAGE) is parser


def test_lookup_unregistered_language_returns_none() -> None:
    registry = ParserRegistry()

    assert registry.lookup(OTHER_LANGUAGE) is None


def test_duplicate_registration_for_same_language_raises() -> None:
    registry = ParserRegistry()
    registry.register(FakeParser())

    with pytest.raises(DuplicateParserError):
        registry.register(FakeParser())


def test_constructor_accepts_initial_parsers() -> None:
    parser = FakeParser()

    registry = ParserRegistry([parser])

    assert registry.lookup(FAKE_LANGUAGE) is parser
    assert len(registry) == 1


def test_constructor_rejects_duplicates_immediately() -> None:
    with pytest.raises(DuplicateParserError):
        ParserRegistry([FakeParser(), FakeParser()])


def test_parsers_enumerates_all_registered_parsers() -> None:
    go_like = FakeParser(language=FAKE_LANGUAGE, parser_id="a")
    other = FakeParser(language=OTHER_LANGUAGE, parser_id="b")
    registry = ParserRegistry([go_like, other])

    assert set(registry.parsers()) == {go_like, other}


def test_contains_reflects_registered_languages() -> None:
    registry = ParserRegistry([FakeParser()])

    assert FAKE_LANGUAGE in registry
    assert OTHER_LANGUAGE not in registry


def test_len_reflects_registered_count() -> None:
    registry = ParserRegistry(
        [FakeParser(language=FAKE_LANGUAGE), FakeParser(language=OTHER_LANGUAGE)]
    )

    assert len(registry) == 2


def test_lookup_is_deterministic_across_repeated_calls() -> None:
    parser = FakeParser()
    registry = ParserRegistry([parser])

    first = registry.lookup(FAKE_LANGUAGE)
    second = registry.lookup(FAKE_LANGUAGE)

    assert first is second is parser
