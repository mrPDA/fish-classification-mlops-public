#!/usr/bin/env python3
"""
Скрипт для регистрации модели в MLflow Model Registry
"""
import mlflow
import os

# Настройка MLflow
MLFLOW_URI = "http://158.160.40.214:5000"
RUN_ID = "bcef140c268343d18847ec0f83245f34"
MODEL_NAME = "fish-classification-model"

# S3 credentials (нужны для доступа к артефактам)
# Получите эти значения из Yandex Cloud консоли или Lockbox
os.environ['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID', 'YOUR_ACCESS_KEY')
os.environ['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY', 'YOUR_SECRET_KEY')
os.environ['MLFLOW_S3_ENDPOINT_URL'] = 'https://storage.yandexcloud.net'

mlflow.set_tracking_uri(MLFLOW_URI)

print(f"🔍 Registering model from run: {RUN_ID}")
print(f"📦 Model name: {MODEL_NAME}")

try:
    # Регистрируем модель
    model_uri = f"runs:/{RUN_ID}/model"
    
    result = mlflow.register_model(
        model_uri=model_uri,
        name=MODEL_NAME,
        tags={"task": "fish-classification", "framework": "tensorflow"}
    )
    
    print(f"\n✅ Model registered successfully!")
    print(f"   Model: {result.name}")
    print(f"   Version: {result.version}")
    print(f"   Status: {result.status}")
    print(f"\n🔗 Model Registry: {MLFLOW_URI}/#/models/{MODEL_NAME}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

