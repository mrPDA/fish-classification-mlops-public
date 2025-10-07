#!/bin/bash

# Создание структуры папок для DataProc в S3

S3_BUCKET="fish-classification-data-7wb4zv"

echo "📁 Создаю папки для DataProc логов..."
echo ""

# Создаём временный файл
echo "placeholder" > /tmp/s3_placeholder.txt

# Создаём папки
echo "📂 logs/dataproc/"
yc storage s3 cp /tmp/s3_placeholder.txt s3://${S3_BUCKET}/logs/dataproc/.keep
echo "✅"

echo "📂 logs/spark/"
yc storage s3 cp /tmp/s3_placeholder.txt s3://${S3_BUCKET}/logs/spark/.keep
echo "✅"

echo "📂 logs/yarn/"
yc storage s3 cp /tmp/s3_placeholder.txt s3://${S3_BUCKET}/logs/yarn/.keep
echo "✅"

echo "📂 logs/hadoop/"
yc storage s3 cp /tmp/s3_placeholder.txt s3://${S3_BUCKET}/logs/hadoop/.keep
echo "✅"

echo "📂 spark-warehouse/"
yc storage s3 cp /tmp/s3_placeholder.txt s3://${S3_BUCKET}/spark-warehouse/.keep
echo "✅"

echo "📂 tmp/"
yc storage s3 cp /tmp/s3_placeholder.txt s3://${S3_BUCKET}/tmp/.keep
echo "✅"

# Очистка
rm /tmp/s3_placeholder.txt

echo ""
echo "✅ Все папки созданы!"
echo ""
echo "🔍 Проверка структуры:"
yc storage s3api list-objects --bucket ${S3_BUCKET} --delimiter "/" | grep "prefix:"

