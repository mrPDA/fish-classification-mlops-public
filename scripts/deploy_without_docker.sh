#!/bin/bash

# ========================================
# 🚀 Deploy без локального Docker
# Использует готовые публичные образы для демонстрации
# ========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🚀 Fish Classification - Deployment без Docker           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Configuration
cd terraform
MLFLOW_IP=$(terraform output -raw mlflow_vm_ip)
KAFKA_BROKERS=$(terraform output -raw kafka_connection_string)
REGISTRY_ID=$(terraform output -raw container_registry_id)
cd ..

echo -e "${GREEN}✅ MLflow IP: ${MLFLOW_IP}${NC}"
echo -e "${GREEN}✅ Kafka: ${KAFKA_BROKERS}${NC}"
echo -e "${GREEN}✅ Registry ID: ${REGISTRY_ID}${NC}"

# Deploy API using Python base image (lightweight alternative)
echo ""
echo -e "${YELLOW}📦 Развёртывание Inference API...${NC}"

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fish-api
  namespace: ml-inference
  labels:
    app: fish-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: fish-api
  template:
    metadata:
      labels:
        app: fish-api
    spec:
      containers:
      - name: api
        image: python:3.11-slim
        command: ["/bin/sh", "-c"]
        args:
          - |
            pip install --no-cache-dir fastapi uvicorn mlflow redis kafka-python pillow numpy && 
            mkdir -p /app && cat > /app/main.py <<'PYEOF'
from fastapi import FastAPI, File, UploadFile
import os

app = FastAPI(title="Fish Classification API (Mock)")

@app.get("/health")
async def health():
    return {"status": "healthy", "model_loaded": True}

@app.get("/ready")
async def ready():
    return {"status": "ready"}

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    # Mock prediction для демонстрации
    import random
    species = ["Perca Fluviatilis", "Esox Lucius", "Abramis Brama"]
    return {
        "species_id": random.randint(0, 16),
        "species_name": random.choice(species),
        "confidence": round(random.uniform(0.7, 0.99), 2),
        "processing_time_ms": random.randint(100, 500),
        "cached": False
    }
PYEOF
            uvicorn main:app --host 0.0.0.0 --port 8000
        ports:
        - containerPort: 8000
        env:
        - name: MLFLOW_TRACKING_URI
          value: "http://${MLFLOW_IP}:5000"
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: fish-api
  namespace: ml-inference
spec:
  selector:
    app: fish-api
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
EOF

echo -e "${GREEN}✅ API развёрнут${NC}"

# Deploy Frontend
echo ""
echo -e "${YELLOW}📦 Развёртывание Frontend...${NC}"

kubectl create configmap frontend-html --from-file=frontend/index.html -n ml-inference --dry-run=client -o yaml | kubectl apply -f -
kubectl create configmap frontend-js --from-file=frontend/app.js -n ml-inference --dry-run=client -o yaml | kubectl apply -f -
kubectl create configmap frontend-nginx --from-file=frontend/nginx.conf -n ml-inference --dry-run=client -o yaml | kubectl apply -f -

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: ml-inference
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
        volumeMounts:
        - name: html
          mountPath: /usr/share/nginx/html/index.html
          subPath: index.html
        - name: js
          mountPath: /usr/share/nginx/html/app.js
          subPath: app.js
        - name: nginx-config
          mountPath: /etc/nginx/conf.d/default.conf
          subPath: nginx.conf
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
      volumes:
      - name: html
        configMap:
          name: frontend-html
      - name: js
        configMap:
          name: frontend-js
      - name: nginx-config
        configMap:
          name: frontend-nginx
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: ml-inference
spec:
  type: LoadBalancer
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
EOF

echo -e "${GREEN}✅ Frontend развёрнут${NC}"

# Wait for deployments
echo ""
echo -e "${YELLOW}⏳ Ожидание готовности подов...${NC}"

kubectl wait --for=condition=available --timeout=300s deployment/fish-api -n ml-inference
kubectl wait --for=condition=available --timeout=300s deployment/frontend -n ml-inference

# Get external IP
echo ""
echo -e "${YELLOW}🌐 Получение внешнего IP...${NC}"

EXTERNAL_IP=""
for i in {1..30}; do
    EXTERNAL_IP=$(kubectl get svc frontend -n ml-inference -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [ ! -z "$EXTERNAL_IP" ]; then
        break
    fi
    echo -n "."
    sleep 5
done

echo ""
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            ✅ РАЗВЁРТЫВАНИЕ ЗАВЕРШЕНО!                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ ! -z "$EXTERNAL_IP" ]; then
    echo -e "${BLUE}🌍 Frontend доступен:${NC}"
    echo -e "   ${GREEN}http://${EXTERNAL_IP}${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  Примечание: Используется MOCK версия API для демонстрации${NC}"
    echo -e "${YELLOW}   Возвращает случайные предсказания${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  Внешний IP ещё не назначен${NC}"
    echo -e "${YELLOW}Проверьте: kubectl get svc frontend -n ml-inference -w${NC}"
fi

echo -e "${BLUE}📊 Полезные команды:${NC}"
echo -e "  Статус:  kubectl get all -n ml-inference"
echo -e "  Логи API: kubectl logs -f -n ml-inference -l app=fish-api"
echo -e "  Логи Frontend: kubectl logs -f -n ml-inference -l app=frontend"
echo ""

