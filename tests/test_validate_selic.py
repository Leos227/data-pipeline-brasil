from collections.abc import Iterator
from typing import Any

import pytest

from src.quality import validate_selic


class FakeCursor:
    """Retorna resultados simulados para cada check."""

    def __init__(self, results: list[int]) -> None:
        self.results: Iterator[int] = iter(results)
        self.executed_queries: list[str] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        return None

    def execute(self, query: str) -> None:
        self.executed_queries.append(query)

    def fetchone(self) -> tuple[int]:
        return (next(self.results),)


class FakeConnection:
    """Simula uma conexão usada pelos checks."""

    def __init__(self, results: list[int]) -> None:
        self.cursor_instance = FakeCursor(results)

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self.cursor_instance


def test_quality_checks_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Aprova a base quando todos os resultados são zero."""

    results = [0] * len(validate_selic.CHECKS)
    connection = FakeConnection(results)

    monkeypatch.setattr(
        validate_selic,
        "get_connection",
        lambda: connection,
    )

    failures = validate_selic.run_quality_checks()

    assert failures == []
    assert len(connection.cursor_instance.executed_queries) == len(
        validate_selic.CHECKS
    )


def test_quality_checks_report_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retorna o nome do check que encontrou anomalia."""

    results = [0] * len(validate_selic.CHECKS)
    results[0] = 2

    connection = FakeConnection(results)

    monkeypatch.setattr(
        validate_selic,
        "get_connection",
        lambda: connection,
    )

    failures = validate_selic.run_quality_checks()

    assert failures == ["Sem datas duplicadas"]
