"""
🐟 ML Worker - Kafka Consumer for Batch Processing
Processes fish classification requests from Kafka queue
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict
import requests

import mlflow
import numpy as np
from PIL import Image
import io
from kafka import KafkaConsumer, KafkaProducer
import psycopg2
from psycopg2.extras import execute_values

# ========================================
# Configuration
# ========================================

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')
KAFKA_TOPIC_REQUESTS = os.getenv("KAFKA_TOPIC_REQUESTS", "fish-classification-requests")
KAFKA_TOPIC_RESULTS = os.getenv("KAFKA_TOPIC_RESULTS", "fish-classification-results")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "ml-workers")
MODEL_NAME = os.getenv("MODEL_NAME", "fish-classifier-efficientnet-b4")
NUM_CLASSES = int(os.getenv("NUM_CLASSES", 17))
IMAGE_SIZE = int(os.getenv("IMAGE_SIZE", 224))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 32))

# PostgreSQL configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
POSTGRES_DB = os.getenv("POSTGRES_DB", "mlops")
POSTGRES_USER = os.getenv("POSTGRES_USER", "mlops_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# ========================================
# Species Mapping
# ========================================

SPECIES_MAP = {
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

# ========================================
# ML Worker Class
# ========================================

class MLWorker:
    def __init__(self):
        self.model = None
        self.consumer = None
        self.producer = None
        self.db_conn = None
        
    def setup(self):
        """Initialize all connections"""
        logger.info("🚀 Starting ML Worker...")
        
        # Load MLflow model
        self._load_model()
        
        # Setup Kafka consumer
        self.consumer = KafkaConsumer(
            KAFKA_TOPIC_REQUESTS,
            bootstrap_servers=KAFKA_SERVERS,
            group_id=KAFKA_GROUP_ID,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        
        # Setup Kafka producer for results
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # Setup PostgreSQL connection
        self._setup_database()
        
        logger.info("✅ ML Worker initialized successfully")
    
    def _load_model(self):
        """Load model from MLflow"""
        try:
            mlflow.set_tracking_uri(MLFLOW_URI)
            model_uri = f"models:/{MODEL_NAME}/Production"
            self.model = mlflow.pyfunc.load_model(model_uri)
            logger.info(f"✅ Model loaded: {MODEL_NAME}")
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            raise
    
    def _setup_database(self):
        """Setup PostgreSQL connection and create tables"""
        try:
            self.db_conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD
            )
            
            # Create table for batch results
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS batch_predictions (
                        id SERIAL PRIMARY KEY,
                        request_id VARCHAR(255) NOT NULL,
                        image_url TEXT NOT NULL,
                        species_id INTEGER NOT NULL,
                        species_name VARCHAR(255) NOT NULL,
                        confidence FLOAT NOT NULL,
                        processing_time_ms FLOAT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_request_id (request_id),
                        INDEX idx_created_at (created_at)
                    )
                """)
                self.db_conn.commit()
            
            logger.info("✅ Database setup complete")
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
            raise
    
    def preprocess_image(self, image_bytes: bytes) -> np.ndarray:
        """Preprocess image for model"""
        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert('RGB')
        image = image.resize((IMAGE_SIZE, IMAGE_SIZE))
        img_array = np.array(image) / 255.0
        return img_array
    
    def download_image(self, url: str) -> bytes:
        """Download image from URL"""
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    
    def predict_batch(self, images: List[np.ndarray]) -> np.ndarray:
        """Run batch prediction"""
        batch = np.array(images)
        predictions = self.model.predict(batch)
        return predictions
    
    def save_results(self, request_id: str, results: List[Dict]):
        """Save results to PostgreSQL"""
        try:
            with self.db_conn.cursor() as cur:
                values = [
                    (
                        request_id,
                        r['image_url'],
                        r['species_id'],
                        r['species_name'],
                        r['confidence'],
                        r['processing_time_ms']
                    )
                    for r in results
                ]
                
                execute_values(
                    cur,
                    """
                    INSERT INTO batch_predictions 
                    (request_id, image_url, species_id, species_name, confidence, processing_time_ms)
                    VALUES %s
                    """,
                    values
                )
                self.db_conn.commit()
            
            logger.info(f"✅ Saved {len(results)} results for request {request_id}")
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")
            self.db_conn.rollback()
    
    def process_message(self, message: Dict):
        """Process single Kafka message"""
        request_id = message['request_id']
        image_urls = message['image_urls']
        
        logger.info(f"📥 Processing batch request: {request_id} ({len(image_urls)} images)")
        
        start_time = datetime.now()
        results = []
        
        # Process in batches
        for i in range(0, len(image_urls), BATCH_SIZE):
            batch_urls = image_urls[i:i+BATCH_SIZE]
            batch_images = []
            batch_metadata = []
            
            # Download and preprocess images
            for url in batch_urls:
                try:
                    img_bytes = self.download_image(url)
                    img_array = self.preprocess_image(img_bytes)
                    batch_images.append(img_array)
                    batch_metadata.append({'url': url, 'success': True})
                except Exception as e:
                    logger.warning(f"⚠️ Failed to process {url}: {e}")
                    batch_metadata.append({'url': url, 'success': False, 'error': str(e)})
            
            # Run batch prediction
            if batch_images:
                predictions = self.predict_batch(batch_images)
                
                # Process results
                for idx, (pred, meta) in enumerate(zip(predictions, batch_metadata)):
                    if meta['success']:
                        species_id = int(np.argmax(pred))
                        confidence = float(pred[species_id])
                        
                        results.append({
                            'image_url': meta['url'],
                            'species_id': species_id,
                            'species_name': SPECIES_MAP.get(species_id, 'Unknown'),
                            'confidence': confidence,
                            'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000
                        })
        
        # Save results to database
        if results:
            self.save_results(request_id, results)
        
        # Send results to Kafka
        result_message = {
            'request_id': request_id,
            'total_images': len(image_urls),
            'successful': len(results),
            'failed': len(image_urls) - len(results),
            'processing_time_seconds': (datetime.now() - start_time).total_seconds(),
            'results': results
        }
        
        self.producer.send(KAFKA_TOPIC_RESULTS, value=result_message)
        self.producer.flush()
        
        logger.info(f"✅ Completed batch request: {request_id} ({len(results)}/{len(image_urls)} successful)")
    
    def run(self):
        """Main worker loop"""
        logger.info("🔄 Starting to consume messages...")
        
        try:
            for message in self.consumer:
                try:
                    self.process_message(message.value)
                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}")
                    
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down worker...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup connections"""
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()
        if self.db_conn:
            self.db_conn.close()
        logger.info("✅ Cleanup complete")

# ========================================
# Main
# ========================================

if __name__ == "__main__":
    worker = MLWorker()
    worker.setup()
    worker.run()
