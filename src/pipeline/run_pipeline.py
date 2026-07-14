import logging
import time

import psycopg
import requests

from src.extract.bcb_sgs import extract_selic, save_raw_data
from src.load.postgres_selic import (
    create_database_structure,
    get_connection,
    load_selic,
)
from src.quality.validate_selic import run_quality_checks
from src.transform.postgres_selic import execute_transformations


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | %(levelname)s | %(message)s"
    ),
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def run_pipeline(days: int = 30) -> None:
    """Executa o pipeline completo da Selic."""

    started_at = time.perf_counter()

    logger.info("Iniciando Data Pipeline Brasil.")

    logger.info("Etapa 1/4: extraindo dados da API do BCB.")
    payload = extract_selic(days=days)
    raw_file = save_raw_data(payload)

    logger.info(
        "Extração concluída: %s registros salvos em %s.",
        payload["record_count"],
        raw_file.name,
    )

    logger.info("Etapa 2/4: carregando dados no PostgreSQL.")

    with get_connection() as connection:
        create_database_structure(connection)

        loaded_records = load_selic(
            connection=connection,
            payload=payload,
        )

        logger.info(
            "Carga concluída: %s registros processados.",
            loaded_records,
        )

        logger.info(
            "Etapa 3/4: criando camadas staging e analytics."
        )

        execute_transformations(connection)

    logger.info("Transformações concluídas.")

    logger.info(
        "Etapa 4/4: executando validações de qualidade."
    )

    failures = run_quality_checks()

    if failures:
        failure_names = ", ".join(failures)

        raise RuntimeError(
            "Qualidade dos dados reprovada. "
            f"Checks com falha: {failure_names}"
        )

    elapsed_seconds = time.perf_counter() - started_at

    logger.info("Qualidade dos dados aprovada.")
    logger.info(
        "Pipeline concluído com sucesso em %.2f segundos.",
        elapsed_seconds,
    )


def main() -> None:
    try:
        run_pipeline()

    except (
        FileNotFoundError,
        OSError,
        ValueError,
        RuntimeError,
        requests.RequestException,
        psycopg.Error,
    ) as error:
        logger.exception("Pipeline interrompido: %s", error)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
