import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIRECTORY = PROJECT_ROOT / "data" / "raw"
SQL_FILE = PROJECT_ROOT / "sql" / "001_create_raw_selic.sql"

load_dotenv(PROJECT_ROOT / ".env")


def get_connection() -> psycopg.Connection[Any]:
    """Cria uma conexão com o PostgreSQL executado pelo Docker."""

    required_variables = [
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_PORT",
    ]

    missing_variables = [
        variable
        for variable in required_variables
        if not os.getenv(variable)
    ]

    if missing_variables:
        missing = ", ".join(missing_variables)
        raise ValueError(f"Variáveis ausentes no .env: {missing}")

    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.environ["POSTGRES_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def find_latest_raw_file() -> Path:
    """Localiza o arquivo JSON mais recente da Selic."""

    files = list(RAW_DIRECTORY.glob("selic_*.json"))

    if not files:
        raise FileNotFoundError(
            "Nenhum arquivo selic_*.json encontrado em data/raw."
        )

    return max(files, key=lambda file: file.stat().st_mtime)


def read_payload(file_path: Path) -> dict[str, Any]:
    """Lê e valida o conteúdo básico do arquivo raw."""

    payload = json.loads(file_path.read_text(encoding="utf-8"))

    if not isinstance(payload.get("records"), list):
        raise ValueError("O arquivo não contém uma lista em 'records'.")

    return payload


def create_database_structure(
    connection: psycopg.Connection[Any],
) -> None:
    """Cria o schema e a tabela, caso ainda não existam."""

    sql = SQL_FILE.read_text(encoding="utf-8")

    with connection.cursor() as cursor:
        cursor.execute(sql)


def load_selic(
    connection: psycopg.Connection[Any],
    payload: dict[str, Any],
) -> int:
    """Carrega os registros no PostgreSQL de forma idempotente."""

    query = """
        INSERT INTO raw.selic (
            reference_date,
            value,
            series_code,
            extracted_at_utc,
            source_payload
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (reference_date)
        DO UPDATE SET
            value = EXCLUDED.value,
            series_code = EXCLUDED.series_code,
            extracted_at_utc = EXCLUDED.extracted_at_utc,
            loaded_at_utc = CURRENT_TIMESTAMP,
            source_payload = EXCLUDED.source_payload;
    """

    extracted_at = datetime.fromisoformat(payload["extracted_at_utc"])
    series_code = int(payload["series_code"])

    rows = []

    for record in payload["records"]:
        reference_date = datetime.strptime(
            record["data"],
            "%d/%m/%Y",
        ).date()

        rows.append(
            (
                reference_date,
                Decimal(record["valor"]),
                series_code,
                extracted_at,
                Jsonb(record),
            )
        )

    with connection.cursor() as cursor:
        cursor.executemany(query, rows)

    return len(rows)


def main() -> None:
    try:
        raw_file = find_latest_raw_file()
        payload = read_payload(raw_file)

        with get_connection() as connection:
            create_database_structure(connection)
            loaded_records = load_selic(connection, payload)

        print("Carregamento concluído com sucesso.")
        print(f"Arquivo processado: {raw_file.name}")
        print(f"Registros carregados: {loaded_records}")

    except (
        FileNotFoundError,
        ValueError,
        OSError,
        psycopg.Error,
    ) as error:
        print(f"Erro durante o carregamento: {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
