#!/bin/bash

# ========================================
# 🌐 Deploy Frontend (без Docker)
# ========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        🌐 Fish Classification - Frontend Deployment       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Create ConfigMaps with frontend files
echo -e "${YELLOW}📦 Создание ConfigMaps с файлами Frontend...${NC}"

kubectl create configmap frontend-html \
  --from-file=index.html=frontend/index.html \
  -n ml-inference \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap frontend-js \
  --from-file=app.js=frontend/app.js \
  -n ml-inference \
  --dry-run=client -o yaml | kubectl apply -f -

# Create nginx config that proxies to fish-api service
cat > /tmp/nginx.conf <<'EOF'
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Frontend static files
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to fish-api service
    location /api/ {
        proxy_pass http://fish-api.ml-inference.svc.cluster.local:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range' always;
    }
}
EOF

kubectl create configmap frontend-nginx \
  --from-file=default.conf=/tmp/nginx.conf \
  -n ml-inference \
  --dry-run=client -o yaml | kubectl apply -f -

rm /tmp/nginx.conf

echo -e "${GREEN}✅ ConfigMaps созданы${NC}"

# Deploy Frontend
echo -e "${YELLOW}🚀 Развёртывание Frontend...${NC}"

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: ml-inference
  labels:
    app: frontend
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
          name: http
        volumeMounts:
        - name: html
          mountPath: /usr/share/nginx/html/index.html
          subPath: index.html
        - name: js
          mountPath: /usr/share/nginx/html/app.js
          subPath: app.js
        - name: nginx-config
          mountPath: /etc/nginx/conf.d/default.conf
          subPath: default.conf
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
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
  labels:
    app: frontend
spec:
  type: LoadBalancer
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
    name: http
EOF

echo -e "${GREEN}✅ Frontend развёрнут${NC}"

# Wait for deployment
echo -e "${YELLOW}⏳ Ожидание готовности Frontend...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/frontend -n ml-inference

# Get external IP
echo ""
echo -e "${YELLOW}🌐 Получение внешнего IP LoadBalancer...${NC}"
echo -e "${BLUE}Это может занять 1-2 минуты...${NC}"

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
echo -e "${GREEN}║           ✅ FRONTEND РАЗВЁРНУТ И ГОТОВ!                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ ! -z "$EXTERNAL_IP" ]; then
    echo -e "${BLUE}🌍 Frontend доступен по адресу:${NC}"
    echo -e "   ${GREEN}${BOLD}http://${EXTERNAL_IP}${NC}"
    echo ""
    echo -e "${YELLOW}💡 Откройте в браузере и загрузите фото рыбы!${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  Примечание: Используется MOCK версия модели${NC}"
    echo -e "${YELLOW}   Возвращает случайные предсказания для демонстрации UI${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  Внешний IP LoadBalancer ещё не назначен${NC}"
    echo -e "${YELLOW}Дождитесь назначения IP:${NC}"
    echo -e "  ${BLUE}kubectl get svc frontend -n ml-inference -w${NC}"
    echo ""
fi

echo -e "${BLUE}📊 Полезные команды:${NC}"
echo -e "  Статус:  ${GREEN}kubectl get all -n ml-inference${NC}"
echo -e "  Логи:    ${GREEN}kubectl logs -f -n ml-inference -l app=frontend${NC}"
echo -e "  IP:      ${GREEN}kubectl get svc frontend -n ml-inference${NC}"
echo ""

