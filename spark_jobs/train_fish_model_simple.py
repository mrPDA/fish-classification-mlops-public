"""
PySpark скрипт для обучения модели классификации рыб с использованием Transfer Learning и MLflow
Упрощённая версия - предполагает, что все зависимости установлены через initialization script
"""

import os
import sys
import argparse
from datetime import datetime

print("🔧 Setting up Python environment...")

# Ensure user-local packages are prioritized
user_site = '/home/dataproc-agent/.local/lib/python3.8/site-packages'
while user_site in sys.path:
    sys.path.remove(user_site)
sys.path.insert(0, user_site)

print(f"✅ Python path configured, user_site: {user_site}")

# Install TensorFlow and MLflow if not available
print("📦 Checking and installing ML dependencies...")

import subprocess

def safe_install(*packages):
    """Install packages with pip, handling errors gracefully"""
    for pkg in packages:
        try:
            print(f"   Installing {pkg}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', pkg])
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Warning: Failed to install {pkg}, continuing...")

# Check and install TensorFlow
try:
    import tensorflow as tf
    print(f"✅ TensorFlow: {tf.__version__}")
except ImportError:
    print("⚠️  TensorFlow not found, installing...")
    # Install TensorFlow with dependencies (simplified approach)
    safe_install('tensorflow==2.13.0')
    # Clear any cached imports and try again
    import importlib
    import sys
    if 'tensorflow' in sys.modules:
        del sys.modules['tensorflow']
    import tensorflow as tf
    print(f"✅ TensorFlow installed: {tf.__version__}")

# Check and install MLflow
try:
    import mlflow
    print(f"✅ MLflow: {mlflow.__version__}")
except ImportError:
    print("⚠️  MLflow not found, installing...")
    safe_install('mlflow==2.9.2')
    # Clear any cached imports and try again
    import importlib
    import sys
    if 'mlflow' in sys.modules:
        del sys.modules['mlflow']
    import mlflow
    print(f"✅ MLflow installed: {mlflow.__version__}")

# Verify NumPy
import numpy as np
print(f"✅ NumPy: {np.__version__} from {np.__file__}")

# Rest of imports
from pyspark.sql import SparkSession
import boto3
from PIL import Image
import io

# Parse arguments
parser = argparse.ArgumentParser(description='Train fish classification model with Transfer Learning')
parser.add_argument('--data-bucket', required=True, help='S3 bucket with dataset')
parser.add_argument('--mlflow-tracking-uri', required=True, help='MLflow tracking server URI')
parser.add_argument('--aws-access-key-id', required=True, help='AWS Access Key ID')
parser.add_argument('--aws-secret-access-key', required=True, help='AWS Secret Access Key')
parser.add_argument('--epochs', type=int, default=5, help='Number of training epochs')
parser.add_argument('--batch-size', type=int, default=32, help='Batch size')
parser.add_argument('--learning-rate', type=float, default=0.001, help='Learning rate')

args = parser.parse_args()

# Set up AWS credentials
os.environ['AWS_ACCESS_KEY_ID'] = args.aws_access_key_id
os.environ['AWS_SECRET_ACCESS_KEY'] = args.aws_secret_access_key

# Set up MLflow
mlflow.set_tracking_uri(args.mlflow_tracking_uri)
mlflow.set_experiment("fish-classification-training")

print("🚀 Starting PySpark session...")

# Initialize Spark
spark = SparkSession.builder \
    .appName("FishClassificationTraining") \
    .config("spark.driver.memory", "4g") \
    .config("spark.executor.memory", "4g") \
    .getOrCreate()

print("✅ Spark session initialized")

# ============ DATA LOADING ============
print(f"📥 Loading dataset from S3: {args.data_bucket}")

s3 = boto3.client('s3')

# List dataset structure
fish_classes = []
try:
    result = s3.list_objects_v2(Bucket=args.data_bucket, Prefix='Fish_Dataset/Fish_Dataset/', Delimiter='/')
    if 'CommonPrefixes' in result:
        for prefix in result['CommonPrefixes']:
            class_name = prefix['Prefix'].split('/')[-2]
            if class_name and class_name not in ['Fish_Dataset', '.DS_Store']:
                fish_classes.append(class_name)
    
    print(f"✅ Found {len(fish_classes)} fish classes: {fish_classes[:5]}...")
except Exception as e:
    print(f"❌ Error listing S3 objects: {e}")
    spark.stop()
    sys.exit(1)

if not fish_classes:
    print("❌ No fish classes found in dataset!")
    spark.stop()
    sys.exit(1)

# ============ LOAD AND PREPROCESS IMAGES ============
print("📸 Loading and preprocessing images...")

def load_images_from_s3(bucket, prefix, limit=50):
    """Load images from S3 with limit per class"""
    images = []
    labels = []
    
    for class_idx, class_name in enumerate(fish_classes):
        class_prefix = f"{prefix}{class_name}/"
        print(f"   Loading class {class_idx + 1}/{len(fish_classes)}: {class_name}")
        
        try:
            response = s3.list_objects_v2(Bucket=bucket, Prefix=class_prefix, MaxKeys=limit)
            if 'Contents' not in response:
                continue
            
            for obj in response['Contents']:
                key = obj['Key']
                if not key.lower().endswith(('.png', '.jpg', '.jpeg')):
                    continue
                
                try:
                    # Download image
                    img_obj = s3.get_object(Bucket=bucket, Key=key)
                    img_data = img_obj['Body'].read()
                    
                    # Open and resize image
                    img = Image.open(io.BytesIO(img_data)).convert('RGB')
                    img = img.resize((224, 224))
                    
                    # Convert to array and normalize
                    img_array = tf.keras.preprocessing.image.img_to_array(img)
                    img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)
                    
                    images.append(img_array)
                    labels.append(class_idx)
                    
                except Exception as e:
                    print(f"      ⚠️  Failed to load image {key}: {e}")
                    continue
        
        except Exception as e:
            print(f"   ⚠️  Error loading class {class_name}: {e}")
            continue
    
    return np.array(images), np.array(labels)

# Load images
X, y = load_images_from_s3(args.data_bucket, 'Fish_Dataset/Fish_Dataset/', limit=50)

print(f"✅ Loaded {len(X)} images")
print(f"   Shape: {X.shape}")
print(f"   Classes: {len(fish_classes)}")

if len(X) == 0:
    print("❌ No images loaded!")
    spark.stop()
    sys.exit(1)

# Split train/val
from sklearn.model_selection import train_test_split
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

print(f"✅ Train set: {len(X_train)} images")
print(f"✅ Val set: {len(X_val)} images")

# ============ BUILD MODEL ============
print("🏗️  Building Transfer Learning model...")

base_model = tf.keras.applications.MobileNetV2(
    input_shape=(224, 224, 3),
    include_top=False,
    weights='imagenet'
)
base_model.trainable = False

model = tf.keras.Sequential([
    base_model,
    tf.keras.layers.GlobalAveragePooling2D(),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.Dense(len(fish_classes), activation='softmax')
])

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=args.learning_rate),
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

print(f"✅ Model built: {model.count_params():,} parameters")

# ============ TRAINING WITH MLFLOW ============
print("🎓 Starting training with MLflow tracking...")

with mlflow.start_run(run_name=f"fish_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
    # Log parameters
    mlflow.log_param("base_model", "MobileNetV2")
    mlflow.log_param("epochs", args.epochs)
    mlflow.log_param("batch_size", args.batch_size)
    mlflow.log_param("learning_rate", args.learning_rate)
    mlflow.log_param("num_classes", len(fish_classes))
    mlflow.log_param("train_samples", len(X_train))
    mlflow.log_param("val_samples", len(X_val))
    
    # Train model
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=args.epochs,
        batch_size=args.batch_size,
        verbose=1
    )
    
    # Log metrics
    for epoch in range(args.epochs):
        mlflow.log_metric("train_loss", history.history['loss'][epoch], step=epoch)
        mlflow.log_metric("train_accuracy", history.history['accuracy'][epoch], step=epoch)
        mlflow.log_metric("val_loss", history.history['val_loss'][epoch], step=epoch)
        mlflow.log_metric("val_accuracy", history.history['val_accuracy'][epoch], step=epoch)
    
    # Final metrics
    final_train_acc = history.history['accuracy'][-1]
    final_val_acc = history.history['val_accuracy'][-1]
    
    print(f"\n✅ Training complete!")
    print(f"   Final train accuracy: {final_train_acc:.4f}")
    print(f"   Final val accuracy: {final_val_acc:.4f}")
    
    # Log model
    print("💾 Saving model to MLflow...")
    mlflow.keras.log_model(model, "model")
    
    # Save class names
    class_names_dict = {str(i): name for i, name in enumerate(fish_classes)}
    mlflow.log_dict(class_names_dict, "class_names.json")
    
    print(f"✅ Model logged to MLflow: run_id={mlflow.active_run().info.run_id}")

# Cleanup
spark.stop()
print("✅ Training complete!")

