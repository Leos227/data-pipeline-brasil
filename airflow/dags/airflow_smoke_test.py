from datetime import datetime, timezone

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG


with DAG(
    dag_id="airflow_smoke_test",
    description="Valida o ambiente Airflow do Data Pipeline Brasil.",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    schedule=None,
    catchup=False,
    default_args={
        "owner": "Leonardo",
        "retries": 1,
    },
    tags=["data-pipeline-brasil", "smoke-test"],
) as dag:
    check_environment = BashOperator(
        task_id="check_environment",
        bash_command=(
            'echo "Airflow funcionando corretamente" '
            "&& python --version"
        ),
    )
