# 🐟 Обучение модели с Transfer Learning и MLflow

## 📋 Обзор

Этот документ описывает процесс обучения модели классификации рыб с использованием:
- **Transfer Learning** на базе предобученной MobileNetV2 (ImageNet weights)
- **Yandex DataProc** для распределённых вычислений
- **MLflow** для отслеживания экспериментов и версионирования моделей
- **Apache Airflow** для оркестрации pipeline

## 🏗️ Архитектура

```
┌─────────────────┐
│  Airflow DAG    │
│  (Orchestrator) │
└────────┬────────┘
         │
         ├──► 1. Создание DataProc кластера
         │
         ├──► 2. Запуск PySpark job для обучения
         │         │
         │         ├──► Загрузка датасета из S3
         │         ├──► Transfer Learning (MobileNetV2)
         │         ├──► Обучение с data augmentation
         │         └──► Логирование в MLflow
         │
         └──► 3. Удаление DataProc кластера
```

## 🎯 Transfer Learning Strategy

### Базовая модель: MobileNetV2

**Почему MobileNetV2?**
- ✅ Предобучена на ImageNet (1.4M изображений, 1000 классов)
- ✅ Легковесная архитектура (~3.5M параметров)
- ✅ Быстрая inference (~20ms на CPU)
- ✅ Хорошо работает на малых датасетах

### Кастомные слои для классификации рыб

```python
base_model = MobileNetV2(weights='imagenet', include_top=False)
base_model.trainable = False  # Замораживаем предобученные слои

# Добавляем кастомные слои
x = GlobalAveragePooling2D()(base_model.output)
x = Dense(512, activation='relu')(x)
x = Dropout(0.5)(x)
x = Dense(256, activation='relu')(x)
x = Dropout(0.3)(x)
predictions = Dense(9, activation='softmax')(x)  # 9 классов рыб
```

### Data Augmentation

Для увеличения разнообразия данных используется:
- Rotation (±20°)
- Width/Height shift (±20%)
- Horizontal flip
- Zoom (±20%)
- Shear (±20%)

## 📊 MLflow Integration

### Логируемые параметры

```python
mlflow.log_param("base_model", "MobileNetV2")
mlflow.log_param("pretrained_weights", "imagenet")
mlflow.log_param("num_classes", 9)
mlflow.log_param("image_size", 224)
mlflow.log_param("batch_size", 32)
mlflow.log_param("epochs", 10)
mlflow.log_param("learning_rate", 0.001)
```

### Логируемые метрики

- `train_accuracy` / `val_accuracy` (по эпохам)
- `train_loss` / `val_loss` (по эпохам)
- `final_train_accuracy`
- `final_val_accuracy`
- `top_k_categorical_accuracy`

### Артефакты

- Обученная модель (Keras format)
- Class indices mapping (JSON)
- Training history

## 🚀 Запуск обучения

### 1. Через Airflow UI

1. Откройте Airflow UI
2. Найдите DAG `fish_classification_training_full`
3. Нажмите "Trigger DAG"
4. Ожидайте завершения (~20-25 минут)

### 2. Через Airflow CLI

```bash
# Trigger DAG
airflow dags trigger fish_classification_training_full

# Проверить статус
airflow dags state fish_classification_training_full
```

### 3. Мониторинг в MLflow

```bash
# Откройте MLflow UI
open http://130.193.38.189:5000

# Найдите эксперимент "fish-classification"
# Просмотрите метрики и артефакты
```

## ⚙️ Настройка параметров

Параметры хранятся в **Airflow Variables** (Lockbox):

| Параметр | Значение по умолчанию | Описание |
|----------|----------------------|----------|
| `NUM_CLASSES` | 9 | Количество классов рыб |
| `IMAGE_SIZE` | 224 | Размер изображения (224x224) |
| `BATCH_SIZE` | 32 | Размер batch |
| `EPOCHS` | 10 | Количество эпох |
| `LEARNING_RATE` | 0.001 | Learning rate |

### Изменение параметров

```python
# В Airflow UI: Admin -> Variables
# Или через CLI:
airflow variables set EPOCHS 20
airflow variables set BATCH_SIZE 64
```

## 📈 Ожидаемые результаты

### Время обучения

- **Создание кластера**: ~5-7 минут
- **Обучение модели**: ~10-15 минут (10 epochs)
- **Удаление кластера**: ~2-3 минуты
- **Итого**: ~20-25 минут

### Точность модели

С Transfer Learning (MobileNetV2):
- **Train accuracy**: ~85-95%
- **Validation accuracy**: ~75-85%
- **Top-3 accuracy**: ~90-95%

Без Transfer Learning (с нуля):
- **Train accuracy**: ~70-80%
- **Validation accuracy**: ~60-70%
- **Требуется**: ~30-60 минут обучения

## 🔍 Troubleshooting

### Проблема: Низкая точность

**Решение**:
1. Увеличьте количество эпох (`EPOCHS = 20`)
2. Уменьшите learning rate (`LEARNING_RATE = 0.0001`)
3. Проверьте качество датасета

### Проблема: Overfitting

**Решение**:
1. Увеличьте dropout (в коде модели)
2. Увеличьте data augmentation
3. Уменьшите количество эпох

### Проблема: Out of Memory

**Решение**:
1. Уменьшите `BATCH_SIZE` (16 или 8)
2. Уменьшите `IMAGE_SIZE` (128 или 160)
3. Увеличьте размер DataProc кластера

## 📦 Файлы проекта

```
Finalwork_2/
├── dags/
│   └── fish_classification_training_full.py  # Airflow DAG
├── spark_jobs/
│   └── train_fish_model.py                   # PySpark скрипт обучения
└── docs/
    └── TRANSFER_LEARNING_TRAINING.md         # Эта документация
```

## 🎓 Дальнейшие улучшения

1. **Fine-tuning**: Разморозить последние слои MobileNetV2 для дообучения
2. **Ensemble**: Комбинировать несколько моделей (MobileNetV2 + ResNet50)
3. **AutoML**: Использовать Optuna для подбора гиперпараметров
4. **GPU**: Использовать DataProc кластер с GPU для ускорения
5. **A/B Testing**: Сравнивать разные версии моделей в production

## 📚 Полезные ссылки

- [MobileNetV2 Paper](https://arxiv.org/abs/1801.04381)
- [Transfer Learning Guide](https://www.tensorflow.org/tutorials/images/transfer_learning)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Yandex DataProc](https://cloud.yandex.ru/docs/data-proc/)
