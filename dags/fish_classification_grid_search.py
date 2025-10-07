"""
Airflow DAG для Grid Search - подбор лучшей модели классификации рыб

Этот DAG тестирует разные архитектуры и гиперпараметры:
- MobileNetV2, EfficientNetB0, ResNet50V2
- Learning rates: [0.001, 0.0001]
- Dropout rates: [0.2, 0.5]

Всего: 3 * 2 * 2 = 12 экспериментов
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.yandex.operators.yandexcloud_dataproc import (
    DataprocCreateClusterOperator,
    DataprocCreatePysparkJobOperator,
    DataprocDeleteClusterOperator
)
from yandex.cloud.dataproc.v1.cluster_pb2 import InitializationAction
from airflow.models import Variable
from airflow.exceptions import AirflowException
import logging

logger = logging.getLogger(__name__)

# Параметры из Variables
FOLDER_ID = Variable.get('FOLDER_ID', 'b1gjj3po03aa3m4j8ps5')
ZONE = Variable.get('ZONE', 'ru-central1-a')
SUBNET_ID = Variable.get('SUBNET_ID', 'e9b5umsufggihj02a3o1')
SECURITY_GROUP_ID = Variable.get('SECURITY_GROUP_ID', 'enpha1v51ug84ddqfob4')
SERVICE_ACCOUNT_ID = Variable.get('DATAPROC_SERVICE_ACCOUNT_ID', 'ajepv2durkr1nk9rnoui')
S3_BUCKET = Variable.get('S3_BUCKET_NAME', 'fish-classification-data-7wb4zv')
S3_ENDPOINT = Variable.get('S3_ENDPOINT_URL', 'https://storage.yandexcloud.net')

try:
    S3_ACCESS_KEY = Variable.get('S3_ACCESS_KEY')
except:
    S3_ACCESS_KEY = 'YOUR_S3_ACCESS_KEY'  # Получите из Yandex Cloud или Lockbox
    
try:
    S3_SECRET_KEY = Variable.get('S3_SECRET_KEY')
except:
    S3_SECRET_KEY = 'YOUR_S3_SECRET_KEY'  # Получите из Yandex Cloud или Lockbox

MLFLOW_IP = Variable.get('MLFLOW_IP', '10.11.0.18')
MLFLOW_URI = f'http://{MLFLOW_IP}:5000'

# Параметры обучения
NUM_CLASSES = 9
IMAGE_SIZE = 224
BATCH_SIZE = 32
EPOCHS = 10  # Можно уменьшить для быстрых экспериментов

SSH_PUBLIC_KEY = Variable.get('YC_SSH_PUBLIC_KEY', 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCtV1GrBDN0NKa0VRfqBaGRyFsW6n4pKN7rqKWuStFo6If+6twnYwDYntTaXQBSQcIwF984u5NMP5BVMd8QKSBEvQK/IL9UFjdr3wB73+hKYMpoK9JPY2wPN6ECoxbGzkINZ+vhOgtnHytqGT7Sh79hoB6mKuJg0+yyMbxk0Lq/k7rtKlQYsm28rea4pIlvGmWgUXqzIcnj02K7x+hNGYYbe3kMlUY3MmvKaV1aM0P80gzWgoM0prpbSmdHUTkoP7QdkVlXHNU1xHINBU2lACt5aTL2OOlw/YLcaIDHmvKtghcpfRRskpc4VnJCLqPZgEIA2BTBe85FMcWwBOwTj4nt4YkbDzCgfDVi+K0SevvAKXJla+2H6KEMpUK6pUlpnnm2Q5UKkEiWd+kZ5Tc5ip0gKxkRPG+Q2lT28CbSgqGWmU0EkK2K1je+E/mWRkBybXyObwDHbDYNWmMF0Ztxoo6Rp7WgF2rtNOzeI58pyXFKI+Qn0vyri7s9aLVSBzAey6LVikYs+W5Vpipioh1sI0hETegDyUMQzrmoufoQeGPCBA5tsdAS715mSEhDey326qN5gVNVYcya4nEn2wJ9hNNS1NoSoy2+xvT5NMrLSLRso2Li/P0ud3dd1Xy5AVoMifzrufgZnFJY7nJUnY+0KgElbP35rsZRdsiRMuc5fVpRuQ== denispukinov@MacBook-Pro-Denis.local')

# DAG configuration
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'fish_classification_grid_search',
    default_args=default_args,
    description='Grid Search для подбора лучшей модели классификации рыб',
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2025, 10, 6),
    catchup=False,
    tags=['fish-classification', 'grid-search', 'ml', 'dataproc'],
)

# Task 1: Создание кластера - более мощного для grid search
create_cluster = DataprocCreateClusterOperator(
    task_id='create_dataproc_cluster',
    folder_id=FOLDER_ID,
    cluster_name=f'fish-grid-search-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
    cluster_description='DataProc cluster for grid search - model selection',
    ssh_public_keys=SSH_PUBLIC_KEY,
    service_account_id=SERVICE_ACCOUNT_ID,
    subnet_id=SUBNET_ID,
    s3_bucket=S3_BUCKET,
    zone=ZONE,
    cluster_image_version='2.1',
    
    # Master node - более мощный для grid search
    masternode_resource_preset='s3-c4-m16',  # 4 vCPU, 16 GB RAM
    masternode_disk_type='network-ssd',
    masternode_disk_size=100,
    
    # Compute nodes - более мощные для grid search
    computenode_resource_preset='s3-c4-m16',  # 4 vCPU, 16 GB RAM
    computenode_disk_type='network-ssd',
    computenode_disk_size=100,
    computenode_count=1,
    computenode_max_hosts_count=1,
    
    # Services
    services=['YARN', 'SPARK'],
    datanode_count=0,
    
    # Security group
    security_group_ids=[SECURITY_GROUP_ID],
    
    # Spark properties
    properties={
        'spark:spark.sql.warehouse.dir': f's3a://{S3_BUCKET}/spark-warehouse/',
        'spark:spark.yarn.submit.waitAppCompletion': 'true',
    },
    
    connection_id='yandexcloud_default',
    dag=dag,
)

# Task 2: Grid Search PySpark job
grid_search_job = DataprocCreatePysparkJobOperator(
    task_id='run_grid_search',
    main_python_file_uri=f's3a://{S3_BUCKET}/spark_jobs/train_fish_model_grid_search.py',
    args=[
        '--s3-endpoint', S3_ENDPOINT,
        '--s3-bucket', S3_BUCKET,
        '--s3-access-key', S3_ACCESS_KEY,
        '--s3-secret-key', S3_SECRET_KEY,
        '--mlflow-tracking-uri', MLFLOW_URI,
        '--mlflow-experiment', 'fish-classification-grid-search',
        '--num-classes', str(NUM_CLASSES),
        '--image-size', str(IMAGE_SIZE),
        '--batch-size', str(BATCH_SIZE),
        '--epochs', str(EPOCHS),
        '--learning-rate', '0.001',  # Default, будет перебираться в скрипте
    ],
    properties={
        'spark.submit.deployMode': 'client',
        'spark.driver.memory': '12g',
        'spark.driver.cores': '4',
        'spark.executor.memory': '12g',
        'spark.executor.cores': '4',
        'spark.executor.instances': '1',
        
        'spark.yarn.appMasterEnv.PYTHONPATH': '/home/dataproc-agent/.local/lib/python3.8/site-packages:/opt/conda/lib/python3.8/site-packages',
        'spark.executorEnv.PYTHONPATH': '/home/dataproc-agent/.local/lib/python3.8/site-packages:/opt/conda/lib/python3.8/site-packages',
        
        'spark.yarn.appMasterEnv.MLFLOW_TRACKING_URI': MLFLOW_URI,
        'spark.executorEnv.MLFLOW_TRACKING_URI': MLFLOW_URI,
        
        'spark.executorEnv.AWS_ACCESS_KEY_ID': S3_ACCESS_KEY,
        'spark.executorEnv.AWS_SECRET_ACCESS_KEY': S3_SECRET_KEY,
        'spark.yarn.appMasterEnv.AWS_ACCESS_KEY_ID': S3_ACCESS_KEY,
        'spark.yarn.appMasterEnv.AWS_SECRET_ACCESS_KEY': S3_SECRET_KEY,
        'spark.executorEnv.S3_ACCESS_KEY': S3_ACCESS_KEY,
        'spark.executorEnv.S3_SECRET_KEY': S3_SECRET_KEY,
        'spark.yarn.appMasterEnv.S3_ACCESS_KEY': S3_ACCESS_KEY,
        'spark.yarn.appMasterEnv.S3_SECRET_KEY': S3_SECRET_KEY,
        'spark.yarn.appMasterEnv.MLFLOW_S3_ENDPOINT_URL': S3_ENDPOINT,
        'spark.executorEnv.MLFLOW_S3_ENDPOINT_URL': S3_ENDPOINT,
        
        'spark.hadoop.fs.s3a.endpoint': S3_ENDPOINT.replace('https://', ''),
        'spark.hadoop.fs.s3a.path.style.access': 'true',
        'spark.hadoop.fs.s3a.connection.ssl.enabled': 'true',
        'spark.hadoop.fs.s3a.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
        'spark.hadoop.fs.s3a.access.key': S3_ACCESS_KEY,
        'spark.hadoop.fs.s3a.secret.key': S3_SECRET_KEY,
        
        'spark.sql.adaptive.enabled': 'true',
    },
    connection_id='yandexcloud_default',
    dag=dag,
)

# Task 3: Удаление кластера
delete_cluster = DataprocDeleteClusterOperator(
    task_id='delete_dataproc_cluster',
    trigger_rule='all_done',
    dag=dag,
)

# DAG flow
create_cluster >> grid_search_job >> delete_cluster

