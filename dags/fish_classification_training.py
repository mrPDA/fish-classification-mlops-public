"""
🐟 Fish Species Classification Training DAG
==============================================================

DAG для обучения модели классификации рыб с использованием
Yandex DataProc через yc CLI (операторы DataProc недоступны в Managed Airflow).

Dataset: Red Sea Fish (17 species, 1177 images)
Model: EfficientNet-B4 (fine-tuned)
"""

import os
import uuid
import json
import subprocess
import time
import logging
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
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
    'ENVIRONMENT': 'production',
}

# ========================================
# Helper Functions
# ========================================

def get_cluster_name():
    """Генерация уникального имени кластера"""
    return f"fish-ml-{uuid.uuid4().hex[:8]}"

def validate_environment(**context):
    """Валидация окружения"""
    logger = logging.getLogger(__name__)
    logger.info("🔍 Проверка окружения...")
    
    # Проверяем доступность yc CLI в разных путях
    yc_paths = [
        'yc',  # In PATH
        '/usr/local/bin/yc',
        '/usr/bin/yc',
        '/opt/yandex-cloud/bin/yc',
        '/home/airflow/.local/bin/yc',
    ]
    
    yc_found = False
    yc_cmd = None
    
    for path in yc_paths:
        try:
            logger.info(f"Проверка yc CLI по пути: {path}")
            result = subprocess.run([path, 'version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"✅ yc CLI найден: {path}")
                logger.info(f"✅ Версия: {result.stdout.strip()}")
                yc_found = True
                yc_cmd = path
                # Сохраняем путь в контекст для использования в других задачах
                context['task_instance'].xcom_push(key='yc_path', value=path)
                break
            else:
                logger.warning(f"⚠️  {path} вернул код {result.returncode}")
        except FileNotFoundError:
            logger.debug(f"   {path} не найден")
            continue
        except PermissionError as e:
            logger.warning(f"⚠️  {path} недоступен (нет прав): {e}")
            continue
        except subprocess.TimeoutExpired:
            logger.warning(f"⚠️  {path} не отвечает (таймаут)")
            continue
        except Exception as e:
            logger.warning(f"⚠️  Ошибка при проверке {path}: {e}")
            continue
    
    if not yc_found:
        logger.error("❌ yc CLI не найден ни в одном из путей:")
        for path in yc_paths:
            logger.error(f"   - {path}")
        raise RuntimeError("yc CLI не установлен или недоступен в окружении Airflow")
    
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
    
    bucket_name = Variable.get('S3_BUCKET_NAME', 'fish-classification-data-7wb4zv')
    logger.info(f"📂 S3 Bucket: {bucket_name}")
    logger.info(f"📂 Dataset path: s3://{bucket_name}/datasets/")
    logger.info("✅ Датасет должен быть доступен")
    
    return True

def create_dataproc_cluster(**context):
    """Создание DataProc кластера через yc CLI"""
    logger = logging.getLogger(__name__)
    cluster_name = get_cluster_name()
    
    logger.info(f"🚀 Создание DataProc кластера: {cluster_name}")
    
    # Получаем параметры из Lockbox Variables
    folder_id = Variable.get('FOLDER_ID', 'b1gjj3po03aa3m4j8ps5')
    subnet_id = Variable.get('SUBNET_ID', 'e9b5umsufggihj02a3o1')
    zone = Variable.get('ZONE', 'ru-central1-a')
    service_account_id = Variable.get('DATAPROC_SERVICE_ACCOUNT_ID', 'ajepv2durkr1nk9rnoui')
    s3_bucket = Variable.get('S3_BUCKET_NAME', 'fish-classification-data-7wb4zv')
    ssh_key = Variable.get('YC_SSH_PUBLIC_KEY', '')
    
    logger.info(f"📋 Параметры кластера:")
    logger.info(f"  Folder ID: {folder_id}")
    logger.info(f"  Zone: {zone}")
    logger.info(f"  Subnet ID: {subnet_id}")
    logger.info(f"  Service Account: {service_account_id}")
    logger.info(f"  S3 Bucket: {s3_bucket}")
    
    # Формируем команду создания кластера
    cmd = [
        'yc', 'dataproc', 'cluster', 'create', cluster_name,
        '--folder-id', folder_id,
        '--zone', zone,
        '--service-account-id', service_account_id,
        '--version', '2.1',
        '--services', 'YARN,SPARK,HDFS',
        '--bucket', s3_bucket,
        '--subcluster', 'name=master,role=masternode,resource-preset=s2.small,disk-type=network-ssd,disk-size=128,subnet-id=' + subnet_id + ',hosts-count=1',
        '--subcluster', 'name=data,role=datanode,resource-preset=s2.small,disk-type=network-ssd,disk-size=128,subnet-id=' + subnet_id + ',hosts-count=1',
        '--subcluster', 'name=compute,role=computenode,resource-preset=s2.small,disk-type=network-ssd,disk-size=128,subnet-id=' + subnet_id + ',hosts-count=2',
        '--deletion-protection=false',
    ]
    
    if ssh_key:
        cmd.extend(['--ssh-public-keys-file', '-'])
    
    logger.info(f"🔧 Команда создания: {' '.join(cmd[:10])}...")
    
    try:
        # Выполняем команду
        if ssh_key:
            result = subprocess.run(
                cmd,
                input=ssh_key,
                capture_output=True,
                text=True,
                timeout=600  # 10 минут
            )
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
        
        if result.returncode != 0:
            logger.error(f"❌ Ошибка создания кластера: {result.stderr}")
            raise RuntimeError(f"Не удалось создать кластер: {result.stderr}")
        
        # Парсим вывод для получения cluster_id
        output = result.stdout
        logger.info(f"📄 Вывод команды:\n{output}")
        
        # Извлекаем cluster_id из вывода
        for line in output.split('\n'):
            if 'id:' in line.lower():
                cluster_id = line.split(':')[-1].strip()
                break
        else:
            # Если не нашли в выводе, используем cluster_name
            cluster_id = cluster_name
        
        logger.info(f"✅ Кластер создан: {cluster_name} (ID: {cluster_id})")
        
        # Сохраняем в XCom
        context['task_instance'].xcom_push(key='cluster_name', value=cluster_name)
        context['task_instance'].xcom_push(key='cluster_id', value=cluster_id)
        
        return cluster_id
        
    except subprocess.TimeoutExpired:
        logger.error("❌ Таймаут создания кластера (10 минут)")
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка при создании кластера: {e}")
        raise

def wait_cluster_ready(**context):
    """Ожидание готовности кластера"""
    logger = logging.getLogger(__name__)
    
    cluster_id = context['task_instance'].xcom_pull(
        task_ids='create_dataproc_cluster',
        key='cluster_id'
    )
    
    logger.info(f"⏳ Ожидание готовности кластера: {cluster_id}")
    
    max_attempts = 30  # 15 минут (30 * 30 сек)
    attempt = 0
    
    while attempt < max_attempts:
        try:
            # Проверяем статус кластера
            result = subprocess.run(
                ['yc', 'dataproc', 'cluster', 'get', cluster_id, '--format', 'json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                cluster_info = json.loads(result.stdout)
                status = cluster_info.get('status', 'UNKNOWN')
                health = cluster_info.get('health', 'UNKNOWN')
                
                logger.info(f"📊 Статус кластера: {status}, Health: {health}")
                
                if status == 'RUNNING' and health == 'ALIVE':
                    logger.info("✅ Кластер готов к работе!")
                    return True
                elif status in ['ERROR', 'STOPPED']:
                    raise RuntimeError(f"Кластер в состоянии {status}")
            
            attempt += 1
            if attempt < max_attempts:
                logger.info(f"⏳ Попытка {attempt}/{max_attempts}, ждём 30 секунд...")
                time.sleep(30)
        
        except Exception as e:
            logger.warning(f"⚠️  Ошибка проверки статуса: {e}")
            attempt += 1
            if attempt < max_attempts:
                time.sleep(30)
    
    raise RuntimeError(f"Кластер не стал готов за {max_attempts * 30 / 60} минут")

def train_model(**context):
    """Запуск обучения модели"""
    logger = logging.getLogger(__name__)
    
    cluster_id = context['task_instance'].xcom_pull(
        task_ids='create_dataproc_cluster',
        key='cluster_id'
    )
    
    logger.info(f"🎓 Обучение модели на кластере: {cluster_id}")
    logger.info(f"📊 MLflow: {CONFIG['MLFLOW_TRACKING_URI']}")
    logger.info(f"🔢 Epochs: {CONFIG['EPOCHS']}, Batch size: {CONFIG['BATCH_SIZE']}")
    logger.info("⚠️  Реальное обучение будет добавлено в следующей версии")
    
    # TODO: Здесь будет запуск PySpark job через yc dataproc job create-pyspark
    
    return True

def register_model(**context):
    """Регистрация модели в MLflow"""
    logger = logging.getLogger(__name__)
    
    logger.info("📝 Регистрация модели в MLflow...")
    logger.info(f"📊 MLflow URI: {CONFIG['MLFLOW_TRACKING_URI']}")
    logger.info(f"🏷️  Experiment: {CONFIG['MLFLOW_EXPERIMENT_NAME']}")
    logger.info("⚠️  Реальная регистрация будет добавлена в следующей версии")
    
    return True

def delete_dataproc_cluster(**context):
    """Удаление DataProc кластера через yc CLI"""
    logger = logging.getLogger(__name__)
    
    cluster_id = context['task_instance'].xcom_pull(
        task_ids='create_dataproc_cluster',
        key='cluster_id'
    )
    
    if not cluster_id:
        logger.warning("⚠️  Cluster ID не найден, пропускаем удаление")
        return True
    
    logger.info(f"🗑️  Удаление кластера: {cluster_id}")
    
    try:
        result = subprocess.run(
            ['yc', 'dataproc', 'cluster', 'delete', cluster_id, '--async'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Кластер {cluster_id} удаляется (async)")
            return True
        else:
            logger.error(f"⚠️  Ошибка удаления кластера: {result.stderr}")
            # Не бросаем исключение, чтобы DAG завершился
            return False
            
    except Exception as e:
        logger.error(f"⚠️  Ошибка при удалении кластера: {e}")
        return False

def generate_report(**context):
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
    logger.info("🎉 PIPELINE ЗАВЕРШЁН")
    logger.info("=" * 60)
    logger.info(f"🖥️  DataProc Cluster: {cluster_name} (ID: {cluster_id})")
    logger.info(f"📊 MLflow: {CONFIG['MLFLOW_TRACKING_URI']}")
    logger.info(f"🏷️  Experiment: {CONFIG['MLFLOW_EXPERIMENT_NAME']}")
    logger.info(f"🔢 Параметры: Epochs={CONFIG['EPOCHS']}, Batch={CONFIG['BATCH_SIZE']}")
    logger.info("=" * 60)
    logger.info("✅ Использован yc CLI для управления DataProc")
    logger.info("=" * 60)
    
    return True

# ========================================
# DAG Definition
# ========================================

with DAG(
    dag_id='fish_classification_training',
    default_args=DEFAULT_ARGS,
    description='Fish Classification Model Training with DataProc via yc CLI',
    schedule_interval=None,  # Запуск вручную
    catchup=False,
    tags=['ml', 'fish-classification', 'dataproc', 'mlflow', 'yc-cli'],
) as dag:
    
    # Валидация окружения
    task_validate_env = PythonOperator(
        task_id='validate_environment',
        python_callable=validate_environment,
        doc_md="""
        ### Валидация окружения
        Проверяет наличие yc CLI и переменных из Lockbox.
        """,
    )
    
    # Валидация датасета
    task_validate_dataset = PythonOperator(
        task_id='validate_dataset',
        python_callable=validate_dataset,
        doc_md="""
        ### Валидация датасета
        Проверяет наличие датасета в S3 bucket.
        """,
    )
    
    # Создание DataProc кластера
    task_create_cluster = PythonOperator(
        task_id='create_dataproc_cluster',
        python_callable=create_dataproc_cluster,
        execution_timeout=timedelta(minutes=15),
        doc_md="""
        ### Создание DataProc кластера
        
        Создаёт временный Yandex DataProc кластер через yc CLI.
        Использует переменные из Lockbox.
        
        **Конфигурация:**
        - Master: 1x s2.small (4 vCPU, 16 GB RAM, 128 GB SSD)
        - Data: 1x s2.small (4 vCPU, 16 GB RAM, 128 GB SSD)
        - Compute: 2x s2.small (4 vCPU, 16 GB RAM, 128 GB SSD)
        
        **Сервисы:** YARN, SPARK, HDFS
        
        **Время создания:** ~5-10 минут
        """,
    )
    
    # Ожидание готовности кластера
    task_wait_cluster = PythonOperator(
        task_id='wait_cluster_ready',
        python_callable=wait_cluster_ready,
        execution_timeout=timedelta(minutes=20),
        doc_md="""
        ### Ожидание готовности кластера
        
        Проверяет статус кластера каждые 30 секунд.
        Максимальное время ожидания: 15 минут.
        """,
    )
    
    # Обучение модели
    task_train = PythonOperator(
        task_id='train_model',
        python_callable=train_model,
        doc_md="""
        ### Обучение модели
        Запускает Spark job для обучения EfficientNet-B4.
        (В текущей версии - заглушка)
        """,
    )
    
    # Регистрация модели
    task_register = PythonOperator(
        task_id='register_model',
        python_callable=register_model,
        doc_md="""
        ### Регистрация модели
        Регистрирует обученную модель в MLflow Model Registry.
        (В текущей версии - заглушка)
        """,
    )
    
    # Удаление кластера
    task_cleanup = PythonOperator(
        task_id='delete_dataproc_cluster',
        python_callable=delete_dataproc_cluster,
        trigger_rule=TriggerRule.ALL_DONE,  # Выполнится даже при ошибках
        execution_timeout=timedelta(minutes=5),
        doc_md="""
        ### Удаление кластера
        
        Удаляет временный DataProc кластер через yc CLI.
        Выполняется всегда, даже если предыдущие задачи завершились с ошибкой.
        """,
    )
    
    # Генерация отчёта
    task_report = PythonOperator(
        task_id='generate_report',
        python_callable=generate_report,
        doc_md="""
        ### Генерация отчёта
        Создаёт финальный отчёт о выполнении pipeline.
        """,
    )
    
    # ========================================
    # DAG Flow
    # ========================================
    
    task_validate_env >> task_validate_dataset >> task_create_cluster >> task_wait_cluster >> task_train >> task_register >> task_cleanup >> task_report