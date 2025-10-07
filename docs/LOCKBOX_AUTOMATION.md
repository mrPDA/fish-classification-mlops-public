# 🔐 Автоматизация передачи переменных через Lockbox

**Дата**: 2025-10-05  
**Статус**: ✅ Полностью автоматизировано

---

## 🎯 Что сделано

### 1. Создана конфигурация Lockbox (`terraform/lockbox.tf`)

**Содержит**:
- Создание Lockbox секрета
- 20+ переменных (секретные + обычные)
- Настройка прав доступа для Airflow SA
- Outputs для мониторинга

### 2. Обновлён Airflow (`terraform/airflow.tf`)

**Добавлено**:
```hcl
lockbox_secrets_backend = {
  enabled = true
}
```

### 3. Создан скрипт развёртывания (`scripts/deploy_with_lockbox.sh`)

**Функции**:
- Проверка конфигурации
- Terraform plan с подтверждением
- Автоматическое применение
- Проверка статуса
- Вывод инструкций

---

## 📦 Переменные в Lockbox

### Секретные переменные 🔐
- `S3_ACCESS_KEY` - ключ доступа к S3
- `S3_SECRET_KEY` - секретный ключ S3
- `POSTGRES_AIRFLOW_PASSWORD` - пароль БД Airflow
- `POSTGRES_MLOPS_PASSWORD` - пароль БД MLOps

### Конфигурационные переменные
- `CLOUD_ID` - ID облака
- `FOLDER_ID` - ID папки
- `ZONE` - зона развёртывания
- `NETWORK_ID` - ID сети
- `SUBNET_ID` - ID подсети
- `SECURITY_GROUP_ID` - ID security group
- `S3_BUCKET_NAME` - имя S3 bucket
- `S3_ENDPOINT_URL` - endpoint S3
- `DATAPROC_SERVICE_ACCOUNT_ID` - ID SA для DataProc
- `MLFLOW_TRACKING_URI` - URI MLflow
- `MLFLOW_EXPERIMENT_NAME` - имя эксперимента

### Параметры обучения
- `NUM_CLASSES` - количество классов (17)
- `IMAGE_SIZE` - размер изображения (224)
- `BATCH_SIZE` - размер батча (32)
- `EPOCHS` - количество эпох (20)
- `LEARNING_RATE` - learning rate (0.001)
- `DEFAULT_RETRIES` - количество повторов (2)
- `ENVIRONMENT` - окружение (production)

### Дополнительные
- `YC_SSH_PUBLIC_KEY` - SSH ключ для DataProc
- `DP_SA_JSON` - JSON Service Account для DataProc

**Всего**: 20+ переменных

---

## 🚀 Использование

### Вариант 1: Автоматический скрипт (рекомендуется)

```bash
cd /Users/denispukinov/Documents/OTUS/Finalwork_2
./scripts/deploy_with_lockbox.sh
```

**Скрипт выполнит**:
1. ✅ Проверит наличие `lockbox.tf`
2. ✅ Инициализирует Terraform
3. ✅ Покажет план изменений
4. ⏸️  Запросит подтверждение
5. ✅ Применит изменения
6. ✅ Выведет статус и инструкции

---

### Вариант 2: Вручную через Terraform

```bash
cd terraform

# 1. Инициализация
terraform init -upgrade

# 2. План
terraform plan \
  -target=yandex_lockbox_secret.airflow_variables \
  -target=yandex_lockbox_secret_version.airflow_variables_v1 \
  -target=yandex_lockbox_secret_iam_binding.airflow_access \
  -target=yandex_airflow_cluster.main

# 3. Применение
terraform apply \
  -target=yandex_lockbox_secret.airflow_variables \
  -target=yandex_lockbox_secret_version.airflow_variables_v1 \
  -target=yandex_lockbox_secret_iam_binding.airflow_access \
  -target=yandex_airflow_cluster.main

# 4. Проверка
terraform output lockbox_secret_id
terraform output lockbox_variables_count
```

---

## 📝 Использование в DAG

### Получение переменных

```python
from airflow.models import Variable

# Airflow автоматически получает значения из Lockbox
cloud_id = Variable.get("CLOUD_ID")
folder_id = Variable.get("FOLDER_ID")
s3_bucket = Variable.get("S3_BUCKET_NAME")

# Секретные переменные
s3_access_key = Variable.get("S3_ACCESS_KEY")
s3_secret_key = Variable.get("S3_SECRET_KEY")

# Параметры обучения
num_classes = int(Variable.get("NUM_CLASSES"))
batch_size = int(Variable.get("BATCH_SIZE"))
epochs = int(Variable.get("EPOCHS"))
```

### Пример использования в задаче

```python
from airflow.decorators import task

@task
def validate_environment():
    """Проверка переменных окружения"""
    from airflow.models import Variable
    
    required_vars = [
        "CLOUD_ID",
        "FOLDER_ID",
        "S3_BUCKET_NAME",
        "DATAPROC_SERVICE_ACCOUNT_ID",
        "MLFLOW_TRACKING_URI"
    ]
    
    for var_name in required_vars:
        value = Variable.get(var_name, default_var=None)
        if value is None:
            raise ValueError(f"Variable {var_name} not set!")
        print(f"✅ {var_name}: {value[:20]}...")  # Показываем первые 20 символов
    
    return "All variables validated"
```

---

## 🔍 Проверка Lockbox

### Через Terraform

```bash
cd terraform

# ID секрета
terraform output lockbox_secret_id

# Имя секрета
terraform output lockbox_secret_name

# Количество переменных
terraform output lockbox_variables_count
```

### Через yc CLI

```bash
# Список секретов
yc lockbox secret list

# Информация о секрете
LOCKBOX_ID=$(cd terraform && terraform output -raw lockbox_secret_id)
yc lockbox secret get $LOCKBOX_ID

# Список ключей (без значений)
yc lockbox payload get $LOCKBOX_ID --format json | jq '.entries[].key'
```

### Через Airflow UI

1. Откройте Airflow UI
2. Admin → Variables
3. Все переменные из Lockbox должны быть видны
4. Секретные переменные будут скрыты (****)

---

## 🔄 Обновление переменных

### Добавление новой переменной

1. Отредактируйте `terraform/lockbox.tf`:

```hcl
entries {
  key        = "NEW_VARIABLE"
  text_value = "value"
}
```

2. Примените изменения:

```bash
cd terraform
terraform apply
```

3. Переменная автоматически станет доступна в Airflow

### Изменение значения

1. Измените `text_value` в `lockbox.tf`
2. Выполните `terraform apply`
3. Airflow автоматически получит новое значение

### Удаление переменной

1. Удалите блок `entries` из `lockbox.tf`
2. Выполните `terraform apply`
3. Переменная исчезнет из Airflow

---

## 🔐 Безопасность

### Права доступа

**Настроены автоматически**:
```hcl
resource "yandex_lockbox_secret_iam_binding" "airflow_access" {
  secret_id = yandex_lockbox_secret.airflow_variables.id
  role      = "lockbox.payloadViewer"
  
  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}
```

### Аудит

```bash
# История изменений секрета
yc lockbox secret list-versions $LOCKBOX_ID

# Права доступа
yc lockbox secret list-access-bindings $LOCKBOX_ID
```

### Ротация секретов

```bash
# Создать новую версию секрета
# (автоматически при terraform apply)

# Откатиться на предыдущую версию
yc lockbox secret activate-version $LOCKBOX_ID --version-id <old-version-id>
```

---

## ⚠️ Важные замечания

### 1. Lockbox vs REST API

**Lockbox** (через Terraform):
- ✅ Автоматическая интеграция
- ✅ Безопасное хранение
- ✅ Версионирование
- ✅ Аудит
- ⚠️ Требует пересоздания Airflow при первом включении

**REST API** (через скрипт):
- ✅ Не требует пересоздания Airflow
- ✅ Быстрое обновление
- ⚠️ Менее безопасно для секретов
- ⚠️ Нет версионирования

### 2. Первое включение Lockbox

При первом включении `lockbox_secrets_backend = { enabled = true }` может потребоваться:
- Пересоздание Airflow кластера
- Или обновление конфигурации (зависит от текущего статуса)

### 3. Стоимость

Lockbox - **платный сервис**:
- Хранение секретов
- Запросы к API
- См. [прайс Yandex Cloud](https://yandex.cloud/ru/docs/lockbox/pricing)

### 4. Лимиты

- Максимум 100 ключей в одном секрете
- Максимум 64 KB на значение
- Максимум 1 MB на весь секрет

---

## 🧪 Тестирование

### Проверка доступности переменных

```python
# В Airflow UI → Admin → Variables
# Или через Python в DAG:

from airflow.models import Variable

def test_lockbox_variables():
    """Тест доступности переменных из Lockbox"""
    test_vars = {
        "CLOUD_ID": "b1ge6d4nfcu57u4f46hi",
        "FOLDER_ID": "b1gjj3po03aa3m4j8ps5",
        "S3_BUCKET_NAME": "fish-classification-data-7wb4zv",
    }
    
    for key, expected in test_vars.items():
        actual = Variable.get(key, default_var=None)
        assert actual is not None, f"{key} not found in Lockbox"
        assert actual == expected, f"{key} mismatch: {actual} != {expected}"
        print(f"✅ {key}: OK")
    
    print("✅ All Lockbox variables accessible!")

# Запустить в PythonOperator
```

---

## 📊 Мониторинг

### Terraform outputs

```bash
cd terraform

# Основная информация
terraform output lockbox_secret_id
terraform output lockbox_secret_name
terraform output lockbox_variables_count

# Статус Airflow
terraform output airflow_cluster_id
```

### Логи Airflow

```bash
# Проверка логов scheduler
yc airflow cluster list-hosts <cluster-id>

# Логи в Airflow UI
# Admin → Logs
```

---

## 🔧 Troubleshooting

### Переменные не видны в Airflow

**Проблема**: Variables пустые в Airflow UI

**Решение**:
1. Проверьте статус кластера: `yc airflow cluster get <id>`
2. Убедитесь, что `lockbox_secrets_backend.enabled = true`
3. Проверьте права доступа SA к Lockbox
4. Перезапустите scheduler (через UI или API)

### Ошибка доступа к Lockbox

**Проблема**: `Permission denied` при доступе к секрету

**Решение**:
```bash
# Проверить права
yc lockbox secret list-access-bindings <secret-id>

# Добавить права вручную (если нужно)
yc lockbox secret add-access-binding <secret-id> \
  --role lockbox.payloadViewer \
  --service-account-id <sa-id>
```

### Terraform ошибки

**Проблема**: `Error creating Lockbox secret`

**Решение**:
1. Проверьте квоты Lockbox
2. Убедитесь, что секрет с таким именем не существует
3. Проверьте права Service Account

---

## 📚 Дополнительные ресурсы

- [Yandex Lockbox Documentation](https://yandex.cloud/docs/lockbox/)
- [Airflow Variables](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/variables.html)
- [Terraform Yandex Provider](https://registry.terraform.io/providers/yandex-cloud/yandex/latest/docs)

---

## 🎯 Итоговая рекомендация

**Для production используйте Lockbox**:
1. ✅ Безопасное хранение секретов
2. ✅ Автоматическая интеграция с Airflow
3. ✅ Версионирование и аудит
4. ✅ Управление через Infrastructure as Code

**Запуск**:
```bash
./scripts/deploy_with_lockbox.sh
```

---

**Автор**: AI Assistant  
**Последнее обновление**: 2025-10-05 04:30 UTC
