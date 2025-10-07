"""
Тестовый DAG для проверки доступности Yandex Provider операторов
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
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
    'test_yandex_provider_operators',
    default_args=default_args,
    description='Test Yandex Provider availability',
    schedule_interval=None,
    catchup=False,
    tags=['test', 'yandex', 'provider'],
)

def test_yandex_imports(**context):
    """Проверяет доступность Yandex Provider операторов"""
    import sys
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("🔍 Проверка доступности Yandex Provider...")
    
    # Проверяем версию пакета
    try:
        import airflow.providers.yandex
        logger.info(f"✅ airflow.providers.yandex доступен")
        logger.info(f"   Путь: {airflow.providers.yandex.__file__}")
        if hasattr(airflow.providers.yandex, '__version__'):
            logger.info(f"   Версия: {airflow.providers.yandex.__version__}")
    except ImportError as e:
        logger.error(f"❌ airflow.providers.yandex не доступен: {e}")
        return False
    
    # Проверяем доступность модуля operators.dataproc
    try:
        import airflow.providers.yandex.operators.dataproc as dataproc_module
        logger.info(f"✅ airflow.providers.yandex.operators.dataproc доступен")
        logger.info(f"   Путь: {dataproc_module.__file__}")
        
        # Показываем все доступные атрибуты
        available_items = [item for item in dir(dataproc_module) if not item.startswith('_')]
        logger.info(f"   Доступные элементы ({len(available_items)}):")
        for item in available_items:
            logger.info(f"     - {item}")
            
    except ImportError as e:
        logger.error(f"❌ airflow.providers.yandex.operators.dataproc не доступен: {e}")
        return False
    
    # Проверяем конкретные операторы
    operators_to_check = [
        'DataprocCreateClusterOperator',
        'DataprocDeleteClusterOperator',
        'DataprocCreatePysparkJobOperator',
        'DataprocCreateHiveJobOperator',
    ]
    
    logger.info("🔍 Проверка конкретных операторов:")
    for operator_name in operators_to_check:
        try:
            operator_class = getattr(dataproc_module, operator_name, None)
            if operator_class:
                logger.info(f"   ✅ {operator_name} - ДОСТУПЕН")
                logger.info(f"      Класс: {operator_class}")
            else:
                logger.warning(f"   ⚠️  {operator_name} - НЕ НАЙДЕН в модуле")
        except Exception as e:
            logger.error(f"   ❌ {operator_name} - ОШИБКА: {e}")
    
    # Проверяем hooks
    try:
        import airflow.providers.yandex.hooks.yandex as yandex_hooks
        logger.info(f"✅ airflow.providers.yandex.hooks.yandex доступен")
        
        available_hooks = [item for item in dir(yandex_hooks) if 'Hook' in item and not item.startswith('_')]
        logger.info(f"   Доступные hooks ({len(available_hooks)}):")
        for hook in available_hooks:
            logger.info(f"     - {hook}")
            
    except ImportError as e:
        logger.error(f"❌ airflow.providers.yandex.hooks не доступен: {e}")
    
    logger.info("✅ Проверка завершена")
    return True

with dag:
    test_task = PythonOperator(
        task_id='test_yandex_imports',
        python_callable=test_yandex_imports,
    )
