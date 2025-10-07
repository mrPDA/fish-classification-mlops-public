#!/bin/bash
#
# Wrapper для установки зависимостей перед запуском PySpark скрипта
# Этот скрипт НЕ НУЖЕН, т.к. DataprocCreatePysparkJobOperator не поддерживает bash обёртки
#
# Вместо этого используем client mode и устанавливаем зависимости через pip в самом Python скрипте

set -e

echo "🔧 Installing ML dependencies..."

# Upgrade pip
sudo pip3 install --upgrade pip

# Install ML libraries
sudo pip3 install \
    tensorflow==2.13.0 \
    mlflow==2.9.2 \
    boto3==1.34.20 \
    pandas==2.0.3 \
    numpy==1.24.3 \
    pillow==10.1.0 \
    scikit-learn==1.3.2 \
    protobuf==3.20.3

echo "✅ Dependencies installed!"

# Run the actual PySpark script
python3 "$@"

