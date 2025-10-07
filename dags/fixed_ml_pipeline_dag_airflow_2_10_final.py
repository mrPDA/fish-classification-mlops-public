"""
🚀 ML Pipeline Batch Processing DAG - Airflow 2.10 Final Version
================================================================
Совместим с Airflow 2.10 и Python 3.12
Максимально похож на рабочий opus_dag.py
"""

import uuid
import logging
import random
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.models import Variable, Connection
from airflow.settings import Session
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from airflow.utils.task_group import TaskGroup
from airflow.providers.yandex.operators.dataproc import (
    DataprocCreateClusterOperator,
    DataprocCreatePysparkJobOperator,
    DataprocDeleteClusterOperator
)

# 🎯 Конфигурация DAG - ИСПОЛЬЗУЕМ days_ago как в рабочем DAG
default_args = {
    'owner': 'ml-engineer',
    'depends_on_past': False,
    'start_date': days_ago(1),  # ИСПРАВЛЕНО: Используем days_ago как в рабочем DAG
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
}

# 🌊 Определение DAG - ИСПОЛЬЗУЕМ ТОЧНО ТАКОЙ ЖЕ DAG ID
dag = DAG(
    'ml_pipeline_batch_processing',  # ИСПРАВЛЕНО: Используем тот же DAG ID
    default_args=default_args,
    description='🚀 ML Pipeline - Пакетная обработка 9 файлов в 3 итерации',
    schedule_interval=None,  # Запускается вручную
    catchup=False,
    tags=['ml', 'dataproc', 'batch', 'spark'],
    max_active_runs=1,
)

# 🗂️ Список файлов для обработки (реальные файлы из бакета)
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

# 🔧 Вспомогательные функции - ИСПОЛЬЗУЕМ ТОЧНО ТАКИЕ ЖЕ
def get_cluster_name(iteration):
    """Генерация уникального имени кластера для итерации"""
    return f"ml-batch-cluster-iter{iteration}-{uuid.uuid4().hex[:6]}"

def get_s3_logs_bucket():
    """Получение пути к логам S3"""
    bucket_name = Variable.get('S3_BUCKET_SCRIPTS')
    return f"{bucket_name}/ml_batch_logs/"

def select_random_files(**context):
    """Выбор 9 случайных файлов и разделение на 3 группы"""
    logger = logging.getLogger(__name__)
    logger.info("🎲 Выбираем 9 случайных файлов...")
    
    # Выбираем 9 случайных файлов
    random.seed(42)  # Для воспроизводимости
    selected_files = random.sample(ALL_FILES, 9)
    
    # Разделяем на 3 группы по 3 файла
    file_groups = {
        'iteration_1': selected_files[0:3],
        'iteration_2': selected_files[3:6], 
        'iteration_3': selected_files[6:9]
    }
    
    logger.info("📋 Выбранные файлы:")
    for iteration, files in file_groups.items():
        logger.info(f"  {iteration}: {', '.join(files)}")
        context['task_instance'].xcom_push(key=iteration, value=files)
    
    return file_groups

def create_yandex_connection(**context):
    """Создание подключения для Yandex Cloud"""
    logger = logging.getLogger(__name__)
    logger.info("🔧 Настройка подключения Yandex Cloud...")
    
    try:
        session = Session()
        
        sa_json = Variable.get('DP_SA_JSON', None)
        if not sa_json:
            raise ValueError("DP_SA_JSON variable is required")
        
        yc_connection = Connection(
            conn_id="yc-dataproc-batch",
            conn_type="yandexcloud",
            extra={
                "extra__yandexcloud__service_account_json": sa_json,
            },
        )
        
        existing_conn = session.query(Connection).filter(
            Connection.conn_id == "yc-dataproc-batch"
        ).first()
        
        if existing_conn:
            existing_conn.extra = yc_connection.extra
            logger.info("🔄 Обновлено подключение yc-dataproc-batch")
        else:
            session.add(yc_connection)
            logger.info("✅ Создано подключение yc-dataproc-batch")
            
        session.commit()
        session.close()
        
        logger.info("✅ Подключение Yandex Cloud настроено")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания подключения: {e}")
        raise

def validate_environment(**context):
    """Валидация окружения и переменных"""
    logger = logging.getLogger(__name__)
    logger.info("🔍 Валидация окружения...")
    
    try:
        required_vars = [
            'ZONE', 'FOLDER_ID', 'SUBNET_ID', 'NETWORK_ID', 'YC_SSH_PUBLIC_KEY',
            'S3_ENDPOINT_URL', 'S3_ACCESS_KEY', 'S3_SECRET_KEY', 'S3_BUCKET_SCRIPTS',
            'DATAPROC_SERVICE_ACCOUNT_ID', 'SECURITY_GROUP_ID', 'DP_SA_JSON', 'S3_DATA_BUCKET'
        ]
        
        missing_vars = []
        
        logger.info("📋 Проверка переменных:")
        for var in required_vars:
            try:
                value = Variable.get(var)
                if 'secret' in var.lower() or 'key' in var.lower():
                    logger.info(f"   ✅ {var}: ***")
                else:
                    logger.info(f"   ✅ {var}: {value}")
            except Exception:
                logger.error(f"   ❌ {var}: ОТСУТСТВУЕТ")
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing variables: {missing_vars}")
        
        logger.info("✅ Все переменные присутствуют")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка валидации: {e}")
        raise

def generate_final_report(**context):
    """Генерация финального отчета пакетной обработки"""
    logger = logging.getLogger(__name__)
    
    data_bucket = Variable.get('S3_DATA_BUCKET')
    results_path = f"s3a://{data_bucket}/ml_batch_results/"
    
    logger.info("🎉 Пакетная обработка ML Pipeline завершена!")
    logger.info(f"📊 Обработано 3 итерации по 3 файла = 9 файлов")
    logger.info(f"📁 Результаты сохранены в: {results_path}")
    logger.info("✅ Готово для ML моделирования")
    
    return True

# 🔄 Создание TaskGroup для каждой итерации внутри DAG контекста
with dag:
    iteration_groups = []
    
    for iteration in [1, 2, 3]:
        with TaskGroup(f"iteration_{iteration}", tooltip=f"Итерация {iteration}: создание кластера → ожидание → обработка → удаление") as iteration_group:
            
            # 🏗️ Создание DataProc кластера через Python функцию - КАК В РАБОЧЕМ DAG
            cluster_name = get_cluster_name(iteration)
            
            def create_cluster_iteration(**context):
                """Создание кластера с динамическими переменными"""
                from airflow.providers.yandex.operators.dataproc import DataprocCreateClusterOperator
                
                # Получаем все переменные во время выполнения
                folder_id = Variable.get('FOLDER_ID')
                subnet_id = Variable.get('SUBNET_ID')
                security_group_id = Variable.get('SECURITY_GROUP_ID')
                zone = Variable.get('ZONE')
                # Опционально получаем SA ID - если не задан, будет использован default
                sa_id = Variable.get('DATAPROC_SERVICE_ACCOUNT_ID', None)
                ssh_key = Variable.get('YC_SSH_PUBLIC_KEY')
                bucket_name = Variable.get('S3_BUCKET_SCRIPTS')
                logs_bucket = f"{bucket_name}/ml_batch_logs/"
                
                logger = logging.getLogger(__name__)
                logger.info(f"🏗️ Создание кластера для итерации {iteration}: {cluster_name}")
                logger.info(f"🔍 Folder ID: {folder_id}")
                logger.info(f"🔍 Subnet ID: {subnet_id}")
                logger.info(f"🛡️ Security Group ID: {security_group_id}")
                if sa_id:
                    logger.info(f"👤 Service Account ID: {sa_id}")
                else:
                    logger.info("👤 Service Account: используется default")
                
                # Базовые параметры для создания кластера
                cluster_params = {
                    'task_id': f'create_cluster_op_{iteration}',
                    'folder_id': folder_id,
                    'cluster_name': cluster_name,
                    'cluster_description': f'ML Batch Processing Cluster - Iteration {iteration}',
                    'subnet_id': subnet_id,
                    's3_bucket': logs_bucket,
                    'ssh_public_keys': [ssh_key],
                    'zone': zone,
                    'cluster_image_version': "2.0",
                    'security_group_ids': [security_group_id] if security_group_id else [],
                    
                    # 🚀 ПОЛНАЯ конфигурация кластера
                    'masternode_resource_preset': 's3-c4-m16',
                    'masternode_disk_type': 'network-ssd',
                    'masternode_disk_size': 40,
                    
                    'datanode_resource_preset': 's3-c4-m16', 
                    'datanode_disk_type': 'network-ssd',
                    'datanode_disk_size': 100,
                    'datanode_count': 1,
                    
                    'computenode_resource_preset': 's3-c8-m32',
                    'computenode_disk_type': 'network-ssd',
                    'computenode_disk_size': 128,
                    'computenode_count': 2,
                    
                    'services': ['YARN', 'SPARK', 'HDFS', 'MAPREDUCE'],
                    'connection_id': 'yc-dataproc-batch',
                }
                
                # Добавляем service_account_id только если он задан и корректен
                if sa_id and sa_id.startswith('aje'):
                    cluster_params['service_account_id'] = sa_id
                
                # Создаем оператор с актуальными переменными
                create_op = DataprocCreateClusterOperator(**cluster_params)
                
                # Выполняем создание кластера
                result = create_op.execute(context)
                
                # Сохраняем имя кластера для следующих задач
                context['task_instance'].xcom_push(key=f'cluster_name_{iteration}', value=cluster_name)
                
                logger.info(f"✅ Кластер создан: {cluster_name}")
                return result
            
            create_cluster_task = PythonOperator(
                task_id='create_cluster',
                python_callable=create_cluster_iteration,
            )
            
            # ⏰ Ожидание готовности кластера - ИСПОЛЬЗУЕМ ТОЧНО ТАКОЙ ЖЕ КОД
            wait_cluster_task = BashOperator(
                task_id='wait_cluster_ready',
                bash_command=f'''
                echo "⏳ Ожидание готовности кластера для итерации {iteration}..."
                sleep 120
                echo "✅ Кластер готов для итерации {iteration}"
                ''',
            )
            
            # 🚀 Обработка файлов через PySpark job - КАК В РАБОЧЕМ DAG
            def run_pyspark_job(**context):
                """Запуск PySpark job с динамическими переменными"""
                from airflow.providers.yandex.operators.dataproc import DataprocCreatePysparkJobOperator
                
                # Получаем переменные
                bucket_scripts = Variable.get('S3_BUCKET_SCRIPTS')
                data_bucket = Variable.get('S3_DATA_BUCKET')
                s3_access_key = Variable.get('S3_ACCESS_KEY')
                s3_secret_key = Variable.get('S3_SECRET_KEY')
                
                # Получаем список файлов из XCom
                files = context['task_instance'].xcom_pull(
                    task_ids='select_random_files', 
                    key=f'iteration_{iteration}'
                )
                files_str = ','.join(files) if files else ''
                
                logger = logging.getLogger(__name__)
                logger.info(f"🚀 Запуск обработки для итерации {iteration}")
                logger.info(f"📋 Файлы: {files_str}")
                
                pyspark_op = DataprocCreatePysparkJobOperator(
                    task_id=f'pyspark_job_{iteration}',
                    main_python_file_uri=f"s3a://{bucket_scripts}/scripts/ML_pipeline_batch_fixed.py",
                    connection_id='yc-dataproc-batch',
                    args=[
                        '--bucket', data_bucket,
                        '--mode', 'fast',
                        '--files', files_str,
                        '--iteration', str(iteration),
                        '--output-folder', 'ml_batch_results'
                    ],
                    properties={
                        'spark.hadoop.fs.s3a.access.key': s3_access_key,
                        'spark.hadoop.fs.s3a.secret.key': s3_secret_key,
                        'spark.hadoop.fs.s3a.endpoint': 'storage.yandexcloud.net',
                        'spark.hadoop.fs.s3a.path.style.access': 'true',
                        'spark.hadoop.fs.s3a.connection.ssl.enabled': 'true',
                        'spark.executorEnv.S3_ACCESS_KEY': s3_access_key,
                        'spark.executorEnv.S3_SECRET_KEY': s3_secret_key,
                        'spark.yarn.appMasterEnv.S3_ACCESS_KEY': s3_access_key,
                        'spark.yarn.appMasterEnv.S3_SECRET_KEY': s3_secret_key
                    },
                )
                
                result = pyspark_op.execute(context)
                logger.info(f"✅ Обработка итерации {iteration} завершена")
                
                return result
            
            process_task = PythonOperator(
                task_id='process_files',
                python_callable=run_pyspark_job,
            )
            
            # 🗑️ Удаление кластера - КАК В РАБОЧЕМ DAG
            def delete_cluster(**context):
                from airflow.providers.yandex.operators.dataproc import DataprocDeleteClusterOperator
                logger = logging.getLogger(__name__)
                # Получаем имя кластера из XCom, а не генерируем заново
                cluster_name = context['task_instance'].xcom_pull(
                    task_ids='create_cluster',
                    key=f'cluster_name_{iteration}'
                )
                logger.info(f"🗑️ Удаление кластера для итерации {iteration}: {cluster_name}")
                delete_op = DataprocDeleteClusterOperator(
                    task_id=f'delete_cluster_op_{iteration}',
                    cluster_id=cluster_name,
                    connection_id='yc-dataproc-batch',
                )
                result = delete_op.execute(context)
                logger.info(f"✅ Кластер {cluster_name} удален")
                return result
                
            cleanup_task = PythonOperator(
                task_id='cleanup_cluster',
                python_callable=delete_cluster,
                trigger_rule=TriggerRule.ALL_DONE,
            )
            
            # СТРОГО ПОСЛЕДОВАТЕЛЬНО внутри группы
            create_cluster_task >> wait_cluster_task >> process_task >> cleanup_task
        
        # Сохраняем группу для связывания
        iteration_groups.append(iteration_group)
    
    # Присваиваем группы переменным для удобства
    iteration_1_group, iteration_2_group, iteration_3_group = iteration_groups

    # 📋 Создание начальных задач
    task_select_files = PythonOperator(
        task_id='select_random_files',
        python_callable=select_random_files,
    )

    task_create_connection = PythonOperator(
        task_id='create_yandex_connection',
        python_callable=create_yandex_connection,
    )

    task_validate = PythonOperator(
        task_id='validate_environment',
        python_callable=validate_environment,
    )

    task_final_report = PythonOperator(
        task_id='generate_final_report',
        python_callable=generate_final_report,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    # 🔗 Связывание задач - ПРАВИЛЬНЫЕ ЗАВИСИМОСТИ
    # Сначала создаем подключение, затем валидируем и выбираем файлы
    task_create_connection >> task_validate >> task_select_files

    # Последовательность итераций - СТРОГО ПОСЛЕДОВАТЕЛЬНО  
    # КРИТИЧНО: Каждая итерация должна ждать создания подключения!
    task_select_files >> iteration_1_group
    iteration_1_group >> iteration_2_group  
    iteration_2_group >> iteration_3_group
    iteration_3_group >> task_final_report
    
    # Дополнительная зависимость: убеждаемся что подключение создано ПЕРЕД итерациями
    task_create_connection >> iteration_1_group 