"""
🐟 Fish Classification Training Script for Spark
=================================================

Обучение EfficientNet-B4 на DataProc кластере
"""

import argparse
import os
import sys
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Train Fish Classifier')
    parser.add_argument('--bucket', required=True, help='S3 bucket name')
    parser.add_argument('--num-classes', type=int, default=17, help='Number of classes')
    parser.add_argument('--epochs', type=int, default=20, help='Number of epochs')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size')
    parser.add_argument('--learning-rate', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--mlflow-uri', required=True, help='MLflow tracking URI')
    return parser.parse_args()

def main():
    """Основная функция обучения"""
    args = parse_args()
    
    logger.info("🚀 Запуск обучения Fish Classifier")
    logger.info(f"📊 Параметры:")
    logger.info(f"  Bucket: {args.bucket}")
    logger.info(f"  Classes: {args.num_classes}")
    logger.info(f"  Epochs: {args.epochs}")
    logger.info(f"  Batch size: {args.batch_size}")
    logger.info(f"  Learning rate: {args.learning_rate}")
    logger.info(f"  MLflow URI: {args.mlflow_uri}")
    
    # Импортируем библиотеки для ML
    try:
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from torchvision import models, transforms
        from PIL import Image
        import mlflow
        import mlflow.pytorch
        import boto3
        from io import BytesIO
        logger.info("✅ Библиотеки импортированы")
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта: {e}")
        logger.info("💡 Убедитесь, что PyTorch и MLflow установлены на кластере")
        sys.exit(1)
    
    # Настройка MLflow
    mlflow.set_tracking_uri(args.mlflow_uri)
    mlflow.set_experiment("fish-classification")
    
    # Получаем S3 credentials из окружения
    s3_access_key = os.environ.get('S3_ACCESS_KEY')
    s3_secret_key = os.environ.get('S3_SECRET_KEY')
    
    if not s3_access_key or not s3_secret_key:
        logger.error("❌ S3 credentials не найдены в окружении")
        sys.exit(1)
    
    # Инициализация S3 client
    s3_client = boto3.client(
        's3',
        endpoint_url='https://storage.yandexcloud.net',
        aws_access_key_id=s3_access_key,
        aws_secret_access_key=s3_secret_key
    )
    
    logger.info("✅ S3 client инициализирован")
    
    # Определяем устройство
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"🖥️  Device: {device}")
    
    # Создаём модель
    logger.info("🏗️  Создание модели EfficientNet-B4...")
    model = models.efficientnet_b4(pretrained=True)
    
    # Замораживаем базовые слои
    for param in model.parameters():
        param.requires_grad = False
    
    # Заменяем classifier
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, args.num_classes)
    model = model.to(device)
    
    logger.info(f"✅ Модель создана (параметров: {sum(p.numel() for p in model.parameters()):,})")
    
    # Определяем функцию потерь и оптимизатор
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.classifier.parameters(), lr=args.learning_rate)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=3)
    
    # Трансформации
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    # Загружаем список файлов из S3
    logger.info("📦 Загрузка списка файлов...")
    
    def get_image_files(prefix):
        """Получить список изображений из S3"""
        files = []
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=args.bucket, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.lower().endswith(('.jpg', '.jpeg', '.png')):
                        # Извлекаем класс из пути
                        parts = key.split('/')
                        if len(parts) >= 2:
                            try:
                                label = int(parts[-2])
                                files.append((key, label))
                            except ValueError:
                                continue
        return files
    
    train_files = get_image_files('datasets/processed_images/train/')
    val_files = get_image_files('datasets/processed_images/val/')
    
    logger.info(f"  Train: {len(train_files)} изображений")
    logger.info(f"  Val: {len(val_files)} изображений")
    
    if len(train_files) == 0 or len(val_files) == 0:
        logger.error("❌ Датасет пуст")
        sys.exit(1)
    
    # Функция для загрузки батча
    def load_batch(files, batch_size, transform):
        """Загрузить батч изображений из S3"""
        import random
        random.shuffle(files)
        
        for i in range(0, len(files), batch_size):
            batch_files = files[i:i + batch_size]
            images = []
            labels = []
            
            for key, label in batch_files:
                try:
                    # Загружаем изображение из S3
                    response = s3_client.get_object(Bucket=args.bucket, Key=key)
                    image_data = response['Body'].read()
                    image = Image.open(BytesIO(image_data)).convert('RGB')
                    
                    # Применяем трансформации
                    if transform:
                        image = transform(image)
                    
                    images.append(image)
                    labels.append(label)
                except Exception as e:
                    logger.warning(f"⚠️  Ошибка загрузки {key}: {e}")
                    continue
            
            if len(images) > 0:
                yield torch.stack(images), torch.tensor(labels)
    
    # MLflow run
    with mlflow.start_run(run_name=f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        # Log parameters
        mlflow.log_params({
            'model': 'efficientnet_b4',
            'num_classes': args.num_classes,
            'epochs': args.epochs,
            'batch_size': args.batch_size,
            'learning_rate': args.learning_rate,
            'optimizer': 'Adam',
            'device': str(device),
            'train_size': len(train_files),
            'val_size': len(val_files)
        })
        
        best_val_loss = float('inf')
        best_val_acc = 0.0
        
        # Training loop
        for epoch in range(args.epochs):
            logger.info(f"\n📊 Epoch {epoch+1}/{args.epochs}")
            
            # Training phase
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            batch_count = 0
            
            for inputs, labels in load_batch(train_files, args.batch_size, train_transform):
                inputs, labels = inputs.to(device), labels.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                train_total += labels.size(0)
                train_correct += predicted.eq(labels).sum().item()
                batch_count += 1
                
                if batch_count % 10 == 0:
                    logger.info(f"  Batch {batch_count}, Loss: {loss.item():.4f}")
            
            train_loss /= max(batch_count, 1)
            train_acc = 100. * train_correct / max(train_total, 1)
            
            # Validation phase
            model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0
            val_batch_count = 0
            
            with torch.no_grad():
                for inputs, labels in load_batch(val_files, args.batch_size, val_transform):
                    inputs, labels = inputs.to(device), labels.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)
                    
                    val_loss += loss.item()
                    _, predicted = outputs.max(1)
                    val_total += labels.size(0)
                    val_correct += predicted.eq(labels).sum().item()
                    val_batch_count += 1
            
            val_loss /= max(val_batch_count, 1)
            val_acc = 100. * val_correct / max(val_total, 1)
            
            # Log metrics
            mlflow.log_metrics({
                'train_loss': train_loss,
                'train_accuracy': train_acc,
                'val_loss': val_loss,
                'val_accuracy': val_acc,
                'learning_rate': optimizer.param_groups[0]['lr']
            }, step=epoch)
            
            logger.info(f"  Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
            logger.info(f"  Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")
            
            # Save best model
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_val_loss = val_loss
                torch.save(model.state_dict(), '/tmp/best_model.pth')
                logger.info(f"  💾 Сохранена лучшая модель (val_acc: {val_acc:.2f}%)")
            
            scheduler.step(val_loss)
        
        # Load best model and save to MLflow
        model.load_state_dict(torch.load('/tmp/best_model.pth'))
        mlflow.pytorch.log_model(model, "model")
        
        # Log final metrics
        mlflow.log_metrics({
            'best_val_loss': best_val_loss,
            'best_val_accuracy': best_val_acc
        })
        
        run_id = mlflow.active_run().info.run_id
        logger.info(f"\n✅ Обучение завершено. MLflow Run ID: {run_id}")
        logger.info(f"📊 Лучшая точность: {best_val_acc:.2f}%")
    
    logger.info("🎉 Готово!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
