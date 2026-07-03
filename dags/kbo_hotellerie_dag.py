import sys
sys.path.insert(0, "/opt/airflow/kbo_scripts")

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


default_args = {
    "owner": "kbo_pipeline",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def task_seed_hotellerie():
    from seed_state_hotellerie import seed_hotellerie
    seed_hotellerie()


def task_scrape_nbb_hotellerie():
    from consult import run_hotellerie_scraping
    run_hotellerie_scraping()


def task_report():
    from state_report import print_report
    print_report()


with DAG(
    dag_id="kbo_hotellerie_pipeline",
    description="Filtre hotellerie + scraping NBB cible + suivi StateDB",
    default_args=default_args,
    schedule=None,          # déclenchement manuel ; mettre "@daily" pour un run quotidien
    start_date=datetime(2026, 7, 1),
    catchup=False,
    tags=["kbo", "hotellerie", "nbb"],
) as dag:

    seed = PythonOperator(
        task_id="seed_state_hotellerie",
        python_callable=task_seed_hotellerie,
    )

    scrape_nbb = PythonOperator(
        task_id="scrape_nbb_hotellerie",
        python_callable=task_scrape_nbb_hotellerie,
    )

    report = PythonOperator(
        task_id="state_report",
        python_callable=task_report,
    )

    seed >> scrape_nbb >> report