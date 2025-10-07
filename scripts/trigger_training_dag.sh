#!/bin/bash

# ========================================
# 🚀 Автоматический запуск DAG для обучения
# ========================================

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Запуск DAG для обучения модели...${NC}"

# ========================================
# Получение данных из Terraform
# ========================================

cd terraform 2>/dev/null || cd ../terraform 2>/dev/null || {
    echo -e "${RED}❌ Не найдена папка terraform${NC}"
    exit 1
}

# Получаем Airflow cluster ID и credentials
AIRFLOW_CLUSTER_ID=$(terraform output -raw airflow_cluster_id 2>/dev/null)
AIRFLOW_ADMIN_PASSWORD=$(terraform output -raw airflow_admin_password 2>/dev/null)

if [ -z "$AIRFLOW_CLUSTER_ID" ]; then
    echo -e "${RED}❌ Airflow cluster ID не найден${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Airflow Cluster ID: $AIRFLOW_CLUSTER_ID${NC}"

# Получаем Airflow URL
echo -e "${BLUE}📡 Получение Airflow URL...${NC}"
AIRFLOW_INFO=$(yc airflow cluster get $AIRFLOW_CLUSTER_ID --format json 2>/dev/null)
AIRFLOW_STATUS=$(echo "$AIRFLOW_INFO" | jq -r '.status')

if [ "$AIRFLOW_STATUS" != "RUNNING" ]; then
    echo -e "${YELLOW}⚠️  Airflow кластер ещё не готов (статус: $AIRFLOW_STATUS)${NC}"
    echo -e "${YELLOW}Дождитесь статуса RUNNING и запустите скрипт снова${NC}"
    exit 1
fi

# Получаем webserver URL
AIRFLOW_HOST=$(yc airflow cluster get $AIRFLOW_CLUSTER_ID --format json | jq -r '.config.webserver.url // empty')

if [ -z "$AIRFLOW_HOST" ]; then
    AIRFLOW_HOST=$(yc airflow cluster list-hosts $AIRFLOW_CLUSTER_ID --format json 2>/dev/null | jq -r '.[0].name // empty')
    
    if [ -z "$AIRFLOW_HOST" ]; then
        echo -e "${RED}❌ Не удалось получить Airflow URL${NC}"
        exit 1
    fi
fi

AIRFLOW_URL="https://${AIRFLOW_HOST}"
echo -e "${GREEN}✅ Airflow URL: $AIRFLOW_URL${NC}"

cd ..

# ========================================
# Проверка наличия DAG
# ========================================

DAG_ID="fish_classification_training"

echo -e "${BLUE}🔍 Проверка наличия DAG...${NC}"

DAG_INFO=$(curl -s -X GET \
    "${AIRFLOW_URL}/api/v1/dags/${DAG_ID}" \
    -H "Content-Type: application/json" \
    -u "admin:${AIRFLOW_ADMIN_PASSWORD}" \
    --insecure 2>/dev/null)

DAG_EXISTS=$(echo "$DAG_INFO" | jq -r '.dag_id // empty')

if [ -z "$DAG_EXISTS" ]; then
    echo -e "${RED}❌ DAG '$DAG_ID' не найден в Airflow${NC}"
    echo -e "${YELLOW}Убедитесь, что DAG загружен в S3 и Airflow успел его прочитать${NC}"
    exit 1
fi

IS_PAUSED=$(echo "$DAG_INFO" | jq -r '.is_paused')

if [ "$IS_PAUSED" = "true" ]; then
    echo -e "${YELLOW}⚠️  DAG на паузе, снимаем паузу...${NC}"
    
    curl -s -X PATCH \
        "${AIRFLOW_URL}/api/v1/dags/${DAG_ID}" \
        -H "Content-Type: application/json" \
        -u "admin:${AIRFLOW_ADMIN_PASSWORD}" \
        -d '{"is_paused": false}' \
        --insecure > /dev/null 2>&1
    
    echo -e "${GREEN}✅ Пауза снята${NC}"
fi

echo -e "${GREEN}✅ DAG найден и активен${NC}"

# ========================================
# Запуск DAG
# ========================================

echo -e "${BLUE}🚀 Запуск DAG...${NC}"

# Генерируем уникальный run_id
RUN_ID="manual_$(date +%Y%m%d_%H%M%S)"

TRIGGER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${AIRFLOW_URL}/api/v1/dags/${DAG_ID}/dagRuns" \
    -H "Content-Type: application/json" \
    -u "admin:${AIRFLOW_ADMIN_PASSWORD}" \
    -d "{
        \"dag_run_id\": \"$RUN_ID\",
        \"conf\": {}
    }" \
    --insecure 2>/dev/null)

HTTP_CODE=$(echo "$TRIGGER_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$TRIGGER_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    echo -e "${GREEN}✅ DAG успешно запущен!${NC}"
    echo ""
    
    DAG_RUN_ID=$(echo "$RESPONSE_BODY" | jq -r '.dag_run_id')
    EXECUTION_DATE=$(echo "$RESPONSE_BODY" | jq -r '.execution_date')
    
    echo -e "${BLUE}📊 Информация о запуске:${NC}"
    echo -e "  DAG Run ID: $DAG_RUN_ID"
    echo -e "  Execution Date: $EXECUTION_DATE"
    echo -e "  URL: ${AIRFLOW_URL}/dags/${DAG_ID}/grid?dag_run_id=${DAG_RUN_ID}"
    
else
    echo -e "${RED}❌ Ошибка запуска DAG (HTTP $HTTP_CODE)${NC}"
    echo -e "${YELLOW}Ответ сервера:${NC}"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    exit 1
fi

# ========================================
# Мониторинг выполнения
# ========================================

echo ""
echo -e "${BLUE}📊 Мониторинг выполнения DAG...${NC}"
echo -e "${YELLOW}(Нажмите Ctrl+C для выхода из мониторинга)${NC}"
echo ""

while true; do
    sleep 10
    
    RUN_INFO=$(curl -s -X GET \
        "${AIRFLOW_URL}/api/v1/dags/${DAG_ID}/dagRuns/${DAG_RUN_ID}" \
        -H "Content-Type: application/json" \
        -u "admin:${AIRFLOW_ADMIN_PASSWORD}" \
        --insecure 2>/dev/null)
    
    STATE=$(echo "$RUN_INFO" | jq -r '.state')
    
    echo -e "$(date '+%H:%M:%S') - Статус: $STATE"
    
    if [ "$STATE" = "success" ]; then
        echo ""
        echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ✅ Обучение завершено успешно!       ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${BLUE}📊 Проверьте результаты:${NC}"
        echo -e "  MLflow: $(cd terraform && terraform output -raw mlflow_url)"
        echo -e "  Airflow: ${AIRFLOW_URL}/dags/${DAG_ID}/grid?dag_run_id=${DAG_RUN_ID}"
        break
    elif [ "$STATE" = "failed" ]; then
        echo ""
        echo -e "${RED}╔════════════════════════════════════════╗${NC}"
        echo -e "${RED}║  ❌ Обучение завершилось с ошибкой    ║${NC}"
        echo -e "${RED}╚════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${YELLOW}Проверьте логи в Airflow UI:${NC}"
        echo -e "  ${AIRFLOW_URL}/dags/${DAG_ID}/grid?dag_run_id=${DAG_RUN_ID}"
        exit 1
    fi
done

echo ""
