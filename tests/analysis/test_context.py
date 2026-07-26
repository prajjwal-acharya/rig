from __future__ import annotations

import dataclasses

import pytest

from rig.analysis.context import AnalysisContext, AnalysisLogger, CancellationToken
from rig.symbols.table import SymbolTable
from tests.analysis.conftest import make_repository


def test_context_requires_only_repository() -> None:
    context = AnalysisContext(repository=make_repository())

    assert context.symbols is None
    assert context.references is None
    assert context.graph is None
    assert context.config == {}
    assert context.cancellation_token is None
    assert context.logger is None


def test_context_accepts_symbols() -> None:
    symbols = SymbolTable()
    context = AnalysisContext(repository=make_repository(), symbols=symbols)

    assert context.symbols is symbols


def test_context_is_immutable() -> None:
    context = AnalysisContext(repository=make_repository())

    with pytest.raises(dataclasses.FrozenInstanceError):
        context.config = {}  # type: ignore[misc]


def test_cancellation_token_defaults_to_not_cancelled() -> None:
    token = CancellationToken()

    assert token.is_cancelled is False


def test_cancellation_token_can_be_cancelled() -> None:
    token = CancellationToken()

    token.cancel()

    assert token.is_cancelled is True


def test_analysis_logger_does_not_raise() -> None:
    logger = AnalysisLogger("test")

    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
