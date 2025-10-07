#!/bin/bash
#
# DataProc Initialization Script
# Устанавливает зависимости для обучения ML модели
#

set -e

echo "🚀 Starting DataProc initialization..."

# Update package list
sudo apt-get update -qq

# Install Python dependencies
echo "📦 Installing Python packages..."
sudo pip3 install --upgrade pip

# Install ML/DL libraries
sudo pip3 install \
    tensorflow==2.13.0 \
    mlflow==2.9.2 \
    boto3==1.34.20 \
    pandas==2.0.3 \
    numpy==1.24.3 \
    pillow==10.1.0 \
    scikit-learn==1.3.2 \
    protobuf==3.20.3

echo "✅ DataProc initialization complete!"
echo "Installed packages:"
pip3 list | grep -E "tensorflow|mlflow|boto3|pandas|numpy|pillow|scikit-learn"

