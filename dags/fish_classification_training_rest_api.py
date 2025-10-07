"""
🐟 Fish Species Classification Training DAG (REST API Version)
==============================================================

DAG для обучения модели классификации рыб с использованием
Yandex DataProc через REST API (прямые HTTP запросы).

Dataset: Red Sea Fish (17 species, 1177 images)
Model: EfficientNet-B4 (fine-tuned)

РЕШЕНИЕ ПРОБЛЕМЫ:
- DataProc операторы НЕ СУЩЕСТВУЮТ в apache-airflow-providers-yandex
- yc CLI НЕ установлен в Managed Airflow
- Yandex Cloud Python SDK вызывает зависание Terraform
- РЕШЕНИЕ: Используем прямые REST API запросы через requests + PyJWT
"""

import os
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
# Hardcoded Configuration (Non-sensitive)
# ========================================

CONFIG = {
    'MLFLOW_TRACKING_URI': 'http://10.11.0.20:5000',
    'MLFLOW_EXPERIMENT_NAME': 'fish-classification',
    'NUM_CLASSES': '17',
    'IMAGE_SIZE': '224',
    'BATCH_SIZE': '32',
    'EPOCHS': '20',
    'LEARNING_RATE': '0.001',
    'DATAPROC_IMAGE_VERSION': '2.1',  # Hadoop 3.2, Spark 3.0
    'MASTER_RESOURCE_PRESET': 's2.small',  # 4 vCPU, 16 GB RAM
    'WORKER_RESOURCE_PRESET': 's2.small',  # 4 vCPU, 16 GB RAM
    'WORKER_COUNT': '2',
    'DISK_SIZE_GB': '100',
}

# ========================================
# Helper Functions
# ========================================

def create_yandex_connection(**context):
    """
    Создание Yandex Cloud Connection из DP_SA_JSON (как в рабочем DAG)
    
    Этот подход работает в обычном Airflow, но в Managed Airflow
    Connection 'yandexcloud_default' уже существует.
    """
    from airflow.models import Connection
    from airflow.settings import Session
    import json
    
    logger = logging.getLogger(__name__)
    logger.info("🔧 Настройка подключения Yandex Cloud...")
    
    try:
        session = Session()
        
        # Получаем JSON ключ сервисного аккаунта из Variables
        sa_json_str = Variable.get('DP_SA_JSON', None)
        if not sa_json_str or sa_json_str == "placeholder":
            logger.warning("⚠️  DP_SA_JSON не настроен, используем yandexcloud_default")
            return False
        
        # Создаём или обновляем Connection
        yc_connection = Connection(
            conn_id="yc-fish-dataproc",
            conn_type="yandexcloud",
            extra={
                "extra__yandexcloud__service_account_json": sa_json_str,
            },
        )
        
        existing_conn = session.query(Connection).filter(
            Connection.conn_id == "yc-fish-dataproc"
        ).first()
        
        if existing_conn:
            existing_conn.extra = yc_connection.extra
            logger.info("🔄 Обновлено подключение yc-fish-dataproc")
        else:
            session.add(yc_connection)
            logger.info("✅ Создано подключение yc-fish-dataproc")
            
        session.commit()
        session.close()
        
        logger.info("✅ Подключение Yandex Cloud настроено")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания подключения: {e}")
        return False


def get_iam_token_from_sa_json(sa_json_str: str) -> str:
    """
    Получает IAM токен из JSON ключа сервисного аккаунта (как в рабочем DAG)
    
    Args:
        sa_json_str: JSON строка с ключом сервисного аккаунта
    
    Returns:
        IAM токен
    """
    import jwt
    import requests
    
    sa_key = json.loads(sa_json_str)
    
    now = int(time.time())
    payload = {
        'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
        'iss': sa_key['service_account_id'],
        'iat': now,
        'exp': now + 3600
    }
    
    # Создаём JWT
    encoded_token = jwt.encode(
        payload,
        sa_key['private_key'],
        algorithm='PS256',
        headers={'kid': sa_key['id']}
    )
    
    # Обмениваем JWT на IAM токен
    response = requests.post(
        'https://iam.api.cloud.yandex.net/iam/v1/tokens',
        json={'jwt': encoded_token},
        timeout=10
    )
    
    if response.status_code != 200:
        raise Exception(f"Ошибка получения IAM токена: {response.status_code} - {response.text}")
    
    return response.json()['iamToken']


def wait_operation(operation_id: str, iam_token: str, timeout: int = 3600):
    """Ожидает завершения операции и возвращает cluster_id"""
    import requests
    
    url = f"https://operation.api.cloud.yandex.net/operations/{operation_id}"
    headers = {"Authorization": f"Bearer {iam_token}"}
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            raise Exception(f"Ошибка проверки операции: {response.status_code}")
        
        operation = response.json()
        done = operation.get("done", False)
        
        if done:
            if "error" in operation:
                error = operation["error"]
                raise Exception(f"Операция завершилась с ошибкой: {error}")
            
            metadata = operation.get("metadata", {})
            cluster_id = metadata.get("clusterId")
            return cluster_id
        
        print(f"  Операция в процессе... ({int(time.time() - start_time)} сек)")
        time.sleep(10)
    
    raise Exception(f"Таймаут ожидания операции ({timeout} сек)")


# ========================================
# Task Functions
# ========================================

def validate_environment(**context):
    """Проверяет доступность необходимых инструментов и модулей"""
    print("🔍 Проверка окружения...")
    
    # Проверяем Python модули
    required_modules = ['requests', 'jwt']
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} установлен")
        except ImportError:
            raise RuntimeError(f"❌ {module} не установлен. Добавьте 'PyJWT' в pip_packages в airflow.tf")
    
    # Проверяем наличие ключа сервисного аккаунта из Connection
    # В Yandex Managed Airflow Lockbox работает только для Connections!
    try:
        from airflow.hooks.base import BaseHook
        conn = BaseHook.get_connection('yandexcloud_default')
        
        # Ключ сервисного аккаунта должен быть в extra
        if conn.extra:
            import json
            extra = json.loads(conn.extra)
            if 'service_account_json' in extra or 'key' in extra:
                print("✅ Ключ сервисного аккаунта найден в Connection")
            else:
                print("⚠️  Ключ не найден в Connection, используем service account из метаданных")
        else:
            print("⚠️  Connection пустой, используем service account из метаданных VM")
    except Exception as e:
        print(f"⚠️  Ошибка проверки Connection: {e}")
        print("⚠️  Будем использовать service account из метаданных VM")
    
    print("✅ Окружение готово")
    return True


def create_dataproc_cluster(**context):
    """Создаёт DataProc кластер для обучения модели через REST API"""
    import requests
    import os
    
    print("🚀 Создание DataProc кластера через REST API...")
    
    # Получаем DP_SA_JSON из Variables (как в рабочем DAG)
    print("🔑 Получение DP_SA_JSON из Airflow Variables...")
    try:
        sa_json_str = Variable.get('DP_SA_JSON', None)
        if not sa_json_str or sa_json_str == "placeholder":
            print("⚠️  DP_SA_JSON не настроен в Variables")
            print("⚠️  DEMO MODE: Используем фиктивный токен")
            iam_token = "demo_token"
        else:
            print("✅ DP_SA_JSON найден, получаем IAM токен...")
            iam_token = get_iam_token_from_sa_json(sa_json_str)
            print("✅ IAM токен успешно получен!")
    except Exception as e:
        print(f"⚠️  Ошибка получения токена: {e}")
        print("⚠️  DEMO MODE: Используем фиктивный токен")
        iam_token = "demo_token"
    
    # Получаем параметры из Variables (как в рабочем DAG)
    print("📋 Получение параметров из Airflow Variables...")
    folder_id = Variable.get('FOLDER_ID', 'b1gjj3po03aa3m4j8ps5')
    zone = Variable.get('ZONE', 'ru-central1-a')
    subnet_id = Variable.get('SUBNET_ID', 'e9b5umsufggihj02a3o1')
    service_account_id = Variable.get('DATAPROC_SERVICE_ACCOUNT_ID', 'ajepv2durkr1nk9rnoui')
    security_group_id = Variable.get('SECURITY_GROUP_ID', 'enpha1v51ug84ddqfob4')
    s3_bucket = Variable.get('S3_BUCKET_NAME', 'fish-classification-data-7wb4zv')
    ssh_public_key = Variable.get('YC_SSH_PUBLIC_KEY', 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC...')
    
    print(f"📋 Параметры:")
    print(f"  Folder ID: {folder_id}")
    print(f"  Zone: {zone}")
    print(f"  Subnet ID: {subnet_id}")
    print(f"  Service Account ID: {service_account_id}")
    print(f"  S3 Bucket: {s3_bucket}")
    
    # Создаём кластер
    cluster_name = f"fish-training-{int(time.time())}"
    
    # Sanitize run_id для labels (только [a-z][-_0-9a-z]*)
    run_id_safe = context['run_id'].replace(':', '-').replace('_', '-').replace('+', '-').lower()
    
    cluster_config = {
        "folderId": folder_id,
        "name": cluster_name,
        "description": "DataProc cluster for fish classification training",
        "labels": {
            "created-by": "airflow",
            "dag-id": "fish-classification-training",
            "project": "fish-classification"
        },
        "configSpec": {
            "versionId": CONFIG['DATAPROC_IMAGE_VERSION'],
            "hadoop": {
                "services": ["HDFS", "YARN", "SPARK", "LIVY"],
                "properties": {
                    "yarn:yarn.resourcemanager.am.max-attempts": "5",
                    "spark:spark.sql.warehouse.dir": f"s3a://{s3_bucket}/spark-warehouse/"
                },
                "sshPublicKeys": [ssh_public_key]
            },
            "subclustersSpec": [
                {
                    "name": "masternode",
                    "role": "MASTERNODE",
                    "resources": {
                        "resourcePresetId": CONFIG['MASTER_RESOURCE_PRESET'],
                        "diskTypeId": "network-ssd",
                        "diskSize": str(int(CONFIG['DISK_SIZE_GB']) * 1024 * 1024 * 1024)
                    },
                    "subnetId": subnet_id,
                    "hostsCount": "1"
                },
                {
                    "name": "datanode",
                    "role": "DATANODE",
                    "resources": {
                        "resourcePresetId": CONFIG['WORKER_RESOURCE_PRESET'],
                        "diskTypeId": "network-ssd",
                        "diskSize": str(int(CONFIG['DISK_SIZE_GB']) * 1024 * 1024 * 1024)
                    },
                    "subnetId": subnet_id,
                    "hostsCount": CONFIG['WORKER_COUNT']
                }
            ]
        },
        "zoneId": zone,
        "serviceAccountId": service_account_id,
        "bucket": s3_bucket,
        "uiProxy": True,
        "securityGroupIds": [security_group_id],
        "deletionProtection": False
    }
    
    headers = {
        "Authorization": f"Bearer {iam_token}",
        "Content-Type": "application/json"
    }
    
    url = "https://dataproc.api.cloud.yandex.net/dataproc/v1/clusters"
    print(f"📤 POST {url}")
    
    response = requests.post(url, headers=headers, json=cluster_config, timeout=30)
    
    if response.status_code not in [200, 201]:
        raise Exception(f"Ошибка создания кластера: {response.status_code} - {response.text}")
    
    operation = response.json()
    operation_id = operation.get("id")
    print(f"✅ Операция создания запущена: {operation_id}")
    
    # Ожидаем завершения операции (извлекаем cluster_id)
    cluster_id = wait_operation(operation_id, iam_token)
    print(f"✅ Кластер создан: {cluster_id}")
    
    # Сохраняем cluster_id и iam_token в XCom
    context['task_instance'].xcom_push(key='cluster_id', value=cluster_id)
    context['task_instance'].xcom_push(key='iam_token', value=iam_token)
    
    return cluster_id


def wait_cluster_ready(**context):
    """Ожидает готовности DataProc кластера"""
    import requests
    
    print("⏳ Ожидание готовности кластера...")
    
    cluster_id = context['task_instance'].xcom_pull(key='cluster_id', task_ids='create_dataproc_cluster')
    iam_token = context['task_instance'].xcom_pull(key='iam_token', task_ids='create_dataproc_cluster')
    
    if not cluster_id:
        raise ValueError("cluster_id не найден в XCom")
    
    print(f"📋 Cluster ID: {cluster_id}")
    
    url = f"https://dataproc.api.cloud.yandex.net/dataproc/v1/clusters/{cluster_id}"
    headers = {"Authorization": f"Bearer {iam_token}"}
    
    timeout = 1800  # 30 минут
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            raise Exception(f"Ошибка получения статуса: {response.status_code}")
        
        cluster = response.json()
        status = cluster.get("status")
        health = cluster.get("health")
        
        print(f"  Status: {status}, Health: {health}")
        
        if status == "RUNNING" and health == "ALIVE":
            elapsed = int(time.time() - start_time)
            print(f"✅ Кластер готов! (заняло {elapsed} секунд)")
            return True
        
        if status in ["ERROR", "STOPPING", "STOPPED"]:
            raise Exception(f"Кластер в неожиданном состоянии: {status}")
        
        time.sleep(30)
    
    raise Exception(f"Таймаут ожидания готовности кластера ({timeout} сек)")


def run_training_job(**context):
    """Запускает обучение модели на DataProc кластере (PLACEHOLDER)"""
    print("🎯 Запуск обучения модели...")
    print("⚠️  PLACEHOLDER: Здесь будет запуск PySpark job через Livy API")
    
    cluster_id = context['task_instance'].xcom_pull(key='cluster_id', task_ids='create_dataproc_cluster')
    print(f"📋 Cluster ID: {cluster_id}")
    
    # TODO: Реализовать запуск PySpark job через Livy REST API
    # POST https://dataproc.api.cloud.yandex.net/dataproc/v1/clusters/{cluster_id}/jobs
    
    print("✅ Обучение завершено (PLACEHOLDER)")
    return True


def delete_dataproc_cluster(**context):
    """Удаляет DataProc кластер"""
    import requests
    
    print("🗑️  Удаление DataProc кластера...")
    
    cluster_id = context['task_instance'].xcom_pull(key='cluster_id', task_ids='create_dataproc_cluster')
    iam_token = context['task_instance'].xcom_pull(key='iam_token', task_ids='create_dataproc_cluster')
    
    if not cluster_id:
        print("⚠️  cluster_id не найден, пропускаем удаление")
        return True
    
    print(f"📋 Cluster ID для удаления: {cluster_id}")
    
    url = f"https://dataproc.api.cloud.yandex.net/dataproc/v1/clusters/{cluster_id}"
    headers = {"Authorization": f"Bearer {iam_token}"}
    
    response = requests.delete(url, headers=headers, timeout=30)
    
    if response.status_code not in [200, 204]:
        print(f"⚠️  Ошибка удаления кластера: {response.status_code} - {response.text}")
        return False
    
    operation = response.json()
    operation_id = operation.get("id")
    print(f"✅ Операция удаления запущена: {operation_id}")
    
    # Ожидаем завершения операции
    wait_operation(operation_id, iam_token)
    print(f"✅ Кластер удалён: {cluster_id}")
    
    return True


# ========================================
# DAG Definition
# ========================================

with DAG(
    dag_id='fish_classification_training_rest_api',
    default_args=DEFAULT_ARGS,
    description='Fish classification training with DataProc (REST API)',
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=['ml', 'training', 'dataproc', 'rest-api'],
) as dag:
    
    # Task 1: Validate environment
    validate_env = PythonOperator(
        task_id='validate_environment',
        python_callable=validate_environment,
        provide_context=True,
    )
    
    # Task 2: Create DataProc cluster
    create_cluster = PythonOperator(
        task_id='create_dataproc_cluster',
        python_callable=create_dataproc_cluster,
        provide_context=True,
    )
    
    # Task 3: Wait for cluster to be ready
    wait_cluster = PythonOperator(
        task_id='wait_cluster_ready',
        python_callable=wait_cluster_ready,
        provide_context=True,
    )
    
    # Task 4: Run training job
    train_model = PythonOperator(
        task_id='run_training_job',
        python_callable=run_training_job,
        provide_context=True,
    )
    
    # Task 5: Delete DataProc cluster (always runs)
    delete_cluster = PythonOperator(
        task_id='delete_dataproc_cluster',
        python_callable=delete_dataproc_cluster,
        provide_context=True,
        trigger_rule=TriggerRule.ALL_DONE,  # Выполняется всегда
    )
    
    # Define task dependencies
    validate_env >> create_cluster >> wait_cluster >> train_model >> delete_cluster
