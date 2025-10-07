# 📊 Датасет: Fish Species Classification

## Обзор

Для обучения модели классификации рыб используется датасет **A Large Scale Fish Dataset** от Kaggle.

## Характеристики

- **Количество классов:** 15 видов пресноводных рыб
- **Общее количество изображений:** ~9,000
- **Разрешение:** Различное (автоматически нормализуется к 224x224)
- **Формат:** JPEG
- **Разделение:** Train (80%) / Val (10%) / Test (10%)

## Список видов рыб

| № | Латинское название | Русское название | Количество изображений |
|---|-------------------|------------------|----------------------|
| 1 | Abramis brama | Лещ | ~800 |
| 2 | Alburnus alburnus | Уклейка | ~700 |
| 3 | Blicca bjoerkna | Густера | ~300 |
| 4 | Carassius gibelio | Карась серебряный | ~600 |
| 5 | Esox lucius | Щука | ~900 |
| 6 | Gobio gobio | Пескарь | ~100 |
| 7 | Gymnocephalus cernua | Ёрш | ~260 |
| 8 | Leuciscus baicalensis | Елец байкальский | ~160 |
| 9 | Leuciscus idus | Язь | ~260 |
| 10 | Perca fluviatilis | Окунь речной | ~650 |
| 11 | Perccottus glenii | Ротан | ~520 |
| 12 | Rutilus lacustris | Плотва | ~540 |
| 13 | Rutilus rutilus | Тарань | ~480 |
| 14 | Sander lucioperca | Судак | ~420 |
| 15 | Scardinius erythrophthalmus | Красноперка | ~580 |

## Скачивание датасета

### Вариант 1: Kaggle API

```bash
# Установите Kaggle CLI
pip install kaggle

# Настройте API token (https://www.kaggle.com/settings)
# Поместите kaggle.json в ~/.kaggle/

# Скачайте датасет
kaggle datasets download -d crowww/a-large-scale-fish-dataset

# Распакуйте
unzip a-large-scale-fish-dataset.zip -d datasets_final/
```

### Вариант 2: Прямая ссылка

Скачайте вручную: https://www.kaggle.com/datasets/crowww/a-large-scale-fish-dataset

## Структура после распаковки

```
datasets_final/
└── processed_images/
    ├── train/
    │   ├── abramis_brama/
    │   │   ├── abramis_brama_0000.jpg
    │   │   ├── abramis_brama_0001.jpg
    │   │   └── ...
    │   ├── alburnus_alburnus/
    │   ├── blicca_bjoerkna/
    │   └── ...
    ├── val/
    │   └── ... (same structure)
    └── test/
        └── ... (same structure)
```

## Подготовка данных для обучения

После скачивания датасет автоматически загружается в Yandex Object Storage:

```bash
# Загрузка в S3
make upload-dataset

# Или вручную
./scripts/upload_dataset.sh
```

## Статистика датасета

```python
# Примерная статистика по размерам изображений
Min size: 512x384
Max size: 4032x3024
Average size: 1024x768

# Распределение по классам (примерно сбалансированное)
Mean images per class: 600
Std deviation: ±200
```

## Лицензия датасета

**License:** [Database: Open Database, Contents: Database Contents]

Датасет предоставлен для исследовательских и образовательных целей.

**Citation:**
```
@dataset{fish_dataset,
  title={A Large Scale Fish Dataset},
  author={Oğuzhan Ulucan et al.},
  year={2020},
  publisher={Kaggle},
  url={https://www.kaggle.com/datasets/crowww/a-large-scale-fish-dataset}
}
```

## Дополнительная информация

- **Источник:** Natural fish images from various sources
- **Качество:** High-quality images with good variety
- **Augmentation:** Применяется автоматически во время обучения
- **Preprocessing:** Resize to 224x224, normalization, random transformations

## Использование в проекте

Датасет используется для:
1. **Обучения модели** (Transfer Learning with EfficientNet-B4)
2. **Валидации** во время обучения
3. **Тестирования** финальной модели
4. **Примеров** в демонстрационном интерфейсе

---

**Примечание:** Датасет не включен в Git репозиторий из-за большого размера (~2GB). Скачайте его отдельно используя инструкции выше.

