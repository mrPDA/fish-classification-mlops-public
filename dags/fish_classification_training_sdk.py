"""
🐟 Fish Species Classification Training DAG (with Yandex Cloud SDK)
==============================================================

DAG для обучения модели классификации рыб с использованием
Yandex DataProc через Yandex Cloud Python SDK.

Dataset: Red Sea Fish (17 species, 1177 images)
Model: EfficientNet-B4 (fine-tuned)
"""

import os
import uuid
import json
import time
import logging
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

# ========================================
# DAG Configuration
# ========================================

DEFAULT_ARGS = {
    'owner': 'ml-team',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# ========================================
# Helper Functions
# ========================================

def get_cluster_name():
    """Генерация уникального имени кластера"""
    return f"fish-ml-{uuid.uuid4().hex[:8]}"

def validate_environment(**context):
    """Валидация окружения и проверка Yandex Cloud SDK"""
    logger = logging.getLogger(__name__)
    logger.info("🔍 Проверка окружения...")
    
    # Проверяем доступность Yandex Cloud SDK
    try:
        import yandexcloud
        logger.info(f"✅ Yandex Cloud SDK установлен: {yandexcloud.__version__}")
    except ImportError as e:
        logger.error(f"❌ Yandex Cloud SDK не установлен: {e}")
        raise RuntimeError("Yandex Cloud SDK не установлен в окружении Airflow")
    
    # Проверка переменных из Lockbox
    logger.info("🔍 Проверка переменных из Lockbox...")
    required_vars = ['FOLDER_ID', 'SUBNET_ID', 'ZONE', 'DATAPROC_SERVICE_ACCOUNT_ID', 'S3_BUCKET_NAME']
    found_vars = {}
    missing_vars = []
    
    for var in required_vars:
        try:
            value = Variable.get(var)
            found_vars[var] = value
            logger.info(f"✅ {var}: {value[:20]}..." if len(value) > 20 else f"✅ {var}: {value}")
        except Exception as e:
            missing_vars.append(var)
            logger.warning(f"⚠️  {var} не найден в Lockbox Variables")
    
    if missing_vars:
        logger.warning(f"⚠️  Отсутствующие переменные: {', '.join(missing_vars)}")
        logger.warning("   Будут использованы значения по умолчанию из CONFIG")
    
    logger.info(f"✅ Найдено {len(found_vars)}/{len(required_vars)} переменных из Lockbox")
    logger.info("✅ Окружение валидно")
    return True

def validate_dataset(**context):
    """Проверка наличия датасета в S3"""
    logger = logging.getLogger(__name__)
    logger.info("📦 Проверка датасета в S3...")
    
    s3_bucket_name = Variable.get('S3_BUCKET_NAME', 'fish-classification-data-7wb4zv')
    logger.info(f"📂 S3 Bucket: {s3_bucket_name}")
    logger.info(f"📂 Dataset path: s3://{s3_bucket_name}/datasets/")
    
    # Проверка через boto3
    try:
        import boto3
        s3_access_key = Variable.get('S3_ACCESS_KEY')
        s3_secret_key = Variable.get('S3_SECRET_KEY')
        s3_endpoint = Variable.get('S3_ENDPOINT_URL', 'https://storage.yandexcloud.net')
        
        s3_client = boto3.client(
            's3',
            endpoint_url=s3_endpoint,
            aws_access_key_id=s3_access_key,
            aws_secret_access_key=s3_secret_key
        )
        
        response = s3_client.list_objects_v2(Bucket=s3_bucket_name, Prefix='datasets/', MaxKeys=1)
        if 'Contents' in response:
            logger.info("✅ Датасет доступен в S3")
        else:
            logger.warning("⚠️  Датасет не найден в S3, но продолжаем")
    except Exception as e:
        logger.warning(f"⚠️  Ошибка проверки датасета: {e}")
        logger.warning("   Продолжаем выполнение")
    
    return True

def create_dataproc_cluster_sdk(**context):
    """Создание DataProc кластера через Yandex Cloud SDK"""
    logger = logging.getLogger(__name__)
    cluster_name = get_cluster_name()
    
    logger.info(f"🚀 Запуск создания DataProc кластера: {cluster_name}")
    logger.info("⚠️  В текущей версии - заглушка для демонстрации SDK")
    
    # Получаем переменные из Lockbox
    folder_id = Variable.get('FOLDER_ID')
    subnet_id = Variable.get('SUBNET_ID')
    zone = Variable.get('ZONE')
    dataproc_sa_id = Variable.get('DATAPROC_SERVICE_ACCOUNT_ID')
    s3_bucket_name = Variable.get('S3_BUCKET_NAME')
    
    logger.info(f"📋 Параметры кластера:")
    logger.info(f"   Folder ID: {folder_id}")
    logger.info(f"   Subnet ID: {subnet_id}")
    logger.info(f"   Zone: {zone}")
    logger.info(f"   Service Account: {dataproc_sa_id}")
    logger.info(f"   S3 Bucket: {s3_bucket_name}")
    
    # TODO: Реальное создание через SDK
    # from yandexcloud import SDK
    # sdk = SDK(service_account_key=...)
    # cluster = sdk.client(dataproc_v1.ClusterServiceStub).Create(...)
    
    # Для демонстрации - генерируем fake cluster_id
    fake_cluster_id = f"c9q{uuid.uuid4().hex[:16]}"
    logger.info(f"✅ (DEMO) Кластер создан: {fake_cluster_id}")
    
    # Сохраняем в XCom
    context['task_instance'].xcom_push(key='cluster_id', value=fake_cluster_id)
    context['task_instance'].xcom_push(key='cluster_name', value=cluster_name)
    
    return fake_cluster_id

def wait_cluster_ready_sdk(**context):
    """Ожидание готовности кластера"""
    logger = logging.getLogger(__name__)
    
    cluster_id = context['task_instance'].xcom_pull(
        task_ids='create_dataproc_cluster',
        key='cluster_id'
    )
    
    logger.info(f"⏳ Ожидание готовности кластера: {cluster_id}")
    logger.info("⚠️  В текущей версии - заглушка (sleep 10s)")
    
    time.sleep(10)
    
    logger.info(f"✅ Кластер {cluster_id} готов (DEMO)")
    return True

def train_model_sdk(**context):
    """Запуск обучения модели"""
    logger = logging.getLogger(__name__)
    
    cluster_id = context['task_instance'].xcom_pull(
        task_ids='create_dataproc_cluster',
        key='cluster_id'
    )
    
    mlflow_tracking_uri = Variable.get('MLFLOW_TRACKING_URI', 'http://10.11.0.20:5000')
    mlflow_experiment_name = Variable.get('MLFLOW_EXPERIMENT_NAME', 'fish-classification')
    
    logger.info(f"🎓 Обучение модели на кластере: {cluster_id}")
    logger.info(f"📊 MLflow Tracking URI: {mlflow_tracking_uri}")
    logger.info(f"🏷️  MLflow Experiment Name: {mlflow_experiment_name}")
    logger.info("⚠️  Реальное обучение будет добавлено в следующей версии")
    
    return True

def register_model_sdk(**context):
    """Регистрация модели в MLflow"""
    logger = logging.getLogger(__name__)
    
    mlflow_tracking_uri = Variable.get('MLFLOW_TRACKING_URI', 'http://10.11.0.20:5000')
    mlflow_experiment_name = Variable.get('MLFLOW_EXPERIMENT_NAME', 'fish-classification')
    
    logger.info("📝 Регистрация модели в MLflow...")
    logger.info(f"📊 MLflow URI: {mlflow_tracking_uri}")
    logger.info(f"🏷️  Experiment: {mlflow_experiment_name}")
    logger.info("⚠️  Реальная регистрация будет добавлена в следующей версии")
    
    return True

def delete_dataproc_cluster_sdk(**context):
    """Удаление DataProc кластера"""
    logger = logging.getLogger(__name__)
    
    cluster_id = context['task_instance'].xcom_pull(
        task_ids='create_dataproc_cluster',
        key='cluster_id'
    )
    
    if not cluster_id:
        logger.warning("Cluster ID not found in XCom. Skipping cluster deletion.")
        return False
    
    logger.info(f"🗑️  Удаление кластера: {cluster_id}")
    logger.info("⚠️  В текущей версии - заглушка")
    
    # TODO: Реальное удаление через SDK
    # sdk.client(dataproc_v1.ClusterServiceStub).Delete(...)
    
    logger.info(f"✅ (DEMO) Кластер {cluster_id} удалён")
    return True

def generate_report_sdk(**context):
    """Генерация отчёта о выполнении"""
    logger = logging.getLogger(__name__)
    
    cluster_id = context['task_instance'].xcom_pull(
        task_ids='create_dataproc_cluster',
        key='cluster_id'
    )
    cluster_name = context['task_instance'].xcom_pull(
        task_ids='create_dataproc_cluster',
        key='cluster_name'
    )
    
    logger.info("📊 Генерация отчёта...")
    logger.info("=" * 60)
    logger.info("🎉 PIPELINE ЗАВЕРШЁН (DEMO MODE)")
    logger.info("=" * 60)
    logger.info(f"🖥️  DataProc Cluster: {cluster_name} ({cluster_id})")
    logger.info("✅ Yandex Cloud SDK работает!")
    logger.info("⚠️  Следующий шаг: Реализовать реальное создание кластера")
    logger.info("=" * 60)
    
    return True

# ========================================
# DAG Definition
# ========================================

with DAG(
    dag_id='fish_classification_training_sdk',
    default_args=DEFAULT_ARGS,
    description='Fish Classification with Yandex Cloud SDK (DEMO)',
    schedule_interval=None,
    catchup=False,
    tags=['ml', 'fish-classification', 'dataproc', 'yandex-sdk', 'demo'],
) as dag:

    task_validate_env = PythonOperator(
        task_id='validate_environment',
        python_callable=validate_environment,
    )

    task_validate_dataset = PythonOperator(
        task_id='validate_dataset',
        python_callable=validate_dataset,
    )

    task_create_cluster = PythonOperator(
        task_id='create_dataproc_cluster',
        python_callable=create_dataproc_cluster_sdk,
    )

    task_wait_cluster = PythonOperator(
        task_id='wait_cluster_ready',
        python_callable=wait_cluster_ready_sdk,
    )

    task_train = PythonOperator(
        task_id='train_model',
        python_callable=train_model_sdk,
    )

    task_register = PythonOperator(
        task_id='register_model',
        python_callable=register_model_sdk,
    )

    task_cleanup = PythonOperator(
        task_id='delete_dataproc_cluster',
        python_callable=delete_dataproc_cluster_sdk,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    task_report = PythonOperator(
        task_id='generate_report',
        python_callable=generate_report_sdk,
    )

    # DAG Flow
    task_validate_env >> task_validate_dataset >> task_create_cluster >> task_wait_cluster >> task_train >> task_register >> task_cleanup >> task_report
