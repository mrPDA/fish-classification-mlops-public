"""
PySpark скрипт для grid search - тестирование разных архитектур и подбор лучшей модели
"""
import os
import sys

# Приоритет: системные пакеты из conda
conda_site = '/opt/conda/lib/python3.8/site-packages'
if conda_site not in sys.path:
    sys.path.insert(0, conda_site)

print("🔧 Python environment setup complete")
print(f"   sys.path[0] = {sys.path[0]}")

# Импорты
import argparse
import numpy as np
import boto3
from PIL import Image
from pyspark.sql import SparkSession
from datetime import datetime
import io

print(f"✅ NumPy: {np.__version__}")
print(f"✅ Boto3: {boto3.__version__}")
print(f"✅ Pillow: OK")

# Устанавливаем TensorFlow и MLflow если нужно
try:
    import tensorflow as tf
    print(f"✅ TensorFlow: {tf.__version__}")
except ImportError:
    print("📦 Installing TensorFlow...")
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', 'tensorflow==2.13.0'])
    import tensorflow as tf
    print(f"✅ TensorFlow installed: {tf.__version__}")

try:
    import mlflow
    print(f"✅ MLflow: {mlflow.__version__}")
except ImportError:
    print("📦 Installing MLflow...")
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', 'mlflow==2.9.2'])
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
spark = SparkSession.builder.appName("FishClassificationGridSearch").getOrCreate()

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

# Grid search configurations
print("\n" + "="*80)
print("🔍 GRID SEARCH: Testing different model architectures")
print("="*80)

model_configs = [
    {
        'name': 'MobileNetV2',
        'base_model_fn': lambda: tf.keras.applications.MobileNetV2(
            input_shape=(args.image_size, args.image_size, 3),
            include_top=False,
            weights='imagenet'
        ),
        'preprocess_fn': tf.keras.applications.mobilenet_v2.preprocess_input
    },
    {
        'name': 'EfficientNetB0',
        'base_model_fn': lambda: tf.keras.applications.EfficientNetB0(
            input_shape=(args.image_size, args.image_size, 3),
            include_top=False,
            weights='imagenet'
        ),
        'preprocess_fn': tf.keras.applications.efficientnet.preprocess_input
    },
    {
        'name': 'ResNet50V2',
        'base_model_fn': lambda: tf.keras.applications.ResNet50V2(
            input_shape=(args.image_size, args.image_size, 3),
            include_top=False,
            weights='imagenet'
        ),
        'preprocess_fn': tf.keras.applications.resnet_v2.preprocess_input
    },
]

learning_rates = [0.001, 0.0001]
dropout_rates = [0.2, 0.5]

best_val_acc = 0
best_config = None
best_model = None
all_results = []

experiment_count = 0
total_experiments = len(model_configs) * len(learning_rates) * len(dropout_rates)

for model_config in model_configs:
    for lr in learning_rates:
        for dropout in dropout_rates:
            experiment_count += 1
            
            print(f"\n{'='*80}")
            print(f"🧪 Experiment {experiment_count}/{total_experiments}")
            print(f"   Model: {model_config['name']}")
            print(f"   Learning Rate: {lr}")
            print(f"   Dropout: {dropout}")
            print(f"{'='*80}")
            
            # Start MLflow run
            with mlflow.start_run(run_name=f"{model_config['name']}_lr{lr}_dropout{dropout}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
                # Log parameters
                mlflow.log_param("base_model", model_config['name'])
                mlflow.log_param("learning_rate", lr)
                mlflow.log_param("dropout", dropout)
                mlflow.log_param("epochs", args.epochs)
                mlflow.log_param("batch_size", args.batch_size)
                mlflow.log_param("image_size", args.image_size)
                mlflow.log_param("num_classes", len(fish_classes))
                mlflow.log_param("train_samples", len(X_train))
                mlflow.log_param("val_samples", len(X_val))
                
                try:
                    # Build model
                    print("🏗️  Building model...")
                    base_model = model_config['base_model_fn']()
                    base_model.trainable = False
                    
                    model = tf.keras.Sequential([
                        base_model,
                        tf.keras.layers.GlobalAveragePooling2D(),
                        tf.keras.layers.Dropout(dropout),
                        tf.keras.layers.Dense(len(fish_classes), activation='softmax')
                    ])
                    
                    model.compile(
                        optimizer=tf.keras.optimizers.Adam(learning_rate=lr),
                        loss='sparse_categorical_crossentropy',
                        metrics=['accuracy']
                    )
                    
                    print(f"✅ Model built: {model.count_params():,} parameters")
                    mlflow.log_param("total_params", model.count_params())
                    
                    # Train
                    print("🎓 Training...")
                    history = model.fit(
                        X_train, y_train,
                        validation_data=(X_val, y_val),
                        epochs=args.epochs,
                        batch_size=args.batch_size,
                        verbose=0  # Silent training for grid search
                    )
                    
                    # Log metrics
                    for epoch in range(args.epochs):
                        mlflow.log_metric("train_loss", history.history['loss'][epoch], step=epoch)
                        mlflow.log_metric("train_accuracy", history.history['accuracy'][epoch], step=epoch)
                        mlflow.log_metric("val_loss", history.history['val_loss'][epoch], step=epoch)
                        mlflow.log_metric("val_accuracy", history.history['val_accuracy'][epoch], step=epoch)
                    
                    final_train_acc = history.history['accuracy'][-1]
                    final_val_acc = history.history['val_accuracy'][-1]
                    final_train_loss = history.history['loss'][-1]
                    final_val_loss = history.history['val_loss'][-1]
                    
                    mlflow.log_metric("final_train_accuracy", final_train_acc)
                    mlflow.log_metric("final_val_accuracy", final_val_acc)
                    mlflow.log_metric("final_train_loss", final_train_loss)
                    mlflow.log_metric("final_val_loss", final_val_loss)
                    
                    print(f"\n✅ Training complete!")
                    print(f"   Final train accuracy: {final_train_acc:.4f}")
                    print(f"   Final val accuracy: {final_val_acc:.4f}")
                    
                    # Track results
                    result = {
                        'model': model_config['name'],
                        'lr': lr,
                        'dropout': dropout,
                        'val_acc': final_val_acc,
                        'train_acc': final_train_acc,
                        'val_loss': final_val_loss,
                        'run_id': mlflow.active_run().info.run_id
                    }
                    all_results.append(result)
                    
                    # Check if best
                    if final_val_acc > best_val_acc:
                        best_val_acc = final_val_acc
                        best_config = result
                        best_model = model
                        mlflow.set_tag("best_model", "True")
                        print(f"   🌟 NEW BEST MODEL! Val accuracy: {final_val_acc:.4f}")
                    else:
                        mlflow.set_tag("best_model", "False")
                    
                except Exception as e:
                    print(f"   ❌ Training failed: {e}")
                    mlflow.log_param("status", "failed")
                    mlflow.log_param("error", str(e))

# Save best model
print(f"\n{'='*80}")
print("🏆 GRID SEARCH COMPLETE!")
print(f"{'='*80}")
print(f"\n🌟 Best Model Configuration:")
print(f"   Architecture: {best_config['model']}")
print(f"   Learning Rate: {best_config['lr']}")
print(f"   Dropout: {best_config['dropout']}")
print(f"   Validation Accuracy: {best_config['val_acc']:.4f}")
print(f"   MLflow Run ID: {best_config['run_id']}")

# Log best model
print(f"\n💾 Saving best model to MLflow...")
with mlflow.start_run(run_id=best_config['run_id']):
    mlflow.tensorflow.log_model(best_model, "model")
    mlflow.log_dict({str(i): name for i, name in enumerate(fish_classes)}, "class_names.json")
    mlflow.set_tag("grid_search_winner", "True")
    print(f"✅ Best model logged!")

# Summary table
print(f"\n📊 All Results Summary:")
print(f"{'Model':<20} {'LR':<10} {'Dropout':<10} {'Val Acc':<10} {'Train Acc':<10}")
print("-" * 70)
for r in sorted(all_results, key=lambda x: x['val_acc'], reverse=True):
    marker = "🏆" if r == best_config else "  "
    print(f"{marker} {r['model']:<18} {r['lr']:<10.4f} {r['dropout']:<10.2f} {r['val_acc']:<10.4f} {r['train_acc']:<10.4f}")

spark.stop()
print("\n✅ Grid search complete!")

