from __future__ import annotations

import threading

from rig.parsers.treesitter.backend import TreeSitterBackend
from rig.parsers.treesitter.grammars.go import GO_GRAMMAR
from tests.parsers.treesitter.conftest import INVALID_GO_SOURCE, VALID_GO_SOURCE


def test_parse_produces_a_syntax_tree() -> None:
    backend = TreeSitterBackend()

    tree = backend.parse(GO_GRAMMAR, VALID_GO_SOURCE.encode("utf-8"))

    assert tree.root.type == "source_file"
    assert tree.has_error is False


def test_parse_handles_invalid_source_without_raising() -> None:
    backend = TreeSitterBackend()

    tree = backend.parse(GO_GRAMMAR, INVALID_GO_SOURCE.encode("utf-8"))

    assert tree.has_error is True


def test_parse_handles_empty_source() -> None:
    backend = TreeSitterBackend()

    tree = backend.parse(GO_GRAMMAR, b"")

    assert tree.root.type == "source_file"
    assert tree.root.child_count == 0
    assert tree.has_error is False


def test_reuses_the_same_underlying_parser_for_repeated_calls() -> None:
    backend = TreeSitterBackend()

    first = backend._parser_for(GO_GRAMMAR)
    second = backend._parser_for(GO_GRAMMAR)

    assert first is second


def test_multiple_parses_on_the_same_backend_all_succeed() -> None:
    backend = TreeSitterBackend()

    for _ in range(50):
        tree = backend.parse(GO_GRAMMAR, VALID_GO_SOURCE.encode("utf-8"))
        assert tree.root.type == "source_file"


def test_parser_is_isolated_per_thread() -> None:
    backend = TreeSitterBackend()
    # Objects are kept alive here (not just their id()) so their lifetimes
    # overlap - otherwise a freed parser's address could be reused by the
    # next thread, making an id()-only comparison unreliable.
    seen: dict[int, object] = {}
    lock = threading.Lock()

    def worker() -> None:
        parser = backend._parser_for(GO_GRAMMAR)
        with lock:
            seen[threading.get_ident()] = parser

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # each thread got its own parser instance - no cross-thread sharing
    assert len({id(parser) for parser in seen.values()}) == len(threads)


def test_concurrent_parsing_does_not_raise() -> None:
    backend = TreeSitterBackend()
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            for _ in range(20):
                backend.parse(GO_GRAMMAR, VALID_GO_SOURCE.encode("utf-8"))
        except BaseException as exc:  # noqa: BLE001 - captured for the assertion below
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
