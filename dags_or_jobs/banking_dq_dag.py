from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from airflow.utils.email import send_email
from airflow.operators.python import PythonOperator
import logging
from datetime import timedelta

# Default args
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def alert_on_failure(context):
    logging.error(f"Task failed: {context['task_instance'].task_id}")
    print(f"ALERT: Task failed: {context['task_instance'].task_id}")

with DAG(
    'banking_data_quality_dag',
    default_args=default_args,
    description='Banking Data Quality Daily Checks',
    schedule_interval='@daily',
    start_date=days_ago(1),
    catchup=False,
    tags=['banking', 'data-quality'],
) as dag:

    generate_data = BashOperator(
        task_id='generate_data',
        bash_command='python src/generate_data.py',
        do_xcom_push=False,
        on_failure_callback=alert_on_failure,
    )

    dq_standards = BashOperator(
        task_id='data_quality_standards',
        bash_command='python src/data_quality_standards.py',
        do_xcom_push=False,
        on_failure_callback=alert_on_failure,
    )

    monitoring_audit = BashOperator(
        task_id='monitoring_audit',
        bash_command='python src/monitoring_audit.py',
        do_xcom_push=False,
        on_failure_callback=alert_on_failure,
    )

    generate_data >> dq_standards >> monitoring_audit 