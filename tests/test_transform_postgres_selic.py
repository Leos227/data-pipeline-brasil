from pathlib import Path
from typing import Any

import pytest

from src.transform import postgres_selic


class FakeCursor:
    """Simula um cursor do PostgreSQL."""

    def __init__(self) -> None:
        self.executed_sql: list[str] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        return None

    def execute(self, sql: str) -> None:
        self.executed_sql.append(sql)


class FakeConnection:
    """Simula uma conexão com o PostgreSQL."""

    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()

    def cursor(self) -> FakeCursor:
        return self.cursor_instance


def test_execute_transformations_runs_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Executa o conteúdo do arquivo de transformação."""

    sql_file = tmp_path / "transformations.sql"
    sql_file.write_text(
        "CREATE VIEW staging.test AS SELECT 1;",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        postgres_selic,
        "TRANSFORMATION_FILE",
        sql_file,
    )

    connection = FakeConnection()

    postgres_selic.execute_transformations(connection)  # type: ignore[arg-type]

    assert connection.cursor_instance.executed_sql == [
        "CREATE VIEW staging.test AS SELECT 1;"
    ]


def test_execute_transformations_rejects_missing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Interrompe a execução quando o SQL não existe."""

    missing_file = tmp_path / "missing.sql"

    monkeypatch.setattr(
        postgres_selic,
        "TRANSFORMATION_FILE",
        missing_file,
    )

    connection = FakeConnection()

    with pytest.raises(
        FileNotFoundError,
        match="Arquivo SQL não encontrado",
    ):
        postgres_selic.execute_transformations(  # type: ignore[arg-type]
            connection
        )
