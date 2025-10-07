#!/bin/bash

# ========================================
# 🚀 Deploy Mock API (без Docker)
# ========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🚀 Fish Classification - Mock API Deployment         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get MLflow IP
cd terraform
MLFLOW_IP=$(terraform output -raw mlflow_vm_ip)
cd ..

echo -e "${GREEN}✅ MLflow IP: ${MLFLOW_IP}${NC}"

# Create ConfigMap with mock API code
echo -e "${YELLOW}📦 Создание ConfigMap с кодом API...${NC}"
kubectl create configmap api-code \
  --from-file=main.py=api/main_mock.py \
  -n ml-inference \
  --dry-run=client -o yaml | kubectl apply -f -

echo -e "${GREEN}✅ ConfigMap создан${NC}"

# Deploy API
echo -e "${YELLOW}🚀 Развёртывание API...${NC}"

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
      initContainers:
      - name: install-deps
        image: python:3.11-slim
        command: ["/bin/sh", "-c"]
        args:
          - |
            pip install --no-cache-dir \
              fastapi==0.104.1 \
              uvicorn[standard]==0.24.0 \
              python-multipart==0.0.6 \
              --target /deps
        volumeMounts:
        - name: deps
          mountPath: /deps
      containers:
      - name: api
        image: python:3.11-slim
        command: ["/bin/sh", "-c"]
        args:
          - |
            export PYTHONPATH=/deps:\$PYTHONPATH && \
            cd /app && \
            python -m uvicorn main:app --host 0.0.0.0 --port 8000
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: MLFLOW_TRACKING_URI
          value: "http://${MLFLOW_IP}:5000"
        - name: PYTHONUNBUFFERED
          value: "1"
        volumeMounts:
        - name: api-code
          mountPath: /app
        - name: deps
          mountPath: /deps
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
      volumes:
      - name: api-code
        configMap:
          name: api-code
      - name: deps
        emptyDir: {}
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
    name: http
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: inference-api
  namespace: ml-inference
spec:
  selector:
    app: fish-api
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  type: ClusterIP
EOF

echo -e "${GREEN}✅ API развёрнут${NC}"

# Wait for deployment
echo -e "${YELLOW}⏳ Ожидание готовности API...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/fish-api -n ml-inference

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ API РАЗВЁРНУТ И ГОТОВ!                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📊 Проверка:${NC}"
echo -e "  Поды:    kubectl get pods -n ml-inference -l app=fish-api"
echo -e "  Логи:    kubectl logs -f -n ml-inference -l app=fish-api"
echo -e "  Сервис:  kubectl get svc fish-api -n ml-inference"
echo ""

