# 🚀 Автоматическое развёртывание Fish Classification System

## Обзор

Полностью автоматизированное развёртывание MLOps системы для классификации рыб с помощью единственной команды:

```bash
make deploy-all
```

## Что разворачивается автоматически

### 1. Инфраструктура (Terraform)

```
✅ Yandex Cloud VPC, подсети, security groups
✅ Managed Kubernetes кластер
✅ Managed PostgreSQL (для MLflow)
✅ Managed Kafka
✅ Managed Airflow
✅ Compute Instances:
   • MLflow Tracking Server
   • Grafana
✅ S3 bucket для данных
✅ Container Registry
✅ IAM roles и service accounts
✅ Lockbox secrets для Airflow
```

### 2. Kubernetes компоненты

```
✅ Namespaces (ml-inference)
✅ Redis (кеширование)
✅ Fish Classification API (FastAPI + MLflow)
✅ Frontend (Nginx + JavaScript)
```

### 3. Настройка Airflow

```
✅ Загрузка DAG в S3
✅ Загрузка Spark скрипта в S3
✅ Настройка переменных
✅ Генерация SSH ключей
```

### 4. Данные

```
✅ Копирование датасета из источника
✅ Загрузка в S3 bucket
```

## Команды Makefile

### Основные команды

```bash
# Полное развёртывание (всё в один клик)
make deploy-all

# Удаление всей инфраструктуры
make destroy

# Статус всех компонентов
make status

# URL всех сервисов
make print-urls

# Справка
make help
```

### Пошаговое развёртывание

```bash
# 1. Проверка инструментов
make check-tools

# 2. Генерация SSH ключей
make generate-ssh-key

# 3. Создание инфраструктуры
make terraform-apply

# 4. Развёртывание Kubernetes
make deploy-k8s

# 5. Копирование датасета
make copy-dataset

# 6. Загрузка датасета в S3
make upload-dataset

# 7. Настройка Airflow
make setup-airflow

# 8. Ожидание готовности Airflow
make wait-for-airflow

# 9. Развёртывание API и Frontend
make deploy-inference
```

### Частичное обновление

```bash
# Переразвернуть только inference (API + Frontend)
make deploy-inference

# Переразвернуть только Kubernetes компоненты
make deploy-k8s

# Обновить конфигурацию Airflow
make setup-airflow

# Загрузить новые данные
make copy-dataset
make upload-dataset
```

## Архитектура развёртывания

### Этап 1: Инфраструктура

```
terraform/
├── main.tf              # VPC, подсети, security groups
├── kubernetes.tf        # Managed K8s кластер
├── postgres.tf          # Managed PostgreSQL
├── kafka.tf            # Managed Kafka
├── airflow.tf          # Managed Airflow
├── vms.tf              # MLflow, Grafana VMs
├── container_registry.tf # Yandex Container Registry
└── lockbox.tf          # Secrets для Airflow
```

### Этап 2: Kubernetes

```
k8s/
├── namespace.yaml       # ml-inference namespace
├── redis/              # Redis кеш
│   ├── deployment.yaml
│   └── service.yaml
└── (API и Frontend разворачиваются через ConfigMaps)
```

### Этап 3: Inference Stack

**API (FastAPI + MLflow):**
- Разворачивается через ConfigMap с Python кодом
- Init container устанавливает зависимости
- Загружает модель из MLflow Production stage
- Интеграция с Redis для кеширования

**Frontend (Nginx + JavaScript):**
- Разворачивается через ConfigMaps (HTML, JS, nginx.conf)
- NodePort service на порту 31649
- Проксирует запросы к API

### Этап 4: Airflow

- DAG загружается в S3
- Переменные настраиваются через Lockbox
- SSH ключи генерируются и загружаются
- Spark скрипт обучения в S3

## Детали реализации

### deploy-all target

```makefile
deploy-all: check-tools \
            generate-ssh-key \
            terraform-apply \
            deploy-k8s \
            copy-dataset \
            upload-dataset \
            setup-airflow \
            wait-for-airflow \
            deploy-inference
```

### Ключевые скрипты

#### 1. `scripts/deploy_real_api.sh`

Разворачивает реальный API с MLflow интеграцией:

```bash
#!/bin/bash
# 1. Получает MLflow IP из Terraform
# 2. Создаёт ConfigMap с Python кодом API
# 3. Разворачивает Deployment с init container
# 4. Создаёт Services (ClusterIP)
```

**Особенности:**
- Init container устанавливает все Python зависимости
- ConfigMap содержит полный код API
- Автоматически загружает модель из Production

#### 2. `scripts/deploy_frontend_simple.sh`

Разворачивает frontend:

```bash
#!/bin/bash
# 1. Создаёт ConfigMaps (HTML, JS, nginx.conf)
# 2. Разворачивает Nginx Deployment
# 3. Создаёт NodePort Service (31649)
```

#### 3. `scripts/setup_airflow.sh`

Настраивает Airflow:

```bash
#!/bin/bash
# 1. Загружает DAG в S3
# 2. Загружает Spark скрипт в S3
# 3. Извлекает переменные из Terraform
# 4. Создаёт Lockbox secrets
# 5. Загружает SSH ключ
```

### API интеграция с MLflow

**Загрузка модели из Production:**

```python
def load_model():
    """Load latest production model from MLflow Model Registry"""
    global model, model_version
    try:
        model_uri = f"models:/{MODEL_NAME}/Production"
        model = mlflow.pyfunc.load_model(model_uri)
        
        # Get version info
        client = MlflowClient()
        prod_models = client.get_latest_versions(MODEL_NAME, stages=["Production"])
        if prod_models:
            model_version = prod_models[0].version
        
        return True
    except Exception as e:
        print(f"Error loading model: {e}")
        return False
```

**Автоматическая перезагрузка:**
- API загружает модель при старте
- При изменении модели в Production: `kubectl rollout restart deployment/fish-api -n ml-inference`

## Workflow использования

### Первое развёртывание

```bash
# 1. Клонируйте репозиторий
git clone <repo-url>
cd Finalwork_2

# 2. Настройте terraform.tfvars
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Заполните: folder_id, cloud_id, token, etc.

# 3. Убедитесь что датасет доступен
# datasets_final/ должна быть в ../Finalwork/

# 4. Запустите развёртывание
make deploy-all

# Дождитесь завершения (~15-20 минут)
```

### Получение URL сервисов

```bash
make print-urls
```

Выведет:
```
🔗 URL сервисов:

🐟 Frontend (для пользователей):
   http://<node-ip>:31649

📊 MLflow:
   http://<mlflow-ip>:5000

📈 Grafana:
   http://<grafana-ip>:3000
   Логин: admin / admin

🌬️  Airflow:
   <airflow-url>
   Логин: admin / <password>
```

### Обучение первой модели

```bash
# 1. Откройте Airflow UI
open $(cd terraform && terraform output -raw airflow_webserver_url)

# 2. Найдите DAG: fish_classification_training_full

# 3. Запустите DAG (кнопка ▶️)

# 4. Дождитесь завершения (~20-25 минут)

# 5. Модель автоматически перейдёт в Production!
```

### Использование системы

```bash
# 1. Откройте Frontend
open http://<node-ip>:31649

# 2. Загрузите фото рыбы

# 3. Получите предсказание!
```

## Мониторинг и проверка

### Проверка статуса

```bash
# Общий статус
make status

# Kubernetes pods
kubectl get pods -n ml-inference

# Логи API
kubectl logs -f -n ml-inference -l app=fish-api

# Логи Frontend
kubectl logs -f -n ml-inference -l app=frontend

# Terraform outputs
cd terraform && terraform output
```

### Проверка API

```bash
# Health check
curl http://<node-ip>:31649/api/health

# Metrics
curl http://<node-ip>:31649/api/metrics

# Проверка загрузки модели
kubectl logs -n ml-inference -l app=fish-api | grep "Model loaded"
```

### Проверка MLflow

```bash
# Открыть MLflow UI
open http://<mlflow-ip>:5000

# Проверить зарегистрированные модели
curl http://<mlflow-ip>:5000/api/2.0/mlflow/registered-models/list

# Проверить Production модели
curl http://<mlflow-ip>:5000/api/2.0/mlflow/registered-models/get?name=fish-classifier-efficientnet-b4
```

## Обновление и переразвёртывание

### Обновление API

```bash
# 1. Отредактируйте код в api/main.py (если нужно)

# 2. Переразверните
make deploy-inference

# 3. Проверьте
kubectl get pods -n ml-inference -l app=fish-api
```

### Обновление Frontend

```bash
# 1. Отредактируйте frontend/index.html или frontend/app.js

# 2. Переразверните
./scripts/deploy_frontend_simple.sh

# 3. Проверьте
open http://<node-ip>:31649
```

### Обновление DAG

```bash
# 1. Отредактируйте dags/fish_classification_training_full.py

# 2. Загрузите в S3
yc storage s3api put-object \
  --bucket <bucket-name> \
  --key dags/fish_classification_training_full.py \
  --body dags/fish_classification_training_full.py

# 3. Дождитесь синхронизации Airflow (1-2 минуты)

# 4. Обновите страницу Airflow UI
```

### Переобучение модели

```bash
# Просто запустите DAG в Airflow UI
# Модель автоматически перейдёт в Production после обучения

# Для применения новой модели в API:
kubectl rollout restart deployment/fish-api -n ml-inference
```

## Удаление и очистка

### Полное удаление

```bash
# Удалить всю инфраструктуру
make destroy

# Это удалит:
# - Все Kubernetes ресурсы
# - Весь Terraform state
# - Все managed services
# - VMs, networks, etc.
```

### Частичное удаление

```bash
# Удалить только inference stack
kubectl delete deployment fish-api -n ml-inference
kubectl delete deployment frontend -n ml-inference
kubectl delete svc fish-api inference-api frontend -n ml-inference

# Удалить только Kubernetes компоненты
kubectl delete namespace ml-inference

# Удалить только инфраструктуру (оставить K8s)
cd terraform && terraform destroy -target=yandex_compute_instance.mlflow
```

## Troubleshooting

### API не загружает модель

**Проблема:** API пишет "Model not loaded"

**Решение:**
1. Проверьте что модель зарегистрирована в MLflow:
   ```bash
   curl http://<mlflow-ip>:5000/api/2.0/mlflow/registered-models/get?name=fish-classifier-efficientnet-b4
   ```

2. Проверьте что модель в Production:
   ```bash
   # Должен вернуть версию с "current_stage": "Production"
   ```

3. Проверьте логи API:
   ```bash
   kubectl logs -n ml-inference -l app=fish-api | grep -i error
   ```

4. Проверьте доступность MLflow из K8s:
   ```bash
   kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
     curl http://<mlflow-ip>:5000/health
   ```

### Frontend не загружается

**Проблема:** 404 или пустая страница

**Решение:**
1. Проверьте что ConfigMaps созданы:
   ```bash
   kubectl get configmap -n ml-inference | grep frontend
   ```

2. Проверьте логи Nginx:
   ```bash
   kubectl logs -n ml-inference -l app=frontend
   ```

3. Проверьте NodePort service:
   ```bash
   kubectl get svc frontend -n ml-inference
   ```

### Airflow не готов

**Проблема:** wait-for-airflow timeout

**Решение:**
1. Managed Airflow может требовать больше времени (до 10 минут)
2. Проверьте статус в Yandex Cloud Console
3. Продолжите вручную: `make deploy-inference`

### Terraform state lock

**Проблема:** State file locked

**Решение:**
```bash
cd terraform
terraform force-unlock <LOCK_ID>
```

### Недостаточно квоты

**Проблема:** Quota exceeded

**Решение:**
1. Проверьте текущие квоты:
   ```bash
   yc quota list --folder-id <folder-id>
   ```

2. Запросите увеличение через Yandex Cloud Console или поддержку

3. Измените размеры ресурсов в `terraform/variables.tf`

## Best Practices

### 1. Версионирование

- Храните `terraform.tfvars` в `.gitignore`
- Коммитьте изменения в `*.tf` файлы
- Используйте git tags для релизов

### 2. Безопасность

- Используйте Lockbox для секретов
- Не храните credentials в коде
- Ограничьте security groups только необходимыми портами

### 3. Мониторинг

- Регулярно проверяйте `make status`
- Настройте alerts в Grafana
- Логируйте все изменения в Production моделях

### 4. CI/CD

- Автоматизируйте обучение через Airflow schedules
- Настройте автоматические тесты моделей
- Используйте A/B testing для новых моделей

## Заключение

Система полностью автоматизирована:

✅ Одна команда разворачивает всё
✅ Автоматическая регистрация моделей в Production
✅ Автоматическое масштабирование в Kubernetes
✅ Полная интеграция всех компонентов

**Просто запустите:**
```bash
make deploy-all
```

**И всё готово! 🎉**

