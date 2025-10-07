"""
🐟 Fish Classification API
FastAPI application for real-time and batch fish species classification
"""

import os
import json
import hashlib
import base64
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import redis
import mlflow
import numpy as np
from PIL import Image
import io
from kafka import KafkaProducer

# ========================================
# Configuration
# ========================================

MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC_REQUESTS", "fish-classification-requests")
MODEL_NAME = os.getenv("MODEL_NAME", "fish-classifier-efficientnet-b4")
NUM_CLASSES = int(os.getenv("NUM_CLASSES", 17))
IMAGE_SIZE = int(os.getenv("IMAGE_SIZE", 224))
CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))

# ========================================
# Initialize services
# ========================================

app = FastAPI(
    title="Fish Classification API",
    description="Real-time and batch fish species classification",
    version="1.0.0"
)

# Redis for caching
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Kafka producer for batch processing
kafka_producer = KafkaProducer(
    bootstrap_servers=KAFKA_SERVERS.split(','),
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# MLflow model
mlflow.set_tracking_uri(MLFLOW_URI)
model = None

def load_model():
    """Load latest production model from MLflow"""
    global model
    try:
        model_uri = f"models:/{MODEL_NAME}/Production"
        model = mlflow.pyfunc.load_model(model_uri)
        return True
    except Exception as e:
        print(f"Error loading model: {e}")
        return False

# ========================================
# Pydantic Models
# ========================================

class PredictionResponse(BaseModel):
    species_id: int
    species_name: str
    confidence: float
    processing_time_ms: float
    cached: bool = False

class BatchRequest(BaseModel):
    request_id: str
    image_urls: List[str]

class BatchResponse(BaseModel):
    request_id: str
    status: str
    message: str
    estimated_time_seconds: int

# ========================================
# Helper Functions
# ========================================

def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """Preprocess image for model inference"""
    image = Image.open(io.BytesIO(image_bytes))
    image = image.convert('RGB')
    image = image.resize((IMAGE_SIZE, IMAGE_SIZE))
    img_array = np.array(image) / 255.0
    return np.expand_dims(img_array, axis=0)

def get_image_hash(image_bytes: bytes) -> str:
    """Calculate hash of image for caching"""
    return hashlib.md5(image_bytes).hexdigest()

def get_species_name(species_id: int) -> str:
    """Map species ID to name"""
    species_map = {
        0: "Perca Fluviatilis",
        1: "Perccottus Glenii",
        2: "Esox Lucius",
        3: "Alburnus Alburnus",
        4: "Abramis Brama",
        5: "Carassius Gibelio",
        6: "Squalius Cephalus",
        7: "Scardinius Erythrophthalmus",
        8: "Rutilus Lacustris",
        9: "Rutilus Rutilus",
        10: "Blicca Bjoerkna",
        11: "Gymnocephalus Cernua",
        12: "Leuciscus Idus",
        13: "Sander Lucioperca",
        14: "Leuciscus Baicalensis",
        15: "Gobio Gobio",
        16: "Tinca Tinca"
    }
    return species_map.get(species_id, "Unknown")

# ========================================
# API Endpoints
# ========================================

@app.on_event("startup")
async def startup_event():
    """Initialize model on startup"""
    if not load_model():
        print("Warning: Model not loaded. Will retry on first request.")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model_loaded": model is not None}

@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not ready")
    return {"status": "ready"}

@app.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...)):
    """
    Real-time prediction endpoint with caching
    """
    import time
    start_time = time.time()
    
    # Load model if not loaded
    if model is None:
        if not load_model():
            raise HTTPException(status_code=503, detail="Model not available")
    
    # Read image
    image_bytes = await file.read()
    image_hash = get_image_hash(image_bytes)
    
    # Check cache
    cached_result = redis_client.get(f"prediction:{image_hash}")
    if cached_result:
        result = json.loads(cached_result)
        result['cached'] = True
        result['processing_time_ms'] = (time.time() - start_time) * 1000
        return result
    
    # Preprocess and predict
    try:
        img_array = preprocess_image(image_bytes)
        predictions = model.predict(img_array)
        
        # Get top prediction
        species_id = int(np.argmax(predictions[0]))
        confidence = float(predictions[0][species_id])
        
        result = {
            "species_id": species_id,
            "species_name": get_species_name(species_id),
            "confidence": confidence,
            "processing_time_ms": (time.time() - start_time) * 1000,
            "cached": False
        }
        
        # Cache result
        redis_client.setex(
            f"prediction:{image_hash}",
            CACHE_TTL,
            json.dumps(result)
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@app.post("/batch/predict", response_model=BatchResponse)
async def batch_predict(request: BatchRequest, background_tasks: BackgroundTasks):
    """
    Batch prediction endpoint - sends to Kafka for async processing
    """
    try:
        # Send to Kafka
        message = {
            "request_id": request.request_id,
            "image_urls": request.image_urls,
            "timestamp": datetime.utcnow().isoformat(),
            "num_images": len(request.image_urls)
        }
        
        kafka_producer.send(KAFKA_TOPIC, value=message)
        kafka_producer.flush()
        
        estimated_time = len(request.image_urls) * 2  # 2 sec per image
        
        return BatchResponse(
            request_id=request.request_id,
            status="accepted",
            message=f"Batch request accepted. Processing {len(request.image_urls)} images.",
            estimated_time_seconds=estimated_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch request failed: {str(e)}")

@app.get("/batch/status/{request_id}")
async def get_batch_status(request_id: str):
    """
    Get status of batch prediction request
    """
    # Query results from cache or database
    result_key = f"batch_result:{request_id}"
    result = redis_client.get(result_key)
    
    if result:
        return JSONResponse(content=json.loads(result))
    else:
        return {
            "request_id": request_id,
            "status": "processing",
            "message": "Results not yet available"
        }

@app.get("/metrics")
async def get_metrics():
    """
    Get API metrics (for Prometheus)
    """
    # TODO: Implement proper metrics collection
    return {
        "requests_total": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "avg_response_time_ms": 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
