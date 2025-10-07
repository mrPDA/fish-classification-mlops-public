#!/bin/bash

# ========================================
# 🚀 Deploy Real API (with MLflow model loading)
# Использует ConfigMap и init container для установки зависимостей
# ========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🚀 Fish Classification - Real API Deployment         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get MLflow IP
cd terraform
MLFLOW_IP=$(terraform output -raw mlflow_vm_ip 2>/dev/null || echo "10.11.0.22")
KAFKA_BROKERS=$(terraform output -raw kafka_connection_string 2>/dev/null || echo "localhost:9092")
cd ..

echo -e "${GREEN}✅ MLflow IP: ${MLFLOW_IP}${NC}"
echo -e "${GREEN}✅ Kafka: ${KAFKA_BROKERS}${NC}"

# Create ConfigMap with real API code
echo -e "${YELLOW}📦 Создание ConfigMap с кодом реального API...${NC}"

# Обновляем api/main.py чтобы использовать правильные переменные окружения
cat > /tmp/api_real.py <<'PYEOF'
"""
🐟 Fish Classification API - Production version with MLflow Model Registry
"""
import os
import json
import hashlib
import time
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import mlflow
import numpy as np
from PIL import Image
import io

# Configuration
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
MODEL_NAME = os.getenv("MODEL_NAME", "fish-classifier-efficientnet-b4")
IMAGE_SIZE = int(os.getenv("IMAGE_SIZE", 224))
CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))

app = FastAPI(
    title="Fish Classification API",
    description="Real-time fish species classification with MLflow",
    version="2.0.0"
)

# CORS для frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis for caching
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False, socket_connect_timeout=2)
    redis_client.ping()
    print(f"✅ Redis connected: {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    print(f"⚠️  Redis not available: {e}")
    redis_client = None

# MLflow model
mlflow.set_tracking_uri(MLFLOW_URI)
model = None
model_version = None

def load_model():
    """Load latest production model from MLflow Model Registry"""
    global model, model_version
    try:
        print(f"🔄 Loading model from MLflow: {MLFLOW_URI}")
        print(f"   Model: {MODEL_NAME}/Production")
        
        model_uri = f"models:/{MODEL_NAME}/Production"
        model = mlflow.pyfunc.load_model(model_uri)
        
        # Get model version info
        from mlflow.tracking import MlflowClient
        client = MlflowClient()
        prod_models = client.get_latest_versions(MODEL_NAME, stages=["Production"])
        if prod_models:
            model_version = prod_models[0].version
            print(f"✅ Model loaded: version {model_version}")
        else:
            print("✅ Model loaded (version unknown)")
        
        return True
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        print(f"   MLflow URI: {MLFLOW_URI}")
        print(f"   Model: {MODEL_NAME}")
        return False

class PredictionResponse(BaseModel):
    species_id: int
    species_name: str
    confidence: float
    processing_time_ms: float
    cached: bool = False
    model_version: Optional[str] = None

def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """Preprocess image for model inference"""
    image = Image.open(io.BytesIO(image_bytes))
    image = image.convert('RGB')
    image = image.resize((IMAGE_SIZE, IMAGE_SIZE))
    image_array = np.array(image) / 255.0
    return np.expand_dims(image_array, axis=0)

def get_image_hash(image_bytes: bytes) -> str:
    """Generate hash for image caching"""
    return hashlib.md5(image_bytes).hexdigest()

# Species names mapping
FISH_SPECIES = [
    "Abramis Brama",
    "Alburnus Alburnus", 
    "Barbus Barbus",
    "Carassius Carassius",
    "Cyprinus Carpio",
    "Esox Lucius",
    "Gobio Gobio",
    "Leuciscus Idus",
    "Perca Fluviatilis",
    "Rutilus Rutilus",
    "Salmo Trutta",
    "Scardinius Erythrophthalmus",
    "Silurus Glanis",
    "Squalius Cephalus",
    "Tinca Tinca",
    "Vimba Vimba",
    "Unknown"
]

@app.on_event("startup")
async def startup_event():
    """Initialize model on startup"""
    print("🚀 Starting Fish Classification API...")
    if not load_model():
        print("⚠️  Warning: Model not loaded. Will retry on first request.")

@app.get("/")
async def root():
    return {
        "service": "Fish Classification API",
        "version": "2.0.0",
        "status": "running",
        "model_loaded": model is not None,
        "model_version": model_version,
        "mlflow_uri": MLFLOW_URI
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_version": model_version,
        "redis_available": redis_client is not None,
        "mlflow_uri": MLFLOW_URI
    }

@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {
        "status": "ready",
        "model_version": model_version
    }

@app.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...)):
    """
    Predict fish species from uploaded image
    """
    start_time = time.time()
    
    # Load model if not loaded
    if model is None:
        print("🔄 Model not loaded, attempting to load...")
        if not load_model():
            raise HTTPException(status_code=503, detail="Model not available")
    
    # Read image
    image_bytes = await file.read()
    image_hash = get_image_hash(image_bytes)
    
    # Check cache
    cached = False
    if redis_client:
        try:
            cached_result = redis_client.get(f"prediction:{image_hash}")
            if cached_result:
                result = json.loads(cached_result)
                result['cached'] = True
                result['processing_time_ms'] = (time.time() - start_time) * 1000
                return PredictionResponse(**result)
        except Exception as e:
            print(f"⚠️  Cache read error: {e}")
    
    # Preprocess
    try:
        image_array = preprocess_image(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")
    
    # Predict
    try:
        prediction = model.predict(image_array)
        
        # Handle different output formats
        if isinstance(prediction, dict):
            probs = prediction.get('predictions', prediction.get('output', prediction))
        else:
            probs = prediction
        
        if len(probs.shape) > 1:
            probs = probs[0]
        
        species_id = int(np.argmax(probs))
        confidence = float(probs[species_id])
        
        # Ensure species_id is within bounds
        if species_id >= len(FISH_SPECIES):
            species_id = len(FISH_SPECIES) - 1  # Unknown
        
        species_name = FISH_SPECIES[species_id]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {e}")
    
    processing_time = (time.time() - start_time) * 1000
    
    result = {
        "species_id": species_id,
        "species_name": species_name,
        "confidence": confidence,
        "processing_time_ms": processing_time,
        "cached": cached,
        "model_version": model_version
    }
    
    # Cache result
    if redis_client and not cached:
        try:
            redis_client.setex(
                f"prediction:{image_hash}",
                CACHE_TTL,
                json.dumps(result)
            )
        except Exception as e:
            print(f"⚠️  Cache write error: {e}")
    
    return PredictionResponse(**result)

@app.get("/metrics")
async def metrics():
    """Simple metrics endpoint"""
    cache_info = {"available": False}
    if redis_client:
        try:
            info = redis_client.info()
            cache_info = {
                "available": True,
                "used_memory": info.get('used_memory_human', 'N/A'),
                "connected_clients": info.get('connected_clients', 0)
            }
        except:
            pass
    
    return {
        "model_loaded": model is not None,
        "model_version": model_version,
        "model_name": MODEL_NAME,
        "mlflow_uri": MLFLOW_URI,
        "cache": cache_info
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
PYEOF

kubectl create configmap real-api-code \
  --from-file=main.py=/tmp/api_real.py \
  -n ml-inference \
  --dry-run=client -o yaml | kubectl apply -f -

rm /tmp/api_real.py

echo -e "${GREEN}✅ ConfigMap создан${NC}"

# Deploy Real API
echo -e "${YELLOW}🚀 Развёртывание реального API...${NC}"

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fish-api
  namespace: ml-inference
  labels:
    app: fish-api
    version: v2
spec:
  replicas: 2
  selector:
    matchLabels:
      app: fish-api
  template:
    metadata:
      labels:
        app: fish-api
        version: v2
    spec:
      initContainers:
      - name: install-deps
        image: python:3.11-slim
        command: ["/bin/sh", "-c"]
        args:
          - |
            echo "📦 Installing dependencies..."
            pip install --no-cache-dir --target /deps \
              tensorflow==2.13.0 \
              typing-extensions==4.5.0 \
              fastapi==0.100.0 \
              uvicorn[standard]==0.23.0 \
              python-multipart==0.0.6 \
              mlflow==2.9.2 \
              redis==5.0.1 \
              pillow==10.1.0 \
              numpy==1.24.3 \
              boto3==1.28.85
            echo "✅ Dependencies installed"
        volumeMounts:
        - name: deps
          mountPath: /deps
      containers:
      - name: api
        image: python:3.11-slim
        command: ["/bin/sh", "-c"]
        args:
          - |
            export PYTHONPATH=/deps:\$PYTHONPATH
            cd /app
            python -m uvicorn main:app --host 0.0.0.0 --port 8000
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: MLFLOW_TRACKING_URI
          value: "http://${MLFLOW_IP}:5000"
        - name: REDIS_HOST
          value: "redis"
        - name: REDIS_PORT
          value: "6379"
        - name: MODEL_NAME
          value: "fish-classifier-efficientnet-b4"
        - name: IMAGE_SIZE
          value: "224"
        - name: CACHE_TTL
          value: "3600"
        - name: PYTHONUNBUFFERED
          value: "1"
        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: s3-credentials
              key: access_key
        - name: AWS_SECRET_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: s3-credentials
              key: secret_key
        - name: MLFLOW_S3_ENDPOINT_URL
          value: "https://storage.yandexcloud.net"
        volumeMounts:
        - name: api-code
          mountPath: /app
        - name: deps
          mountPath: /deps
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 10
          timeoutSeconds: 5
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 45
          periodSeconds: 5
          timeoutSeconds: 3
      volumes:
      - name: api-code
        configMap:
          name: real-api-code
      - name: deps
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: fish-api
  namespace: ml-inference
  labels:
    app: fish-api
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
  labels:
    app: fish-api
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
echo -e "${YELLOW}⏳ Ожидание готовности API (может занять 2-3 минуты)...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/fish-api -n ml-inference || true

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ РЕАЛЬНЫЙ API РАЗВЁРНУТ!                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📊 Проверка:${NC}"
echo -e "  Поды:    kubectl get pods -n ml-inference -l app=fish-api"
echo -e "  Логи:    kubectl logs -f -n ml-inference -l app=fish-api"
echo -e "  Сервис:  kubectl get svc fish-api -n ml-inference"
echo ""
echo -e "${YELLOW}⚠️  Важно:${NC}"
echo -e "  API загружает модель из MLflow Model Registry"
echo -e "  Убедитесь что модель зарегистрирована в Production stage!"
echo ""

