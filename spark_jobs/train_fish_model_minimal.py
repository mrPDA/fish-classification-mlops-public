"""
Минимальный PySpark скрипт для обучения - использует предустановленные пакеты
"""
import os
import sys
import subprocess

# Добавляем ~/.local в PYTHONPATH ПЕРЕД всем остальным
local_site = os.path.expanduser('~/.local/lib/python3.8/site-packages')
if os.path.exists(local_site) and local_site not in sys.path:
    sys.path.insert(0, local_site)

# Приоритет: системные пакеты из conda
conda_site = '/opt/conda/lib/python3.8/site-packages'
if conda_site not in sys.path:
    sys.path.insert(1, conda_site)

print("🔧 Python environment setup complete")
print(f"   sys.path[0] = {sys.path[0]}")
print(f"   sys.path[1] = {sys.path[1]}")

# КРИТИЧНО: Сначала обновляем NumPy до версии совместимой с TensorFlow
print("📦 Upgrading NumPy for TensorFlow compatibility...")
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', '--upgrade', 'numpy==1.24.3'])
if local_site not in sys.path:
    sys.path.insert(0, local_site)

# Теперь импортируем NumPy ПОСЛЕ обновления
import argparse
import numpy as np
import boto3
from PIL import Image
from pyspark.sql import SparkSession
from datetime import datetime
import io

print(f"✅ NumPy: {np.__version__}")
print(f"✅ Boto3: {boto3.__version__}")
print("✅ Pillow: OK")

# Устанавливаем TensorFlow если нужно
try:
    import tensorflow as tf
    print(f"✅ TensorFlow: {tf.__version__}")
except ImportError:
    print("📦 Installing TensorFlow...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', 'tensorflow==2.13.0'])
    # Перезагружаем sys.path после установки
    if local_site not in sys.path:
        sys.path.insert(0, local_site)
    import tensorflow as tf
    print(f"✅ TensorFlow installed: {tf.__version__}")

try:
    import mlflow
    print(f"✅ MLflow: {mlflow.__version__}")
except ImportError:
    print("📦 Installing MLflow...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', 'mlflow==2.9.2'])
    # Перезагружаем sys.path после установки
    if local_site not in sys.path:
        sys.path.insert(0, local_site)
    import mlflow
    print(f"✅ MLflow installed: {mlflow.__version__}")

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('--s3-endpoint', required=True)
parser.add_argument('--s3-bucket', required=True)
parser.add_argument('--s3-access-key', required=True)
parser.add_argument('--s3-secret-key', required=True)
parser.add_argument('--mlflow-tracking-uri', required=True)
parser.add_argument('--mlflow-experiment', required=True)
parser.add_argument('--num-classes', type=int, default=9)
parser.add_argument('--image-size', type=int, default=224)
parser.add_argument('--batch-size', type=int, default=32)
parser.add_argument('--epochs', type=int, default=10)
parser.add_argument('--learning-rate', type=float, default=0.001)
args = parser.parse_args()

# Setup S3 and MLflow
os.environ['AWS_ACCESS_KEY_ID'] = args.s3_access_key
os.environ['AWS_SECRET_ACCESS_KEY'] = args.s3_secret_key
os.environ['MLFLOW_S3_ENDPOINT_URL'] = args.s3_endpoint

# Явно настраиваем boto3 default session для MLflow
boto3.setup_default_session(
    aws_access_key_id=args.s3_access_key,
    aws_secret_access_key=args.s3_secret_key,
    region_name='ru-central1'
)

mlflow.set_tracking_uri(args.mlflow_tracking_uri)
mlflow.set_experiment(args.mlflow_experiment)

print("🚀 Starting Spark...")
spark = SparkSession.builder.appName("FishClassificationTraining").getOrCreate()

# Load data from S3
print(f"📥 Loading dataset from S3: {args.s3_bucket}")
s3 = boto3.client(
    's3',
    endpoint_url=args.s3_endpoint,
    aws_access_key_id=args.s3_access_key,
    aws_secret_access_key=args.s3_secret_key
)

# List classes
fish_classes = []
result = s3.list_objects_v2(Bucket=args.s3_bucket, Prefix='datasets/', Delimiter='/')
if 'CommonPrefixes' in result:
    for prefix in result['CommonPrefixes']:
        class_name = prefix['Prefix'].split('/')[-2]
        if class_name and class_name not in ['datasets', '.DS_Store']:
            fish_classes.append(class_name)

print(f"✅ Found {len(fish_classes)} fish classes: {fish_classes[:5]}...")

# Load images
def load_images_from_s3(bucket, prefix, limit=50):
    images = []
    labels = []
    
    for class_idx, class_name in enumerate(fish_classes):
        class_prefix = f"{prefix}{class_name}/"
        print(f"   Loading class {class_idx + 1}/{len(fish_classes)}: {class_name}")
        
        response = s3.list_objects_v2(Bucket=bucket, Prefix=class_prefix, MaxKeys=limit)
        if 'Contents' not in response:
            continue
        
        for obj in response['Contents']:
            key = obj['Key']
            if not key.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
            
            try:
                img_obj = s3.get_object(Bucket=bucket, Key=key)
                img_data = img_obj['Body'].read()
                img = Image.open(io.BytesIO(img_data)).convert('RGB')
                img = img.resize((args.image_size, args.image_size))
                img_array = tf.keras.preprocessing.image.img_to_array(img)
                img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)
                images.append(img_array)
                labels.append(class_idx)
            except Exception as e:
                print(f"      ⚠️  Failed to load {key}: {e}")
                continue
    
    return np.array(images), np.array(labels)

X, y = load_images_from_s3(args.s3_bucket, 'datasets/', limit=50)
print(f"✅ Loaded {len(X)} images, shape: {X.shape}")

# Split
from sklearn.model_selection import train_test_split
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f"✅ Train: {len(X_train)}, Val: {len(X_val)}")

# Build model
print("🏗️  Building model...")
base_model = tf.keras.applications.MobileNetV2(
    input_shape=(args.image_size, args.image_size, 3),
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

# Train with MLflow
print("🎓 Training...")
with mlflow.start_run(run_name=f"fish_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
    mlflow.log_param("base_model", "MobileNetV2")
    mlflow.log_param("epochs", args.epochs)
    mlflow.log_param("batch_size", args.batch_size)
    mlflow.log_param("learning_rate", args.learning_rate)
    mlflow.log_param("num_classes", len(fish_classes))
    mlflow.log_param("train_samples", len(X_train))
    mlflow.log_param("val_samples", len(X_val))
    
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=args.epochs,
        batch_size=args.batch_size,
        verbose=1
    )
    
    for epoch in range(args.epochs):
        mlflow.log_metric("train_loss", history.history['loss'][epoch], step=epoch)
        mlflow.log_metric("train_accuracy", history.history['accuracy'][epoch], step=epoch)
        mlflow.log_metric("val_loss", history.history['val_loss'][epoch], step=epoch)
        mlflow.log_metric("val_accuracy", history.history['val_accuracy'][epoch], step=epoch)
    
    final_train_acc = history.history['accuracy'][-1]
    final_val_acc = history.history['val_accuracy'][-1]
    
    print(f"\n✅ Training complete!")
    print(f"   Final train accuracy: {final_train_acc:.4f}")
    print(f"   Final val accuracy: {final_val_acc:.4f}")
    
    mlflow.tensorflow.log_model(model, "model")
    mlflow.log_dict({str(i): name for i, name in enumerate(fish_classes)}, "class_names.json")
    
    print(f"✅ Model logged to MLflow: run_id={mlflow.active_run().info.run_id}")
    
    # Регистрация модели в Model Registry и переход в Production
    print("\n" + "=" * 80)
    print("📦 Registering model in MLflow Model Registry...")
    print("=" * 80)
    
    try:
        from mlflow.tracking import MlflowClient
        
        client = MlflowClient()
        model_name = "fish-classifier-efficientnet-b4"
        
        # Получаем информацию о текущем run
        run_id = mlflow.active_run().info.run_id
        model_uri = f"runs:/{run_id}/model"
        
        print(f"   Model URI: {model_uri}")
        print(f"   Model Name: {model_name}")
        
        # Регистрируем новую версию модели
        model_version = mlflow.register_model(
            model_uri=model_uri,
            name=model_name,
            tags={
                "accuracy": f"{final_train_acc:.4f}",
                "val_accuracy": f"{final_val_acc:.4f}",
                "framework": "tensorflow",
                "architecture": "mobilenet-v2",
                "training_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "auto_registered": "true"
            }
        )
        
        print(f"✅ Model registered: {model_name}, version: {model_version.version}")
        
        # Переводим модель в Production
        # Сначала архивируем все предыдущие Production модели
        try:
            production_models = client.get_latest_versions(model_name, stages=["Production"])
            for prod_model in production_models:
                print(f"   Archiving previous Production model version {prod_model.version}")
                client.transition_model_version_stage(
                    name=model_name,
                    version=prod_model.version,
                    stage="Archived",
                    archive_existing_versions=False
                )
        except Exception as e:
            print(f"   No previous Production models to archive: {e}")
        
        # Переводим новую модель в Production
        client.transition_model_version_stage(
            name=model_name,
            version=model_version.version,
            stage="Production",
            archive_existing_versions=True
        )
        
        print(f"✅ Model version {model_version.version} transitioned to Production stage")
        print(f"   Model Registry URL: {mlflow_uri}/#/models/{model_name}")
        
    except Exception as e:
        print(f"⚠️  Warning: Failed to register model in Model Registry: {e}")
        print("   Model artifacts are still logged in MLflow run")
    
    mlflow.end_run()

spark.stop()
print("\n" + "=" * 80)
print("✅ Training completed successfully!")
print("🎯 Model automatically registered and deployed to Production!")
print("=" * 80)
