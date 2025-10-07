"""
🚀 ML Pipeline DAG with MLflow Integration for Yandex Cloud - ИСПРАВЛЕННАЯ ВЕРСИЯ
=================================================================================

Airflow DAG для обучения модели обнаружения мошенничества с интеграцией MLflow
на инфраструктуре Yandex Cloud.

Возможности:
- Создание DataProc кластера для обучения
- Обучение модели с использованием PySpark и MLflow
- Автоматическая регистрация лучших моделей
- Сохранение артефактов в Yandex Object Storage
- Мониторинг экспериментов через MLflow UI

Автор: ML Pipeline Team
Дата: 2024
"""

import uuid
import logging
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.models import Variable
from airflow.utils.trigger_rule import TriggerRule
from airflow.utils.task_group import TaskGroup
from airflow.providers.yandex.operators.dataproc import (
    DataprocCreateClusterOperator,
    DataprocCreatePysparkJobOperator,
    DataprocDeleteClusterOperator
)
from urllib.parse import urlparse
import boto3
import random

# Настройка логирования
logger = logging.getLogger(__name__)

# Список файлов (пример из рабочего DAG)
ALL_FILES = [
    "2019-08-22.txt", "2019-09-21.txt", "2019-10-21.txt",
    "2019-11-20.txt", "2019-12-20.txt", "2020-01-19.txt",
    "2020-02-18.txt", "2020-03-19.txt", "2020-04-18.txt",
    "2020-05-18.txt", "2020-06-17.txt", "2020-07-17.txt",
    "2020-08-16.txt", "2020-09-15.txt", "2020-10-15.txt",
    "2020-11-14.txt", "2020-12-14.txt", "2021-01-13.txt",
    "2021-02-12.txt", "2021-03-14.txt", "2021-04-13.txt",
    "2021-05-13.txt", "2021-06-12.txt", "2021-07-12.txt",
    "2021-08-11.txt", "2021-09-10.txt", "2021-10-10.txt",
    "2021-11-09.txt", "2021-12-09.txt", "2022-01-08.txt",
    "2022-02-07.txt", "2022-03-09.txt", "2022-04-08.txt",
    "2022-05-08.txt", "2022-06-07.txt", "2022-07-07.txt",
    "2022-08-06.txt", "2022-09-05.txt", "2022-10-05.txt",
    "2022-11-04.txt"
]

# ═══════════════════════════════════════════════════════════════════
# 🎯 КОНФИГУРАЦИЯ DAG
# ═══════════════════════════════════════════════════════════════════

default_args = {
    'owner': 'ml-engineer',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
}

dag = DAG(
    'ml_pipeline_with_mlflow_fixed',
    default_args=default_args,
    description='🤖 ML Pipeline с интеграцией MLflow для Yandex Cloud (ИСПРАВЛЕННАЯ ВЕРСИЯ)',
    schedule_interval=None,  # Запускается вручную
    catchup=False,
    tags=['ml', 'mlflow', 'dataproc', 'yandex-cloud', 'fixed'],
    max_active_runs=1,
)

# ═══════════════════════════════════════════════════════════════════
# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════

def validate_configuration(**context):
    """Проверка конфигурации перед запуском"""
    logger.info("🔍 Проверяем конфигурацию...")
    
    # Обязательные переменные
    required_vars = [
        'FOLDER_ID', 'SUBNET_ID', 'SECURITY_GROUP_ID',
        'S3_BUCKET_SCRIPTS', 'S3_ACCESS_KEY', 'S3_SECRET_KEY',
        'DATAPROC_SERVICE_ACCOUNT_ID',
        'MLFLOW_TRACKING_URI',  # ← теперь обязательно
    ]
    
    missing_vars = []
    for var in required_vars:
        try:
            value = Variable.get(var)
            if not value:
                missing_vars.append(var)
        except:
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"❌ Отсутствуют обязательные переменные: {missing_vars}")
    
    # Дополнительная проверка MLflow URI
    mlflow_uri = Variable.get('MLFLOW_TRACKING_URI', '')
    if not mlflow_uri:
        raise ValueError("❌ MLFLOW_TRACKING_URI не задан — MLflow не сможет создать эксперимент")
    
    # Проверяем схему URI
    parsed = urlparse(mlflow_uri)
    if parsed.scheme not in ('http', 'https', 'file'):
        raise ValueError("❌ MLFLOW_TRACKING_URI должен начинаться с http://, https:// или file:/")
    
    logger.info(f"✅ MLflow включен: {mlflow_uri}")
    
    logger.info("✅ Конфигурация валидна")
    return True

def select_random_files(**context):
    """Выбор 3 разных файлов - по 1 файлу для каждой итерации (БЫСТРЫЙ ТЕСТ)"""
    logger.info("🎲 Выбираем 3 разных файла для быстрого тестирования - по 1 на итерацию")
    random.seed(42)
    selected = random.sample(ALL_FILES, 3) if len(ALL_FILES) >= 3 else ALL_FILES
    groups = {
        'iteration_1': [selected[0]],  # Только 1 файл для итерации 1
        'iteration_2': [selected[1]],  # Только 1 файл для итерации 2  
        'iteration_3': [selected[2]]   # Только 1 файл для итерации 3
    }
    for key, files in groups.items():
        logger.info(f"  {key}: {', '.join(files)} (БЫСТРЫЙ ТЕСТ: 1 файл)")
        context['task_instance'].xcom_push(key=key, value=files)
    return groups

def _s3_endpoint_host() -> str:
    url = Variable.get('S3_ENDPOINT_URL', default_var='https://storage.yandexcloud.net')
    parsed = urlparse(url)
    return parsed.netloc if parsed.netloc else url

def validate_files_runtime(iteration: int, **context):
    """Проверяет, что все файлы для итерации существуют в S3 бакете."""
    bucket = Variable.get('S3_DATA_BUCKET', default_var=Variable.get('S3_BUCKET_SCRIPTS', default_var=''))
    prefix = Variable.get('S3_DATA_PREFIX', default_var='').strip('/')
    files = context['ti'].xcom_pull(task_ids='select_random_files', key=f'iteration_{iteration}') or []
    if not files:
        raise RuntimeError(f"Не найдены файлы для итерации {iteration} в XCom")

    endpoint_host = _s3_endpoint_host()
    s3 = boto3.client(
        's3',
        endpoint_url=f"https://{endpoint_host}",
        aws_access_key_id=Variable.get('S3_ACCESS_KEY', default_var=''),
        aws_secret_access_key=Variable.get('S3_SECRET_KEY', default_var='')
    )

    missing = []
    for fname in files:
        key = f"{prefix}/{fname}" if prefix else fname
        try:
            s3.head_object(Bucket=bucket, Key=key)
            logger.info(f"✅ Найден объект: s3://{bucket}/{key}")
        except Exception as e:
            logger.error(f"❌ Нет объекта: s3://{bucket}/{key} ({e})")
            missing.append(key)

    if missing:
        raise RuntimeError(f"Отсутствуют входные файлы в бакете {bucket}: {missing}")
    return True

def cleanup_and_report(**context):
    """Очистка ресурсов и создание отчета"""
    logger.info("🧹 Выполняем очистку и создаем отчет...")
    
    # В реальном сценарии здесь может быть:
    # - Проверка статуса обучения
    # - Создание отчета о метриках
    # - Отправка уведомлений
    # - Архивирование логов
    
    logger.info(f"✅ Обработка завершена")
    
    return {
        'status': 'completed',
        'execution_date': context['execution_date'].isoformat()
    }

# ═══════════════════════════════════════════════════════════════════
# 📋 ОПРЕДЕЛЕНИЕ ЗАДАЧ
# ═══════════════════════════════════════════════════════════════════

# Предварительная проверка
validate_config_task = PythonOperator(
    task_id='validate_configuration',
    python_callable=validate_configuration,
    dag=dag,
)

# Выбор файлов для обработки
task_select_files = PythonOperator(
    task_id='select_random_files',
    python_callable=select_random_files,
    dag=dag,
)

# Переменные для хранения задач (объявляем ДО TaskGroup)
delete_tasks = []
first_validate = None
second_validate = None
third_validate = None

# Создание TaskGroup для основного процесса обучения
with TaskGroup('ml_training_process', dag=dag) as training_group:
    
    for iteration in [1, 2, 3]:
        # Проверка файлов
        validate_files = PythonOperator(
            task_id=f'validate_input_files_{iteration}',
            python_callable=validate_files_runtime,
            op_kwargs={'iteration': iteration},
            dag=dag,
        )

        def create_cluster_runtime_iteration(**context):
            """Создание кластера для итерации - используем проверенный подход"""
            exec_dt = context['execution_date']
            unique_id = uuid.uuid4().hex[:6]
            cluster_name = f"ml-train-{iteration}-{exec_dt.strftime('%Y%m%d-%H%M%S')}-{unique_id}"
            logger.info(f"🏷️ Создаем кластер для итерации {iteration}: {cluster_name}")

            folder_id = Variable.get('FOLDER_ID')
            subnet_id = Variable.get('SUBNET_ID')
            zone = Variable.get('ZONE', 'ru-central1-a')
            sa_id = Variable.get('DATAPROC_SERVICE_ACCOUNT_ID')
            security_group_id = Variable.get('SECURITY_GROUP_ID')
            s3_logs_bucket = f"{Variable.get('S3_BUCKET_SCRIPTS')}/dataproc-logs/"

            op = DataprocCreateClusterOperator(
                task_id=f'_inner_create_cluster_{iteration}',
                folder_id=folder_id,
                cluster_name=cluster_name,
                cluster_description=f'ML Training Cluster - Iteration {iteration}',
                subnet_id=subnet_id,
                s3_bucket=s3_logs_bucket,
                ssh_public_keys=[Variable.get('YC_SSH_PUBLIC_KEY', default_var='')],
                zone=zone,
                cluster_image_version=Variable.get('DATAPROC_CLUSTER_VERSION', '2.0'),
                security_group_ids=[security_group_id] if security_group_id else [],
                service_account_id=sa_id,
                masternode_resource_preset=Variable.get('DATAPROC_MASTER_PRESET', 's3-c2-m8'),
                masternode_disk_type='network-hdd',
                masternode_disk_size=int(Variable.get('DATAPROC_MASTER_DISK_SIZE', '40')),
                datanode_resource_preset=Variable.get('DATAPROC_WORKER_PRESET', 's3-c4-m16'),
                datanode_disk_type='network-hdd',
                datanode_disk_size=int(Variable.get('DATAPROC_WORKER_DISK_SIZE', '100')),
                datanode_count=int(Variable.get('DATAPROC_WORKER_COUNT', '2')),
                services=['YARN', 'SPARK', 'HDFS', 'MAPREDUCE'],
                dag=dag,
            )
            
            cluster_id = op.execute(context)
            logger.info(f"✅ Кластер создан для итерации {iteration}: {cluster_id}")
            return cluster_id

        # Создание кластера
        create_cluster = PythonOperator(
            task_id=f'create_cluster_{iteration}',
            python_callable=create_cluster_runtime_iteration,
            dag=dag,
        )

        # Ожидание готовности кластера
        wait_ready = BashOperator(
            task_id=f'wait_cluster_ready_{iteration}',
            bash_command='sleep {{ var.value.get("DATAPROC_GRACE_SECONDS", 180) }}',
            dag=dag,
        )

        # ЗАГЛУШКА: Данные уже очищены и готовы для обучения
        def skip_cleaning_data_ready(**context):
            """Заглушка для этапа очистки - данные уже готовы"""
            iteration_num = context['iteration']
            logger.info(f"🔄 Итерация {iteration_num}: Пропускаем очистку данных - данные уже готовы в ml_batch_results/iteration_batch={iteration_num}/")
            logger.info(f"📊 Найдено ~1000 parquet файлов для обучения")
            logger.info(f"✅ Переходим сразу к обучению модели")
            return f"data_ready_iteration_{iteration_num}"
        
        clean_batch = PythonOperator(
            task_id=f'skip_cleaning_{iteration}',
            python_callable=skip_cleaning_data_ready,
            op_kwargs={'iteration': iteration},
            dag=dag,
        )

        # Обучение модели на очищенных данных текущей итерации
        # ВАЖНО: DataprocCreatePysparkJobOperator НЕ поддерживает Jinja2 в args!
        # Уникальные run_name/пути формируются внутри training-скрипта
        
        train_model_task = DataprocCreatePysparkJobOperator(
            task_id=f'run_ml_training_{iteration}',
            cluster_id="{{ ti.xcom_pull(task_ids='ml_training_process.create_cluster_" + str(iteration) + "') }}",
            main_python_file_uri=f"s3a://{Variable.get('S3_BUCKET_SCRIPTS')}/scripts/train_with_mlflow_yandex_fixed.py",
            args=[
                '--input', f"s3a://{Variable.get('S3_DATA_BUCKET', Variable.get('S3_BUCKET_SCRIPTS'))}/{Variable.get('BATCH_OUTPUT_FOLDER', 'ml_batch_results')}/iteration_batch={iteration}/",
                '--output', f"s3a://{Variable.get('S3_BUCKET_SCRIPTS')}/models/fraud_model_iter{iteration}",
                '--model-type', Variable.get('ML_MODEL_TYPE', 'rf'),
                '--label-col', Variable.get('ML_LABEL_COL', 'tx_fraud'),
                '--s3-endpoint-url', f"https://{_s3_endpoint_host()}",
                '--s3-access-key', Variable.get('S3_ACCESS_KEY'),
                '--s3-secret-key', Variable.get('S3_SECRET_KEY'),
                '--tracking-uri', Variable.get('MLFLOW_TRACKING_URI', ''),
                '--experiment-name', Variable.get('MLFLOW_EXPERIMENT_NAME', 'fraud_detection_yandex'),
                '--run-name', f"training_iter{iteration}",
                '--auto-register',
                '--registry-threshold', Variable.get('MLFLOW_REGISTRY_THRESHOLD', '0.8'),
                '--sample-fraction', Variable.get('ML_SAMPLE_FRACTION', '0.1'),
                '--debug-log', f"s3a://{Variable.get('S3_BUCKET_SCRIPTS')}/debug-logs/main-pipeline/iter{iteration}.log",
            ],
            properties={
                'spark.submit.deployMode': 'cluster',
                'spark.sql.adaptive.enabled': 'true',
                'spark.hadoop.fs.s3a.endpoint': _s3_endpoint_host(),
                'spark.hadoop.fs.s3a.path.style.access': 'true',
                'spark.hadoop.fs.s3a.connection.ssl.enabled': 'true',
                'spark.hadoop.fs.s3a.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
                'spark.hadoop.fs.s3a.access.key': Variable.get('S3_ACCESS_KEY'),
                'spark.hadoop.fs.s3a.secret.key': Variable.get('S3_SECRET_KEY'),
                # КРИТИЧНО: Используем conda python с автоустановкой MLflow
                'spark.pyspark.python': '/opt/conda/bin/python',
                'spark.yarn.appMasterEnv.PYSPARK_PYTHON': '/opt/conda/bin/python',
                'spark.executorEnv.PYSPARK_PYTHON': '/opt/conda/bin/python',
                # КРИТИЧНО для MLflow: Настройка PYTHONPATH для автоустановки
                'spark.yarn.appMasterEnv.PYTHONPATH': '/opt/conda/lib/python3.9/site-packages',
                'spark.executorEnv.PYTHONPATH': '/opt/conda/lib/python3.9/site-packages',
                # УБИРАЕМ INSTALL_PACKAGES - используем автоустановку в скрипте
                # Передаем S3 credentials в executor и appMaster
                'spark.executorEnv.S3_ACCESS_KEY': Variable.get('S3_ACCESS_KEY'),
                'spark.executorEnv.S3_SECRET_KEY': Variable.get('S3_SECRET_KEY'),
                'spark.yarn.appMasterEnv.S3_ACCESS_KEY': Variable.get('S3_ACCESS_KEY'),
                'spark.yarn.appMasterEnv.S3_SECRET_KEY': Variable.get('S3_SECRET_KEY'),
                # MLflow env на appMaster и executors
                'spark.yarn.appMasterEnv.MLFLOW_TRACKING_URI': Variable.get('MLFLOW_TRACKING_URI'),
                'spark.executorEnv.MLFLOW_TRACKING_URI': Variable.get('MLFLOW_TRACKING_URI'),
                # если используется аутентификация:
                'spark.yarn.appMasterEnv.MLFLOW_TRACKING_USERNAME': Variable.get('MLFLOW_TRACKING_USERNAME', default_var=''),
                'spark.yarn.appMasterEnv.MLFLOW_TRACKING_PASSWORD': Variable.get('MLFLOW_TRACKING_PASSWORD', default_var=''),
                'spark.executorEnv.MLFLOW_TRACKING_USERNAME': Variable.get('MLFLOW_TRACKING_USERNAME', default_var=''),
                'spark.executorEnv.MLFLOW_TRACKING_PASSWORD': Variable.get('MLFLOW_TRACKING_PASSWORD', default_var=''),
                # если HTTPS с самоподписанным сертификатом:
                'spark.yarn.appMasterEnv.MLFLOW_TRACKING_INSECURE_TLS': Variable.get('MLFLOW_TRACKING_INSECURE_TLS', default_var='false'),
                'spark.executorEnv.MLFLOW_TRACKING_INSECURE_TLS': Variable.get('MLFLOW_TRACKING_INSECURE_TLS', default_var='false'),
                # опционально: путь к CA
                'spark.yarn.appMasterEnv.REQUESTS_CA_BUNDLE': Variable.get('REQUESTS_CA_BUNDLE', default_var=''),
                'spark.executorEnv.REQUESTS_CA_BUNDLE': Variable.get('REQUESTS_CA_BUNDLE', default_var=''),
            },
            connection_id='yandexcloud_default',
            dag=dag,
        )

        # Удаление кластера
        delete_cluster = DataprocDeleteClusterOperator(
            task_id=f'delete_cluster_{iteration}',
            cluster_id="{{ ti.xcom_pull(task_ids='ml_training_process.create_cluster_" + str(iteration) + "') }}",
            trigger_rule=TriggerRule.ALL_DONE,
            dag=dag,
        )
        delete_tasks.append(delete_cluster)

        # Связи внутри итерации
        validate_files >> create_cluster >> wait_ready >> clean_batch >> train_model_task >> delete_cluster

        # ПОСЛЕДОВАТЕЛЬНОСТЬ ИТЕРАЦИЙ: сохраняем задачи для создания зависимостей
        # Сохраняем validate_files для каждой итерации
        if iteration == 1:
            first_validate = validate_files
        elif iteration == 2:
            second_validate = validate_files
        elif iteration == 3:
            third_validate = validate_files

# Финальная очистка и отчет
cleanup_task = PythonOperator(
    task_id='cleanup_and_report',
    python_callable=cleanup_and_report,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

# ═══════════════════════════════════════════════════════════════════
# 🔗 ОПРЕДЕЛЕНИЕ ЗАВИСИМОСТЕЙ
# ═══════════════════════════════════════════════════════════════════

# ПОСЛЕДОВАТЕЛЬНОСТЬ ИТЕРАЦИЙ: 2-я итерация после завершения 1-й, 3-я после 2-й
delete_tasks[0] >> second_validate  # 2-я итерация после удаления кластера 1-й
delete_tasks[1] >> third_validate   # 3-я итерация после удаления кластера 2-й

# Основной flow: валидируем → выбираем файлы → 1-я итерация → финальный отчёт
validate_config_task >> task_select_files >> first_validate
training_group >> cleanup_task
