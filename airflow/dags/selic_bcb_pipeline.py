from datetime import timedelta

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG


PROJECT_PATH = "/opt/airflow/project"


with DAG(
    dag_id="selic_bcb_pipeline",
    description="Pipeline da taxa Selic do Banco Central do Brasil.",
    start_date=pendulum.datetime(
        2026,
        1,
        1,
        tz="America/Sao_Paulo",
    ),
    schedule="0 6 * * *",
    catchup=False,
    default_args={
        "owner": "Leonardo",
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
    },
    tags=[
        "data-pipeline-brasil",
        "selic",
        "banco-central",
    ],
) as dag:
    extract_selic = BashOperator(
        task_id="extract_selic",
        bash_command=(
            f"cd {PROJECT_PATH} "
            "&& python -m src.extract.bcb_sgs"
        ),
    )

    load_postgres = BashOperator(
        task_id="load_postgres",
        bash_command=(
            f"cd {PROJECT_PATH} "
            "&& python -m src.load.postgres_selic"
        ),
    )

    transform_selic = BashOperator(
        task_id="transform_selic",
        bash_command=(
            f"cd {PROJECT_PATH} "
            "&& python -m src.transform.postgres_selic"
        ),
    )

    validate_quality = BashOperator(
        task_id="validate_quality",
        bash_command=(
            f"cd {PROJECT_PATH} "
            "&& python -m src.quality.validate_selic"
        ),
    )

    (
        extract_selic
        >> load_postgres
        >> transform_selic
        >> validate_quality
    )
