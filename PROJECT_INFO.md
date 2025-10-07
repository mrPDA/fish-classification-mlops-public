# 📚 Project Information

## Образовательный проект - Fish Classification MLOps

Этот проект создан в рамках финальной работы курса **MLOps** (OTUS) и представляет собой полнофункциональную production-ready систему машинного обучения.

## 🎯 Цели проекта

### Образовательные цели
1. ✅ Продемонстрировать полный цикл MLOps: от обучения до production
2. ✅ Показать best practices автоматизации ML пайплайнов
3. ✅ Реализовать Infrastructure as Code подход
4. ✅ Внедрить мониторинг и наблюдаемость ML систем
5. ✅ Применить современные облачные технологии

### Технические достижения
- ✅ Автоматическое обучение моделей на распределенном кластере
- ✅ CI/CD для ML с использованием Airflow
- ✅ Автоматическая регистрация моделей в Model Registry
- ✅ Production-ready API с автомасштабированием
- ✅ Полная автоматизация через Terraform и Kubernetes
- ✅ Комплексный мониторинг с Grafana

## 📊 Технический стек

### Cloud & Infrastructure
- **Yandex Cloud** - облачный провайдер
- **Terraform 1.5+** - Infrastructure as Code
- **Kubernetes 1.30** - контейнерная оркестрация

### ML & Data Processing
- **TensorFlow 2.13** - deep learning framework
- **Apache Spark** - distributed data processing
- **Transfer Learning** - EfficientNet-B4 pretrained model

### MLOps Tools
- **Apache Airflow 2.10** - workflow orchestration
- **MLflow 2.9** - experiment tracking & model registry
- **DVC** - data version control (optional)

### Backend & API
- **FastAPI** - REST API framework
- **Redis** - caching layer
- **PostgreSQL** - metadata storage
- **Nginx** - web server & reverse proxy

### Monitoring & Observability
- **Grafana** - visualization
- **Prometheus** - metrics collection
- **Yandex Monitoring** - cloud metrics

### DevOps & Automation
- **Docker** - containerization
- **Make** - automation scripts
- **GitHub Actions** (ready for CI/CD)

## 📈 Результаты

### Модель
- **Архитектура:** EfficientNet-B4 (Transfer Learning)
- **Точность:** ~85-90% на validation set
- **Время инференса:** ~45ms per image
- **Размер модели:** ~70MB

### Инфраструктура
- **Автоматическое развертывание:** 1 команда (`make deploy-all`)
- **Время развертывания:** ~15-20 минут
- **Автомасштабирование:** 1-10 pods (HPA)
- **Высокая доступность:** Load balancing, health checks

### Производительность
- **API throughput:** ~100 requests/second
- **Cache hit rate:** ~60-70% (Redis)
- **Training time:** ~10-15 минут (DataProc cluster)
- **Auto-scaling latency:** ~30 seconds

## 🏆 Ключевые особенности

### 1. Полная автоматизация
```bash
make deploy-all  # Одна команда для всего
```
- Создание инфраструктуры (Terraform)
- Развертывание приложений (Kubernetes)
- Настройка Airflow DAGs
- Загрузка данных в S3

### 2. Production-Ready
- ✅ High Availability (Load Balancing)
- ✅ Auto-scaling (Horizontal Pod Autoscaler)
- ✅ Health checks & Readiness probes
- ✅ Redis caching
- ✅ Monitoring & Alerting
- ✅ Secure secrets management

### 3. MLOps Best Practices
- ✅ Automated model training
- ✅ Model versioning (MLflow Registry)
- ✅ Automated model deployment
- ✅ Experiment tracking
- ✅ Data versioning ready (DVC)
- ✅ CI/CD ready (GitHub Actions templates)

### 4. Cost Optimization
- ✅ Auto-scaling (scale to zero ready)
- ✅ Spot instances support
- ✅ Efficient resource allocation
- ✅ DataProc cluster auto-deletion after training

## 📁 Структура проекта

```
fish-classification-mlops/
├── README.md                    # Основная документация
├── LICENSE                      # MIT License
├── .gitignore                   # Git ignore rules
├── Makefile                     # Automation commands
│
├── terraform/                   # Infrastructure as Code
│   ├── main.tf                  # Main infrastructure
│   ├── kubernetes.tf            # K8s cluster
│   ├── airflow.tf              # Managed Airflow
│   ├── kafka.tf                # Managed Kafka
│   ├── postgres.tf             # Managed PostgreSQL
│   ├── lockbox.tf              # Secrets management
│   ├── grafana.tf              # Grafana VM
│   └── variables.tf            # Variables definition
│
├── dags/                        # Airflow DAGs
│   └── fish_classification_training_full.py
│
├── spark_jobs/                  # Spark training scripts
│   └── train_fish_model_minimal.py
│
├── api/                         # FastAPI application
│   └── main.py
│
├── frontend/                    # Web interface
│   ├── index.html
│   ├── app.js
│   └── nginx.conf
│
├── k8s/                         # Kubernetes manifests
│   ├── namespace.yaml
│   ├── redis/
│   ├── inference-api/
│   └── frontend/
│
├── scripts/                     # Automation scripts
│   ├── setup_airflow.sh
│   ├── deploy_real_api.sh
│   ├── deploy_frontend_simple.sh
│   └── ...
│
├── monitoring/                  # Monitoring configs
│   └── grafana/
│       └── dashboards/
│
└── docs/                        # Documentation
    ├── TRAINING.md
    ├── DEPLOYMENT_AUTO.md
    ├── MODEL_REGISTRY_AUTOMATION.md
    └── ...
```

## 🚀 Быстрый старт

```bash
# 1. Клонирование
git clone https://github.com/denispukinov/fish-classification-mlops.git
cd fish-classification-mlops

# 2. Настройка
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Отредактируйте terraform.tfvars

# 3. Развертывание
make deploy-all

# 4. Проверка статуса
make status

# 5. Получение URLs
make print-urls
```

## 📖 Документация

Полная документация доступна в папке `docs/`:

- [README.md](README.md) - Основная документация
- [DATASET.md](DATASET.md) - Информация о датасете
- [CONTRIBUTING.md](CONTRIBUTING.md) - Как внести вклад
- [docs/TRAINING.md](docs/TRAINING.md) - Обучение моделей
- [docs/DEPLOYMENT_AUTO.md](docs/DEPLOYMENT_AUTO.md) - Автоматическое развертывание

## 🎓 Использование в образовательных целях

Проект может быть использован для:

1. **Изучения MLOps практик**
   - CI/CD для ML
   - Model Registry
   - Automated training pipelines

2. **Изучения Kubernetes**
   - Deployments, Services, HPA
   - ConfigMaps, Secrets
   - Ingress, Load Balancing

3. **Изучения Terraform**
   - Infrastructure as Code
   - Cloud resources management
   - State management

4. **Изучения ML**
   - Transfer Learning
   - Model optimization
   - Production deployment

## 🔬 Возможные улучшения

Проект может быть расширен:

- [ ] A/B testing для моделей
- [ ] Model drift detection
- [ ] Feature store integration
- [ ] Advanced monitoring (Prometheus alerts)
- [ ] Multi-region deployment
- [ ] Edge deployment (TensorFlow Lite)
- [ ] Batch prediction API
- [ ] Model explainability (SHAP, LIME)

## 📞 Контакты

**Автор:** Денис Пукинов  
**Email:** [ваш email]  
**GitHub:** [@denispukinov](https://github.com/denispukinov)  
**LinkedIn:** [ваш профиль]  

**Курс:** MLOps (OTUS)  
**Год:** 2025  

---

## 🙏 Благодарности

- **OTUS** - за качественный курс по MLOps
- **Yandex Cloud** - за предоставленную инфраструктуру
- **Open Source Community** - за amazing tools

---

⭐️ **Если проект был полезен, поставьте звезду на GitHub!**

📚 **Используйте проект для обучения и экспериментов!**

🤝 **Вклад в проект приветствуется!**

