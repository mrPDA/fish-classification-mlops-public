#!/bin/bash

# ========================================
# 📦 Dataset Upload Script
# ========================================
# Автоматическая загрузка датасета в S3

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}📦 Загрузка датасета в S3...${NC}"

# ========================================
# Проверка переменных
# ========================================

# Путь к датасету
DATASET_SOURCE="${1:-../Finalwork_2/datasets_final}"

if [ ! -d "$DATASET_SOURCE" ]; then
    echo -e "${RED}❌ Датасет не найден: $DATASET_SOURCE${NC}"
    exit 1
fi

# Получаем данные из Terraform outputs
cd terraform 2>/dev/null || cd ../terraform 2>/dev/null || {
    echo -e "${RED}❌ Не найдена папка terraform${NC}"
    exit 1
}

BUCKET_NAME=$(terraform output -raw s3_bucket_name 2>/dev/null)
ACCESS_KEY=$(terraform output -raw s3_access_key 2>/dev/null)
SECRET_KEY=$(terraform output -raw s3_secret_key 2>/dev/null)

if [ -z "$BUCKET_NAME" ] || [ -z "$ACCESS_KEY" ] || [ -z "$SECRET_KEY" ]; then
    echo -e "${RED}❌ Не удалось получить S3 credentials из Terraform${NC}"
    echo -e "${YELLOW}Убедитесь, что terraform apply выполнен успешно${NC}"
    exit 1
fi

cd ..

echo -e "${GREEN}✅ S3 Bucket: $BUCKET_NAME${NC}"

# ========================================
# Проверка структуры датасета
# ========================================

echo -e "${BLUE}🔍 Проверка структуры датасета...${NC}"

if [ ! -d "$DATASET_SOURCE/processed_images" ]; then
    echo -e "${RED}❌ Не найдена папка processed_images в $DATASET_SOURCE${NC}"
    exit 1
fi

if [ ! -d "$DATASET_SOURCE/annotations" ]; then
    echo -e "${RED}❌ Не найдена папка annotations в $DATASET_SOURCE${NC}"
    exit 1
fi

# Подсчёт файлов
TRAIN_COUNT=$(find "$DATASET_SOURCE/processed_images/train" -type f 2>/dev/null | wc -l | tr -d ' ')
VAL_COUNT=$(find "$DATASET_SOURCE/processed_images/val" -type f 2>/dev/null | wc -l | tr -d ' ')
TEST_COUNT=$(find "$DATASET_SOURCE/processed_images/test" -type f 2>/dev/null | wc -l | tr -d ' ')

echo -e "${GREEN}📊 Статистика датасета:${NC}"
echo -e "  Train: $TRAIN_COUNT изображений"
echo -e "  Val: $VAL_COUNT изображений"
echo -e "  Test: $TEST_COUNT изображений"
echo -e "  Всего: $((TRAIN_COUNT + VAL_COUNT + TEST_COUNT)) изображений"

# ========================================
# Загрузка в S3
# ========================================

echo -e "${BLUE}☁️  Загрузка в S3 через yc CLI...${NC}"

# Функция для загрузки через yc storage
upload_directory() {
    local source_dir=$1
    local target_path=$2
    local description=$3
    
    echo -e "${YELLOW}📤 $description...${NC}"
    
    # Используем yc storage s3 cp с --recursive
    yc storage s3 cp "$source_dir" "s3://$BUCKET_NAME/$target_path" \
        --recursive \
        --quiet 2>&1 | while read line; do
            echo "  $line"
        done
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo -e "${GREEN}  ✅ Загружено${NC}"
    else
        echo -e "${RED}  ❌ Ошибка загрузки${NC}"
        return 1
    fi
}

# Загружаем обработанные изображения
upload_directory \
    "$DATASET_SOURCE/processed_images/train" \
    "datasets/processed_images/train" \
    "Train images"

upload_directory \
    "$DATASET_SOURCE/processed_images/val" \
    "datasets/processed_images/val" \
    "Validation images"

upload_directory \
    "$DATASET_SOURCE/processed_images/test" \
    "datasets/processed_images/test" \
    "Test images"

# Загружаем аннотации
upload_directory \
    "$DATASET_SOURCE/annotations" \
    "datasets/annotations" \
    "Annotations"

# Загружаем README
if [ -f "$DATASET_SOURCE/README.md" ]; then
    echo -e "${YELLOW}📤 README.md...${NC}"
    yc storage s3 cp "$DATASET_SOURCE/README.md" \
        "s3://$BUCKET_NAME/datasets/README.md" \
        --quiet
    echo -e "${GREEN}  ✅ Загружено${NC}"
fi

# ========================================
# Создание метаданных
# ========================================

echo -e "${BLUE}📝 Создание метаданных...${NC}"

# Создаём JSON с информацией о датасете
cat > /tmp/dataset_metadata.json << EOF
{
  "dataset_name": "Red Sea Fish Classification",
  "version": "1.0",
  "upload_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "source": "iNaturalist Marine Fish Project",
  "statistics": {
    "train_images": $TRAIN_COUNT,
    "val_images": $VAL_COUNT,
    "test_images": $TEST_COUNT,
    "total_images": $((TRAIN_COUNT + VAL_COUNT + TEST_COUNT)),
    "num_classes": 17
  },
  "s3_paths": {
    "train": "s3://$BUCKET_NAME/datasets/processed_images/train/",
    "val": "s3://$BUCKET_NAME/datasets/processed_images/val/",
    "test": "s3://$BUCKET_NAME/datasets/processed_images/test/",
    "annotations": "s3://$BUCKET_NAME/datasets/annotations/"
  },
  "species": [
    "Perca Fluviatilis",
    "Perccottus Glenii",
    "Esox Lucius",
    "Alburnus Alburnus",
    "Abramis Brama",
    "Carassius Gibelio",
    "Squalius Cephalus",
    "Scardinius Erythrophthalmus",
    "Rutilus Lacustris",
    "Rutilus Rutilus",
    "Blicca Bjoerkna",
    "Gymnocephalus Cernua",
    "Leuciscus Idus",
    "Sander Lucioperca",
    "Leuciscus Baicalensis",
    "Gobio Gobio",
    "Tinca Tinca"
  ]
}
EOF

yc storage s3 cp /tmp/dataset_metadata.json \
    "s3://$BUCKET_NAME/datasets/metadata.json" \
    --quiet

rm /tmp/dataset_metadata.json

echo -e "${GREEN}  ✅ Метаданные созданы${NC}"

# ========================================
# Проверка загрузки
# ========================================

echo -e "${BLUE}🔍 Проверка загрузки...${NC}"

# Подсчитываем файлы в S3 через yc
S3_TRAIN=$(yc storage s3api list-objects --bucket "$BUCKET_NAME" --prefix "datasets/processed_images/train/" 2>/dev/null | grep -c "Key:" || echo "0")
S3_VAL=$(yc storage s3api list-objects --bucket "$BUCKET_NAME" --prefix "datasets/processed_images/val/" 2>/dev/null | grep -c "Key:" || echo "0")
S3_TEST=$(yc storage s3api list-objects --bucket "$BUCKET_NAME" --prefix "datasets/processed_images/test/" 2>/dev/null | grep -c "Key:" || echo "0")

echo -e "${GREEN}📊 Файлов в S3:${NC}"
echo -e "  Train: $S3_TRAIN"
echo -e "  Val: $S3_VAL"
echo -e "  Test: $S3_TEST"

# Проверка соответствия
if [ "$TRAIN_COUNT" -eq "$S3_TRAIN" ] && [ "$VAL_COUNT" -eq "$S3_VAL" ] && [ "$TEST_COUNT" -eq "$S3_TEST" ]; then
    echo -e "${GREEN}✅ Все файлы загружены успешно!${NC}"
else
    echo -e "${YELLOW}⚠️  Количество файлов не совпадает, проверьте логи${NC}"
fi

# ========================================
# Итоговая информация
# ========================================

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Датасет успешно загружен!         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📦 S3 Bucket:${NC} $BUCKET_NAME"
echo -e "${BLUE}📂 Базовый путь:${NC} s3://$BUCKET_NAME/datasets/"
echo ""
echo -e "${YELLOW}Следующий шаг:${NC} Запустите DAG для обучения модели в Airflow"
echo ""
