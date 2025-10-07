# 🐟 Fish Classification MLOps System

**Production-Ready ML System for Automatic Fish Species Classification**

[![Terraform](https://img.shields.io/badge/Terraform-1.5+-7B42BC?logo=terraform)](https://www.terraform.io/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.30+-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![Airflow](https://img.shields.io/badge/Airflow-2.10+-017CEE?logo=apache-airflow)](https://airflow.apache.org/)
[![MLflow](https://img.shields.io/badge/MLflow-2.9+-0194E2?logo=mlflow)](https://mlflow.org/)
[![Yandex Cloud](https://img.shields.io/badge/Yandex_Cloud-Managed_Services-1A90FF)](https://cloud.yandex.com/)

## 📋 Содержание

- [О проекте](#о-проекте)
- [Архитектура](#архитектура)
- [Технологии](#технологии)
- [Быстрый старт](#быстрый-старт)
- [Компоненты системы](#компоненты-системы)
- [Развертывание](#развертывание)
- [Мониторинг](#мониторинг)
- [Датасет](#датасет)
- [Примеры использования](#примеры-использования)
- [Документация](#документация)
- [Автор](#автор)

## 🎯 О проекте

Полнофункциональная MLOps система для автоматической классификации видов рыб по фотографиям. Проект реализует полный цикл машинного обучения: от автоматического обучения моделей до production-ready инференса с мониторингом.

### Основные возможности

- ✅ **Автоматическое обучение** на распределенном кластере (Yandex DataProc + Spark)
- ✅ **Transfer Learning** с использованием EfficientNet-B4
- ✅ **Автоматическая регистрация моделей** в MLflow Model Registry
- ✅ **Production-ready инференс** с горизонтальным масштабированием (Kubernetes HPA)
- ✅ **CI/CD для ML** с помощью Apache Airflow
- ✅ **Мониторинг и наблюдаемость** (Grafana + Prometheus)
- ✅ **Infrastructure as Code** (Terraform)

## 🏗 Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                     TRAINING PIPELINE                            │
│                                                                  │
│  Airflow DAG → DataProc Cluster → Spark Training → MLflow       │
│                     ↓                      ↓                     │
│              Auto Scaling           Model Registry               │
│              (on demand)            (Production)                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   INFERENCE PIPELINE                             │
│                                                                  │
│  User → Frontend → API Gateway → FastAPI → MLflow Model         │
│                            ↓                    ↓                │
│                        Redis Cache          S3 Storage           │
│                            ↓                                     │
│                    K8s HPA (auto-scaling)                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      MONITORING                                  │
│                                                                  │
│         Grafana ← Prometheus ← K8s Metrics & App Logs           │
└─────────────────────────────────────────────────────────────────┘
```

### Компоненты

**Training**
- **Yandex Managed Airflow** - оркестрация пайплайнов обучения
- **Yandex DataProc (Spark)** - распределенное обучение моделей
- **MLflow** - tracking экспериментов и Model Registry

**Inference**
- **Kubernetes (Managed K8s)** - контейнерная оркестрация
- **FastAPI** - REST API для инференса
- **Redis** - кеширование результатов
- **Nginx** - reverse proxy и load balancing

**Storage & Data**
- **Yandex Object Storage (S3)** - хранение данных, моделей, логов
- **PostgreSQL (Managed)** - метаданные Airflow и MLflow

**Monitoring**
- **Grafana** - визуализация метрик и дашборды
- **Prometheus** - сбор и хранение метрик

## 🛠 Технологии

### ML/DL Framework
- **TensorFlow 2.13** - обучение нейронных сетей
- **Transfer Learning** - EfficientNet-B4 (ImageNet weights)
- **Apache Spark** - распределенная обработка данных

### MLOps & Orchestration
- **Apache Airflow 2.10** - workflow orchestration
- **MLflow 2.9** - experiment tracking, model registry
- **DVC** (опционально) - версионирование данных

### Infrastructure
- **Terraform 1.5+** - IaC для облачной инфраструктуры
- **Kubernetes 1.30** - контейнерная оркестрация
- **Docker** - контейнеризация приложений
- **Yandex Cloud** - облачный провайдер

### Backend & API
- **FastAPI** - REST API для инференса
- **Redis** - кеширование
- **PostgreSQL** - реляционная БД
- **Nginx** - веб-сервер и reverse proxy

### Monitoring & Logging
- **Grafana** - визуализация
- **Prometheus** - метрики
- **CloudWatch/Yandex Monitoring** - облачные логи

## 🚀 Быстрый старт

### Предварительные требования

```bash
# Установите инструменты
terraform >= 1.5
kubectl >= 1.30
yc (Yandex Cloud CLI)
make

# Настройте аутентификацию Yandex Cloud
yc init
```

### Шаг 1: Настройка переменных

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Отредактируйте terraform.tfvars с вашими значениями
```

<details>
<summary>Пример terraform.tfvars</summary>

```hcl
# Yandex Cloud
cloud_id     = "your-cloud-id"
folder_id    = "your-folder-id"
zone         = "ru-central1-a"

# Network
services_subnet_cidr = "10.11.0.0/24"
k8s_subnet_cidr      = "10.12.0.0/16"

# SSH
ssh_public_key_path = "~/.ssh/id_rsa.pub"

# Пароли (генерируйте безопасные!)
postgres_airflow_password = "CHANGE_ME"
grafana_admin_password    = "CHANGE_ME"
airflow_admin_password    = "CHANGE_ME"
```
</details>

### Шаг 2: Развертывание инфраструктуры

```bash
# Полное автоматическое развертывание
make deploy-all
```

Эта команда:
1. ✅ Создаст всю облачную инфраструктуру (Terraform)
2. ✅ Развернет Kubernetes кластер
3. ✅ Настроит Airflow, MLflow, Grafana
4. ✅ Загрузит датасет в S3
5. ✅ Развернет inference API и фронтенд

### Шаг 3: Доступ к сервисам

После развертывания получите URLs:

```bash
make print-urls
```

Вывод:
```
🐟 Frontend:    http://<node-ip>:<port>
📊 Grafana:     http://<grafana-ip>:3000
🤖 MLflow:      http://<mlflow-ip>:5000
🌬️  Airflow:    https://<cluster-id>.airflow.yandexcloud.net
```

### Шаг 4: Запуск обучения модели

1. Откройте Airflow UI
2. Найдите DAG `fish_classification_training_full`
3. Нажмите "Trigger DAG"

Автоматически:
- Создастся DataProc кластер
- Обучится модель с Transfer Learning
- Модель зарегистрируется в MLflow Production
- Кластер удалится
- API автоматически подхватит новую модель

## 📦 Компоненты системы

### 1. Training Pipeline

**Airflow DAG:** `fish_classification_training_full.py`
- Валидация окружения и параметров
- Создание DataProc кластера (auto-scaling)
- Запуск Spark job для обучения
- Валидация результатов в MLflow
- Автоматическая регистрация модели в Production
- Генерация отчета об обучении
- Автоматическое удаление кластера

**PySpark Training:** `spark_jobs/train_fish_model_minimal.py`
- Transfer Learning (EfficientNet-B4)
- Автоматическая установка зависимостей (NumPy, TensorFlow, MLflow)
- Обработка данных из S3
- Логирование метрик в MLflow
- Сохранение модели в Model Registry

### 2. Inference API

**FastAPI Application:** `api/main.py`
- Загрузка модели из MLflow Production stage
- REST endpoints: `/predict`, `/health`, `/ready`
- Redis кеширование результатов
- Автомасштабирование (HPA)

### 3. Frontend

**Web Interface:** `frontend/index.html`
- Загрузка изображений рыб
- Отображение результатов классификации
- Responsive design (Bootstrap 5)

### 4. Monitoring

**Grafana Dashboards:**
- Training metrics (accuracy, loss)
- API performance (latency, throughput)
- Infrastructure metrics (CPU, memory, disk)
- Model drift detection

## 🔧 Развертывание

### Makefile команды

```bash
make init              # Инициализация Terraform
make terraform-apply   # Создание инфраструктуры
make deploy-k8s        # Развертывание K8s компонентов
make deploy-inference  # Развертывание API и Frontend
make setup-airflow     # Настройка Airflow (загрузка DAGs)
make deploy-all        # Полное развертывание (все шаги)
make destroy           # Удаление всей инфраструктуры
make status            # Проверка статуса всех компонентов
```

### Ручное развертывание

<details>
<summary>Развернуть вручную</summary>

```bash
# 1. Terraform
cd terraform
terraform init
terraform plan
terraform apply

# 2. Kubernetes
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/redis/
kubectl apply -f k8s/inference-api/
kubectl apply -f k8s/frontend/

# 3. Загрузка датасета
./scripts/upload_dataset.sh

# 4. Настройка Airflow
./scripts/setup_airflow.sh
```
</details>

## 📊 Мониторинг

### Grafana Dashboards

1. **ML Training Dashboard**
   - Метрики обучения (accuracy, loss)
   - Время обучения
   - Использование ресурсов DataProc

2. **Inference API Dashboard**
   - Request rate
   - Response time (p50, p95, p99)
   - Error rate
   - Cache hit rate

3. **Infrastructure Dashboard**
   - K8s nodes status
   - Pod resources
   - Network traffic

### Доступ к метрикам

```bash
# Метрики API
curl http://<api-url>/metrics

# Prometheus
http://<prometheus-ip>:9090

# Grafana
http://<grafana-ip>:3000
```

## 📚 Датасет

### Источник данных

Датасет: **Fish Species Image Data** (15 видов рыб, ~9000 изображений)

Источник: [Fish Dataset on Kaggle](https://www.kaggle.com/datasets/crowww/a-large-scale-fish-dataset)

### Структура

```
datasets_final/
├── processed_images/
│   ├── train/          # 80% данных
│   │   ├── abramis_brama/
│   │   ├── alburnus_alburnus/
│   │   └── ...
│   ├── val/            # 10% данных
│   └── test/           # 10% данных
└── README.md
```

### Классы рыб

15 видов пресноводных рыб:
- Лещ (Abramis brama)
- Уклейка (Alburnus alburnus)
- Густера (Blicca bjoerkna)
- Карась серебряный (Carassius gibelio)
- Щука (Esox lucius)
- Пескарь (Gobio gobio)
- Ёрш (Gymnocephalus cernua)
- И другие...

### Подготовка данных

```bash
# Скачайте датасет
kaggle datasets download -d crowww/a-large-scale-fish-dataset

# Распакуйте
unzip a-large-scale-fish-dataset.zip -d datasets_final/

# Загрузите в S3
make upload-dataset
```

## 💡 Примеры использования

### Python Client

```python
import requests
from PIL import Image
import io

# Загрузка изображения
with open('fish.jpg', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://<api-url>/predict',
        files=files
    )

result = response.json()
print(f"Predicted: {result['predicted_class']}")
print(f"Confidence: {result['confidence']:.2%}")
```

### cURL

```bash
curl -X POST \
  -F "file=@fish.jpg" \
  http://<api-url>/predict
```

### Response Example

```json
{
  "predicted_class": "esox_lucius",
  "predicted_label": "Щука (Esox lucius)",
  "confidence": 0.9847,
  "top_3_predictions": [
    {
      "class": "esox_lucius",
      "label": "Щука",
      "probability": 0.9847
    },
    {
      "class": "sander_lucioperca",
      "label": "Судак",
      "probability": 0.0123
    },
    {
      "class": "perca_fluviatilis",
      "label": "Окунь",
      "probability": 0.0018
    }
  ],
  "processing_time_ms": 45.2,
  "model_version": "1",
  "cached": false
}
```

## 📖 Документация

Подробная документация находится в папке `docs/`:

- [TRAINING.md](docs/TRAINING.md) - Обучение моделей
- [DEPLOYMENT_AUTO.md](docs/DEPLOYMENT_AUTO.md) - Автоматическое развертывание
- [MODEL_REGISTRY_AUTOMATION.md](docs/MODEL_REGISTRY_AUTOMATION.md) - MLflow Registry
- [K8S_AUTOSCALING.md](docs/K8S_AUTOSCALING.md) - Автомасштабирование
- [DATAPROC_TROUBLESHOOTING.md](docs/DATAPROC_TROUBLESHOOTING.md) - Troubleshooting

## 🎓 Образовательный проект

Этот проект создан в рамках курса **MLOps** (OTUS) и демонстрирует:

✅ Production-ready архитектуру ML системы  
✅ Автоматизацию полного ML цикла  
✅ Infrastructure as Code подход  
✅ Best practices DevOps и MLOps  
✅ Работу с облачными сервисами  

## 🤝 Вклад

Проект открыт для образовательных целей. Вы можете:
- Форкнуть и экспериментировать
- Открывать issues с вопросами
- Предлагать улучшения через pull requests

## 📝 Лицензия

MIT License - см. [LICENSE](LICENSE)

## 👤 Автор

**Денис Пукинов**

- 📧 Email: [ваш email]
- 💼 LinkedIn: [ваш профиль]
- 🐙 GitHub: [@denispukinov](https://github.com/denispukinov)

---

⭐️ Если проект был полезен, поставьте звезду!

## 🙏 Благодарности

- **OTUS** - за отличный курс по MLOps
- **Yandex Cloud** - за облачную инфраструктуру
- **Fish Dataset Contributors** - за предоставленный датасет
- **Open Source Community** - за замечательные инструменты

---

**Сделано с ❤️ для ML сообщества**
