from pathlib import Path
from typing import Any

import psycopg

from src.load.postgres_selic import get_connection


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRANSFORMATION_FILE = (
    PROJECT_ROOT / "sql" / "002_create_selic_analytics.sql"
)


def execute_transformations(
    connection: psycopg.Connection[Any],
) -> None:
    """Cria ou atualiza as views staging e analytics."""

    if not TRANSFORMATION_FILE.exists():
        raise FileNotFoundError(
            f"Arquivo SQL não encontrado: {TRANSFORMATION_FILE}"
        )

    sql = TRANSFORMATION_FILE.read_text(encoding="utf-8")

    with connection.cursor() as cursor:
        cursor.execute(sql)


def run_transformations() -> None:
    """Executa as transformações usando uma nova conexão."""

    with get_connection() as connection:
        execute_transformations(connection)


def main() -> None:
    try:
        run_transformations()
        print("Transformações executadas com sucesso.")

    except (
        FileNotFoundError,
        OSError,
        ValueError,
        psycopg.Error,
    ) as error:
        print(f"Erro durante as transformações: {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
