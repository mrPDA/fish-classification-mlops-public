#!/bin/bash

# ========================================
# 🐟 Fish Classification - Frontend Deployment
# ========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Развёртывание Frontend для Fish Classification${NC}"
echo ""

# Get configuration from Terraform outputs
cd terraform
echo -e "${YELLOW}📊 Получение конфигурации из Terraform...${NC}"

K8S_CLUSTER_ID=$(terraform output -raw k8s_cluster_id)
REGISTRY_ID=$(terraform output -raw container_registry_id 2>/dev/null || echo "")

cd ..

# Configure kubectl
echo -e "${YELLOW}⚙️  Настройка kubectl...${NC}"
yc managed-kubernetes cluster get-credentials $K8S_CLUSTER_ID --external --force

# Build Docker image
echo -e "${YELLOW}🐳 Сборка Docker образа...${NC}"

if [ -z "$REGISTRY_ID" ]; then
    echo -e "${RED}❌ Container Registry ID не найден в Terraform outputs${NC}"
    echo -e "${YELLOW}Использую локальную сборку образа...${NC}"
    FRONTEND_IMAGE="fish-classification-frontend:latest"
else
    FRONTEND_IMAGE="cr.yandexcloud.net/${REGISTRY_ID}/fish-classification-frontend:latest"
fi

docker build -t $FRONTEND_IMAGE frontend/

# Push to registry if using Yandex Container Registry
if [ ! -z "$REGISTRY_ID" ]; then
    echo -e "${YELLOW}📤 Отправка образа в Container Registry...${NC}"
    docker push $FRONTEND_IMAGE
fi

# Update K8s manifest with correct image
echo -e "${YELLOW}📝 Обновление Kubernetes манифестов...${NC}"

# Create temporary manifest with correct image
cat k8s/frontend/deployment.yaml | \
    sed "s|cr.yandexcloud.net/YOUR_REGISTRY_ID/fish-classification-frontend:latest|${FRONTEND_IMAGE}|g" \
    > /tmp/frontend-deployment.yaml

# Deploy to Kubernetes
echo -e "${YELLOW}🚢 Развёртывание в Kubernetes...${NC}"
kubectl apply -f /tmp/frontend-deployment.yaml

# Wait for deployment
echo -e "${YELLOW}⏳ Ожидание развёртывания...${NC}"
kubectl rollout status deployment/frontend -n ml-inference --timeout=5m

# Get service endpoint
echo ""
echo -e "${GREEN}✅ Frontend успешно развёрнут!${NC}"
echo ""

# Get LoadBalancer IP
echo -e "${YELLOW}🌐 Получение внешнего IP адреса...${NC}"
echo -e "${BLUE}Ожидание назначения внешнего IP (это может занять 1-2 минуты)...${NC}"

for i in {1..30}; do
    EXTERNAL_IP=$(kubectl get svc frontend -n ml-inference -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [ ! -z "$EXTERNAL_IP" ]; then
        break
    fi
    echo -n "."
    sleep 5
done

echo ""

if [ -z "$EXTERNAL_IP" ]; then
    echo -e "${YELLOW}⚠️  Внешний IP ещё не назначен${NC}"
    echo -e "${YELLOW}Проверьте статус вручную:${NC}"
    echo -e "  kubectl get svc frontend -n ml-inference -w"
else
    echo -e "${GREEN}✅ Frontend доступен по адресу:${NC}"
    echo ""
    echo -e "${BLUE}🌍  http://${EXTERNAL_IP}${NC}"
    echo ""
    echo -e "${GREEN}Откройте этот адрес в браузере для доступа к веб-интерфейсу!${NC}"
fi

# Show pod status
echo ""
echo -e "${YELLOW}📊 Статус подов:${NC}"
kubectl get pods -n ml-inference -l app=frontend

# Show service details
echo ""
echo -e "${YELLOW}🔗 Детали сервиса:${NC}"
kubectl get svc frontend -n ml-inference

echo ""
echo -e "${GREEN}✅ Развёртывание завершено!${NC}"
echo ""
echo -e "${BLUE}📝 Полезные команды:${NC}"
echo -e "  Логи:         kubectl logs -f -n ml-inference -l app=frontend"
echo -e "  Статус:       kubectl get all -n ml-inference -l app=frontend"
echo -e "  Масштаб:      kubectl scale deployment frontend -n ml-inference --replicas=3"
echo -e "  Удалить:      kubectl delete -f k8s/frontend/"
echo ""

