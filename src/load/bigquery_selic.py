from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google.cloud import bigquery

from src.load.postgres_selic import (
    find_latest_raw_file,
    read_payload,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CREATE_TABLE_FILE = (
    PROJECT_ROOT
    / "sql"
    / "bigquery"
    / "001_create_raw_selic.sql"
)


def get_bigquery_client() -> bigquery.Client:
    """Cria o cliente do BigQuery usando as credenciais locais."""

    load_dotenv(PROJECT_ROOT / ".env")

    project_id = os.getenv("GCP_PROJECT_ID")

    if not project_id:
        raise ValueError(
            "A variável GCP_PROJECT_ID não foi configurada."
        )

    return bigquery.Client(project=project_id)


def prepare_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Converte os registros do BCB para o schema do BigQuery."""

    records = payload.get("records")

    if not isinstance(records, list):
        raise ValueError(
            "O payload não contém uma lista válida em 'records'."
        )

    extracted_at_utc = payload.get("extracted_at_utc")
    series_code = payload.get("series_code")

    if not extracted_at_utc:
        raise ValueError(
            "O payload não contém extracted_at_utc."
        )

    if series_code is None:
        raise ValueError(
            "O payload não contém series_code."
        )

    rows_by_date: dict[str, dict[str, Any]] = {}

    for record in records:
        reference_date = datetime.strptime(
            record["data"],
            "%d/%m/%Y",
        ).date().isoformat()

        row = {
            "reference_date": reference_date,
            "value": str(record["valor"]).replace(",", "."),
            "series_code": int(series_code),
            "extracted_at_utc": extracted_at_utc,
            "source_payload": json.dumps(
                record,
                ensure_ascii=False,
            ),
        }

        rows_by_date[reference_date] = row

    return list(rows_by_date.values())


def create_target_table(
    client: bigquery.Client,
    project_id: str,
    location: str,
) -> None:
    """Cria a tabela raw.selic caso ela ainda não exista."""

    if not CREATE_TABLE_FILE.exists():
        raise FileNotFoundError(
            f"SQL não encontrado: {CREATE_TABLE_FILE}"
        )

    sql = CREATE_TABLE_FILE.read_text(
        encoding="utf-8"
    ).format(
        project_id=project_id
    )

    client.query(
        sql,
        location=location,
    ).result()


def load_selic_to_bigquery() -> int:
    """Carrega o JSON mais recente na camada raw do BigQuery."""

    load_dotenv(PROJECT_ROOT / ".env")

    location = os.getenv(
        "BIGQUERY_LOCATION",
        "southamerica-east1",
    )

    dataset = os.getenv(
        "BIGQUERY_RAW_DATASET",
        "raw",
    )

    client = get_bigquery_client()
    project_id = client.project

    raw_file = find_latest_raw_file()
    payload = read_payload(raw_file)
    rows = prepare_rows(payload)

    if not rows:
        raise ValueError(
            "Nenhum registro foi encontrado para carregar."
        )

    create_target_table(
        client=client,
        project_id=project_id,
        location=location,
    )

    target_table = (
        f"{project_id}.{dataset}.selic"
    )

    temporary_table = (
        f"{project_id}.{dataset}."
        f"_selic_stage_{uuid.uuid4().hex[:12]}"
    )

    schema = [
        bigquery.SchemaField(
            "reference_date",
            "DATE",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "value",
            "NUMERIC",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "series_code",
            "INTEGER",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "extracted_at_utc",
            "TIMESTAMP",
            mode="REQUIRED",
        ),
        bigquery.SchemaField(
            "source_payload",
            "STRING",
            mode="REQUIRED",
        ),
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=(
            bigquery.WriteDisposition.WRITE_TRUNCATE
        ),
    )

    try:
        load_job = client.load_table_from_json(
            rows,
            temporary_table,
            job_config=job_config,
            location=location,
        )

        load_job.result()

        merge_sql = f"""
            MERGE `{target_table}` AS target
            USING `{temporary_table}` AS source
                ON target.reference_date = source.reference_date

            WHEN MATCHED THEN
                UPDATE SET
                    value = source.value,
                    series_code = source.series_code,
                    extracted_at_utc = source.extracted_at_utc,
                    loaded_at_utc = CURRENT_TIMESTAMP(),
                    source_payload = source.source_payload

            WHEN NOT MATCHED THEN
                INSERT
                (
                    reference_date,
                    value,
                    series_code,
                    extracted_at_utc,
                    loaded_at_utc,
                    source_payload
                )
                VALUES
                (
                    source.reference_date,
                    source.value,
                    source.series_code,
                    source.extracted_at_utc,
                    CURRENT_TIMESTAMP(),
                    source.source_payload
                );
        """

        merge_job = client.query(
            merge_sql,
            location=location,
        )

        merge_job.result()

    finally:
        client.delete_table(
            temporary_table,
            not_found_ok=True,
        )

    return len(rows)


def main() -> None:
    try:
        loaded_records = load_selic_to_bigquery()

        print(
            "Carga no BigQuery concluída: "
            f"{loaded_records} registros processados."
        )

    except Exception as error:
        print(
            f"Erro durante a carga no BigQuery: {error}"
        )
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
