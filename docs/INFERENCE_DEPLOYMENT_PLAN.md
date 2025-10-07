# 🚀 План развёртывания Inference сервиса

## 📋 Обзор

После обучения модели мы развернём полноценный inference сервис с Web UI для классификации рыб.

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      User Browser                           │
│                    (Web Interface)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTP (Upload Image)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Kubernetes LoadBalancer                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Service                           │
│              (Fish Classification API)                      │
│                                                             │
│  - POST /predict (upload image)                            │
│  - GET /health                                             │
│  - GET /model_info                                         │
└────────────┬────────────────────────┬───────────────────────┘
             │                        │
             │ Load model             │ Log predictions
             ▼                        ▼
┌────────────────────┐    ┌──────────────────────┐
│   MLflow Server    │    │   PostgreSQL         │
│  (Model Registry)  │    │  (Predictions Log)   │
└────────────────────┘    └──────────────────────┘
```

## 📦 Компоненты

### 1. FastAPI Inference Service

**Файл**: `api/inference_service.py`

**Функции**:
- Загрузка модели из MLflow при старте
- Endpoint для предсказаний
- Preprocessing изображений
- Логирование предсказаний

**Endpoints**:
```python
POST /predict
  - Input: multipart/form-data (image file)
  - Output: JSON {
      "class": "salmon",
      "confidence": 0.95,
      "all_predictions": {
        "salmon": 0.95,
        "trout": 0.03,
        ...
      },
      "prediction_time": 0.123
    }

GET /health
  - Output: {"status": "healthy", "model_loaded": true}

GET /model_info
  - Output: {"model_name": "...", "version": "1", "classes": [...]}
```

### 2. Web UI

**Файл**: `web/index.html`

**Функции**:
- Drag & drop для загрузки изображений
- Превью загруженного изображения
- Отображение результатов классификации
- Визуализация вероятностей (progress bars)
- История последних предсказаний

**Технологии**:
- HTML5 + CSS3 + JavaScript (vanilla)
- Bootstrap 5 для UI
- Chart.js для визуализации

### 3. Kubernetes Deployment

**Файлы**:
- `k8s/inference-api-deployment.yaml`
- `k8s/inference-api-service.yaml`
- `k8s/inference-api-hpa.yaml`

**Конфигурация**:
- 2-3 реплики для HA
- HPA: автоскейлинг 2-10 реплик
- Resource limits: 2 CPU, 4GB RAM
- Liveness/Readiness probes
- LoadBalancer для внешнего доступа

## 🔄 Workflow развёртывания

### Шаг 1: Обучение модели ✅ (сегодня)

```bash
# 1. Тестируем MLflow
Airflow DAG: test_mlflow_integration (~2-3 мин)

# 2. Обучаем модель
Airflow DAG: fish_classification_training_full (~20-25 мин)

# 3. Проверяем модель в MLflow UI
http://130.193.38.189:5000
  - Experiment: fish-classification
  - Model: fish-classification-mobilenetv2
  - Version: 1
```

### Шаг 2: Создание Inference API 🔄 (следующий шаг)

```bash
# 1. Создаём FastAPI сервис
api/inference_service.py
api/requirements.txt
api/Dockerfile

# 2. Собираем Docker образ
docker build -t fish-inference-api:latest api/
docker tag fish-inference-api:latest cr.yandex/...
docker push cr.yandex/...

# 3. Деплоим в Kubernetes
kubectl apply -f k8s/inference-api-deployment.yaml
kubectl apply -f k8s/inference-api-service.yaml
kubectl apply -f k8s/inference-api-hpa.yaml

# 4. Получаем внешний IP
kubectl get svc inference-api-service
```

### Шаг 3: Создание Web UI 🔄 (финал)

```bash
# 1. Создаём статический сайт
web/index.html
web/style.css
web/app.js

# 2. Деплоим в Kubernetes (Nginx)
kubectl apply -f k8s/web-ui-deployment.yaml
kubectl apply -f k8s/web-ui-service.yaml

# 3. Получаем URL
kubectl get svc web-ui-service
```

## 📝 Пример использования

### Через Web UI:

1. Открываете `http://<web-ui-ip>`
2. Перетаскиваете фото рыбы
3. Нажимаете "Classify"
4. Видите результат:
   ```
   🐟 Salmon (95.3% confidence)
   
   All predictions:
   ████████████████████ Salmon: 95.3%
   ██ Trout: 2.1%
   █ Bass: 1.5%
   ...
   ```

### Через API:

```bash
# Upload image
curl -X POST http://<api-ip>/predict \
  -F "file=@my_fish.jpg"

# Response
{
  "class": "salmon",
  "confidence": 0.953,
  "all_predictions": {
    "salmon": 0.953,
    "trout": 0.021,
    "bass": 0.015,
    ...
  },
  "prediction_time": 0.123
}
```

## 🔧 Технические детали

### Model Loading Strategy

```python
# При старте сервиса
def load_model():
    mlflow.set_tracking_uri(MLFLOW_URI)
    
    # Загружаем latest version
    model = mlflow.keras.load_model(
        f"models:/fish-classification-mobilenetv2/latest"
    )
    
    # Загружаем class indices
    client = mlflow.tracking.MlflowClient()
    run = client.get_latest_versions("fish-classification-mobilenetv2")[0]
    class_indices = mlflow.artifacts.load_dict(
        f"runs:/{run.run_id}/class_indices.json"
    )
    
    return model, class_indices
```

### Image Preprocessing

```python
def preprocess_image(image_bytes):
    # Load image
    img = Image.open(io.BytesIO(image_bytes))
    
    # Resize to model input size
    img = img.resize((224, 224))
    
    # Convert to array
    img_array = np.array(img) / 255.0
    
    # Add batch dimension
    img_array = np.expand_dims(img_array, axis=0)
    
    return img_array
```

### Prediction with Logging

```python
async def predict(image_bytes):
    # Preprocess
    img_array = preprocess_image(image_bytes)
    
    # Predict
    start_time = time.time()
    predictions = model.predict(img_array)
    prediction_time = time.time() - start_time
    
    # Get top class
    top_class_idx = np.argmax(predictions[0])
    top_class = class_names[top_class_idx]
    confidence = float(predictions[0][top_class_idx])
    
    # Log to database
    log_prediction(
        image_hash=hashlib.md5(image_bytes).hexdigest(),
        predicted_class=top_class,
        confidence=confidence,
        prediction_time=prediction_time
    )
    
    return {
        "class": top_class,
        "confidence": confidence,
        "all_predictions": dict(zip(class_names, predictions[0])),
        "prediction_time": prediction_time
    }
```

## 📊 Мониторинг

### Метрики для Prometheus

```python
from prometheus_client import Counter, Histogram

prediction_counter = Counter(
    'predictions_total',
    'Total number of predictions',
    ['class', 'confidence_bucket']
)

prediction_latency = Histogram(
    'prediction_latency_seconds',
    'Prediction latency in seconds'
)
```

### Grafana Dashboard

- Predictions per minute
- Average confidence by class
- Prediction latency (p50, p95, p99)
- Error rate
- Model version in use

## 🚀 Следующие шаги

### Сегодня:
1. ✅ Запустить `test_mlflow_integration` DAG
2. 🔄 Запустить `fish_classification_training_full` DAG
3. ✅ Проверить модель в MLflow UI

### Завтра:
1. 📝 Создать FastAPI Inference Service
2. 🐳 Собрать Docker образ
3. ☸️ Развернуть в Kubernetes
4. 🌐 Создать Web UI
5. 🎉 Протестировать полный pipeline

## 💡 Дополнительные возможности (опционально)

- **A/B Testing**: сравнение разных версий модели
- **Batch Predictions**: обработка множества изображений
- **Feedback Loop**: пользователи могут корректировать предсказания
- **Model Retraining**: автоматическое переобучение на новых данных
- **Multi-model Serving**: ensemble из нескольких моделей
