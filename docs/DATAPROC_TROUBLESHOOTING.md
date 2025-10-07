# 🔧 DataProc Troubleshooting

## Проблема: "Failed initialization actions" и "Unhealthy services: YARN"

### Симптомы

```
Error: Cluster c9qglkokffhea36bth6d has failed initialization actions
Cluster c9qglkokffhea36bth6d has unhealthy services: YARN
```

### Причины

1. **Недостаточные ресурсы для YARN**
   - `s2.micro` (2 CPU, 8GB RAM) слишком мало для стабильной работы YARN
   - YARN требует минимум 4 CPU и 16GB RAM для надёжной работы

2. **Initialization actions конфликты**
   - Установка зависимостей через init actions может вызывать проблемы
   - Timeout или ошибки скрипта приводят к падению кластера

3. **Медленный диск**
   - `network-hdd` слишком медленный для YARN и Spark
   - Рекомендуется `network-ssd`

### Решение

#### 1. Увеличить ресурсы кластера

```python
# В dags/fish_classification_training_full.py

# Master node
masternode_resource_preset='s2.small',  # 4 CPU, 16GB RAM
masternode_disk_type='network-ssd',
masternode_disk_size=30,

# Compute nodes
computenode_resource_preset='s2.small',  # 4 CPU, 16GB RAM
computenode_disk_type='network-ssd',
computenode_disk_size=30,
computenode_count=1,
```

**Преимущества:**
- ✅ YARN работает стабильно
- ✅ Быстрая инициализация
- ✅ Надёжное выполнение Spark jobs

**Требования:**
- Нужно 8 CPU (4 master + 4 compute)
- Проверьте квоту: `yc quota list --folder-id=<folder-id>`

#### 2. Отключить initialization actions

```python
# Отключить initialization action
# initialization_actions=[
#     InitializationAction(
#         uri=f's3a://{S3_BUCKET}/scripts/dataproc-init.sh',
#         timeout=600
#     )
# ],
```

**Почему:**
- Зависимости устанавливаются в Spark job (более надёжно)
- Меньше точек отказа при создании кластера
- Быстрее инициализация

#### 3. Оптимизировать конфигурацию

```python
# Минимальные services
services=['YARN', 'SPARK', 'LIVY'],

# Без data nodes (используем compute nodes)
datanode_count=0,

# Минимальные Spark properties
properties={
    'spark:spark.sql.warehouse.dir': f's3a://{S3_BUCKET}/spark-warehouse/',
    'spark:spark.yarn.submit.waitAppCompletion': 'true',
},
```

## Проблема: Недостаточно квоты CPU

### Симптом

```
Error: insufficient Compute quota for: compute.instanceCores.count
required 8.00 but available 6.00
```

### Решение 1: Увеличить квоту (рекомендуется)

**Через консоль:**
1. Откройте [Yandex Cloud Console](https://console.cloud.yandex.ru/)
2. Перейдите в ваш folder
3. Слева выберите "Квоты"
4. Найдите "Compute Cloud" → "Количество vCPU"
5. Нажмите "Увеличить квоты"
6. Укажите:
   - Текущее значение: 6
   - Требуемое значение: 12-16 (с запасом)
   - Причина: "MLOps проект с DataProc для обучения ML моделей"
7. Отправьте запрос

**Через CLI:**
```bash
# Проверить текущие квоты
yc quota list --folder-id=<folder-id>

# Через поддержку
# 1. Создайте тикет в консоли
# 2. Или напишите на support@cloud.yandex.ru
```

**Сроки:**
- Обычно 1-4 часа в рабочее время
- До 24 часов в выходные

### Решение 2: Освободить ресурсы

**Временно остановите VM:**

```bash
# Посмотреть текущие VM
yc compute instance list

# Остановить Grafana (2 CPU)
yc compute instance stop <grafana-instance-id>

# Или остановить MLflow (2 CPU)
yc compute instance stop <mlflow-instance-id>

# Освободится 2-4 CPU → можно запустить DataProc
```

**После обучения:**
```bash
# Запустить обратно
yc compute instance start <instance-id>
```

### Решение 3: Использовать минимальную конфигурацию (не рекомендуется)

```python
# ВНИМАНИЕ: YARN может быть нестабильным!

# Вариант 1: Только master node (без compute)
masternode_resource_preset='s2.small',  # 4 CPU
computenode_count=0,  # Без compute nodes

# Вариант 2: s2.micro (риск падения YARN)
masternode_resource_preset='s2.micro',  # 2 CPU
computenode_resource_preset='s2.micro',  # 2 CPU
# Итого: 4 CPU (но YARN нестабилен)
```

## Проблема: DataProc кластер создаётся очень долго

### Нормальное время

```
✅ Создание кластера:    5-7 минут
✅ Инициализация YARN:   2-3 минуты
✅ Готовность к работе:  7-10 минут
```

### Если дольше 15 минут

**1. Проверить логи в консоли:**
```bash
# В Airflow UI → Logs → create_dataproc_cluster
# Или в Yandex Cloud Console → DataProc → Clusters → <cluster-id> → Logs
```

**2. Проверить состояние кластера:**
```bash
yc dataproc cluster list
yc dataproc cluster get <cluster-id>
```

**3. Типичные проблемы:**
- Нет доступа к S3 → проверьте service account IAM roles
- Нет доступа в интернет → проверьте NAT Gateway
- Security group блокирует → добавьте правила

## Проблема: Spark job падает с OOM (Out of Memory)

### Симптом

```
Error: Container killed by YARN for exceeding memory limits
```

### Решение

```python
# Увеличить память для executor
properties={
    'spark:spark.executor.memory': '4g',
    'spark:spark.executor.cores': '2',
    'spark:spark.driver.memory': '4g',
    'spark:spark.memory.fraction': '0.8',
},

# Или увеличить размер кластера
computenode_resource_preset='s2.medium',  # 8 CPU, 32GB RAM
```

## Проблема: Не находится файл в S3

### Симптом

```
Error: Path does not exist: s3a://bucket/path/to/file
```

### Решение

**1. Проверить что файл в S3:**
```bash
yc storage s3api list-objects --bucket <bucket-name> --prefix spark_jobs/
```

**2. Проверить IAM роли service account:**
```bash
yc iam service-account list-access-bindings <service-account-id>
```

Нужны роли:
- `storage.viewer` (минимум)
- `storage.editor` (для записи)

**3. Проверить S3 credentials в DAG:**
```python
# В create_pyspark_job
s3_main_script=f's3a://{S3_BUCKET}/spark_jobs/train_fish_model_minimal.py',
```

## Best Practices

### 1. Размеры кластера

| Задача | Master | Compute | Итого |
|--------|--------|---------|-------|
| **Тестирование** | s2.micro (2 CPU) | 0 | 2 CPU |
| **Development** | s2.small (4 CPU) | s2.small (4 CPU) × 1 | 8 CPU |
| **Production** | s2.medium (8 CPU) | s2.medium (8 CPU) × 2-3 | 24-32 CPU |

### 2. Оптимизация стоимости

```python
# Используйте preemptible compute nodes (дешевле в 3 раза)
computenode_preemptible=True,

# Автоудаление кластера после job
# (реализовано через delete_dataproc_cluster task)

# Минимальный timeout для init actions
initialization_actions=[
    InitializationAction(
        uri=f's3a://{S3_BUCKET}/scripts/init.sh',
        timeout=300  # 5 минут максимум
    )
],
```

### 3. Мониторинг

**Логи в S3:**
```python
log_group_id='<log-group-id>',  # Yandex Cloud Logging
```

**YARN UI:**
```
http://<master-node-ip>:8088/cluster
```

**Spark History Server:**
```
http://<master-node-ip>:18080
```

### 4. Безопасность

```python
# Всегда используйте security groups
security_group_ids=[SECURITY_GROUP_ID],

# Не храните credentials в коде
S3_ACCESS_KEY = Variable.get('S3_ACCESS_KEY')  # Из Lockbox

# SSH ключи из Airflow Variables
ssh_public_keys=[SSH_PUBLIC_KEY],
```

## Полезные команды

```bash
# Список кластеров
yc dataproc cluster list

# Детали кластера
yc dataproc cluster get <cluster-id>

# Удалить зависший кластер
yc dataproc cluster delete <cluster-id>

# Проверить квоты
yc quota list --folder-id=<folder-id>

# Логи кластера
yc logging read --group-id=<log-group-id> --filter="resource_id='<cluster-id>'"

# Список jobs
yc dataproc job list --cluster-name=<cluster-name>

# Отменить job
yc dataproc job cancel --cluster-name=<cluster-name> --job-id=<job-id>
```

## Контрольный список перед запуском

- [ ] Квота CPU достаточна (минимум 8 CPU)
- [ ] Service account имеет все нужные роли
- [ ] Файлы загружены в S3 (spark script, dataset)
- [ ] NAT Gateway настроен для доступа в интернет
- [ ] Security group разрешает внутренний трафик
- [ ] SSH ключи сгенерированы и загружены
- [ ] Airflow variables настроены
- [ ] MLflow доступен из кластера

## Заключение

**Рекомендуемая конфигурация для стабильной работы:**

```python
masternode_resource_preset='s2.small',      # 4 CPU, 16GB RAM
masternode_disk_type='network-ssd',
masternode_disk_size=30,

computenode_resource_preset='s2.small',     # 4 CPU, 16GB RAM
computenode_disk_type='network-ssd',
computenode_disk_size=30,
computenode_count=1,

# Без initialization actions
# Зависимости устанавливаются в Spark job
```

**Итого: 8 CPU, 32GB RAM, ~$3-5 за полный цикл обучения (20-25 минут)**

