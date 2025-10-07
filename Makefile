# ========================================
# 🐟 Fish Classification System - Makefile
# ========================================
# Полная автоматизация развёртывания MLOps системы

.PHONY: help init deploy destroy clean status test

# Цвета для вывода
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m

# Переменные
TERRAFORM_DIR := terraform
K8S_DIR := k8s
DOCKER_DIR := docker
DATASET_SOURCE := ../Finalwork/datasets_final
REGISTRY := cr.yandex

# ========================================
# Help
# ========================================

help: ## 📖 Показать справку
	@echo "$(BLUE)🐟 Fish Classification System - Makefile$(NC)"
	@echo ""
	@echo "$(GREEN)Доступные команды:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ========================================
# Инициализация
# ========================================

init: ## 🚀 Первоначальная инициализация проекта
	@echo "$(BLUE)🚀 Инициализация проекта...$(NC)"
	@if [ ! -f $(TERRAFORM_DIR)/terraform.tfvars ]; then \
		echo "$(RED)❌ Файл terraform.tfvars не найден!$(NC)"; \
		echo "$(YELLOW)Скопируйте terraform.tfvars.example и заполните значения:$(NC)"; \
		echo "  cp $(TERRAFORM_DIR)/terraform.tfvars.example $(TERRAFORM_DIR)/terraform.tfvars"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Проверка terraform.tfvars$(NC)"
	@cd $(TERRAFORM_DIR) && terraform init
	@echo "$(GREEN)✅ Terraform инициализирован$(NC)"

check-tools: ## 🔧 Проверка установленных инструментов
	@echo "$(BLUE)🔧 Проверка инструментов...$(NC)"
	@command -v terraform >/dev/null 2>&1 || { echo "$(RED)❌ terraform не установлен$(NC)"; exit 1; }
	@command -v yc >/dev/null 2>&1 || { echo "$(RED)❌ yc CLI не установлен$(NC)"; exit 1; }
	@command -v kubectl >/dev/null 2>&1 || { echo "$(RED)❌ kubectl не установлен$(NC)"; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)❌ docker не установлен$(NC)"; exit 1; }
	@echo "$(GREEN)✅ Все инструменты установлены$(NC)"

# ========================================
# Terraform - Инфраструктура
# ========================================

terraform-plan: init ## 📋 Terraform plan - показать изменения
	@echo "$(BLUE)📋 Проверка плана Terraform...$(NC)"
	@cd $(TERRAFORM_DIR) && terraform plan

terraform-apply: init ## 🏗️  Terraform apply - создать инфраструктуру
	@echo "$(BLUE)🏗️  Создание инфраструктуры...$(NC)"
	@cd $(TERRAFORM_DIR) && terraform apply -auto-approve
	@echo "$(GREEN)✅ Инфраструктура создана$(NC)"
	@$(MAKE) save-outputs

save-outputs: ## 💾 Сохранить outputs Terraform
	@echo "$(BLUE)💾 Сохранение outputs...$(NC)"
	@cd $(TERRAFORM_DIR) && terraform output -json > ../deployment_outputs.json
	@echo "$(GREEN)✅ Outputs сохранены в deployment_outputs.json$(NC)"

# ========================================
# Kubernetes - Настройка
# ========================================

configure-kubectl: ## ⚙️  Настроить kubectl для кластера
	@echo "$(BLUE)⚙️  Настройка kubectl...$(NC)"
	@CLUSTER_ID=$$(cd $(TERRAFORM_DIR) && terraform output -raw k8s_cluster_id 2>/dev/null); \
	if [ -z "$$CLUSTER_ID" ]; then \
		echo "$(RED)❌ Не удалось получить cluster ID$(NC)"; \
		exit 1; \
	fi; \
	yc managed-kubernetes cluster get-credentials $$CLUSTER_ID --external --force
	@echo "$(GREEN)✅ kubectl настроен$(NC)"

wait-for-cluster: configure-kubectl ## ⏳ Дождаться готовности кластера
	@echo "$(BLUE)⏳ Ожидание готовности кластера...$(NC)"
	@for i in $$(seq 1 60); do \
		if kubectl get nodes >/dev/null 2>&1; then \
			echo "$(GREEN)✅ Кластер готов$(NC)"; \
			kubectl get nodes; \
			break; \
		fi; \
		echo "Попытка $$i/60..."; \
		sleep 10; \
	done

deploy-k8s: wait-for-cluster ## 🚢 Развернуть приложения в Kubernetes
	@echo "$(BLUE)🚢 Развёртывание Kubernetes компонентов...$(NC)"
	
	@echo "$(YELLOW)📦 Создание namespaces...$(NC)"
	@kubectl apply -f $(K8S_DIR)/namespace.yaml
	
	@echo "$(YELLOW)💾 Развёртывание Redis...$(NC)"
	@kubectl apply -f $(K8S_DIR)/redis/
	@kubectl wait --for=condition=available --timeout=300s deployment/redis -n ml-inference || true
	
	@echo "$(GREEN)✅ Базовая инфраструктура развёрнута$(NC)"
	@echo "$(BLUE)ℹ️  Kafka развёрнут как Managed Service (см. Terraform outputs)$(NC)"

# ========================================
# Docker - Сборка образов
# ========================================

build-images: ## 🐳 Собрать Docker образы
	@echo "$(BLUE)🐳 Сборка Docker образов...$(NC)"
	@$(MAKE) build-api
	@$(MAKE) build-worker

build-api: ## 🔨 Собрать образ API
	@echo "$(YELLOW)🔨 Сборка fish-classification-api...$(NC)"
	@docker build -f $(DOCKER_DIR)/Dockerfile.api -t fish-classification-api:latest .
	@echo "$(GREEN)✅ API образ собран$(NC)"

build-worker: ## 🔨 Собрать образ Worker
	@echo "$(YELLOW)🔨 Сборка fish-classification-worker...$(NC)"
	@docker build -f $(DOCKER_DIR)/Dockerfile.worker -t fish-classification-worker:latest .
	@echo "$(GREEN)✅ Worker образ собран$(NC)"

push-images: build-images ## 📤 Push образов в registry
	@echo "$(BLUE)📤 Push образов в Yandex Container Registry...$(NC)"
	@REGISTRY_ID=$$(cd $(TERRAFORM_DIR) && terraform output -raw container_registry_id 2>/dev/null || echo ""); \
	if [ -z "$$REGISTRY_ID" ]; then \
		echo "$(YELLOW)⚠️  Container Registry не создан в Terraform$(NC)"; \
		echo "$(YELLOW)Используйте локальные образы или создайте registry вручную$(NC)"; \
	else \
		docker tag fish-classification-api:latest $(REGISTRY)/$$REGISTRY_ID/fish-classification-api:latest; \
		docker tag fish-classification-worker:latest $(REGISTRY)/$$REGISTRY_ID/fish-classification-worker:latest; \
		docker push $(REGISTRY)/$$REGISTRY_ID/fish-classification-api:latest; \
		docker push $(REGISTRY)/$$REGISTRY_ID/fish-classification-worker:latest; \
		echo "$(GREEN)✅ Образы загружены в registry$(NC)"; \
	fi

# ========================================
# Развёртывание приложений
# ========================================

create-secrets: ## 🔐 Создать Kubernetes secrets
	@echo "$(BLUE)🔐 Создание secrets...$(NC)"
	@POSTGRES_PASSWORD=$$(cd $(TERRAFORM_DIR) && terraform output -raw postgres_mlops_password 2>/dev/null); \
	kubectl create secret generic postgres-secrets \
		--from-literal=mlops-password="$$POSTGRES_PASSWORD" \
		-n ml-inference \
		--dry-run=client -o yaml | kubectl apply -f -
	@echo "$(GREEN)✅ Secrets созданы$(NC)"

update-k8s-manifests: ## 📝 Обновить переменные в K8s манифестах
	@echo "$(BLUE)📝 Обновление K8s манифестов...$(NC)"
	@MLFLOW_IP=$$(cd $(TERRAFORM_DIR) && terraform output -raw mlflow_vm_ip 2>/dev/null); \
	POSTGRES_HOST=$$(cd $(TERRAFORM_DIR) && terraform output -raw postgres_host 2>/dev/null); \
	REGISTRY_ID=$$(cd $(TERRAFORM_DIR) && terraform output -raw container_registry_id 2>/dev/null || echo "local"); \
	\
	sed -i.bak "s|{{ MLFLOW_HOST }}|$$MLFLOW_IP|g" $(K8S_DIR)/inference-api/deployment.yaml; \
	sed -i.bak "s|{{ MLFLOW_HOST }}|$$MLFLOW_IP|g" $(K8S_DIR)/ml-workers/deployment.yaml; \
	sed -i.bak "s|{{ POSTGRES_HOST }}|$$POSTGRES_HOST|g" $(K8S_DIR)/ml-workers/deployment.yaml; \
	sed -i.bak "s|{{ REGISTRY }}|$(REGISTRY)/$$REGISTRY_ID|g" $(K8S_DIR)/inference-api/deployment.yaml; \
	sed -i.bak "s|{{ REGISTRY }}|$(REGISTRY)/$$REGISTRY_ID|g" $(K8S_DIR)/ml-workers/deployment.yaml; \
	rm -f $(K8S_DIR)/inference-api/*.bak $(K8S_DIR)/ml-workers/*.bak
	@echo "$(GREEN)✅ Манифесты обновлены$(NC)"

deploy-apps: create-secrets update-k8s-manifests ## 🚀 Развернуть API и Workers
	@echo "$(BLUE)🚀 Развёртывание приложений...$(NC)"
	
	@echo "$(YELLOW)🌐 Развёртывание Inference API...$(NC)"
	@kubectl apply -f $(K8S_DIR)/inference-api/
	
	@echo "$(YELLOW)👷 Развёртывание ML Workers...$(NC)"
	@kubectl apply -f $(K8S_DIR)/ml-workers/
	
	@echo "$(GREEN)✅ Приложения развёрнуты$(NC)"
	@$(MAKE) status

# ========================================
# Датасет
# ========================================

copy-dataset: ## 📁 Скопировать датасет из Finalwork
	@echo "$(BLUE)📁 Копирование датасета...$(NC)"
	@if [ -d "../Finalwork/datasets_final" ]; then \
		cp -r ../Finalwork/datasets_final ./datasets_final; \
		echo "$(GREEN)✅ Датасет скопирован в ./datasets_final$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  Датасет ../Finalwork/datasets_final не найден$(NC)"; \
		echo "$(YELLOW)Используйте существующий датасет или укажите другой путь$(NC)"; \
	fi

upload-dataset: ## ☁️  Загрузить датасет в S3
	@echo "$(BLUE)☁️  Загрузка датасета в S3...$(NC)"
	@if [ -x ./scripts/upload_dataset.sh ]; then \
		./scripts/upload_dataset.sh; \
	else \
		echo "$(RED)❌ Скрипт upload_dataset.sh не найден или не исполняемый$(NC)"; \
		exit 1; \
	fi

generate-ssh-key: ## 🔑 Сгенерировать SSH ключ для DataProc
	@echo "$(BLUE)🔑 Генерация SSH ключа...$(NC)"
	@if [ -x ./scripts/generate_ssh_key.sh ]; then \
		./scripts/generate_ssh_key.sh; \
	else \
		echo "$(RED)❌ Скрипт generate_ssh_key.sh не найден$(NC)"; \
		exit 1; \
	fi

setup-airflow: ## 🌬️  Настроить Airflow (загрузить DAG и переменные)
	@echo "$(BLUE)🌬️  Настройка Airflow...$(NC)"
	@if [ -x ./scripts/setup_airflow.sh ]; then \
		./scripts/setup_airflow.sh; \
	else \
		echo "$(RED)❌ Скрипт setup_airflow.sh не найден или не исполняемый$(NC)"; \
		exit 1; \
	fi

wait-for-airflow: ## ⏳ Ожидание готовности Airflow
	@echo "$(BLUE)⏳ Ожидание готовности Airflow...$(NC)"
	@AIRFLOW_URL=$$(cd $(TERRAFORM_DIR) && terraform output -raw airflow_webserver_url 2>/dev/null); \
	if [ -z "$$AIRFLOW_URL" ]; then \
		echo "$(RED)❌ Не удалось получить URL Airflow$(NC)"; \
		exit 1; \
	fi; \
	echo "   Проверка: $$AIRFLOW_URL/health"; \
	MAX_ATTEMPTS=60; \
	ATTEMPT=0; \
	while [ $$ATTEMPT -lt $$MAX_ATTEMPTS ]; do \
		if curl -s -o /dev/null -w "%{http_code}" "$$AIRFLOW_URL/health" | grep -q "200"; then \
			echo "$(GREEN)✅ Airflow готов!$(NC)"; \
			exit 0; \
		fi; \
		ATTEMPT=$$((ATTEMPT + 1)); \
		echo "   Попытка $$ATTEMPT/$$MAX_ATTEMPTS..."; \
		sleep 10; \
	done; \
	echo "$(YELLOW)⚠️  Airflow ещё не готов, но продолжаем...$(NC)"

# ========================================
# Полное развёртывание
# ========================================

deploy-inference: ## 🐟 Развернуть inference стек (API + Frontend) с реальной моделью
	@echo "$(BLUE)🐟 Развёртывание inference стека...$(NC)"
	@if [ -x ./scripts/deploy_real_api.sh ]; then \
		./scripts/deploy_real_api.sh; \
	else \
		echo "$(RED)❌ Скрипт deploy_real_api.sh не найден$(NC)"; \
		exit 1; \
	fi
	@if [ -x ./scripts/deploy_frontend_simple.sh ]; then \
		./scripts/deploy_frontend_simple.sh; \
	else \
		echo "$(RED)❌ Скрипт deploy_frontend_simple.sh не найден$(NC)"; \
		exit 1; \
	fi
	@echo ""
	@echo "$(GREEN)✅ Inference стек развёрнут!$(NC)"
	@echo ""
	@echo "$(BLUE)🌐 Frontend доступен на NodePort:$(NC)"
	@NODE_IP=$$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null); \
	if [ ! -z "$$NODE_IP" ]; then \
		echo "   http://$$NODE_IP:31649"; \
	else \
		echo "   Ошибка получения IP ноды"; \
	fi
	@echo ""
	@echo "$(GREEN)✅ Реальный API с MLflow Model Registry!$(NC)"
	@echo "$(YELLOW)⚠️  API загружает модель из Production stage в MLflow$(NC)"

deploy-all: check-tools generate-ssh-key terraform-apply deploy-k8s copy-dataset upload-dataset setup-airflow wait-for-airflow deploy-inference ## 🎯 ПОЛНОЕ развёртывание системы
	@echo ""
	@echo "$(GREEN)╔════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║  ✅ Система успешно развёрнута!       ║$(NC)"
	@echo "$(GREEN)╚════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)✅ Все компоненты развёрнуты и готовы!$(NC)"
	@echo ""
	@echo "$(BLUE)📊 Что развёрнуто:$(NC)"
	@echo "  ✅ Инфраструктура (Terraform)"
	@echo "  ✅ Kubernetes кластер"
	@echo "  ✅ Redis, Реальный API, Frontend"
	@echo "  ✅ MLflow, Grafana"
	@echo "  ✅ Managed Kafka, PostgreSQL, Airflow"
	@echo ""
	@echo "$(YELLOW)⚠️  ВАЖНО:$(NC)"
	@echo "  1. Зайдите в Airflow и запустите DAG 'fish_classification_training_full'"
	@echo "  2. После обучения модель автоматически перейдёт в Production"
	@echo "  3. Frontend начнёт работать с реальными предсказаниями!"
	@echo ""
	@$(MAKE) print-urls

# ========================================
# Статус и мониторинг
# ========================================

status: ## 📊 Показать статус всех компонентов
	@echo "$(BLUE)📊 Статус системы:$(NC)"
	@echo ""
	@echo "$(YELLOW)=== Kubernetes Pods ===$(NC)"
	@kubectl get pods -n ml-inference 2>/dev/null || echo "Namespace ml-inference не найден"
	@echo ""
	@echo "$(YELLOW)=== Managed Kafka (Yandex Cloud) ===$(NC)"
	@yc managed-kafka cluster list 2>/dev/null || echo "Kafka кластер управляется через Yandex Cloud"
	@echo ""
	@echo "$(YELLOW)=== Kubernetes Services ===$(NC)"
	@kubectl get svc -n ml-inference 2>/dev/null || true
	@echo ""
	@echo "$(YELLOW)=== HPA ===$(NC)"
	@kubectl get hpa -n ml-inference 2>/dev/null || true

logs-api: ## 📜 Логи Inference API
	@kubectl logs -f deployment/fish-api -n ml-inference --tail=100

logs-worker: ## 📜 Логи ML Worker
	@kubectl logs -f deployment/ml-worker -n ml-inference --tail=100

logs-kafka: ## 📜 Информация о Kafka кластере
	@echo "$(BLUE)Kafka развёрнут как Managed Service$(NC)"
	@yc managed-kafka cluster list

print-urls: ## 🔗 Показать URL всех сервисов
	@echo "$(BLUE)🔗 URL сервисов:$(NC)"
	@echo ""
	@echo "$(GREEN)🐟 Frontend (для пользователей):$(NC)"
	@NODE_IP=$$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null); \
	NODEPORT=$$(kubectl get svc frontend -n ml-inference -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null); \
	if [ ! -z "$$NODE_IP" ] && [ ! -z "$$NODEPORT" ]; then \
		echo "   http://$$NODE_IP:$$NODEPORT"; \
		echo "   $(YELLOW)(или любой другой IP ноды с тем же портом)$(NC)"; \
	else \
		echo "   $(YELLOW)⏳ Frontend ещё не развёрнут$(NC)"; \
	fi
	@echo ""
	@echo "$(GREEN)📊 MLflow:$(NC)"
	@cd $(TERRAFORM_DIR) && terraform output -raw mlflow_url 2>/dev/null || echo "   Не развёрнут"
	@echo ""
	@echo "$(GREEN)📈 Grafana:$(NC)"
	@cd $(TERRAFORM_DIR) && terraform output -raw grafana_url 2>/dev/null || echo "   Не развёрнут"
	@echo "   $(YELLOW)Логин:$(NC) admin / admin"
	@echo ""
	@echo "$(GREEN)🌬️  Airflow:$(NC)"
	@AIRFLOW_URL=$$(cd $(TERRAFORM_DIR) && terraform output -raw airflow_webserver_url 2>/dev/null || echo ""); \
	if [ ! -z "$$AIRFLOW_URL" ]; then \
		echo "   $$AIRFLOW_URL"; \
		echo "   $(YELLOW)Логин:$(NC) admin / (см. terraform.tfvars)"; \
	else \
		echo "   Не развёрнут"; \
	fi

# ========================================
# Тестирование
# ========================================

test-api: ## 🧪 Тестировать API
	@echo "$(BLUE)🧪 Тестирование API...$(NC)"
	@API_IP=$$(kubectl get svc fish-api -n ml-inference -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null); \
	if [ -z "$$API_IP" ]; then \
		echo "$(RED)❌ API LoadBalancer не готов$(NC)"; \
		exit 1; \
	fi; \
	echo "$(YELLOW)Health check:$(NC)"; \
	curl -s http://$$API_IP/health | jq .; \
	echo ""; \
	echo "$(YELLOW)Readiness check:$(NC)"; \
	curl -s http://$$API_IP/ready | jq .

# ========================================
# Очистка
# ========================================

clean-k8s: ## 🧹 Удалить все из Kubernetes
	@echo "$(BLUE)🧹 Удаление Kubernetes ресурсов...$(NC)"
	@kubectl delete -f $(K8S_DIR)/ml-workers/ --ignore-not-found=true
	@kubectl delete -f $(K8S_DIR)/inference-api/ --ignore-not-found=true
	@kubectl delete -f $(K8S_DIR)/redis/ --ignore-not-found=true
	@kubectl delete -f $(K8S_DIR)/namespace.yaml --ignore-not-found=true
	@echo "$(BLUE)ℹ️  Kafka (Managed Service) будет удалён через Terraform$(NC)"
	@echo "$(GREEN)✅ Kubernetes ресурсы удалены$(NC)"

destroy: ## 🗑️  ПОЛНОЕ уничтожение инфраструктуры
	@echo "$(RED)🗑️  Уничтожение инфраструктуры...$(NC)"
	@echo "$(YELLOW)⚠️  Это удалит ВСЕ ресурсы!$(NC)"
	@read -p "Продолжить? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(MAKE) clean-k8s; \
		cd $(TERRAFORM_DIR) && terraform destroy -auto-approve; \
		echo "$(GREEN)✅ Инфраструктура удалена$(NC)"; \
	else \
		echo "$(YELLOW)Отменено$(NC)"; \
	fi

clean: ## 🧹 Очистить временные файлы
	@echo "$(BLUE)🧹 Очистка...$(NC)"
	@find . -type f -name "*.bak" -delete
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✅ Очистка завершена$(NC)"

# ========================================
# По умолчанию
# ========================================

.DEFAULT_GOAL := help
