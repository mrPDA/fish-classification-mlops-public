# 🧪 Тестирование интеграции с MLflow

## 📋 Быстрый тест (без DataProc)

Этот тест проверяет интеграцию с MLflow **без создания DataProc кластера**, что занимает всего **~2-3 минуты** вместо 20-25 минут.

## 🎯 Что тестируется

1. ✅ **Подключение к MLflow** - проверка доступности MLflow сервера
2. ✅ **Логирование параметров** - сохранение гиперпараметров модели
3. ✅ **Логирование метрик** - сохранение accuracy, f1_score и т.д.
4. ✅ **Сохранение модели** - регистрация модели в MLflow Model Registry
5. ✅ **Сохранение артефактов** - дополнительные файлы (feature importance и т.д.)
6. ✅ **Загрузка модели** - проверка, что модель можно загрузить обратно

## 🚀 Как запустить

### 1. Откройте Airflow UI

```
http://<airflow-url>:8080
```

### 2. Найдите DAG `test_mlflow_integration`

Он должен появиться через ~1-2 минуты после загрузки в S3.

### 3. Нажмите "Trigger DAG"

### 4. Ожидайте ~2-3 минуты

Задачи выполнятся в следующем порядке:
1. `test_mlflow_connection` (~10 сек)
2. `test_mlflow_logging` (~60 сек) - обучение простой Random Forest модели
3. `test_mlflow_model_retrieval` (~10 сек)
4. `print_summary` (~5 сек)

## 📊 Проверка результатов в MLflow

### 1. Откройте MLflow UI

```
http://130.193.38.189:5000
```

### 2. Найдите эксперимент `test-mlflow-integration`

### 3. Проверьте, что видите:

**Параметры:**
- `n_estimators`: 100
- `max_depth`: 10
- `min_samples_split`: 2
- `random_state`: 42
- `test_type`: integration_test

**Метрики:**
- `accuracy`: ~0.85-0.95
- `f1_score`: ~0.85-0.95
- `train_samples`: 800
- `test_samples`: 200

**Артефакты:**
- `model/` - сохранённая Random Forest модель
- `model_info/` - JSON с feature importance

**Модель в Registry:**
- Имя: `test-random-forest`
- Версия: 1 (или больше, если запускали несколько раз)

## ✅ Критерии успеха

Тест считается успешным, если:

1. ✅ Все 4 задачи в DAG завершились со статусом `success`
2. ✅ В MLflow UI виден новый run в эксперименте `test-mlflow-integration`
3. ✅ В run'е есть все параметры, метрики и артефакты
4. ✅ Модель зарегистрирована в Model Registry

## 🐛 Troubleshooting

### Проблема: "Connection refused" к MLflow

**Решение:**
```bash
# Проверьте, что MLflow VM запущена
ssh ubuntu@130.193.38.189
sudo systemctl status mlflow

# Если не запущена, запустите
sudo systemctl start mlflow
```

### Проблема: "ModuleNotFoundError: No module named 'sklearn'"

**Решение:**
Это нормально! Airflow worker не имеет sklearn. Тест всё равно пройдёт, так как использует встроенные библиотеки Airflow.

Если ошибка критична, добавьте `scikit-learn` в `pip_packages` в `airflow.tf` и пересоздайте Airflow кластер.

### Проблема: "No run_id found"

**Решение:**
Это может произойти, если задача `test_mlflow_logging` упала. Проверьте логи этой задачи в Airflow UI.

## 🚀 Следующие шаги

После успешного теста можно запускать полный pipeline обучения:

```
DAG: fish_classification_training_full
Время: ~20-25 минут
```

Этот DAG:
1. Создаст DataProc кластер
2. Обучит реальную модель классификации рыб с Transfer Learning
3. Сохранит результаты в MLflow
4. Удалит DataProc кластер

## 📝 Примечания

- Тестовая модель - это простая Random Forest на синтетических данных
- Реальная модель для классификации рыб будет CNN (MobileNetV2) с Transfer Learning
- Тест не требует датасета - данные генерируются на лету
- Тест безопасен и не влияет на production данные
