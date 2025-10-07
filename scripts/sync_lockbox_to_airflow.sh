#!/bin/bash
#
# Автоматическая синхронизация переменных из Lockbox в Airflow Variables
#
# Использование:
#   ./sync_lockbox_to_airflow.sh
#
# Или с параметрами:
#   ./sync_lockbox_to_airflow.sh <lockbox_secret_id> <airflow_url> <airflow_password>
#

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🔐 Lockbox → Airflow Sync${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Переходим в директорию terraform для получения outputs
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$PROJECT_DIR/terraform"

cd "$TERRAFORM_DIR"

# Получаем параметры из Terraform или аргументов
if [ -z "$1" ]; then
    echo -e "${YELLOW}📊 Fetching parameters from Terraform...${NC}"
    LOCKBOX_SECRET_ID=$(terraform output -raw lockbox_secret_id 2>/dev/null || echo "")
    AIRFLOW_CLUSTER_ID=$(terraform output -raw airflow_cluster_id 2>/dev/null || echo "")
    AIRFLOW_PASSWORD=$(terraform output -raw airflow_admin_password 2>/dev/null || echo "")
else
    LOCKBOX_SECRET_ID="$1"
    AIRFLOW_URL="$2"
    AIRFLOW_PASSWORD="$3"
fi

# Проверяем обязательные параметры
if [ -z "$LOCKBOX_SECRET_ID" ]; then
    echo -e "${RED}❌ Error: LOCKBOX_SECRET_ID not found${NC}"
    echo "   Please provide it as first argument or ensure Terraform is initialized"
    exit 1
fi

if [ -z "$AIRFLOW_PASSWORD" ]; then
    echo -e "${RED}❌ Error: AIRFLOW_PASSWORD not found${NC}"
    echo "   Please provide it as third argument or ensure Terraform is initialized"
    exit 1
fi

# Получаем Airflow URL если не передан
if [ -z "$AIRFLOW_URL" ]; then
    if [ -n "$AIRFLOW_CLUSTER_ID" ]; then
        echo -e "${YELLOW}🔍 Getting Airflow URL from cluster...${NC}"
        AIRFLOW_URL=$(yc airflow cluster get "$AIRFLOW_CLUSTER_ID" --format json | jq -r '.webserver_url' 2>/dev/null || echo "")
    fi
fi

if [ -z "$AIRFLOW_URL" ]; then
    echo -e "${RED}❌ Error: AIRFLOW_URL not found${NC}"
    echo "   Please provide it as second argument or ensure Airflow cluster is running"
    exit 1
fi

# Убираем trailing slash из URL
AIRFLOW_URL="${AIRFLOW_URL%/}"

echo -e "${GREEN}✅ Configuration:${NC}"
echo "   Lockbox Secret ID: $LOCKBOX_SECRET_ID"
echo "   Airflow URL: $AIRFLOW_URL"
echo "   Airflow Username: admin"
echo ""

# Проверяем наличие Python скрипта
PYTHON_SCRIPT="$SCRIPT_DIR/import_lockbox_to_airflow.py"
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}❌ Error: Python script not found at $PYTHON_SCRIPT${NC}"
    exit 1
fi

# Делаем скрипт исполняемым
chmod +x "$PYTHON_SCRIPT"

# Запускаем импорт
echo -e "${BLUE}🚀 Starting import...${NC}"
echo ""

export LOCKBOX_SECRET_ID="$LOCKBOX_SECRET_ID"
export AIRFLOW_URL="$AIRFLOW_URL"
export AIRFLOW_USERNAME="admin"
export AIRFLOW_PASSWORD="$AIRFLOW_PASSWORD"

python3 "$PYTHON_SCRIPT"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ Sync completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${YELLOW}💡 Next steps:${NC}"
    echo "   1. Open Airflow UI: $AIRFLOW_URL"
    echo "   2. Go to Admin → Variables"
    echo "   3. Verify that all variables are imported"
    echo "   4. Trigger your DAG!"
    echo ""
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ Sync failed with exit code $EXIT_CODE${NC}"
    echo -e "${RED}========================================${NC}"
    exit $EXIT_CODE
fi
