"""
Тестовый DAG с прямым импортом DataProc операторов
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.utils.dates import days_ago

# ПРЯМОЙ ИМПОРТ - как в рабочем DAG
from airflow.providers.yandex.operators.dataproc import (
    DataprocCreateClusterOperator,
    DataprocCreatePysparkJobOperator,
    DataprocDeleteClusterOperator
)

default_args = {
    'owner': 'test',
    'start_date': days_ago(1),
}

dag = DAG(
    'test_direct_dataproc_import',
    default_args=default_args,
    description='Test direct DataProc operators import',
    schedule_interval=None,
    catchup=False,
    tags=['test', 'dataproc', 'import'],
)

# Если DAG парсится без ошибок, значит импорт работает!
print("✅ DataProc операторы успешно импортированы!")
print(f"   DataprocCreateClusterOperator: {DataprocCreateClusterOperator}")
print(f"   DataprocCreatePysparkJobOperator: {DataprocCreatePysparkJobOperator}")
print(f"   DataprocDeleteClusterOperator: {DataprocDeleteClusterOperator}")
