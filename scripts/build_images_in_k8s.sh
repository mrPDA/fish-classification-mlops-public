#!/bin/bash

# ========================================
# 🐳 Build Docker images in Kubernetes using Kaniko
# ========================================
# Сборка образов БЕЗ Docker daemon

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🐳 Building Docker Images in Kubernetes (Kaniko)      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get configuration
cd terraform
REGISTRY_ID=$(terraform output -raw container_registry_id)
SA_KEY_ID=$(terraform output -raw s3_access_key)
SA_KEY_SECRET=$(terraform output -raw s3_secret_key)
cd ..

echo -e "${GREEN}✅ Registry ID: ${REGISTRY_ID}${NC}"

# Create build namespace
echo -e "${YELLOW}📦 Создание namespace для сборки...${NC}"
kubectl create namespace build 2>/dev/null || echo "Namespace build уже существует"

# Create secret with registry credentials
echo -e "${YELLOW}🔐 Создание секрета для registry...${NC}"

# Создаём docker config для yc registry
mkdir -p /tmp/docker-config
cat > /tmp/docker-config/config.json << EOF
{
  "auths": {
    "cr.yandexcloud.net": {
      "auth": "$(echo -n "json_key:$(yc iam key create --service-account-name terraform-sa --format json 2>/dev/null | base64)" | base64)"
    }
  }
}
EOF

kubectl create secret generic regcred \
  --from-file=config.json=/tmp/docker-config/config.json \
  -n build --dry-run=client -o yaml | kubectl apply -f -

rm -rf /tmp/docker-config

echo -e "${GREEN}✅ Секрет создан${NC}"

# Build API image
echo ""
echo -e "${YELLOW}🔨 Сборка образа API...${NC}"

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: kaniko-api
  namespace: build
spec:
  restartPolicy: Never
  containers:
  - name: kaniko
    image: gcr.io/kaniko-project/executor:latest
    args:
    - "--context=git://github.com/YOUR_REPO/Finalwork_2.git#main"
    - "--context-sub-path=."
    - "--dockerfile=docker/Dockerfile.api"
    - "--destination=cr.yandexcloud.net/${REGISTRY_ID}/fish-classification-api:latest"
    - "--cache=true"
    volumeMounts:
    - name: docker-config
      mountPath: /kaniko/.docker/
  volumes:
  - name: docker-config
    secret:
      secretName: regcred
      items:
      - key: config.json
        path: config.json
EOF

echo -e "${BLUE}⏳ Ожидание завершения сборки API...${NC}"
kubectl wait --for=condition=complete --timeout=600s pod/kaniko-api -n build 2>/dev/null || {
    echo -e "${RED}❌ Сборка API не завершена за 10 минут${NC}"
    kubectl logs kaniko-api -n build --tail=50
    exit 1
}

echo -e "${GREEN}✅ Образ API собран!${NC}"

# Build Frontend image  
echo ""
echo -e "${YELLOW}🔨 Сборка образа Frontend...${NC}"

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: kaniko-frontend
  namespace: build
spec:
  restartPolicy: Never
  containers:
  - name: kaniko
    image: gcr.io/kaniko-project/executor:latest
    args:
    - "--context=git://github.com/YOUR_REPO/Finalwork_2.git#main"
    - "--context-sub-path=frontend"
    - "--dockerfile=Dockerfile"
    - "--destination=cr.yandexcloud.net/${REGISTRY_ID}/fish-classification-frontend:latest"
    - "--cache=true"
    volumeMounts:
    - name: docker-config
      mountPath: /kaniko/.docker/
  volumes:
  - name: docker-config
    secret:
      secretName: regcred
      items:
      - key: config.json
        path: config.json
EOF

echo -e "${BLUE}⏳ Ожидание завершения сборки Frontend...${NC}"
kubectl wait --for=condition=complete --timeout=600s pod/kaniko-frontend -n build 2>/dev/null || {
    echo -e "${RED}❌ Сборка Frontend не завершена за 10 минут${NC}"
    kubectl logs kaniko-frontend -n build --tail=50
    exit 1
}

echo -e "${GREEN}✅ Образ Frontend собран!${NC}"

# Cleanup
echo ""
echo -e "${YELLOW}🧹 Очистка...${NC}"
kubectl delete pod kaniko-api kaniko-frontend -n build 2>/dev/null || true

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ ОБРАЗЫ УСПЕШНО СОБРАНЫ!                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Образы доступны:${NC}"
echo -e "  📦 cr.yandexcloud.net/${REGISTRY_ID}/fish-classification-api:latest"
echo -e "  📦 cr.yandexcloud.net/${REGISTRY_ID}/fish-classification-frontend:latest"
echo ""

