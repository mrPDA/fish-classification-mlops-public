"""
PySpark скрипт для обучения модели классификации рыб с использованием Transfer Learning и MLflow
"""

import os
import sys
import subprocess
import argparse
import shutil
from datetime import datetime

# === ПРОВЕРКА ЗАВИСИМОСТЕЙ ===
# DataProc 2.1 использует conda окружение с Python 3.8 (/opt/conda/bin/python)
# Согласно документации DataProc 2.1:
# - Python: 3.8.13
# - Предустановлены: scikit-learn 0.24.1, pandas 1.2.4, numpy 1.20.1, boto3 1.16.7, botocore 1.19.7
# - КРИТИЧНО: botocore 1.19.7 требует urllib3<1.26,>=1.25.4
# - Нужно установить: tensorflow, mlflow, pillow
print("🔧 Checking ML dependencies in DataProc 2.1 conda environment (Python 3.8)...")

# Список пакетов, которые нужно проверить/установить
required_packages = {
    'tensorflow': 'tensorflow==2.13.0',  # Устанавливаем
    'mlflow': 'mlflow==2.9.2',  # Устанавливаем (не в базовом образе 2.1)
    'boto3': None,   # Уже есть: 1.16.7
    'pandas': None,  # Уже есть: 1.2.4
    'numpy': None,   # Уже есть: 1.20.1, но будем обновлять до 1.24.3
    'scipy': 'scipy==1.10.1',  # Обновляем для совместимости с numpy 1.24.3
    'pillow': 'pillow==10.1.0',  # Устанавливаем
    'scikit-learn': None,  # Уже есть: 0.24.1
}

packages_to_install = []

for pkg_name, pkg_spec in required_packages.items():
    try:
        import_name = pkg_name.replace('-', '_').lower()
        if pkg_name == 'pillow':
            import_name = 'PIL'
        elif pkg_name == 'scikit-learn':
            import_name = 'sklearn'
        
        __import__(import_name)
        print(f"✅ {pkg_name} already available")
    except ImportError:
        if pkg_spec:
            print(f"⚠️  {pkg_name} not found, will install: {pkg_spec}")
            packages_to_install.append(pkg_spec)
        else:
            print(f"⚠️  {pkg_name} not found but should be in conda!")

# Устанавливаем только отсутствующие пакеты
if packages_to_install:
    print(f"📦 Installing {len(packages_to_install)} packages...")
    
    # КРИТИЧНО: Устанавливаем пакеты БЕЗ обновления зависимостей
    # Используем --no-deps для TensorFlow и MLflow, затем устанавливаем их зависимости вручную
    
    # Шаг 1: Устанавливаем базовые зависимости с правильными версиями
    print("🔧 Step 1: Installing compatible base dependencies...")
    base_deps = [
        'urllib3<1.26,>=1.25.4',  # Совместимая с botocore 1.19.7
        'typing-extensions<4.6.0,>=3.6.6',  # Для TensorFlow
        'protobuf<5,>=3.12.0',  # Для TensorFlow и MLflow
        'click<9,>=7.0',  # Для MLflow
        'packaging<24',  # Для MLflow
    ]
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user'] + base_deps)
    print("✅ Base dependencies installed!")
    
    # Шаг 2: Устанавливаем TensorFlow и MLflow БЕЗ автоматического разрешения зависимостей
    print("🔧 Step 2: Installing TensorFlow and MLflow with --no-deps...")
    for pkg in packages_to_install:
        print(f"   Installing {pkg} (no-deps)...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', '--no-deps', pkg])
    print("✅ TensorFlow and MLflow installed!")
    
    # Шаг 3: Устанавливаем numpy 1.24.3 и настраиваем sys.path для приоритета
    print("🔧 Step 3a: Installing numpy 1.24.3...")
    subprocess.check_call([
        sys.executable, '-m', 'pip', 'install', '--user',
        '--force-reinstall', '--no-deps', 'numpy==1.24.3'
    ])
    print("✅ NumPy 1.24.3 installed!")
    
    # КРИТИЧНО: Вставляем user-local ПЕРЕД всеми остальными путями, включая conda
    print("🔧 Step 3b: Reconfiguring sys.path to prioritize user-local packages...")
    user_site = '/home/dataproc-agent/.local/lib/python3.8/site-packages'
    # Удаляем все вхождения user_site из sys.path
    while user_site in sys.path:
        sys.path.remove(user_site)
    # Вставляем в самое начало
    sys.path.insert(0, user_site)
    print(f"   ✅ sys.path[0] = {sys.path[0]}")
    
    # КРИТИЧНО: Устанавливаем scipy ОТДЕЛЬНО в user-local ДО предзагрузки numpy
    print("🔧 Step 3c: Installing scipy 1.10.1 in user-local...")
    subprocess.check_call([
        sys.executable, '-m', 'pip', 'install', '--user',
        '--force-reinstall', '--no-deps', 'scipy==1.10.1'
    ])
    print("✅ SciPy 1.10.1 installed in user-local!")
    
    # ДОПОЛНИТЕЛЬНО: Предзагружаем numpy 1.24.3 И scipy 1.10.1 в sys.modules
    print("🔧 Step 3d: Pre-loading numpy 1.24.3 and scipy 1.10.1 into sys.modules...")
    # Удаляем любые ранее загруженные numpy и scipy модули
    to_reload = [key for key in sys.modules.keys() if key.startswith(('numpy', 'scipy'))]
    for mod in to_reload:
        del sys.modules[mod]
    # Теперь импортируем numpy и scipy - ДОЛЖНЫ загрузиться из user-local
    import numpy as np_test
    import scipy as sp_test
    print(f"   ✅ Pre-loaded numpy: {np_test.__version__} from {np_test.__file__}")
    print(f"   ✅ Pre-loaded scipy: {sp_test.__version__} from {sp_test.__file__}")
    if not np_test.__version__.startswith('1.24'):
        raise RuntimeError(f"❌ WRONG NUMPY! Expected 1.24.x, got {np_test.__version__}")
    if not sp_test.__version__.startswith('1.10'):
        raise RuntimeError(f"❌ WRONG SCIPY! Expected 1.10.x, got {sp_test.__version__}")
    print("   ✅ NumPy 1.24.3 and SciPy 1.10.1 successfully pre-loaded!")
    
    # Затем устанавливаем остальные зависимости с --upgrade-strategy only-if-needed
    print("🔧 Step 3e: Installing remaining dependencies with constraints...")
    ml_deps = [
        'absl-py>=1.0.0',
        'astunparse>=1.6.0',
        'flatbuffers>=23.1.21',
        'gast<=0.4.0,>=0.2.1',
        'google-pasta>=0.1.1',
        'h5py>=2.9.0',
        'keras<2.14,>=2.13.1',
        'libclang>=13.0.0',
        'opt-einsum>=2.3.2',
        'tensorboard<2.14,>=2.13',
        'tensorflow-estimator<2.14,>=2.13.0',
        'tensorflow-io-gcs-filesystem>=0.23.1',
        'termcolor>=1.1.0',
        'wrapt>=1.11.0',
        # MLflow dependencies
        'alembic!=1.10.0,<2',
        'cloudpickle<4',
        'databricks-cli<1,>=0.8.7',
        'docker<7,>=4.0.0',
        'entrypoints<1',
        'Flask<4',
        'gitpython<4,>=2.1.0',
        'gunicorn<22',
        'importlib-metadata!=4.7.0,<8,>=3.7.0',
        'Jinja2<4,>=2.11',
        'markdown<4,>=3.3',
        'pytz<2024',
        'pyyaml<7,>=5.1',
        'querystring-parser<2',
        'sqlparse<1,>=0.4.0',
    ]
    subprocess.check_call([
        sys.executable, '-m', 'pip', 'install', '--user',
        '--upgrade-strategy', 'only-if-needed'  # НЕ обновлять уже установленные!
    ] + ml_deps)
    print("✅ All dependencies installed!")
    
    print("✅ All missing packages installed successfully!")
else:
    print("✅ All dependencies already available!")

print("✅ Dependency check complete!")

# УДАЛЯЕМ несовместимые пакеты из user-local (urllib3, typing-extensions)
user_site = '/home/dataproc-agent/.local/lib/python3.8/site-packages'

# 1. urllib3 (конфликтует с boto3)
urllib3_path = os.path.join(user_site, 'urllib3')
if os.path.exists(urllib3_path):
    print(f"🗑️  Removing incompatible urllib3 from {urllib3_path}")
    shutil.rmtree(urllib3_path)
    # Также удаляем метаданные
    for item in os.listdir(user_site):
        if item.startswith('urllib3-'):
            item_path = os.path.join(user_site, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
    print(f"✅ Removed incompatible urllib3")

# 2. typing-extensions (конфликтует с TensorFlow и sqlalchemy)
typing_ext_path = os.path.join(user_site, 'typing_extensions.py')
if os.path.exists(typing_ext_path):
    print(f"🗑️  Removing typing-extensions 4.13.2 from {typing_ext_path}")
    os.remove(typing_ext_path)
    # Удаляем метаданные
    for item in os.listdir(user_site):
        if item.startswith('typing_extensions-'):
            item_path = os.path.join(user_site, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
    print(f"✅ Removed typing-extensions 4.13.2 (will use 4.5.0 for TensorFlow)")

# Spark imports
from pyspark.sql import SparkSession
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer
from pyspark.ml.evaluation import MulticlassClassificationEvaluator

# TensorFlow/Keras imports
print(f"🔍 Attempting to import tensorflow from sys.path:")
for i, path in enumerate(sys.path[:5]):
    print(f"   [{i}] {path}")
import tensorflow as tf
print(f"✅ TensorFlow imported successfully! Version: {tf.__version__}")
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

# MLflow imports
import mlflow
import mlflow.keras
from mlflow.tracking import MlflowClient

# S3/Boto3 imports
import boto3
from botocore.client import Config


def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Train fish classification model')
    
    # S3 параметры
    parser.add_argument('--s3-endpoint', required=True, help='S3 endpoint URL')
    parser.add_argument('--s3-bucket', required=True, help='S3 bucket name')
    parser.add_argument('--s3-access-key', required=True, help='S3 access key')
    parser.add_argument('--s3-secret-key', required=True, help='S3 secret key')
    
    # MLflow параметры
    parser.add_argument('--mlflow-tracking-uri', required=True, help='MLflow tracking URI')
    parser.add_argument('--mlflow-experiment', default='fish-classification', help='MLflow experiment name')
    
    # Параметры модели
    parser.add_argument('--num-classes', type=int, default=9, help='Number of fish classes')
    parser.add_argument('--image-size', type=int, default=224, help='Image size')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size')
    parser.add_argument('--epochs', type=int, default=10, help='Number of epochs')
    parser.add_argument('--learning-rate', type=float, default=0.001, help='Learning rate')
    
    return parser.parse_args()


def setup_s3_client(endpoint, access_key, secret_key):
    """Настройка S3 клиента"""
    return boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version='s3v4')
    )


def download_dataset_from_s3(s3_client, bucket, local_path='/tmp/fish_dataset'):
    """Скачивание датасета из S3"""
    print(f"📥 Downloading dataset from S3 bucket: {bucket}")
    
    os.makedirs(local_path, exist_ok=True)
    
    # Скачиваем только обработанные изображения
    prefix = 'datasets/processed_images/'
    
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
    
    file_count = 0
    for page in pages:
        if 'Contents' not in page:
            continue
            
        for obj in page['Contents']:
            key = obj['Key']
            if key.endswith('/'):  # Skip directories
                continue
                
            # Создаём локальную структуру директорий
            local_file = os.path.join(local_path, key.replace(prefix, ''))
            os.makedirs(os.path.dirname(local_file), exist_ok=True)
            
            # Скачиваем файл
            s3_client.download_file(bucket, key, local_file)
            file_count += 1
            
            if file_count % 100 == 0:
                print(f"   Downloaded {file_count} files...")
    
    print(f"✅ Downloaded {file_count} files to {local_path}")
    return local_path


def create_transfer_learning_model(num_classes, image_size, learning_rate):
    """
    Создание модели с Transfer Learning на базе MobileNetV2
    """
    print(f"🏗️ Creating transfer learning model (MobileNetV2)")
    
    # Загружаем предобученную модель MobileNetV2 (ImageNet weights)
    base_model = MobileNetV2(
        input_shape=(image_size, image_size, 3),
        include_top=False,
        weights='imagenet'
    )
    
    # Замораживаем базовые слои
    base_model.trainable = False
    
    # Добавляем кастомные слои для классификации рыб
    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(512, activation='relu')(x)
    x = Dropout(0.5)(x)
    x = Dense(256, activation='relu')(x)
    x = Dropout(0.3)(x)
    predictions = Dense(num_classes, activation='softmax')(x)
    
    # Создаём финальную модель
    model = Model(inputs=base_model.input, outputs=predictions)
    
    # Компилируем модель
    model.compile(
        optimizer=Adam(learning_rate=learning_rate),
        loss='categorical_crossentropy',
        metrics=['accuracy', 'top_k_categorical_accuracy']
    )
    
    print(f"✅ Model created with {model.count_params():,} parameters")
    print(f"   Trainable parameters: {sum([tf.size(w).numpy() for w in model.trainable_weights]):,}")
    
    return model


def train_model(model, dataset_path, batch_size, epochs, image_size):
    """
    Обучение модели с использованием ImageDataGenerator
    """
    print(f"🎓 Starting model training...")
    
    # Data augmentation для train set
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=20,
        width_shift_range=0.2,
        height_shift_range=0.2,
        horizontal_flip=True,
        zoom_range=0.2,
        shear_range=0.2,
        fill_mode='nearest',
        validation_split=0.2  # 80% train, 20% validation
    )
    
    # Только rescale для validation set
    val_datagen = ImageDataGenerator(
        rescale=1./255,
        validation_split=0.2
    )
    
    # Только rescale для test set
    test_datagen = ImageDataGenerator(rescale=1./255)
    
    # Загружаем train данные
    train_generator = train_datagen.flow_from_directory(
        os.path.join(dataset_path, 'train'),
        target_size=(image_size, image_size),
        batch_size=batch_size,
        class_mode='categorical',
        subset='training',
        shuffle=True
    )
    
    # Загружаем validation данные
    validation_generator = val_datagen.flow_from_directory(
        os.path.join(dataset_path, 'train'),
        target_size=(image_size, image_size),
        batch_size=batch_size,
        class_mode='categorical',
        subset='validation',
        shuffle=False
    )
    
    # Проверяем наличие test set
    test_dir = os.path.join(dataset_path, 'test')
    test_generator = None
    if os.path.exists(test_dir) and os.listdir(test_dir):
        test_generator = test_datagen.flow_from_directory(
            test_dir,
            target_size=(image_size, image_size),
            batch_size=batch_size,
            class_mode='categorical',
            shuffle=False
        )
        print(f"   Test samples: {test_generator.samples}")
    
    print(f"   Train samples: {train_generator.samples}")
    print(f"   Validation samples: {validation_generator.samples}")
    print(f"   Classes: {train_generator.class_indices}")
    
    # Callbacks
    early_stopping = EarlyStopping(
        monitor='val_loss',
        patience=3,
        restore_best_weights=True,
        verbose=1
    )
    
    reduce_lr = ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=2,
        min_lr=1e-7,
        verbose=1
    )
    
    # Обучение
    history = model.fit(
        train_generator,
        epochs=epochs,
        validation_data=validation_generator,
        callbacks=[early_stopping, reduce_lr],
        verbose=1
    )
    
    return history, train_generator.class_indices, test_generator


def main():
    """Основная функция"""
    args = parse_args()
    
    print("=" * 80)
    print("🐟 Fish Classification Model Training with Transfer Learning")
    print("=" * 80)
    print(f"Start time: {datetime.now()}")
    print(f"MLflow Tracking URI: {args.mlflow_tracking_uri}")
    print(f"S3 Bucket: {args.s3_bucket}")
    print(f"Image size: {args.image_size}x{args.image_size}")
    print(f"Batch size: {args.batch_size}")
    print(f"Epochs: {args.epochs}")
    print(f"Learning rate: {args.learning_rate}")
    print("=" * 80)
    
    # Настройка MLflow
    mlflow.set_tracking_uri(args.mlflow_tracking_uri)
    mlflow.set_experiment(args.mlflow_experiment)
    
    # Настройка S3
    s3_client = setup_s3_client(
        args.s3_endpoint,
        args.s3_access_key,
        args.s3_secret_key
    )
    
    # Начинаем MLflow run
    with mlflow.start_run(run_name=f"fish-classification-{datetime.now().strftime('%Y%m%d-%H%M%S')}"):
        
        # Логируем параметры
        mlflow.log_param("base_model", "MobileNetV2")
        mlflow.log_param("pretrained_weights", "imagenet")
        mlflow.log_param("num_classes", args.num_classes)
        mlflow.log_param("image_size", args.image_size)
        mlflow.log_param("batch_size", args.batch_size)
        mlflow.log_param("epochs", args.epochs)
        mlflow.log_param("learning_rate", args.learning_rate)
        mlflow.log_param("optimizer", "Adam")
        mlflow.log_param("loss", "categorical_crossentropy")
        
        # Скачиваем датасет
        dataset_path = download_dataset_from_s3(
            s3_client,
            args.s3_bucket
        )
        
        # Создаём модель
        model = create_transfer_learning_model(
            args.num_classes,
            args.image_size,
            args.learning_rate
        )
        
        # Обучаем модель
        history, class_indices, test_generator = train_model(
            model,
            dataset_path,
            args.batch_size,
            args.epochs,
            args.image_size
        )
        
        # Логируем метрики обучения
        final_train_acc = history.history['accuracy'][-1]
        final_val_acc = history.history['val_accuracy'][-1]
        final_train_loss = history.history['loss'][-1]
        final_val_loss = history.history['val_loss'][-1]
        
        mlflow.log_metric("final_train_accuracy", final_train_acc)
        mlflow.log_metric("final_val_accuracy", final_val_acc)
        mlflow.log_metric("final_train_loss", final_train_loss)
        mlflow.log_metric("final_val_loss", final_val_loss)
        
        # Оценка на test set (если доступен)
        test_acc = None
        test_loss = None
        if test_generator is not None:
            print("🧪 Evaluating model on test set...")
            test_results = model.evaluate(test_generator, verbose=1)
            test_loss = test_results[0]
            test_acc = test_results[1]
            test_top_k = test_results[2] if len(test_results) > 2 else None
            
            mlflow.log_metric("test_accuracy", test_acc)
            mlflow.log_metric("test_loss", test_loss)
            if test_top_k is not None:
                mlflow.log_metric("test_top_k_accuracy", test_top_k)
            
            print(f"✅ Test accuracy: {test_acc:.4f}")
            print(f"✅ Test loss: {test_loss:.4f}")
        
        # Логируем историю обучения
        for epoch in range(len(history.history['accuracy'])):
            mlflow.log_metric("train_accuracy", history.history['accuracy'][epoch], step=epoch)
            mlflow.log_metric("val_accuracy", history.history['val_accuracy'][epoch], step=epoch)
            mlflow.log_metric("train_loss", history.history['loss'][epoch], step=epoch)
            mlflow.log_metric("val_loss", history.history['val_loss'][epoch], step=epoch)
        
        # Сохраняем модель в MLflow с дополнительными метаданными
        print("💾 Saving model to MLflow...")
        mlflow.keras.log_model(
            model,
            "model",
            registered_model_name="fish-classification-mobilenetv2"
        )
        
        # Сохраняем class indices
        mlflow.log_dict(class_indices, "class_indices.json")
        
        # Получаем информацию о зарегистрированной модели
        client = MlflowClient()
        run_id = mlflow.active_run().info.run_id
        
        # Получаем последнюю версию модели
        latest_versions = client.get_latest_versions("fish-classification-mobilenetv2")
        if latest_versions:
            model_version = latest_versions[0].version
            
            # Добавляем теги для быстрого поиска
            client.set_model_version_tag(
                name="fish-classification-mobilenetv2",
                version=model_version,
                key="val_accuracy",
                value=f"{final_val_acc:.4f}"
            )
            
            if test_acc is not None:
                client.set_model_version_tag(
                    name="fish-classification-mobilenetv2",
                    version=model_version,
                    key="test_accuracy",
                    value=f"{test_acc:.4f}"
                )
            
            client.set_model_version_tag(
                name="fish-classification-mobilenetv2",
                version=model_version,
                key="training_date",
                value=datetime.now().isoformat()
            )
            
            client.set_model_version_tag(
                name="fish-classification-mobilenetv2",
                version=model_version,
                key="base_model",
                value="MobileNetV2"
            )
            
            # Добавляем описание модели
            client.update_model_version(
                name="fish-classification-mobilenetv2",
                version=model_version,
                description=f"Fish classification model trained with Transfer Learning (MobileNetV2). "
                           f"Val Accuracy: {final_val_acc:.4f}, "
                           f"Test Accuracy: {test_acc:.4f if test_acc else 'N/A'}, "
                           f"Trained on {datetime.now().strftime('%Y-%m-%d')}"
            )
            
            # Автоматический stage management
            # Если accuracy хорошая (>75%), переводим в Staging
            if final_val_acc > 0.75:
                print(f"🎯 Model performance is good (val_acc: {final_val_acc:.4f} > 0.75)")
                print("📦 Promoting model to Staging stage...")
                
                client.transition_model_version_stage(
                    name="fish-classification-mobilenetv2",
                    version=model_version,
                    stage="Staging",
                    archive_existing_versions=False
                )
                print(f"✅ Model version {model_version} promoted to Staging")
            else:
                print(f"⚠️  Model performance is below threshold (val_acc: {final_val_acc:.4f} <= 0.75)")
                print("   Model will remain in 'None' stage")
            
            print(f"📦 Model registered: fish-classification-mobilenetv2 v{model_version}")
        
        print("=" * 80)
        print("✅ Training completed successfully!")
        print(f"   Final train accuracy: {final_train_acc:.4f}")
        print(f"   Final validation accuracy: {final_val_acc:.4f}")
        if test_acc is not None:
            print(f"   Final test accuracy: {test_acc:.4f}")
        print(f"   Final train loss: {final_train_loss:.4f}")
        print(f"   Final validation loss: {final_val_loss:.4f}")
        if test_loss is not None:
            print(f"   Final test loss: {test_loss:.4f}")
        print(f"   MLflow run ID: {run_id}")
        print("=" * 80)
        print(f"End time: {datetime.now()}")


if __name__ == "__main__":
    main()
