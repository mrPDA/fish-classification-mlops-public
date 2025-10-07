# 🚀 Автоматическая регистрация моделей в MLflow

## Обзор

Система настроена для автоматической регистрации обученных моделей в MLflow Model Registry и их автоматического развёртывания в Production stage.

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Airflow DAG                              │
│  (fish_classification_training_full)                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              DataProc Spark Job                             │
│        (train_fish_model_minimal.py)                        │
├─────────────────────────────────────────────────────────────┤
│  1. Train model                                             │
│  2. Log metrics & artifacts to MLflow                       │
│  3. ✨ Register model in Model Registry                     │
│  4. ✨ Archive previous Production model                    │
│  5. ✨ Transition new model to Production                   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              MLflow Model Registry                          │
├─────────────────────────────────────────────────────────────┤
│  Model: fish-classifier-efficientnet-b4                     │
│  ├─ Version 1: Production ✅                                │
│  ├─ Version 2: Archived                                     │
│  └─ Version 3: Archived                                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Inference API                                  │
├─────────────────────────────────────────────────────────────┤
│  model_uri = "models:/fish-classifier.../Production"       │
│  model = mlflow.pyfunc.load_model(model_uri)               │
│  ✨ Always uses latest Production model                     │
└─────────────────────────────────────────────────────────────┘
```

## Жизненный цикл модели

### 1. Обучение (Training)

```python
# В spark_jobs/train_fish_model_minimal.py
with mlflow.start_run():
    # Training...
    model.fit(X_train, y_train, ...)
    
    # Log model artifacts
    mlflow.tensorflow.log_model(model, "model")
    mlflow.log_metrics({
        "train_accuracy": train_acc,
        "val_accuracy": val_acc
    })
```

### 2. Регистрация (Registration)

```python
from mlflow.tracking import MlflowClient

client = MlflowClient()
model_name = "fish-classifier-efficientnet-b4"

# Register new version
model_version = mlflow.register_model(
    model_uri=f"runs:/{run_id}/model",
    name=model_name,
    tags={
        "accuracy": f"{final_train_acc:.4f}",
        "val_accuracy": f"{final_val_acc:.4f}",
        "framework": "tensorflow",
        "architecture": "mobilenet-v2",
        "training_date": datetime.now().isoformat(),
        "auto_registered": "true"
    }
)
```

### 3. Переход в Production (Promotion)

```python
# Archive previous Production models
production_models = client.get_latest_versions(model_name, stages=["Production"])
for prod_model in production_models:
    client.transition_model_version_stage(
        name=model_name,
        version=prod_model.version,
        stage="Archived"
    )

# Promote new model to Production
client.transition_model_version_stage(
    name=model_name,
    version=model_version.version,
    stage="Production",
    archive_existing_versions=True
)
```

### 4. Загрузка в API (Deployment)

```python
# В api/main.py
def load_model():
    """Load latest production model from MLflow"""
    model_uri = f"models:/{MODEL_NAME}/Production"
    model = mlflow.pyfunc.load_model(model_uri)
    return model
```

## Stages модели

| Stage | Описание | Когда используется |
|-------|----------|-------------------|
| **None** | Только зарегистрирована | Сразу после регистрации |
| **Staging** | На тестировании | Ручной перевод для тестирования |
| **Production** | В production | Автоматически после обучения |
| **Archived** | Устарела | Автоматически при появлении новой |

## Мониторинг

### MLflow UI

Откройте MLflow UI для просмотра всех версий:

```
http://158.160.61.2:5000/#/models/fish-classifier-efficientnet-b4
```

Здесь можно увидеть:
- Все версии модели
- Текущий stage каждой версии
- Метрики (accuracy, val_accuracy)
- Дата регистрации
- Run ID для трассировки

### API для проверки

```python
from mlflow.tracking import MlflowClient

client = MlflowClient()

# Получить Production модель
prod_models = client.get_latest_versions(
    "fish-classifier-efficientnet-b4", 
    stages=["Production"]
)

for model in prod_models:
    print(f"Version: {model.version}")
    print(f"Stage: {model.current_stage}")
    print(f"Run ID: {model.run_id}")
```

## Ручное управление

### Откат на предыдущую версию

```python
from mlflow.tracking import MlflowClient

client = MlflowClient()

# Перевести версию 1 обратно в Production
client.transition_model_version_stage(
    name="fish-classifier-efficientnet-b4",
    version="1",
    stage="Production",
    archive_existing_versions=True
)
```

### Удаление версии

```python
# Удалить конкретную версию
client.delete_model_version(
    name="fish-classifier-efficientnet-b4",
    version="2"
)
```

### Обновление тегов

```python
# Добавить или обновить теги
client.set_model_version_tag(
    name="fish-classifier-efficientnet-b4",
    version="1",
    key="reviewed",
    value="true"
)
```

## Преимущества

### 1. 🚀 Zero-Downtime Deployments

API автоматически использует последнюю Production модель. При обновлении модели просто перезапустите API pods:

```bash
kubectl rollout restart deployment/fish-api -n ml-inference
```

### 2. 📊 Full Traceability

- История всех версий моделей
- Кто и когда зарегистрировал
- Какие метрики у каждой версии
- Легко откатиться на любую версию

### 3. 🔄 CI/CD для ML

Полностью автоматизированный pipeline:
```
Train → Log → Register → Archive Old → Deploy → Monitor
```

### 4. 📝 Compliance & Audit

Все изменения логируются в MLflow:
- Кто создал модель
- Когда была зарегистрирована
- Когда переведена в Production
- История всех transitions

## Troubleshooting

### Модель не регистрируется

**Проблема:** Ошибка при регистрации модели

**Решение:**
1. Проверьте доступность MLflow:
   ```bash
   curl http://158.160.61.2:5000/api/2.0/mlflow/registered-models/list
   ```

2. Проверьте логи Spark job в Airflow

3. Убедитесь, что модель залогирована:
   ```python
   mlflow.tensorflow.log_model(model, "model")
   ```

### API загружает старую модель

**Проблема:** API не видит новую Production модель

**Решение:**
1. Перезапустите API pods:
   ```bash
   kubectl rollout restart deployment/fish-api -n ml-inference
   ```

2. Проверьте что модель в Production:
   ```bash
   curl http://158.160.61.2:5000/api/2.0/mlflow/registered-models/get?name=fish-classifier-efficientnet-b4
   ```

### Несколько моделей в Production

**Проблема:** Две версии одновременно в Production

**Решение:**
```python
from mlflow.tracking import MlflowClient

client = MlflowClient()

# Архивировать все кроме последней
prod_models = client.get_latest_versions(
    "fish-classifier-efficientnet-b4", 
    stages=["Production"]
)

# Оставить только последнюю версию
latest = max(prod_models, key=lambda x: int(x.version))
for model in prod_models:
    if model.version != latest.version:
        client.transition_model_version_stage(
            name=model.name,
            version=model.version,
            stage="Archived"
        )
```

## Best Practices

### 1. Версионирование

- ✅ Каждая модель автоматически получает новую версию
- ✅ Версии никогда не удаляются (только архивируются)
- ✅ Всегда можно откатиться на любую версию

### 2. Тестирование

Перед переводом в Production можно:
1. Зарегистрировать модель в Staging
2. Протестировать на тестовом API
3. Вручную перевести в Production

```python
# Не автоматически, а через Staging
client.transition_model_version_stage(
    name=model_name,
    version=model_version.version,
    stage="Staging"  # Сначала в Staging
)

# После тестирования
client.transition_model_version_stage(
    name=model_name,
    version=model_version.version,
    stage="Production"
)
```

### 3. Мониторинг метрик

Всегда логируйте:
- Training metrics (accuracy, loss)
- Validation metrics
- Inference latency
- Memory usage
- Model size

### 4. Документация

Добавляйте описания к моделям:

```python
client.update_model_version(
    name=model_name,
    version=model_version.version,
    description=f"""
    Model trained on {train_samples} samples
    Architecture: MobileNetV2 + Custom head
    Val Accuracy: {val_acc:.4f}
    Training date: {datetime.now().isoformat()}
    """
)
```

## Заключение

Система полностью автоматизирована:
1. ✅ Обучение запускается через Airflow
2. ✅ Модель автоматически регистрируется в MLflow
3. ✅ Автоматически переводится в Production
4. ✅ API автоматически использует Production модель

**Никаких ручных действий не требуется! 🎉**

