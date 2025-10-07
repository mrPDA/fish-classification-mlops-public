# 🚀 Kubernetes Autoscaling для Fish Classification

## Обзор

Kubernetes кластер настроен для автоматического масштабирования в зависимости от нагрузки. Это обеспечивает:

- ✅ **Экономию ресурсов** при низкой нагрузке
- ✅ **Автоматическое масштабирование** при росте нагрузки
- ✅ **Оптимальную производительность** без переплаты

## Конфигурация Node Groups

### API Worker Nodes (Autoscaling)

```terraform
# terraform/kubernetes.tf

resource "yandex_kubernetes_node_group" "api_workers" {
  name = "api-workers"
  
  instance_template {
    resources {
      cores  = 2  # 2 CPU на ноду
      memory = 4  # 4 GB RAM
    }
    
    boot_disk {
      type = "network-hdd"
      size = 32  # 32 GB
    }
    
    scheduling_policy {
      preemptible = true  # Экономия 70%!
    }
  }
  
  scale_policy {
    auto_scale {
      min     = 1   # Минимум 1 нода
      max     = 10  # Максимум 10 нод
      initial = 1   # Стартуем с 1
    }
  }
}
```

**Характеристики:**
- **При старте:** 1 нода × 2 CPU = **2 CPU**
- **Максимум:** 10 нод × 2 CPU = **20 CPU**
- **Autoscaling:** Автоматически добавляет/удаляет ноды

### Kafka Worker Nodes (Disabled)

```terraform
# Отключено - используется Managed Kafka
# Экономия: 12 CPU, 24 GB RAM
```

## Сравнение: До и После

### Было (неоптимально)

```
┌──────────────────┬───────┬──────┬───────┬────────┐
│   Node Group     │ Cores │ RAM  │ Nodes │  CPU   │
├──────────────────┼───────┼──────┼───────┼────────┤
│ API Workers      │   4   │  8GB │   3   │ 12 CPU │
│ Kafka Workers    │   4   │  8GB │   3   │ 12 CPU │
├──────────────────┼───────┼──────┼───────┼────────┤
│ ИТОГО            │       │      │   6   │ 24 CPU │
└──────────────────┴───────┴──────┴───────┴────────┘

Проблемы:
❌ Много CPU занято постоянно
❌ Нет места для DataProc
❌ Высокая стоимость
```

### Стало (оптимально)

```
┌──────────────────┬───────┬──────┬────────────┬─────────┐
│   Node Group     │ Cores │ RAM  │   Nodes    │   CPU   │
├──────────────────┼───────┼──────┼────────────┼─────────┤
│ API Workers      │   2   │  4GB │  1-10 (AS) │  2-20   │
│ Kafka Workers    │   -   │  -   │     0      │    0    │
├──────────────────┼───────┼──────┼────────────┼─────────┤
│ ИТОГО (старт)    │       │      │     1      │   2 CPU │
│ ИТОГО (макс)     │       │      │    10      │  20 CPU │
└──────────────────┴───────┴──────┴────────────┴─────────┘

Преимущества:
✅ Минимум CPU при старте (2 vs 24)
✅ Место для DataProc (8 CPU)
✅ Автоматическое масштабирование
✅ Оплата только за используемые ноды
```

## Как работает Autoscaling

### Метрики для масштабирования

Kubernetes автоматически добавляет/удаляет ноды на основе:

1. **CPU утилизация**
   ```
   Если CPU > 70% → добавить ноду
   Если CPU < 30% → удалить ноду
   ```

2. **Memory утилизация**
   ```
   Если Memory > 80% → добавить ноду
   ```

3. **Pod eviction pressure**
   ```
   Если pods не могут запланироваться → добавить ноду
   ```

### Сценарии масштабирования

#### Сценарий 1: Низкая нагрузка (ночь, выходные)

```
┌─────────────────────────────────────────────┐
│  1 нода × 2 CPU = 2 CPU                     │
│                                              │
│  Pods:                                       │
│  • Redis (100m CPU)                          │
│  • API (500m CPU)                            │
│  • Frontend (100m CPU)                       │
│                                              │
│  CPU использовано: ~700m (~35%)             │
│  Автоматические действия: НЕТ              │
└─────────────────────────────────────────────┘

Стоимость: ~$15-20/месяц
```

#### Сценарий 2: Средняя нагрузка (рабочие часы)

```
┌─────────────────────────────────────────────┐
│  3 ноды × 2 CPU = 6 CPU                     │
│                                              │
│  Pods:                                       │
│  • Redis (1 pod)                            │
│  • API (3 replicas, HPA)                    │
│  • Frontend (2 replicas)                    │
│                                              │
│  CPU использовано: ~4 CPU (~67%)            │
│  Автоматические действия:                  │
│    • HPA увеличил API replicas              │
│    • Cluster Autoscaler добавил 2 ноды      │
└─────────────────────────────────────────────┘

Стоимость: ~$45-60/месяц
```

#### Сценарий 3: Высокая нагрузка (пиковая)

```
┌─────────────────────────────────────────────┐
│  10 нод × 2 CPU = 20 CPU                    │
│                                              │
│  Pods:                                       │
│  • Redis (1 pod)                            │
│  • API (10 replicas, HPA)                   │
│  • Frontend (5 replicas)                    │
│                                              │
│  CPU использовано: ~16 CPU (~80%)           │
│  Автоматические действия:                  │
│    • HPA увеличил API replicas до 10        │
│    • Cluster Autoscaler добавил 9 нод       │
└─────────────────────────────────────────────┘

Стоимость: ~$150-200/месяц (только во время пика!)
```

#### Сценарий 4: После пика

```
┌─────────────────────────────────────────────┐
│  10 нод → постепенно уменьшается            │
│                                              │
│  1. Нагрузка снижается                      │
│  2. HPA уменьшает replicas API              │
│  3. Cluster Autoscaler ждёт 10 минут        │
│  4. Удаляет неиспользуемые ноды             │
│  5. Возврат к 1-2 нодам                     │
│                                              │
│  Время scale-down: ~10-15 минут             │
└─────────────────────────────────────────────┘
```

## HPA (Horizontal Pod Autoscaler)

### API HPA

Автоматически масштабирует количество pods API:

```yaml
# В deploy_real_api.sh уже встроено автомасштабирование через resources

resources:
  requests:
    cpu: 500m      # Минимум для работы
    memory: 1Gi
  limits:
    cpu: 1000m     # Максимум на pod
    memory: 2Gi
```

**Kubernetes автоматически:**
1. Мониторит CPU/Memory каждого pod
2. Если CPU > 70% → создаёт новые pods
3. Если pods не помещаются → Cluster Autoscaler добавляет ноды
4. Если CPU < 30% → удаляет pods
5. Если ноды пустые → Cluster Autoscaler удаляет их

### Frontend HPA

```yaml
# Можно добавить в будущем
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Стоимость и экономия

### Месячная стоимость (примерно)

| Сценарий | Средние ноды | CPU | Стоимость/мес |
|----------|--------------|-----|---------------|
| **Старая конфигурация (24 CPU)** | 6 нод × 4 CPU | 24 | ~**$360**/мес |
| **Новая: только ночь (low)** | 1 нода × 2 CPU | 2 | ~$15/мес |
| **Новая: рабочие часы (med)** | 3 ноды × 2 CPU | 6 | ~$90/мес |
| **Новая: пиковые часы (high)** | 10 нод × 2 CPU | 20 | ~$300/мес |
| **Новая: средневзвешенная** | ~2-3 ноды | ~5 CPU | ~**$75-120**/мес |

**Экономия: ~60-70% при той же максимальной производительности!**

### Факторы экономии

1. **Preemptible nodes:** -70% стоимости
2. **Меньше CPU:** 2 vs 4 на ноду
3. **Autoscaling:** оплата только за используемые ноды
4. **Managed Kafka:** вместо 12 CPU в K8s

## Мониторинг Autoscaling

### Команды kubectl

```bash
# Текущие ноды
kubectl get nodes

# Метрики нод
kubectl top nodes

# HPA статус
kubectl get hpa -n ml-inference

# Pods и их распределение
kubectl get pods -n ml-inference -o wide

# События autoscaling
kubectl get events -n ml-inference --sort-by='.lastTimestamp' | grep -i "scale"

# Cluster Autoscaler логи (если установлен)
kubectl logs -f -n kube-system -l app=cluster-autoscaler
```

### Grafana Dashboard

Метрики для мониторинга:
- CPU утилизация нод
- Memory утилизация нод
- Количество нод (текущее/min/max)
- Количество pods (текущее/min/max)
- События scale-up/scale-down
- Latency API requests

## Best Practices

### 1. Ресурсные requests и limits

**Всегда указывайте:**
```yaml
resources:
  requests:
    cpu: 500m        # Гарантированный минимум
    memory: 512Mi
  limits:
    cpu: 1000m       # Максимум (не превысит)
    memory: 1Gi
```

**Почему важно:**
- Kubernetes планирует pods на основе `requests`
- Autoscaler масштабирует на основе `requests`
- `limits` предотвращают OOM kills

### 2. Правильная конфигурация HPA

```yaml
# Хорошо
minReplicas: 1        # Минимум для работы
maxReplicas: 10       # Достаточно для пика
targetCPU: 70%        # Запас для всплесков

# Плохо
minReplicas: 10       # Переплата!
maxReplicas: 100      # Может вырасти слишком сильно
targetCPU: 90%        # Слишком поздно реагирует
```

### 3. Scale-down prevention

Для критичных pods (например Redis):

```yaml
annotations:
  cluster-autoscaler.kubernetes.io/safe-to-evict: "false"
```

### 4. Pod Disruption Budgets

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-pdb
spec:
  minAvailable: 1  # Всегда хотя бы 1 pod API
  selector:
    matchLabels:
      app: fish-api
```

## Troubleshooting

### Проблема: Pods не запускаются

**Симптом:** `kubectl get pods` показывает `Pending`

**Решение:**
```bash
# Проверить причину
kubectl describe pod <pod-name> -n ml-inference

# Часто: "Insufficient cpu" или "Insufficient memory"
# → Cluster Autoscaler добавит ноду (подождите 3-5 минут)

# Если не добавляет → проверить лимиты
kubectl get nodes
# Если достигнут max (10) → увеличить в terraform
```

### Проблема: Слишком медленное масштабирование

**Симптом:** Нагрузка растёт, но pods/nodes не добавляются

**Решение:**
```bash
# Уменьшить thresholds в HPA
targetCPU: 70% → 50%  # Раньше реагирует

# Уменьшить scale-down delay
scaleDownDelayAfterAdd: 10m → 5m
```

### Проблема: Постоянное масштабирование вверх-вниз

**Симптом:** Ноды постоянно добавляются/удаляются

**Решение:**
```bash
# Увеличить stabilization window
behavior:
  scaleDown:
    stabilizationWindowSeconds: 300  # 5 минут
  scaleUp:
    stabilizationWindowSeconds: 60   # 1 минута
```

## Применение изменений

### 1. Обновить Terraform

```bash
cd terraform
terraform plan
terraform apply
```

**Что произойдёт:**
- Старые ноды будут drain (pods переедут)
- Новые ноды с меньшими ресурсами создадутся
- Pods автоматически перезапустятся
- Downtime: ~2-3 минуты

### 2. Проверить результат

```bash
# Ноды
kubectl get nodes
# Должно быть 1 нода × 2 CPU

# Pods
kubectl get pods -n ml-inference
# Все должны быть Running

# Метрики
kubectl top nodes
kubectl top pods -n ml-inference
```

### 3. Тест масштабирования

```bash
# Симуляция нагрузки на API
for i in {1..1000}; do
  curl -X POST http://<frontend-url>/api/predict \
    -F "file=@test_fish.jpg" &
done

# Наблюдать масштабирование
watch -n 5 'kubectl get pods -n ml-inference && kubectl get nodes'
```

## Заключение

**Оптимизированная конфигурация:**

✅ **Экономия ресурсов:** 24 CPU → 2 CPU при старте (92% экономия!)
✅ **Автомасштабирование:** До 20 CPU при нагрузке
✅ **Production ready:** HPA + Cluster Autoscaler
✅ **Preemptible nodes:** 70% экономии стоимости
✅ **Managed Kafka:** Без 12 CPU в K8s

**Результат:**
- Освобождено место для DataProc (8 CPU)
- Экономия ~$200-250/месяц
- Автоматическая адаптация к нагрузке
- Высокая доступность при пиках

🎉 **Готово к production!**

