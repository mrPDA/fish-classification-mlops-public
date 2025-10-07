# DataProc REST API Solution

## 🎯 Проблема

После многочисленных попыток интеграции DataProc с Yandex Managed Airflow мы столкнулись с:

1. **DataProc операторы НЕ СУЩЕСТВУЮТ** в `apache-airflow-providers-yandex`
   - `DataprocCreateClusterOperator` - не существует
   - `DataprocDeleteClusterOperator` - не существует
   - Документация Yandex Cloud устарела или относится к другой версии

2. **yc CLI НЕ установлен** в Managed Airflow
   - Попытки использовать `BashOperator` + `yc` провалились
   - CLI недоступен в окружении Airflow workers

3. **Yandex Cloud Python SDK вызывает зависание**
   - Добавление `yandexcloud` в `pip_packages` приводит к зависанию `terraform apply`
   - Кластер Airflow не создаётся

## ✅ Решение: REST API + PyJWT

Мы используем **прямые HTTP запросы** к Yandex Cloud REST API:

### Архитектура решения

```
┌─────────────────────────────────────────────────────────────┐
│                    Airflow DAG                              │
│                                                             │
│  1. validate_environment()                                  │
│     ├─ Проверка модулей: requests, jwt                     │
│     └─ Проверка DP_SA_JSON в Lockbox                       │
│                                                             │
│  2. create_dataproc_cluster()                               │
│     ├─ Получение IAM токена (PyJWT)                        │
│     ├─ POST /dataproc/v1/clusters                          │
│     └─ Ожидание операции создания                          │
│                                                             │
│  3. wait_cluster_ready()                                    │
│     ├─ GET /dataproc/v1/clusters/{id}                      │
│     └─ Проверка status=RUNNING, health=ALIVE               │
│                                                             │
│  4. run_training_job()                                      │
│     ├─ POST /dataproc/v1/clusters/{id}/jobs                │
│     └─ Запуск PySpark job через Livy API                   │
│                                                             │
│  5. delete_dataproc_cluster()                               │
│     ├─ DELETE /dataproc/v1/clusters/{id}                   │
│     └─ Ожидание операции удаления                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Ключевые компоненты

#### 1. Получение IAM токена

```python
import jwt
import requests

def get_iam_token(sa_key_json: str) -> str:
    sa_key = json.loads(sa_key_json)
    
    # Создаём JWT
    payload = {
        'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
        'iss': sa_key['service_account_id'],
        'iat': int(time.time()),
        'exp': int(time.time()) + 3600
    }
    
    encoded_token = jwt.encode(
        payload,
        sa_key['private_key'],
        algorithm='PS256',
        headers={'kid': sa_key['id']}
    )
    
    # Обмениваем JWT на IAM токен
    response = requests.post(
        'https://iam.api.cloud.yandex.net/iam/v1/tokens',
        json={'jwt': encoded_token}
    )
    
    return response.json()['iamToken']
```

#### 2. Создание кластера

```python
def create_dataproc_cluster(**context):
    # Получаем IAM токен
    iam_token = get_iam_token(dp_sa_json)
    
    # Конфигурация кластера
    cluster_config = {
        "folderId": folder_id,
        "name": cluster_name,
        "configSpec": {
            "versionId": "2.1",
            "hadoop": {
                "services": ["HDFS", "YARN", "SPARK", "LIVY"],
                "sshPublicKeys": [ssh_public_key]
            },
            "subclustersSpec": [
                {"name": "masternode", "role": "MASTERNODE", ...},
                {"name": "datanode", "role": "DATANODE", ...}
            ]
        },
        ...
    }
    
    # Отправляем запрос
    response = requests.post(
        "https://dataproc.api.cloud.yandex.net/dataproc/v1/clusters",
        headers={"Authorization": f"Bearer {iam_token}"},
        json=cluster_config
    )
    
    # Ожидаем завершения операции
    operation_id = response.json()['id']
    cluster_id = wait_operation(operation_id, iam_token)
    
    return cluster_id
```

#### 3. Проверка статуса

```python
def wait_cluster_ready(**context):
    cluster_id = context['task_instance'].xcom_pull(...)
    iam_token = context['task_instance'].xcom_pull(...)
    
    while True:
        response = requests.get(
            f"https://dataproc.api.cloud.yandex.net/dataproc/v1/clusters/{cluster_id}",
            headers={"Authorization": f"Bearer {iam_token}"}
        )
        
        cluster = response.json()
        if cluster['status'] == 'RUNNING' and cluster['health'] == 'ALIVE':
            return True
        
        time.sleep(30)
```

## 📦 Требования

### Terraform (airflow.tf)

```hcl
pip_packages = [
  "apache-airflow-providers-yandex",
  "apache-airflow-providers-amazon",
  "boto3",
  "psycopg2-binary",
  "PyJWT",  # ← ВАЖНО!
]
```

### Lockbox Variables

Необходимые переменные в Lockbox:
- `DP_SA_JSON` - JSON ключ сервисного аккаунта для DataProc
- `FOLDER_ID` - ID каталога
- `ZONE` - Зона (ru-central1-a)
- `SUBNET_ID` - ID подсети
- `SECURITY_GROUP_ID` - ID группы безопасности
- `DATAPROC_SERVICE_ACCOUNT_ID` - ID сервисного аккаунта для DataProc
- `S3_BUCKET_NAME` - Имя S3 бакета
- `YC_SSH_PUBLIC_KEY` - Публичный SSH ключ

## 🚀 Использование

### 1. Пересоздать Airflow кластер с PyJWT

```bash
cd terraform
terraform apply -target=yandex_airflow_cluster.main
```

### 2. Загрузить новый DAG

```bash
yc storage s3api put-object \
  --bucket fish-classification-data-7wb4zv \
  --key airflow-dags/fish_classification_training_rest_api.py \
  --body ../dags/fish_classification_training_rest_api.py
```

### 3. Запустить DAG в Airflow UI

1. Откройте Airflow UI
2. Найдите DAG `fish_classification_training_rest_api`
3. Trigger DAG
4. Наблюдайте за выполнением:
   - `validate_environment` - проверка окружения
   - `create_dataproc_cluster` - создание кластера (~10 мин)
   - `wait_cluster_ready` - ожидание готовности (~15 мин)
   - `run_training_job` - обучение модели (TODO)
   - `delete_dataproc_cluster` - удаление кластера (~5 мин)

## 📊 Преимущества решения

✅ **Надёжность**: Используем официальный REST API
✅ **Простота**: Не требует дополнительных зависимостей (кроме PyJWT)
✅ **Гибкость**: Полный контроль над конфигурацией кластера
✅ **Отладка**: Легко логировать и отслеживать запросы
✅ **Переносимость**: Работает в любом окружении с Python + requests

## ⚠️ Недостатки

⚠️ **Больше кода**: Нужно вручную реализовывать логику операторов
⚠️ **Обработка ошибок**: Требуется тщательная обработка HTTP ошибок
⚠️ **Обновления API**: Нужно следить за изменениями в API

## 📚 Документация API

- [Yandex DataProc API](https://cloud.yandex.ru/docs/data-proc/api-ref/)
- [IAM Token API](https://cloud.yandex.ru/docs/iam/api-ref/authentication)
- [Operations API](https://cloud.yandex.ru/docs/api-design-guide/concepts/operation)

## 🎓 Уроки

1. **Не доверяйте устаревшей документации** - всегда проверяйте актуальность
2. **REST API - универсальное решение** - работает везде, где есть HTTP
3. **PyJWT легковесный** - не вызывает проблем с зависимостями
4. **Lockbox для секретов** - безопасное хранение ключей сервисных аккаунтов

## 🔮 Дальнейшие шаги

1. ✅ Создать кластер через REST API
2. ✅ Проверить статус кластера
3. ✅ Удалить кластер
4. 🔄 Реализовать запуск PySpark job через Livy API
5. 🔄 Добавить мониторинг прогресса обучения
6. 🔄 Интеграция с MLflow для трекинга экспериментов
