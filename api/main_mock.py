from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import random
import os

app = FastAPI(title="Fish Classification API (Mock Demo)")

# CORS для frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Список рыб для демонстрации
FISH_SPECIES = [
    "Perca Fluviatilis",
    "Esox Lucius", 
    "Abramis Brama",
    "Cyprinus Carpio",
    "Salmo Trutta",
    "Rutilus Rutilus",
    "Leuciscus Idus",
    "Silurus Glanis"
]

@app.get("/")
async def root():
    return {
        "service": "Fish Classification API",
        "version": "1.0.0-mock",
        "status": "running",
        "note": "DEMO версия с mock предсказаниями"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model_loaded": True,
        "mlflow_uri": os.getenv("MLFLOW_TRACKING_URI", "not set"),
        "mode": "MOCK"
    }

@app.get("/ready")
async def ready():
    return {"status": "ready", "mode": "MOCK"}

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """
    Mock предсказание для демонстрации UI
    В реальной версии здесь загрузка модели из MLflow
    """
    
    # Имитация обработки
    import time
    start = time.time()
    
    # Читаем файл (для валидации)
    contents = await file.read()
    
    processing_time = int((time.time() - start) * 1000)
    
    # Генерируем случайное предсказание
    species_id = random.randint(0, len(FISH_SPECIES) - 1)
    species_name = FISH_SPECIES[species_id]
    confidence = round(random.uniform(0.75, 0.98), 2)
    
    return {
        "species_id": species_id,
        "species_name": species_name,
        "confidence": confidence,
        "processing_time_ms": processing_time,
        "cached": False,
        "mode": "MOCK",
        "note": "Это демонстрационное предсказание"
    }

@app.get("/metrics")
async def metrics():
    return {
        "total_predictions": random.randint(100, 1000),
        "cache_hit_rate": round(random.uniform(0.3, 0.7), 2),
        "avg_processing_time_ms": random.randint(150, 350)
    }

