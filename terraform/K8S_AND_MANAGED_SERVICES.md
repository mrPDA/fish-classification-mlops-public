# ☸️ Kubernetes + Managed Services - Полная картина

## 🎯 Гибридная архитектура проекта

```
┌─────────────────────────────────────────────────────────────────────┐
│                         YANDEX CLOUD                                │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────────┐  ┌──────────────────────────────────────┐
│   MANAGED SERVICES       │  │         KUBERNETES                   │
│   (Managed by Yandex)    │  │      (Your workloads)                │
├──────────────────────────┤  ├──────────────────────────────────────┤
│                          │  │                                      │
│  🌊 Airflow              │  │  Namespace: ml-inference             │
│     • Orchestration      │◄─┤  ┌────────────────────────────────┐ │
│     • DAG scheduling     │  │  │ 🌐 Inference API (FastAPI)    │ │
│     • DataProc control   │  │  │    • 3-20 replicas            │ │
│                          │  │  │    • HPA (CPU-based)          │ │
│  🤖 MLflow (VM)          │  │  │    • LoadBalancer service     │ │
│     • Tracking server    │◄─┤  └────────────────────────────────┘ │
│     • Model registry     │  │  ┌────────────────────────────────┐ │
│     • Artifact storage   │  │  │ 👷 ML Workers                 │ │
│                          │  │  │    • 2-10 replicas            │ │
│  🗄️  PostgreSQL          │  │  │    • Kafka consumers          │ │
│     • Airflow metadata   │  │  │    • Batch processing         │ │
│     • MLflow backend     │  │  └────────────────────────────────┘ │
│                          │  │  ┌────────────────────────────────┐ │
│  📨 Kafka ⭐             │◄─┤  │ 🚀 Redis                      │ │
│     • 1 broker           │  │  │    • 1 replica                │ │
│     • Topics:            │  │  │    • Caching                  │ │
│       - requests         │  │  │    • Status tracking          │ │
│       - results          │  │  └────────────────────────────────┘ │
│     • s2.micro (2vCPU)   │  │                                      │
│     • 32GB HDD           │  │  📊 Monitoring (optional)            │
│                          │  │     • Prometheus                     │
│  🔥 DataProc             │  │     • Node exporters                 │
│     • On-demand clusters │  │                                      │
│     • Spark + GPU        │  └──────────────────────────────────────┘
│     • Auto-termination   │              ▲
│                          │              │
│  📊 Grafana (VM)         │              │
│     • Monitoring         │         LoadBalancer
│     • Dashboards         │         (External IP)
│                          │              │
│  ☁️  S3 Storage          │              │
│     • Datasets           │              │
│     • Models             │              ▼
│     • Artifacts          │         👥 Users
│     • Kafka data         │         (API Clients)
│                          │
└──────────────────────────┘
```

---

## 📦 Что где развернуто

### ✅ MANAGED SERVICES (Yandex Cloud)

#### 1. **Apache Airflow**
```
Type:       Managed Service for Apache Airflow
Purpose:    Orchestration ML pipeline
Version:    2.9.x
Resources:  2 vCPU, 8 GB RAM (s2.medium)
Features:
  • DAG scheduling
  • DataProc cluster creation
  • Lockbox secrets integration
  • S3 integration for DAGs
```

#### 2. **PostgreSQL**
```
Type:       Managed Service for PostgreSQL
Purpose:    Metadata storage
Version:    14
Resources:  2 vCPU, 8 GB RAM (s2.medium)
Databases:
  • airflow - Airflow metadata
  • mlflow - MLflow backend (optional)
Features:
  • Automatic backups
  • High availability
  • Connection pooling (PgBouncer)
```

#### 3. **Kafka** ⭐
```
Type:       Managed Service for Apache Kafka
Purpose:    Message queue for batch processing
Version:    3.6
Brokers:    1
Resources:  s2.micro (2 vCPU, 8 GB RAM)
Disk:       32 GB HDD
Connection: rc1a-mjs21l34cb7dh25g.mdb.yandexcloud.net:9091
Auth:       SASL_SSL

Pre-created Topics:
  • fish-classification-requests (3 partitions, 1 replication)
  • fish-classification-results (3 partitions, 1 replication)

Config:
  • Compression: GZIP
  • Retention: 7 days
  • Retention size: 1 GB per topic
```

#### 4. **MLflow** (VM)
```
Type:       Compute Instance (VM)
Purpose:    Experiment tracking & model registry
Resources:  2 vCPU, 4 GB RAM
OS:         Ubuntu 22.04
Services:
  • MLflow Server (port 5000)
  • PostgreSQL backend (optional)
  • S3 artifact storage
```

#### 5. **Grafana** (VM)
```
Type:       Compute Instance (VM)
Purpose:    Monitoring & visualization
Resources:  2 vCPU, 4 GB RAM
OS:         Ubuntu 22.04
Features:
  • Auto-installed via cloud-init
  • Pre-configured datasources (MLflow, PostgreSQL)
  • Dashboard provisioning
```

#### 6. **DataProc** (On-demand)
```
Type:       Managed Service for Apache Spark
Purpose:    Model training
Mode:       On-demand (created by Airflow, auto-terminated)
Resources:  s3-c4-m16 (4 vCPU, 16 GB RAM)
Features:
  • PySpark jobs
  • GPU support (optional)
  • S3 integration
  • MLflow logging
```

#### 7. **S3 Object Storage**
```
Type:       Object Storage
Purpose:    Data lake
Bucket:     fish-classification-data-<suffix>
Contents:
  • datasets/ - Fish images
  • models/ - Trained models
  • spark_jobs/ - PySpark scripts
  • airflow-dags/ - Airflow DAG files
  • mlflow-artifacts/ - MLflow artifacts
```

---

### ☸️ KUBERNETES

#### K8s Cluster
```
Type:       Managed Kubernetes
Version:    1.28
Master:     Managed by Yandex
Nodes:      2× s3-c2-m8 (2 vCPU, 8 GB RAM)
Network:    Internal subnet
```

#### Namespace: `ml-inference`

##### 1. **Inference API (FastAPI)**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fish-api
  namespace: ml-inference
spec:
  replicas: 3
  
  # HPA configuration
  minReplicas: 2
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2
      memory: 2Gi
  
  env:
  - name: MLFLOW_TRACKING_URI
    value: "http://51.250.15.131:5000"
  - name: REDIS_HOST
    value: "redis.ml-inference.svc.cluster.local"
  - name: KAFKA_BOOTSTRAP_SERVERS
    value: "rc1a-mjs21l34cb7dh25g.mdb.yandexcloud.net:9091"
  - name: KAFKA_USER
    value: "kafka_user"
  - name: KAFKA_PASSWORD
    valueFrom:
      secretKeyRef:
        name: kafka-credentials
        key: password
```

**Endpoints:**
- `POST /predict` - Real-time inference
- `POST /batch/predict` - Batch via Kafka
- `GET /batch/status/:id` - Batch status
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

##### 2. **ML Workers**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-worker
  namespace: ml-inference
spec:
  replicas: 2
  
  # Scale based on Kafka lag
  minReplicas: 1
  maxReplicas: 10
  
  resources:
    requests:
      cpu: 1
      memory: 2Gi
    limits:
      cpu: 4
      memory: 4Gi
  
  env:
  - name: KAFKA_BOOTSTRAP_SERVERS
    value: "rc1a-mjs21l34cb7dh25g.mdb.yandexcloud.net:9091"
  - name: KAFKA_TOPIC
    value: "fish-classification-requests"
  - name: KAFKA_GROUP_ID
    value: "ml-workers"
```

**Functions:**
- Read from Kafka (Managed Service)
- Load images from URLs
- Run inference
- Save results to S3
- Update status in Redis

##### 3. **Redis**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: ml-inference
spec:
  replicas: 1
  
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi
```

**Usage:**
- Cache predictions (TTL: 1 hour)
- Store batch job statuses (TTL: 24 hours)
- Atomic operations

---

## 🔄 Data Flow

### Training Pipeline (Managed Services):

```
1. Airflow DAG triggered (scheduled/manual)
   │
2. Create DataProc cluster
   │
3. Submit PySpark job
   │
   ├─→ Read dataset from S3
   ├─→ Train model (TensorFlow)
   ├─→ Log to MLflow
   └─→ Save model to S3
   │
4. Terminate DataProc cluster
   │
5. Verify results in MLflow
```

### Real-time Inference (K8s):

```
User → LoadBalancer → API Pod
                        │
                        ├─→ Check Redis cache
                        │   ├─ Hit: return cached result
                        │   └─ Miss: continue
                        │
                        ├─→ Load model from S3 (via MLflow)
                        ├─→ Run inference
                        ├─→ Cache result in Redis
                        └─→ Return prediction
```

### Batch Inference (K8s + Managed Kafka):

```
User → API Pod
        │
        ├─→ Generate request_id
        ├─→ Send to Managed Kafka ⭐
        ├─→ Set status in Redis: "queued"
        └─→ Return {"request_id": "abc", "status": "queued"}

Managed Kafka ⭐
        │
        ├─→ Store message (persistent)
        └─→ Notify consumers

ML Worker Pod (K8s)
        │
        ├─→ Read from Managed Kafka ⭐
        ├─→ Update Redis: "processing"
        ├─→ Load images
        ├─→ Run inference
        ├─→ Save to S3
        └─→ Update Redis: "completed"

User → API Pod → Redis → Return results
```

---

## 💰 Cost Breakdown

| Component | Type | Resources | Cost/month |
|-----------|------|-----------|------------|
| **Managed Services** |||
| Airflow | Managed | s2.medium | ~5,000₽ |
| PostgreSQL | Managed | s2.medium | ~4,000₽ |
| **Kafka** ⭐ | **Managed** | **s2.micro + 32GB** | **~3,000₽** |
| MLflow VM | VM | s3-c2-m4 | ~1,500₽ |
| Grafana VM | VM | s3-c2-m4 | ~1,500₽ |
| S3 Storage | Object Storage | 100 GB | ~300₽ |
| **Kubernetes** |||
| K8s Master | Managed | - | ~1,500₽ |
| Worker Nodes | VM | 2× s3-c2-m8 | ~6,000₽ |
| Load Balancer | Network | - | ~600₽ |
| **On-Demand** |||
| DataProc | Spark cluster | Pay-per-use | ~500₽ |
| **TOTAL** ||| **~24,000₽/month** |

---

## 🎯 Почему Kafka - Managed Service?

### ✅ Преимущества Managed Kafka:

1. **Reliability**
   - Автоматические бэкапы
   - Высокая доступность
   - Репликация данных

2. **Operations**
   - Не требует управления в K8s
   - Автоматические обновления
   - Managed мониторинг

3. **Performance**
   - Оптимизированная конфигурация
   - Гарантированные ресурсы
   - Persistent storage

4. **Cost-effective**
   - s2.micro достаточно для начала
   - HDD вместо SSD (дешевле)
   - Платите только за использование

### ❌ Почему НЕ Kafka в K8s:

- ❌ Сложная настройка StatefulSet
- ❌ Требует persistent volumes
- ❌ Управление Zookeeper
- ❌ Сложная отладка проблем
- ❌ Больше операционной нагрузки

---

## 🚀 Deployment

### 1. Terraform creates everything:

```bash
cd terraform
terraform init
terraform apply

# Creates:
# ✅ Managed Airflow
# ✅ Managed PostgreSQL
# ✅ Managed Kafka ⭐
# ✅ MLflow VM
# ✅ Grafana VM
# ✅ Kubernetes cluster
# ✅ S3 bucket
```

### 2. Deploy to Kubernetes:

```bash
# Configure kubectl
yc managed-kubernetes cluster get-credentials <cluster-id> --external --force

# Deploy applications
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/redis/
kubectl apply -f k8s/inference-api/
kubectl apply -f k8s/ml-workers/

# Note: Kafka is NOT deployed to K8s!
# Workers connect to Managed Kafka via external endpoint
```

### 3. Verify connections:

```bash
# Test Managed Kafka from K8s
kubectl run kafka-test --rm -it --image=confluentinc/cp-kafka:7.5.0 -- \
  kafka-console-producer \
  --bootstrap-server rc1a-mjs21l34cb7dh25g.mdb.yandexcloud.net:9091 \
  --topic fish-classification-requests \
  --producer-property security.protocol=SASL_SSL \
  --producer-property sasl.mechanism=SCRAM-SHA-512 \
  --producer-property sasl.jaas.config='org.apache.kafka.common.security.scram.ScramLoginModule required username="kafka_user" password="<password>";'
```

---

## 📋 Summary

### В KUBERNETES развернуто:
- ✅ Inference API (FastAPI) - 3-20 pods
- ✅ ML Workers (Kafka consumers) - 2-10 pods
- ✅ Redis (caching) - 1 pod
- ✅ Monitoring (optional) - Prometheus, Node exporters

### В MANAGED SERVICES развернуто:
- ✅ Airflow - оркестрация
- ✅ PostgreSQL - метаданные
- ✅ **Kafka** ⭐ - **message queue**
- ✅ MLflow (VM) - tracking
- ✅ Grafana (VM) - мониторинг
- ✅ DataProc - training (on-demand)
- ✅ S3 - хранение

### Kafka подключение из K8s:
```python
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers='rc1a-mjs21l34cb7dh25g.mdb.yandexcloud.net:9091',
    security_protocol='SASL_SSL',
    sasl_mechanism='SCRAM-SHA-512',
    sasl_plain_username='kafka_user',
    sasl_plain_password='<password>',
    ssl_check_hostname=True
)

producer.send('fish-classification-requests', b'{"image_url": "..."}')
```

---

**Создано:** 2025-10-07  
**Статус:** ✅ Production Ready  
**Kafka:** Managed Service (не в K8s!)
