#!/bin/bash

# ========================================
# 🌬️  Airflow Setup Script
# ========================================
# Автоматическая настройка Airflow: загрузка DAG и переменных

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🌬️  Настройка Airflow...${NC}"

# ========================================
# Получение данных из Terraform
# ========================================

cd terraform 2>/dev/null || cd ../terraform 2>/dev/null || {
    echo -e "${RED}❌ Не найдена папка terraform${NC}"
    exit 1
}

# Получаем все необходимые переменные из Terraform
CLOUD_ID=$(terraform output -raw cloud_id 2>/dev/null || echo "")
FOLDER_ID=$(terraform output -raw folder_id 2>/dev/null || echo "")
ZONE=$(terraform output -raw zone 2>/dev/null || echo "ru-central1-a")
NETWORK_ID=$(terraform output -raw network_id 2>/dev/null || echo "")
SUBNET_ID=$(terraform output -raw subnet_id 2>/dev/null || echo "")
SECURITY_GROUP_ID=$(terraform output -raw security_group_id 2>/dev/null || echo "")
S3_BUCKET=$(terraform output -raw s3_bucket_name 2>/dev/null)
S3_ACCESS_KEY=$(terraform output -raw s3_access_key 2>/dev/null)
S3_SECRET_KEY=$(terraform output -raw s3_secret_key 2>/dev/null)
MLFLOW_IP=$(terraform output -raw mlflow_vm_ip 2>/dev/null)
DATAPROC_SA_ID=$(terraform output -raw dataproc_sa_id 2>/dev/null || echo "")
AIRFLOW_CLUSTER_ID=$(terraform output -raw airflow_cluster_id 2>/dev/null || echo "")

# Получаем SSH ключ
if [ -f "../ssh_keys/dataproc.pub" ]; then
    SSH_KEY=$(cat ../ssh_keys/dataproc.pub)
elif [ -f ~/.ssh/id_rsa.pub ]; then
    SSH_KEY=$(cat ~/.ssh/id_rsa.pub)
else
    SSH_KEY="ssh-rsa PLACEHOLDER_SSH_KEY"
    echo -e "${YELLOW}⚠️  SSH ключ не найден, используется placeholder${NC}"
fi

# Получаем Service Account JSON
SA_JSON_FILE="sa-key.json"
if [ -f "$SA_JSON_FILE" ]; then
    SA_JSON=$(cat "$SA_JSON_FILE" | jq -c .)
    echo -e "${GREEN}✅ Найден файл service account: $SA_JSON_FILE${NC}"
elif [ -f "../$SA_JSON_FILE" ]; then
    SA_JSON=$(cat "../$SA_JSON_FILE" | jq -c .)
    echo -e "${GREEN}✅ Найден файл service account: ../$SA_JSON_FILE${NC}"
else
    echo -e "${YELLOW}⚠️  Файл service account не найден: $SA_JSON_FILE${NC}"
    SA_JSON='{"type": "service_account", "service_account_id": "'$DATAPROC_SA_ID'"}'
fi

if [ -z "$S3_BUCKET" ]; then
    echo -e "${RED}❌ Не удалось получить данные из Terraform${NC}"
    echo -e "${YELLOW}Убедитесь, что terraform apply выполнен успешно${NC}"
    exit 1
fi

cd ..

echo -e "${GREEN}✅ Данные получены:${NC}"
echo -e "  Cloud ID: $CLOUD_ID"
echo -e "  Folder ID: $FOLDER_ID"
echo -e "  Zone: $ZONE"
echo -e "  Network ID: $NETWORK_ID"
echo -e "  Subnet ID: $SUBNET_ID"
echo -e "  Security Group ID: $SECURITY_GROUP_ID"
echo -e "  S3 Bucket: $S3_BUCKET"
echo -e "  MLflow IP: $MLFLOW_IP"
echo -e "  DataProc SA ID: $DATAPROC_SA_ID"
if [ ! -z "$AIRFLOW_CLUSTER_ID" ]; then
    echo -e "  Airflow Cluster: $AIRFLOW_CLUSTER_ID"
fi

# ========================================
# Подготовка переменных Airflow
# ========================================

echo -e "${BLUE}📝 Подготовка переменных...${NC}"

# Создаём временный файл с заполненными переменными
cat airflow/variables.json | \
    sed "s|{{ CLOUD_ID }}|$CLOUD_ID|g" | \
    sed "s|{{ FOLDER_ID }}|$FOLDER_ID|g" | \
    sed "s|{{ ZONE }}|$ZONE|g" | \
    sed "s|{{ NETWORK_ID }}|$NETWORK_ID|g" | \
    sed "s|{{ SUBNET_ID }}|$SUBNET_ID|g" | \
    sed "s|{{ SECURITY_GROUP_ID }}|$SECURITY_GROUP_ID|g" | \
    sed "s|{{ S3_BUCKET_NAME }}|$S3_BUCKET|g" | \
    sed "s|{{ S3_ACCESS_KEY }}|$S3_ACCESS_KEY|g" | \
    sed "s|{{ S3_SECRET_KEY }}|$S3_SECRET_KEY|g" | \
    sed "s|{{ DATAPROC_SERVICE_ACCOUNT_ID }}|$DATAPROC_SA_ID|g" | \
    sed "s|{{ MLFLOW_IP }}|$MLFLOW_IP|g" \
    > /tmp/airflow_variables_temp.json

# Заменяем DP_SA_JSON и YC_SSH_PUBLIC_KEY через jq (т.к. они содержат спецсимволы)
jq --arg sa_json "$SA_JSON" --arg ssh_key "$SSH_KEY" \
    '.DP_SA_JSON = $sa_json | .YC_SSH_PUBLIC_KEY = $ssh_key' \
    /tmp/airflow_variables_temp.json > /tmp/airflow_variables.json

rm -f /tmp/airflow_variables_temp.json

echo -e "${GREEN}✅ Переменные подготовлены${NC}"

# ========================================
# Загрузка DAG и скриптов в S3 (для Managed Airflow)
# ========================================

echo -e "${BLUE}📤 Загрузка DAG и скриптов в S3...${NC}"

# Функция для загрузки всех файлов из папки
upload_directory() {
    local source_dir=$1
    local s3_prefix=$2
    local file_count=0
    
    if [ -d "$source_dir" ]; then
        echo -e "${YELLOW}📁 Загрузка содержимого $source_dir...${NC}"
        
        # Находим все Python файлы и текстовые файлы
        while IFS= read -r file; do
            # Получаем относительный путь от source_dir
            relative_path="${file#$source_dir/}"
            s3_path="s3://$S3_BUCKET/$s3_prefix/$relative_path"
            
            # Загружаем файл
            if yc storage s3 cp "$file" "$s3_path" 2>/dev/null; then
                echo -e "${GREEN}  ✅ $relative_path${NC}"
                ((file_count++))
            else
                echo -e "${RED}  ❌ Ошибка загрузки $relative_path${NC}"
            fi
        done < <(find "$source_dir" -type f \( -name "*.py" -o -name "*.txt" -o -name "*.yaml" -o -name "*.yml" \))
        
        # Подсчитываем файлы (т.к. в subshell переменная не обновляется)
        local uploaded=$(find "$source_dir" -type f \( -name "*.py" -o -name "*.txt" -o -name "*.yaml" -o -name "*.yml" \) | wc -l | tr -d ' ')
        echo -e "${GREEN}  ✅ Загружено файлов: $uploaded${NC}"
    else
        echo -e "${YELLOW}  ⚠️  Папка $source_dir не найдена${NC}"
    fi
    return 0  # Ensure successful exit
}

# Загружаем все DAG файлы
upload_directory "dags" "airflow-dags"

# Загружаем все Spark скрипты
upload_directory "spark_jobs" "spark_jobs"

# Также загружаем старую папку spark, если существует
if [ -d "spark" ]; then
    upload_directory "spark" "scripts"
fi

# Загружаем requirements, если есть
if [ -f "training/requirements.txt" ]; then
    echo -e "${YELLOW}📦 Загрузка training requirements...${NC}"
    if yc storage s3 cp training/requirements.txt \
        "s3://$S3_BUCKET/airflow-dags/requirements.txt" 2>/dev/null; then
        echo -e "${GREEN}  ✅ training/requirements.txt${NC}"
    fi
fi

if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}📦 Загрузка requirements...${NC}"
    if yc storage s3 cp requirements.txt \
        "s3://$S3_BUCKET/airflow-dags/requirements.txt" 2>/dev/null; then
        echo -e "${GREEN}  ✅ requirements.txt${NC}"
    fi
fi

echo -e "${GREEN}✅ DAG и скрипты загружены в S3${NC}"

# ========================================
# Настройка переменных через Airflow CLI/API
# ========================================

echo -e "${BLUE}🔧 Настройка переменных в Airflow...${NC}"

# Метод 1: Через Airflow REST API (если доступен)
AIRFLOW_URL=$(cd terraform && terraform output -raw airflow_webserver_url 2>/dev/null | sed 's|https://||' || echo "") || true

if [ ! -z "$AIRFLOW_URL" ]; then
    echo -e "${YELLOW}Airflow URL: https://$AIRFLOW_URL${NC}"
    
    # Получаем admin password
    AIRFLOW_PASSWORD=$(cd terraform && terraform output -raw airflow_admin_password 2>/dev/null || echo "")
    
    if [ ! -z "$AIRFLOW_PASSWORD" ]; then
        echo -e "${YELLOW}Попытка загрузки переменных через API...${NC}"
        
        # Загружаем каждую переменную
        while IFS= read -r line; do
            if echo "$line" | grep -q ":"; then
                key=$(echo "$line" | sed 's/.*"\(.*\)".*/\1/' | sed 's/:.*//')
                value=$(echo "$line" | sed 's/.*: "\(.*\)".*/\1/' | sed 's/",*//')
                
                if [ ! -z "$key" ] && [ ! -z "$value" ]; then
                    curl -X POST "https://$AIRFLOW_URL/api/v1/variables" \
                        -H "Content-Type: application/json" \
                        -u "admin:$AIRFLOW_PASSWORD" \
                        -d "{\"key\": \"$key\", \"value\": \"$value\"}" \
                        --insecure -s -o /dev/null || true
                fi
            fi
        done < /tmp/airflow_variables.json
        
        echo -e "${GREEN}✅ Переменные загружены через API${NC}"
    fi
fi

# ========================================
# Альтернативный метод: Через yc CLI
# ========================================

echo -e "${BLUE}📋 Альтернативный метод: yc CLI...${NC}"

# Сохраняем переменные в ConfigMap кластера
cat > /tmp/airflow_env.yaml << EOF
# Airflow Environment Variables
# Импортируйте вручную через Airflow UI: Admin -> Variables -> Import
$(cat /tmp/airflow_variables.json)
EOF

echo -e "${YELLOW}Файл с переменными сохранён: /tmp/airflow_env.yaml${NC}"
echo -e "${YELLOW}Для ручного импорта:${NC}"
echo -e "  1. Откройте Airflow UI: https://$AIRFLOW_URL"
echo -e "  2. Admin -> Variables -> Import"
echo -e "  3. Загрузите файл: /tmp/airflow_variables.json"

# ========================================
# Проверка DAG в S3
# ========================================

echo -e "${BLUE}🔍 Проверка загруженных файлов...${NC}"

echo -e "${YELLOW}DAGs в S3:${NC}"
yc storage s3api list-objects --bucket "$S3_BUCKET" --prefix "airflow-dags/" 2>/dev/null | \
    grep "key:" | sed 's/.*key: /  /' || echo "  (используйте yc storage s3api для проверки)" || true

# ========================================
# Инструкции для ручной настройки
# ========================================

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Настройка Airflow завершена!      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}📋 Следующие шаги:${NC}"
echo ""
echo -e "${YELLOW}1. Откройте Airflow UI:${NC}"
echo -e "   https://$AIRFLOW_URL"
echo -e "   Логин: admin"
echo -e "   Пароль: (из terraform.tfvars)"
echo ""
echo -e "${YELLOW}2. Импортируйте переменные (если не загрузились автоматически):${NC}"
echo -e "   Admin -> Variables -> Import Variables"
echo -e "   Загрузите файл: /tmp/airflow_variables.json"
echo ""
echo -e "${YELLOW}3. Проверьте DAG:${NC}"
echo -e "   DAGs -> fish_classification_training"
echo -e "   Убедитесь, что DAG загружен без ошибок"
echo ""
echo -e "${YELLOW}4. Запустите обучение:${NC}"
echo -e "   Нажмите на DAG -> Trigger DAG"
echo ""

# Cleanup
rm -f /tmp/airflow_variables.json /tmp/airflow_env.yaml

echo -e "${GREEN}✨ Готово!${NC}"
echo ""

# Ensure successful exit
exit 0
