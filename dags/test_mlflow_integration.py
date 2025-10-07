"""
Тестовый DAG для проверки интеграции с MLflow через HTTP API

Этот DAG проверяет:
1. Доступность MLflow сервера
2. Создание эксперимента
3. Логирование параметров и метрик через REST API
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from datetime import datetime
import logging
import requests
import json

logger = logging.getLogger(__name__)


def test_mlflow_connection(**context):
    """Проверка подключения к MLflow через HTTP API"""
    mlflow_uri = Variable.get("MLFLOW_TRACKING_URI", "http://130.193.38.189:5000")
    
    logger.info(f"🔗 Testing MLflow connection to: {mlflow_uri}")
    
    try:
        # Проверяем health endpoint
        response = requests.get(f"{mlflow_uri}/health", timeout=10)
        response.raise_for_status()
        logger.info(f"✅ MLflow server is healthy: {response.text}")
        
        # Получаем список экспериментов
        response = requests.get(f"{mlflow_uri}/api/2.0/mlflow/experiments/search", timeout=10)
        response.raise_for_status()
        experiments = response.json()
        logger.info(f"✅ Found {len(experiments.get('experiments', []))} experiments")
        
        return {"status": "success", "mlflow_uri": mlflow_uri}
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to MLflow: {e}")
        raise


def create_test_experiment(**context):
    """Создание тестового эксперимента"""
    mlflow_uri = Variable.get("MLFLOW_TRACKING_URI", "http://130.193.38.189:5000")
    experiment_name = "airflow-test-integration"
    
    logger.info(f"📊 Creating experiment: {experiment_name}")
    
    try:
        # Создаём или получаем эксперимент
        response = requests.post(
            f"{mlflow_uri}/api/2.0/mlflow/experiments/create",
            json={"name": experiment_name},
            timeout=10
        )
        
        if response.status_code == 200:
            experiment_id = response.json().get("experiment_id")
            logger.info(f"✅ Created new experiment with ID: {experiment_id}")
        else:
            # Эксперимент уже существует, получаем его ID
            response = requests.get(
                f"{mlflow_uri}/api/2.0/mlflow/experiments/get-by-name",
                params={"experiment_name": experiment_name},
                timeout=10
            )
            response.raise_for_status()
            experiment_id = response.json()["experiment"]["experiment_id"]
            logger.info(f"✅ Using existing experiment with ID: {experiment_id}")
        
        return {"experiment_id": experiment_id, "experiment_name": experiment_name}
        
    except Exception as e:
        logger.error(f"❌ Failed to create experiment: {e}")
        raise


def log_test_run(**context):
    """Логирование тестового run с параметрами и метриками"""
    ti = context['ti']
    experiment_data = ti.xcom_pull(task_ids='create_test_experiment')
    experiment_id = experiment_data['experiment_id']
    
    mlflow_uri = Variable.get("MLFLOW_TRACKING_URI", "http://130.193.38.189:5000")
    
    logger.info(f"📝 Logging test run to experiment {experiment_id}")
    
    try:
        # Создаём run
        response = requests.post(
            f"{mlflow_uri}/api/2.0/mlflow/runs/create",
            json={
                "experiment_id": experiment_id,
                "start_time": int(datetime.now().timestamp() * 1000),
                "tags": [
                    {"key": "source", "value": "airflow"},
                    {"key": "dag_id", "value": context['dag'].dag_id},
                    {"key": "run_id", "value": context['run_id']}
                ]
            },
            timeout=10
        )
        response.raise_for_status()
        run_id = response.json()["run"]["info"]["run_id"]
        logger.info(f"✅ Created run with ID: {run_id}")
        
        # Логируем параметры
        params = [
            {"key": "test_param_1", "value": "value_1"},
            {"key": "test_param_2", "value": "42"},
            {"key": "model_type", "value": "test"},
        ]
        
        for param in params:
            response = requests.post(
                f"{mlflow_uri}/api/2.0/mlflow/runs/log-parameter",
                json={"run_id": run_id, **param},
                timeout=10
            )
            response.raise_for_status()
        
        logger.info(f"✅ Logged {len(params)} parameters")
        
        # Логируем метрики
        metrics = [
            {"key": "test_accuracy", "value": 0.95, "timestamp": int(datetime.now().timestamp() * 1000)},
            {"key": "test_loss", "value": 0.15, "timestamp": int(datetime.now().timestamp() * 1000)},
            {"key": "test_f1_score", "value": 0.93, "timestamp": int(datetime.now().timestamp() * 1000)},
        ]
        
        for metric in metrics:
            response = requests.post(
                f"{mlflow_uri}/api/2.0/mlflow/runs/log-metric",
                json={"run_id": run_id, **metric},
                timeout=10
            )
            response.raise_for_status()
        
        logger.info(f"✅ Logged {len(metrics)} metrics")
        
        # Завершаем run
        response = requests.post(
            f"{mlflow_uri}/api/2.0/mlflow/runs/update",
            json={
                "run_id": run_id,
                "status": "FINISHED",
                "end_time": int(datetime.now().timestamp() * 1000)
            },
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"✅ Finished run {run_id}")
        
        return {
            "run_id": run_id,
            "experiment_id": experiment_id,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to log test run: {e}")
        raise


def verify_mlflow_data(**context):
    """Проверка, что данные успешно записались в MLflow"""
    ti = context['ti']
    run_data = ti.xcom_pull(task_ids='log_test_run')
    run_id = run_data['run_id']
    
    mlflow_uri = Variable.get("MLFLOW_TRACKING_URI", "http://130.193.38.189:5000")
    
    logger.info(f"🔍 Verifying data for run {run_id}")
    
    try:
        # Получаем информацию о run
        response = requests.get(
            f"{mlflow_uri}/api/2.0/mlflow/runs/get",
            params={"run_id": run_id},
            timeout=10
        )
        response.raise_for_status()
        run_info = response.json()["run"]
        
        # Проверяем параметры
        params = run_info["data"]["params"]
        logger.info(f"✅ Found {len(params)} parameters: {[p['key'] for p in params]}")
        
        # Проверяем метрики
        metrics = run_info["data"]["metrics"]
        logger.info(f"✅ Found {len(metrics)} metrics: {[m['key'] for m in metrics]}")
        
        # Проверяем статус
        status = run_info["info"]["status"]
        logger.info(f"✅ Run status: {status}")
        
        if status == "FINISHED" and len(params) >= 3 and len(metrics) >= 3:
            logger.info("=" * 80)
            logger.info("🎉 MLflow integration test PASSED!")
            logger.info(f"   MLflow UI: {mlflow_uri}")
            logger.info(f"   Experiment: {run_data['experiment_id']}")
            logger.info(f"   Run ID: {run_id}")
            logger.info("=" * 80)
            return {"status": "passed", "run_id": run_id}
        else:
            raise ValueError("Test validation failed: incomplete data")
        
    except Exception as e:
        logger.error(f"❌ Failed to verify MLflow data: {e}")
        raise


# DAG definition
with DAG(
    dag_id='test_mlflow_integration',
    start_date=datetime(2023, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=['mlflow', 'test', 'integration'],
    description='Test MLflow integration via HTTP API',
) as dag:
    
    test_connection = PythonOperator(
        task_id='test_mlflow_connection',
        python_callable=test_mlflow_connection,
    )
    
    create_experiment = PythonOperator(
        task_id='create_test_experiment',
        python_callable=create_test_experiment,
    )
    
    log_run = PythonOperator(
        task_id='log_test_run',
        python_callable=log_test_run,
    )
    
    verify_data = PythonOperator(
        task_id='verify_mlflow_data',
        python_callable=verify_mlflow_data,
    )
    
    # Task dependencies
    test_connection >> create_experiment >> log_run >> verify_data