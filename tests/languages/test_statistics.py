from __future__ import annotations

from rig.languages.model import UNKNOWN_LANGUAGE, Language
from rig.languages.statistics import LanguageCount, aggregate_language_counts

GO = Language(id="go", display_name="Go", extensions=frozenset({"go"}))
YAML = Language(id="yaml", display_name="YAML", extensions=frozenset({"yaml"}))
MARKDOWN = Language(id="markdown", display_name="Markdown", extensions=frozenset({"md"}))


def test_aggregates_counts_per_language() -> None:
    languages = [GO, GO, GO, YAML, MARKDOWN]

    result = aggregate_language_counts(languages)

    assert LanguageCount(language=GO, count=3) in result
    assert LanguageCount(language=YAML, count=1) in result
    assert LanguageCount(language=MARKDOWN, count=1) in result


def test_statistics_are_ordered_descending_by_count() -> None:
    languages = [YAML, GO, GO, GO, MARKDOWN, MARKDOWN]

    result = aggregate_language_counts(languages)

    assert [entry.count for entry in result] == [3, 2, 1]
    assert result[0].language == GO
    assert result[1].language == MARKDOWN
    assert result[2].language == YAML


def test_ties_are_broken_deterministically_by_display_name() -> None:
    languages = [GO, MARKDOWN, YAML]  # each appears exactly once

    first = aggregate_language_counts(languages)
    second = aggregate_language_counts(list(reversed(languages)))

    assert first == second
    assert [entry.language.display_name for entry in first] == ["Go", "Markdown", "YAML"]


def test_unknown_language_is_included_in_statistics() -> None:
    languages = [GO, UNKNOWN_LANGUAGE, UNKNOWN_LANGUAGE]

    result = aggregate_language_counts(languages)

    assert LanguageCount(language=UNKNOWN_LANGUAGE, count=2) in result


def test_empty_input_produces_empty_statistics() -> None:
    assert aggregate_language_counts([]) == ()


def test_aggregation_is_deterministic_across_repeated_calls() -> None:
    languages = [GO, YAML, MARKDOWN, GO, UNKNOWN_LANGUAGE]

    first = aggregate_language_counts(languages)
    second = aggregate_language_counts(languages)

    assert first == second
