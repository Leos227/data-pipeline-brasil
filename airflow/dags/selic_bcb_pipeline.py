import os
from datetime import timedelta

import pendulum
from google.cloud.dataform_v1beta1 import WorkflowInvocation

from airflow.providers.google.cloud.operators.dataform import (
    DataformCreateCompilationResultOperator,
    DataformCreateWorkflowInvocationOperator,
)
from airflow.providers.google.cloud.sensors.dataform import (
    DataformWorkflowInvocationStateSensor,
)
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG


PROJECT_PATH = "/opt/airflow/project"

GCP_PROJECT_ID = os.getenv(
    "GCP_PROJECT_ID",
    "data-pipeline-brasil",
)

DATAFORM_REGION = os.getenv(
    "DATAFORM_REGION",
    "southamerica-east1",
)

DATAFORM_REPOSITORY_ID = os.getenv(
    "DATAFORM_REPOSITORY_ID",
    "data-pipeline-brasil",
)

DATAFORM_WORKSPACE_ID = os.getenv(
    "DATAFORM_WORKSPACE_ID",
    "dev-leo",
)

DATAFORM_WORKSPACE = (
    f"projects/{GCP_PROJECT_ID}"
    f"/locations/{DATAFORM_REGION}"
    f"/repositories/{DATAFORM_REPOSITORY_ID}"
    f"/workspaces/{DATAFORM_WORKSPACE_ID}"
)

GCP_CONN_ID = "google_cloud_default"


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

    load_bigquery = BashOperator(
        task_id="load_bigquery",
        bash_command=(
            f"cd {PROJECT_PATH} "
            "&& python -m src.load.bigquery_selic"
        ),
    )

    compile_dataform = DataformCreateCompilationResultOperator(
        task_id="compile_dataform",
        project_id=GCP_PROJECT_ID,
        region=DATAFORM_REGION,
        repository_id=DATAFORM_REPOSITORY_ID,
        compilation_result={
            "workspace": DATAFORM_WORKSPACE,
        },
        gcp_conn_id=GCP_CONN_ID,
    )

    run_dataform = DataformCreateWorkflowInvocationOperator(
        task_id="run_dataform",
        project_id=GCP_PROJECT_ID,
        region=DATAFORM_REGION,
        repository_id=DATAFORM_REPOSITORY_ID,
        workflow_invocation={
            "compilation_result": (
                "{{ task_instance.xcom_pull("
                "'compile_dataform'"
                ")['name'] }}"
            ),
        },
        asynchronous=True,
        gcp_conn_id=GCP_CONN_ID,
    )

    wait_dataform = DataformWorkflowInvocationStateSensor(
        task_id="wait_dataform",
        project_id=GCP_PROJECT_ID,
        region=DATAFORM_REGION,
        repository_id=DATAFORM_REPOSITORY_ID,
        workflow_invocation_id=(
            "{{ task_instance.xcom_pull("
            "'run_dataform'"
            ")['name'].split('/')[-1] }}"
        ),
        expected_statuses={
            WorkflowInvocation.State.SUCCEEDED,
        },
        failure_statuses={
            WorkflowInvocation.State.FAILED,
            WorkflowInvocation.State.CANCELLED,
        },
        poke_interval=10,
        timeout=600,
        mode="reschedule",
        gcp_conn_id=GCP_CONN_ID,
    )

    (
        extract_selic
        >> load_postgres
        >> transform_selic
        >> validate_quality
        >> load_bigquery
        >> compile_dataform
        >> run_dataform
        >> wait_dataform
    )
