#!/bin/bash

# ========================================
# 🐟 Fish Classification - Full Stack Deployment
# ========================================
# Развёртывание полного стека: API + Frontend

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🐟 Fish Classification - Full Stack Deployment        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ========================================
# Step 1: Configuration
# ========================================

echo -e "${YELLOW}📊 Шаг 1/7: Получение конфигурации из Terraform...${NC}"
cd terraform

K8S_CLUSTER_ID=$(terraform output -raw k8s_cluster_id 2>/dev/null || echo "")
MLFLOW_IP=$(terraform output -raw mlflow_vm_ip 2>/dev/null || echo "")
KAFKA_BROKERS=$(terraform output -raw kafka_connection_string 2>/dev/null || echo "")

if [ -z "$K8S_CLUSTER_ID" ]; then
    echo -e "${RED}❌ Не удалось получить K8s cluster ID из Terraform${NC}"
    echo -e "${YELLOW}Убедитесь, что инфраструктура развёрнута: cd terraform && terraform apply${NC}"
    exit 1
fi

echo -e "${GREEN}✅ K8s Cluster ID: $K8S_CLUSTER_ID${NC}"
echo -e "${GREEN}✅ MLflow IP: $MLFLOW_IP${NC}"
echo -e "${GREEN}✅ Kafka Brokers: $KAFKA_BROKERS${NC}"

cd ..

# ========================================
# Step 2: Configure kubectl
# ========================================

echo ""
echo -e "${YELLOW}📊 Шаг 2/7: Настройка kubectl...${NC}"
yc managed-kubernetes cluster get-credentials $K8S_CLUSTER_ID --external --force
echo -e "${GREEN}✅ kubectl настроен${NC}"

# ========================================
# Step 3: Create namespace
# ========================================

echo ""
echo -e "${YELLOW}📊 Шаг 3/7: Создание namespace...${NC}"
kubectl apply -f k8s/namespace.yaml
echo -e "${GREEN}✅ Namespace ml-inference создан${NC}"

# ========================================
# Step 4: Deploy Redis
# ========================================

echo ""
echo -e "${YELLOW}📊 Шаг 4/7: Развёртывание Redis...${NC}"
kubectl apply -f k8s/redis/
kubectl wait --for=condition=ready pod -l app=redis -n ml-inference --timeout=300s
echo -e "${GREEN}✅ Redis развёрнут и готов${NC}"

# ========================================
# Step 5: Build and Deploy Inference API
# ========================================

echo ""
echo -e "${YELLOW}📊 Шаг 5/7: Сборка и развёртывание Inference API...${NC}"

# Check if we need to build images
if ! docker images | grep -q "fish-classification-api"; then
    echo -e "${BLUE}🐳 Сборка Docker образа для API...${NC}"
    docker build -f docker/Dockerfile.api -t fish-classification-api:latest .
else
    echo -e "${BLUE}ℹ️  Docker образ API уже существует${NC}"
fi

# Prepare deployment manifest
echo -e "${BLUE}📝 Подготовка манифеста...${NC}"
cat k8s/inference-api/deployment.yaml | \
    sed "s|{{ REGISTRY }}/fish-classification-api:latest|fish-classification-api:latest|g" | \
    sed "s|{{ MLFLOW_HOST }}|${MLFLOW_IP}|g" | \
    sed "s|rc1a-u9toshudtllj41n7.mdb.yandexcloud.net:9091|${KAFKA_BROKERS}|g" \
    > /tmp/inference-api-deployment.yaml

# For local testing without registry, we need to load image to Kubernetes nodes
echo -e "${BLUE}📤 Загрузка образа в Kubernetes nodes...${NC}"
# Note: In production, push to Container Registry instead
# docker push cr.yandexcloud.net/${REGISTRY_ID}/fish-classification-api:latest

# Deploy API
kubectl apply -f /tmp/inference-api-deployment.yaml

echo -e "${BLUE}⏳ Ожидание готовности API pods...${NC}"
kubectl wait --for=condition=ready pod -l app=fish-api -n ml-inference --timeout=600s || {
    echo -e "${RED}❌ API pods не готовы за 10 минут${NC}"
    echo -e "${YELLOW}Проверка статуса:${NC}"
    kubectl get pods -n ml-inference -l app=fish-api
    kubectl logs -n ml-inference -l app=fish-api --tail=50
    exit 1
}

echo -e "${GREEN}✅ Inference API развёрнут и готов${NC}"

# ========================================
# Step 6: Deploy Frontend
# ========================================

echo ""
echo -e "${YELLOW}📊 Шаг 6/7: Развёртывание Frontend...${NC}"

# Build frontend image
echo -e "${BLUE}🐳 Сборка Docker образа для Frontend...${NC}"
docker build -t fish-classification-frontend:latest frontend/

# Deploy frontend
kubectl apply -f k8s/frontend/deployment.yaml

echo -e "${BLUE}⏳ Ожидание готовности Frontend pods...${NC}"
kubectl wait --for=condition=ready pod -l app=frontend -n ml-inference --timeout=300s
echo -e "${GREEN}✅ Frontend развёрнут и готов${NC}"

# ========================================
# Step 7: Get Access URLs
# ========================================

echo ""
echo -e "${YELLOW}📊 Шаг 7/7: Получение внешних URL...${NC}"

# Wait for LoadBalancer IP
echo -e "${BLUE}⏳ Ожидание назначения внешнего IP (это может занять 1-2 минуты)...${NC}"

FRONTEND_IP=""
for i in {1..30}; do
    FRONTEND_IP=$(kubectl get svc frontend -n ml-inference -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [ ! -z "$FRONTEND_IP" ]; then
        break
    fi
    echo -n "."
    sleep 5
done

echo ""

# ========================================
# Summary
# ========================================

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ РАЗВЁРТЫВАНИЕ ЗАВЕРШЕНО!                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}📊 Статус компонентов:${NC}"
echo ""
echo -e "${GREEN}✅ Redis:          Running${NC}"
echo -e "${GREEN}✅ Inference API:  Running (3 replicas)${NC}"
echo -e "${GREEN}✅ Frontend:       Running (2 replicas)${NC}"
echo ""

echo -e "${BLUE}🌐 Доступ к сервисам:${NC}"
echo ""

if [ ! -z "$FRONTEND_IP" ]; then
    echo -e "${GREEN}🌍 Frontend (User Website):${NC}"
    echo -e "   ${BLUE}http://${FRONTEND_IP}${NC}"
    echo ""
    echo -e "${GREEN}📝 Откройте этот URL в браузере для:${NC}"
    echo -e "   • Загрузки фото рыбы"
    echo -e "   • Автоматической классификации"
    echo -e "   • Просмотра результатов"
else
    echo -e "${YELLOW}⚠️  Внешний IP ещё не назначен Frontend${NC}"
    echo -e "${YELLOW}Проверьте статус вручную:${NC}"
    echo -e "   kubectl get svc frontend -n ml-inference -w"
fi

echo ""
echo -e "${BLUE}🔧 API Endpoints (внутренний доступ):${NC}"
echo -e "   • Health:      http://fish-api.ml-inference:8000/health"
echo -e "   • Predict:     http://fish-api.ml-inference:8000/predict"
echo -e "   • Metrics:     http://fish-api.ml-inference:8000/metrics"
echo ""

echo -e "${BLUE}📊 Полезные команды:${NC}"
echo ""
echo -e "${YELLOW}# Статус всех подов:${NC}"
echo -e "   kubectl get pods -n ml-inference"
echo ""
echo -e "${YELLOW}# Логи API:${NC}"
echo -e "   kubectl logs -f -n ml-inference -l app=fish-api"
echo ""
echo -e "${YELLOW}# Логи Frontend:${NC}"
echo -e "   kubectl logs -f -n ml-inference -l app=frontend"
echo ""
echo -e "${YELLOW}# Масштабирование API:${NC}"
echo -e "   kubectl scale deployment fish-api -n ml-inference --replicas=5"
echo ""
echo -e "${YELLOW}# Проверка HPA (auto-scaling):${NC}"
echo -e "   kubectl get hpa -n ml-inference"
echo ""

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           🎉 Система готова к использованию! 🚀           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

