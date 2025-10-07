# 🎓 Обучение модели классификации рыб

Руководство по обучению модели классификации видов рыб Красного моря.

## 📋 Содержание

- [Автоматический процесс](#автоматический-процесс)
- [Ручная настройка](#ручная-настройка)
- [Мониторинг обучения](#мониторинг-обучения)
- [Работа с MLflow](#работа-с-mlflow)

## 🤖 Автоматический процесс

### Полное развёртывание с обучением

Вся система, включая загрузку DAG и переменных, разворачивается автоматически:

```bash
make deploy-all
```

Эта команда выполняет:
1. ✅ Генерацию SSH ключа для DataProc
2. ✅ Создание инфраструктуры (Terraform)
3. ✅ Развёртывание Kubernetes приложений
4. ✅ Копирование датасета
5. ✅ Загрузку датасета в S3
6. ✅ Загрузку DAG и Spark скриптов в S3
7. ✅ Настройку переменных Airflow

### Только настройка Airflow

Если нужно только обновить DAG или переменные:

```bash
make setup-airflow
```

## 🛠️ Ручная настройка

### 1. Проверка переменных Airflow

После развёртывания откройте Airflow UI и проверьте переменные:

```bash
make get-airflow-url
```

Перейдите: **Admin → Variables**

Должны быть установлены:

**Инфраструктурные:**
- `CLOUD_ID` - ID облака Yandex Cloud
- `FOLDER_ID` - ID папки
- `ZONE` - зона доступности (ru-central1-a)
- `NETWORK_ID` - ID сети VPC
- `SUBNET_ID` - ID подсети
- `SECURITY_GROUP_ID` - ID группы безопасности

**DataProc:**
- `DATAPROC_SERVICE_ACCOUNT_ID` - ID service account для DataProc
- `DP_SA_JSON` - JSON ключ service account
- `YC_SSH_PUBLIC_KEY` - публичный SSH ключ

**S3 и MLflow:**
- `S3_BUCKET_NAME` - имя S3 bucket
- `S3_ACCESS_KEY` - ключ доступа к S3
- `S3_SECRET_KEY` - секретный ключ S3
- `MLFLOW_TRACKING_URI` - адрес MLflow сервера

**Параметры обучения:**
- `NUM_CLASSES` - количество классов (17)
- `IMAGE_SIZE` - размер изображения (224)
- `BATCH_SIZE` - размер батча (32)
- `EPOCHS` - количество эпох (20)
- `LEARNING_RATE` - скорость обучения (0.001)

### 2. Импорт переменных вручную (если требуется)

Если переменные не загрузились автоматически:

1. Откройте Airflow UI
2. Перейдите: **Admin → Variables → Import Variables**
3. Загрузите файл: `/tmp/airflow_variables.json`

### 3. Проверка DAG

Перейдите в раздел **DAGs** и найдите:

**`fish_classification_training`** 🐟

Убедитесь, что:
- ✅ DAG загружен без ошибок
- ✅ Все задачи видны в Graph View
- ✅ Нет красных иконок ошибок

## 🚀 Запуск обучения

### Через Airflow UI

1. Откройте DAG: `fish_classification_training`
2. Нажмите кнопку **▶️ Trigger DAG**
3. (Опционально) Установите параметры в Config JSON:
   ```json
   {
     "epochs": 20,
     "batch_size": 32,
     "learning_rate": 0.001
   }
   ```
4. Нажмите **Trigger**

### График выполнения

DAG состоит из следующих задач:

```
create_yandex_connection
       ↓
validate_environment
       ↓
validate_dataset
       ↓
  create_cluster
       ↓
wait_cluster_ready
       ↓
   train_model (DataProc)
       ↓
  register_model
       ↓
promote_to_production
       ↓
  cleanup_cluster
       ↓
 generate_report
```

#### Описание задач:

1. **create_yandex_connection** - Создание подключения к Yandex Cloud
2. **validate_environment** - Проверка всех необходимых переменных
3. **validate_dataset** - Проверка наличия и структуры датасета в S3
4. **create_cluster** - Создание DataProc кластера для обучения
5. **wait_cluster_ready** - Ожидание готовности кластера (120 сек)
6. **train_model** - Обучение EfficientNet-B4 на Spark кластере
7. **register_model** - Регистрация модели в MLflow Model Registry
8. **promote_to_production** - Перевод модели в Production stage
9. **cleanup_cluster** - Удаление DataProc кластера
10. **generate_report** - Генерация итогового отчёта

## 📊 Мониторинг обучения

### В Airflow

1. Откройте DAG Run
2. Перейдите в **Graph View** для визуализации
3. Кликните на задачу → **Logs** для просмотра логов

### В MLflow

Для просмотра метрик обучения:

```bash
make get-mlflow-url
```

В MLflow UI:
- **Experiments** - все запуски обучения
- **Models** - зарегистрированные модели
- **Metrics** - графики loss и accuracy
- **Artifacts** - сохранённые модели

### Метрики обучения

Во время обучения отслеживаются:

**Per-epoch метрики:**
- `train_loss` - функция потерь на train
- `train_accuracy` - точность на train
- `val_loss` - функция потерь на validation
- `val_accuracy` - точность на validation
- `learning_rate` - текущая скорость обучения

**Итоговые метрики:**
- `best_val_loss` - лучшее значение val loss
- `best_val_accuracy` - лучшая точность на validation

**Тестовые метрики:**
- `test_accuracy` - точность на тесте
- `test_precision` - precision
- `test_recall` - recall
- `test_f1_score` - F1 score

## 🎯 Параметры обучения

### Модель

- **Архитектура**: EfficientNet-B4 (pretrained на ImageNet)
- **Fine-tuning**: Только classifier layer
- **Классы**: 17 видов рыб

### Датасет

- **Train**: ~900 изображений
- **Validation**: ~150 изображений
- **Test**: ~150 изображений
- **Augmentation**: 
  - Horizontal flip
  - Random rotation (±15°)
  - Color jitter (brightness, contrast)

### Гиперпараметры (по умолчанию)

```python
IMAGE_SIZE = 224          # Размер входного изображения
BATCH_SIZE = 32           # Размер батча
EPOCHS = 20               # Количество эпох
LEARNING_RATE = 0.001     # Начальная скорость обучения
OPTIMIZER = 'Adam'        # Оптимизатор
SCHEDULER = 'ReduceLROnPlateau'  # Планировщик LR
```

## 📈 Grafana мониторинг

Для мониторинга системных метрик:

```bash
make get-grafana-url
```

Доступные дашборды:
- **Airflow Metrics** - статус DAG runs
- **MLflow Metrics** - метрики экспериментов
- **System Resources** - CPU, Memory, Disk

## 🔧 Устранение проблем

### DAG не появляется в Airflow

**Решение:**
```bash
# Проверьте логи Airflow Scheduler
kubectl logs -n mlops-system deployment/airflow-scheduler

# Перезагрузите DAG
make setup-airflow
```

### Ошибка подключения к S3

**Причина:** Неверные S3 credentials

**Решение:**
```bash
# Проверьте переменные в Airflow UI
# Или обновите через:
make setup-airflow
```

### Ошибка подключения к MLflow

**Причина:** MLflow сервер недоступен

**Решение:**
```bash
# Проверьте статус MLflow VM
cd terraform
terraform output mlflow_vm_ip

# Проверьте доступность
curl http://<MLFLOW_IP>:5000/health
```

### Out of Memory при обучении

**Решение:** Уменьшите `BATCH_SIZE`:

1. Откройте Airflow UI → Admin → Variables
2. Измените `BATCH_SIZE` на `16` или `8`
3. Перезапустите DAG

## 📚 Дополнительная информация

### Виды рыб в датасете

1. Perca Fluviatilis (Речной окунь)
2. Perccottus Glenii (Ротан)
3. Esox Lucius (Щука)
4. Alburnus Alburnus (Уклейка)
5. Abramis Brama (Лещ)
6. Carassius Gibelio (Карась серебряный)
7. Squalius Cephalus (Голавль)
8. Scardinius Erythrophthalmus (Красноперка)
9. Rutilus Lacustris (Плотва озерная)
10. Rutilus Rutilus (Плотва обыкновенная)
11. Blicca Bjoerkna (Густера)
12. Gymnocephalus Cernua (Ёрш)
13. Leuciscus Idus (Язь)
14. Sander Lucioperca (Судак)
15. Leuciscus Baicalensis (Елец байкальский)
16. Gobio Gobio (Пескарь)
17. Tinca Tinca (Линь)

### Структура модели

```python
EfficientNet-B4
├── Features (frozen)
│   └── ... (pretrained layers)
└── Classifier
    ├── Dropout(0.4)
    └── Linear(in_features=1792, out_features=17)  # Trainable
```

### Расположение файлов

```
S3 Bucket:
  datasets/
    ├── processed_images/
    │   ├── train/
    │   ├── val/
    │   └── test/
    ├── annotations/
    └── metadata.json
  
  airflow-dags/
    ├── fish_classification_training.py
    └── requirements.txt

MLflow:
  experiments/
    └── fish-classification/
        └── runs/
            ├── metrics/
            ├── params/
            └── artifacts/
                └── model/
```

## 🎉 Успешное обучение

После успешного завершения обучения:

1. ✅ Модель зарегистрирована в MLflow Model Registry
2. ✅ Модель переведена в Production stage
3. ✅ Модель готова к использованию в Inference API

Для использования модели в inference:

```bash
# Перезапустите ML Workers для загрузки новой модели
kubectl rollout restart deployment/ml-worker -n ml-inference

# Протестируйте API
make test-api
```

---

**Документация:** [README.md](../README.md) | **Архитектура:** [ARCHITECTURE.md](../ARCHITECTURE.md)
