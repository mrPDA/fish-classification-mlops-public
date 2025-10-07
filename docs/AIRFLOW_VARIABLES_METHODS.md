# 🔧 Способы передачи переменных в Airflow

**Дата**: 2025-10-05

---

## 📋 Все доступные методы

### 1. REST API (автоматизировано в наших скриптах) ✅

**Преимущества**: Полная автоматизация, идеально для CI/CD

**Скрипт**: `scripts/import_airflow_variables.sh`

```bash
curl -X POST "https://<airflow-url>/api/v1/variables" \
  -H "Content-Type: application/json" \
  -u "admin:password" \
  -d '{"key": "VARIABLE_NAME", "value": "value"}'
```

**Пример из нашего скрипта**:
```bash
./scripts/import_airflow_variables.sh
```

---

### 2. Airflow UI (ручной импорт) 🖱️

**Преимущества**: Визуальный контроль, проверка значений

**Шаги**:
1. Откройте Airflow UI
2. Admin → Variables
3. Кнопка "Import Variables"
4. Загрузите JSON файл

**Формат JSON файла**:
```json
{
  "CLOUD_ID": "b1ge6d4nfcu57u4f46hi",
  "FOLDER_ID": "b1gjj3po03aa3m4j8ps5",
  "S3_BUCKET_NAME": "fish-classification-data-7wb4zv"
}
```

**Создание файла**:
```bash
cd terraform
cat > /tmp/airflow_vars.json << EOF
{
  "CLOUD_ID": "$(terraform output -raw cloud_id)",
  "FOLDER_ID": "$(terraform output -raw folder_id)",
  "S3_BUCKET_NAME": "$(terraform output -raw s3_bucket_name)"
}
EOF
```

---

### 3. Airflow CLI (если есть доступ к контейнеру)

**Преимущества**: Прямой доступ, быстро

**Для Managed Airflow** (через SSH к воркеру):
```bash
# Получить доступ к контейнеру
yc airflow cluster list-hosts c9qovnmqug9fv5nfdi8j

# Установить переменную
airflow variables set VARIABLE_NAME "value"

# Импортировать из файла
airflow variables import /path/to/variables.json
```

---

### 4. Environment Variables в Terraform

**Преимущества**: Часть инфраструктуры как кода

**В `airflow.tf`**:
```hcl
resource "yandex_airflow_cluster" "main" {
  # ... другие настройки ...
  
  airflow_config = {
    "core" = {
      "load_examples" = "False"
    }
  }
  
  # Переменные окружения (если поддерживается)
  environment_variables = {
    CLOUD_ID     = var.cloud_id
    FOLDER_ID    = var.folder_id
    S3_BUCKET    = yandex_storage_bucket.data.bucket
  }
}
```

**Примечание**: Не все Managed Services поддерживают прямую передачу env vars.

---

### 5. Через S3 (конфигурационный файл)

**Преимущества**: Централизованное хранение, версионирование

**Шаг 1**: Создать конфигурационный файл
```bash
cat > config.json << EOF
{
  "cloud_id": "b1ge6d4nfcu57u4f46hi",
  "folder_id": "b1gjj3po03aa3m4j8ps5",
  "s3_bucket": "fish-classification-data-7wb4zv"
}
EOF
```

**Шаг 2**: Загрузить в S3
```bash
yc storage s3 cp config.json s3://fish-classification-data-7wb4zv/config/airflow_vars.json
```

**Шаг 3**: Читать в DAG
```python
from airflow.decorators import dag, task
import boto3
import json

@task
def load_config_from_s3():
    s3 = boto3.client('s3', endpoint_url='https://storage.yandexcloud.net')
    obj = s3.get_object(Bucket='fish-classification-data-7wb4zv', Key='config/airflow_vars.json')
    config = json.loads(obj['Body'].read())
    
    # Установить как Airflow Variables
    from airflow.models import Variable
    for key, value in config.items():
        Variable.set(key, value)
```

---

### 6. Через Yandex Lockbox (секреты)

**Преимущества**: Безопасное хранение секретов, интеграция с IAM

**Шаг 1**: Создать секрет в Lockbox
```bash
yc lockbox secret create \
  --name airflow-secrets \
  --payload '[{"key":"S3_ACCESS_KEY","text_value":"YCAJEOWhtBDtvKvP1hI4z2L8p"}]'
```

**Шаг 2**: Настроить в Terraform
```hcl
resource "yandex_airflow_cluster" "main" {
  # ...
  
  lockbox_secrets_backend = {
    enabled = true
  }
}
```

**Шаг 3**: Использовать в DAG
```python
from airflow.models import Variable

# Airflow автоматически получит из Lockbox
s3_key = Variable.get("S3_ACCESS_KEY")
```

---

### 7. Через Connections (для подключений)

**Преимущества**: Специально для подключений к БД, API, S3

**REST API**:
```bash
curl -X POST "https://<airflow-url>/api/v1/connections" \
  -H "Content-Type: application/json" \
  -u "admin:password" \
  -d '{
    "connection_id": "yc_s3",
    "conn_type": "aws",
    "host": "storage.yandexcloud.net",
    "login": "YOUR_S3_ACCESS_KEY",
    "password": "YOUR_S3_SECRET_KEY"
  }'
```

**Через UI**:
1. Admin → Connections
2. Кнопка "+"
3. Заполнить форму

**В DAG**:
```python
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

hook = S3Hook(aws_conn_id='yc_s3')
```

---

### 8. Через init-контейнер (для Kubernetes Airflow)

**Преимущества**: Автоматизация при деплое

**В Helm values**:
```yaml
airflow:
  extraInitContainers:
    - name: import-variables
      image: curlimages/curl:latest
      command:
        - sh
        - -c
        - |
          curl -X POST "http://airflow-webserver:8080/api/v1/variables" \
            -H "Content-Type: application/json" \
            -u "admin:${ADMIN_PASSWORD}" \
            -d '{"key": "CLOUD_ID", "value": "'${CLOUD_ID}'"}'
```

---

## 🎯 Рекомендации для нашего проекта

### Для Production (Managed Airflow):

**Вариант 1: REST API через скрипт** ✅ (уже реализовано)
```bash
./scripts/import_airflow_variables.sh
```

**Вариант 2: UI Import** (для проверки/отладки)
1. Сгенерировать файл: `./scripts/setup_airflow.sh`
2. Импортировать через UI

**Вариант 3: Lockbox для секретов** (рекомендуется для production)
- S3 ключи
- Пароли БД
- API токены

### Для Development:

**Локальный Airflow**:
```bash
# Через CLI
airflow variables set CLOUD_ID "b1ge6d4nfcu57u4f46hi"

# Или импорт файла
airflow variables import variables.json
```

---

## 📝 Создание файла переменных вручную

### Простой способ:
```bash
cd /Users/denispukinov/Documents/OTUS/Finalwork_2

# Запустить setup_airflow.sh (создаст /tmp/airflow_variables.json)
./scripts/setup_airflow.sh

# Скопировать для ручного импорта
cp /tmp/airflow_variables.json ~/airflow_vars_backup.json
```

### Ручное создание:
```bash
cd terraform

cat > ~/airflow_variables.json << EOF
{
  "CLOUD_ID": "$(terraform output -raw cloud_id)",
  "FOLDER_ID": "$(terraform output -raw folder_id)",
  "ZONE": "$(terraform output -raw zone)",
  "NETWORK_ID": "$(terraform output -raw network_id)",
  "SUBNET_ID": "$(terraform output -raw subnet_id)",
  "SECURITY_GROUP_ID": "$(terraform output -raw security_group_id)",
  "S3_BUCKET_NAME": "$(terraform output -raw s3_bucket_name)",
  "S3_ENDPOINT_URL": "https://storage.yandexcloud.net",
  "S3_ACCESS_KEY": "$(terraform output -raw s3_access_key)",
  "S3_SECRET_KEY": "$(terraform output -raw s3_secret_key)",
  "DATAPROC_SERVICE_ACCOUNT_ID": "$(terraform output -raw dataproc_sa_id)",
  "MLFLOW_TRACKING_URI": "http://$(terraform output -raw mlflow_vm_ip):5000",
  "MLFLOW_EXPERIMENT_NAME": "fish-classification",
  "NUM_CLASSES": "17",
  "IMAGE_SIZE": "224",
  "BATCH_SIZE": "32",
  "EPOCHS": "20",
  "LEARNING_RATE": "0.001",
  "DEFAULT_RETRIES": "2",
  "ENVIRONMENT": "production"
}
EOF

echo "✅ Файл создан: ~/airflow_variables.json"
```

---

## 🔐 Безопасность

### Секретные переменные:

**Через Airflow UI** (помечаются как sensitive):
- Пароли
- API ключи
- Токены

**Через REST API** (с флагом):
```bash
curl -X POST "https://<airflow-url>/api/v1/variables" \
  -H "Content-Type: application/json" \
  -u "admin:password" \
  -d '{
    "key": "S3_SECRET_KEY",
    "value": "secret_value",
    "is_encrypted": true
  }'
```

**Через Lockbox** (рекомендуется):
- Централизованное управление
- Аудит доступа
- Ротация секретов

---

## 🧪 Проверка переменных

### Через REST API:
```bash
AIRFLOW_URL="https://your-airflow-url"
ADMIN_PASSWORD="your-password"

# Список всех переменных
curl -X GET "${AIRFLOW_URL}/api/v1/variables" \
  -u "admin:${ADMIN_PASSWORD}" | jq .

# Конкретная переменная
curl -X GET "${AIRFLOW_URL}/api/v1/variables/CLOUD_ID" \
  -u "admin:${ADMIN_PASSWORD}" | jq .
```

### Через UI:
1. Admin → Variables
2. Поиск по имени
3. Просмотр значения (если не секретное)

### В DAG:
```python
from airflow.models import Variable

# Получить переменную
cloud_id = Variable.get("CLOUD_ID")

# С значением по умолчанию
bucket = Variable.get("S3_BUCKET_NAME", default_var="default-bucket")

# Проверка существования
if Variable.get("CLOUD_ID", default_var=None) is None:
    raise ValueError("CLOUD_ID not set!")
```

---

## 📊 Сравнение методов

| Метод | Автоматизация | Безопасность | Сложность | Рекомендуется |
|-------|---------------|--------------|-----------|---------------|
| REST API | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ✅ Production |
| UI Import | ⭐⭐ | ⭐⭐⭐ | ⭐ | ✅ Dev/Debug |
| CLI | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ Если есть доступ |
| Terraform | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ Не все поддерживают |
| S3 Config | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ✅ Для конфигов |
| Lockbox | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ Для секретов |
| Connections | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ✅ Для подключений |

---

## 🎯 Итоговая рекомендация

**Для нашего проекта используем комбинацию**:

1. **REST API** (основной метод) - через `import_airflow_variables.sh`
2. **UI Import** (резервный) - для проверки и отладки
3. **Lockbox** (для секретов) - в будущем для production

**Запуск**:
```bash
# Автоматический (рекомендуется)
./scripts/auto_deploy_and_train.sh

# Или поэтапно
./scripts/import_airflow_variables.sh
```

---

**Автор**: AI Assistant  
**Последнее обновление**: 2025-10-05 04:00 UTC
