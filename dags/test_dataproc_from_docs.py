"""
Тестовый DAG для создания DataProc кластера
На основе официальной документации Yandex Cloud
"""

import uuid
import datetime
from airflow import DAG
from airflow.utils.trigger_rule import TriggerRule
from airflow.models import Variable
from airflow.operators.python import PythonOperator

# ИМПОРТ ИЗ ДОКУМЕНТАЦИИ - с yandexcloud_dataproc!
from airflow.providers.yandex.operators.yandexcloud_dataproc import (
    DataprocCreateClusterOperator,
    DataprocCreatePysparkJobOperator,
    DataprocDeleteClusterOperator,
)

# Получаем данные из Airflow Variables
def get_cluster_config(**context):
    """Получение конфигурации из Variables"""
    config = {
        'zone': Variable.get('ZONE', 'ru-central1-a'),
        'ssh_key': Variable.get('YC_SSH_PUBLIC_KEY', ''),
        'subnet_id': Variable.get('SUBNET_ID', ''),
        'sa_id': Variable.get('DATAPROC_SERVICE_ACCOUNT_ID', ''),
        's3_bucket': Variable.get('S3_BUCKET_NAME', ''),
        'security_group_id': Variable.get('SECURITY_GROUP_ID', ''),
    }
    
    print("📋 Конфигурация кластера:")
    for key, value in config.items():
        if 'key' in key.lower():
            print(f"  {key}: ***")
        else:
            print(f"  {key}: {value}")
    
    return config

# Настройки DAG
with DAG(
    'test_dataproc_cluster_from_docs',
    schedule_interval=None,
    tags=['test', 'dataproc', 'docs'],
    start_date=datetime.datetime.now(),
    max_active_runs=1,
    catchup=False,
    description='Test DataProc cluster creation using operators from documentation'
) as test_dag:
    
    # Проверка конфигурации
    check_config = PythonOperator(
        task_id='check_config',
        python_callable=get_cluster_config,
    )
    
    # 1 этап: создание кластера Yandex Data Proc
    # Используем hardcoded параметры (как в рабочем DAG)
    def create_cluster_task(**context):
        """Создание кластера с параметрами"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Получаем параметры с fallback значениями (как в fish_classification_training.py)
        folder_id = Variable.get('FOLDER_ID', 'b1gjj3po03aa3m4j8ps5')
        zone = Variable.get('ZONE', 'ru-central1-a')
        subnet_id = Variable.get('SUBNET_ID', 'e9b5umsufggihj02a3o1')
        sa_id = Variable.get('DATAPROC_SERVICE_ACCOUNT_ID', 'ajepv2durkr1nk9rnoui')
        security_group_id = Variable.get('SECURITY_GROUP_ID', 'enpha1v51ug84ddqfob4')
        s3_bucket = Variable.get('S3_BUCKET_NAME', 'fish-classification-data-7wb4zv')
        ssh_key = Variable.get('YC_SSH_PUBLIC_KEY', 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCtV1GrBDN0NKa0VRfqBaGRyFsW6n4pKN7rqKWuStFo6If+6twnYwDYntTaXQBSQcIwF984u5NMP5BVMd8QKSBEvQK/IL9UFjdr3wB73+hKYMpoK9JPY2wPN6ECoxbGzkINZ+vhOgtnHytqGT7Sh79hoB6mKuJg0+yyMbxk0Lq/k7rtKlQYsm28rea4pIlvGmWgUXqzIcnj02K7x+hNGYYbe3kMlUY3MmvKaV1aM0P80gzWgoM0prpbSmdHUTkoP7QdkVlXHNU1xHINBU2lACt5aTL2OOlw/YLcaIDHmvKtghcpfRRskpc4VnJCLqPZgEIA2BTBe85FMcWwBOwTj4nt4YkbDzCgfDVi+K0SevvAKXJla+2H6KEMpUK6pUlpnnm2Q5UKkEiWd+kZ5Tc5ip0gKxkRPG+Q2lT28CbSgqGWmU0EkK2K1je+E/mWRkBybXyObwDHbDYNWmMF0Ztxoo6Rp7WgF2rtNOzeI58pyXFKI+Qn0vyri7s9aLVSBzAey6LVikYs+W5Vpipioh1sI0hETegDyUMQzrmoufoQeGPCBA5tsdAS715mSEhDey326qN5gVNVYcya4nEn2wJ9hNNS1NoSoy2+xvT5NMrLSLRso2Li/P0ud3dd1Xy5AVoMifzrufgZnFJY7nJUnY+0KgElbP35rsZRdsiRMuc5fVpRuQ== denispukinov@MacBook-Pro-Denis.local')
        
        cluster_name = f'test-fish-dp-{uuid.uuid4().hex[:8]}'
        
        logger.info(f"🏗️ Создание кластера: {cluster_name}")
        logger.info(f"📋 Folder ID: {folder_id}")
        logger.info(f"📋 Zone: {zone}")
        logger.info(f"📋 Subnet ID: {subnet_id}")
        logger.info(f"📋 Service Account ID: {sa_id}")
        logger.info(f"📋 Security Group ID: {security_group_id}")
        logger.info(f"📋 S3 Bucket: {s3_bucket}")
        
        # Создаём оператор с параметрами из Lockbox
        create_op = DataprocCreateClusterOperator(
            task_id='dp_cluster_create_op',
            folder_id=folder_id,
            cluster_name=cluster_name,
            cluster_description='Test DataProc cluster for fish classification',
            ssh_public_keys=ssh_key,
            service_account_id=sa_id,
            subnet_id=subnet_id,
            s3_bucket=s3_bucket,
            zone=zone,
            cluster_image_version='2.1',
            
            # Master node (минимальный размер диска для экономии квоты)
            masternode_resource_preset='s2.small',
            masternode_disk_type='network-hdd',  # HDD вместо SSD для экономии квоты
            masternode_disk_size=20,  # Минимум для DataProc (требуется минимум 20 GB)
            
            # Compute nodes (для обработки)
            computenode_resource_preset='s2.small',
            computenode_disk_type='network-hdd',  # HDD вместо SSD для экономии квоты
            computenode_disk_size=20,  # Минимум для DataProc (требуется минимум 20 GB)
            computenode_count=1,
            computenode_max_hosts_count=1,  # Без автоскейлинга для экономии
            
            # Легковесный кластер без data nodes
            services=['YARN', 'SPARK', 'LIVY'],
            datanode_count=0,
            
            # Security group
            security_group_ids=[security_group_id],
            
            # Свойства Spark
            properties={
                'spark:spark.sql.warehouse.dir': f's3a://{s3_bucket}/spark-warehouse/',
            },
        )
        
        # Выполняем создание кластера
        result = create_op.execute(context)
        
        # Сохраняем имя кластера для удаления
        context['task_instance'].xcom_push(key='cluster_name', value=cluster_name)
        
        logger.info(f"✅ Кластер создан: {cluster_name}")
        return result
    
    create_spark_cluster = PythonOperator(
        task_id='dp_cluster_create',
        python_callable=create_cluster_task,
    )
    
    # 2 этап: простая задача-заглушка (вместо PySpark job)
    test_placeholder = PythonOperator(
        task_id='test_placeholder',
        python_callable=lambda: print("✅ Кластер создан! Здесь будет PySpark job."),
    )
    
    # 3 этап: удаление кластера
    delete_spark_cluster = DataprocDeleteClusterOperator(
        task_id='dp_cluster_delete',
        trigger_rule=TriggerRule.ALL_DONE,
    )
    
    # Формирование DAG
    check_config >> create_spark_cluster >> test_placeholder >> delete_spark_cluster
