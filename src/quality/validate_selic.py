from dataclasses import dataclass

import psycopg

from src.load.postgres_selic import get_connection


@dataclass(frozen=True)
class DataQualityCheck:
    """Representa uma regra de qualidade dos dados."""

    name: str
    query: str
    expected_value: int = 0


CHECKS = (
    DataQualityCheck(
        name="Sem datas duplicadas",
        query="""
            SELECT COUNT(*)
            FROM (
                SELECT reference_date
                FROM raw.selic
                GROUP BY reference_date
                HAVING COUNT(*) > 1
            ) AS duplicates;
        """,
    ),
    DataQualityCheck(
        name="Sem campos obrigatórios nulos",
        query="""
            SELECT COUNT(*)
            FROM raw.selic
            WHERE
                reference_date IS NULL
                OR value IS NULL
                OR series_code IS NULL
                OR extracted_at_utc IS NULL;
        """,
    ),
    DataQualityCheck(
        name="Sem valores menores ou iguais a zero",
        query="""
            SELECT COUNT(*)
            FROM raw.selic
            WHERE value <= 0;
        """,
    ),
    DataQualityCheck(
        name="Sem datas futuras",
        query="""
            SELECT COUNT(*)
            FROM raw.selic
            WHERE reference_date > CURRENT_DATE;
        """,
    ),
    DataQualityCheck(
        name="Contagem raw igual à staging",
        query="""
            SELECT ABS(
                (SELECT COUNT(*) FROM raw.selic)
                -
                (SELECT COUNT(*) FROM staging.selic_daily)
            );
        """,
    ),
    DataQualityCheck(
        name="Camada raw contém registros",
        query="""
            SELECT
                CASE
                    WHEN COUNT(*) > 0 THEN 0
                    ELSE 1
                END
            FROM raw.selic;
        """,
    ),
)


def run_quality_checks() -> list[str]:
    """Executa todos os checks e retorna os nomes das falhas."""

    failures: list[str] = []

    with get_connection() as connection:
        with connection.cursor() as cursor:
            for check in CHECKS:
                cursor.execute(check.query)
                result = cursor.fetchone()

                actual_value = int(result[0]) if result else -1

                if actual_value == check.expected_value:
                    print(f"[OK] {check.name}")
                else:
                    print(
                        f"[FALHA] {check.name}: "
                        f"resultado encontrado = {actual_value}"
                    )
                    failures.append(check.name)

    return failures


def main() -> None:
    try:
        failures = run_quality_checks()

        if failures:
            print()
            print("Qualidade dos dados reprovada.")
            print(f"Checks com falha: {len(failures)}")
            raise SystemExit(1)

        print()
        print(f"Qualidade aprovada: {len(CHECKS)}/{len(CHECKS)} checks.")

    except (ValueError, psycopg.Error) as error:
        print(f"Erro durante a validação: {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
