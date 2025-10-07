#!/bin/bash

# ========================================
# 🔧 Автоматический импорт переменных в Airflow
# ========================================

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 Импорт переменных в Airflow...${NC}"

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

# Получаем webserver URL из кластера
AIRFLOW_HOST=$(yc airflow cluster get $AIRFLOW_CLUSTER_ID --format json | jq -r '.config.webserver.url // empty')

if [ -z "$AIRFLOW_HOST" ]; then
    echo -e "${YELLOW}⚠️  Webserver URL не найден в конфигурации кластера${NC}"
    echo -e "${YELLOW}Попробуем получить через список хостов...${NC}"
    
    # Альтернативный способ - через хосты
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
# Подготовка переменных
# ========================================

echo -e "${BLUE}📝 Подготовка переменных...${NC}"

# Запускаем setup_airflow.sh для генерации переменных
./scripts/setup_airflow.sh > /dev/null 2>&1 || {
    echo -e "${YELLOW}⚠️  Ошибка при генерации переменных, продолжаем...${NC}"
}

# Проверяем, что файл переменных создан
if [ ! -f "/tmp/airflow_variables.json" ]; then
    echo -e "${RED}❌ Файл переменных не создан${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Переменные подготовлены${NC}"

# ========================================
# Импорт переменных через Airflow REST API
# ========================================

echo -e "${BLUE}📤 Импорт переменных через REST API...${NC}"

# Читаем переменные и импортируем каждую
IMPORTED=0
FAILED=0

while IFS= read -r line; do
    # Пропускаем пустые строки и комментарии
    if [ -z "$line" ] || [[ "$line" =~ ^[[:space:]]*# ]]; then
        continue
    fi
    
    # Извлекаем ключ и значение
    KEY=$(echo "$line" | jq -r 'keys[0]' 2>/dev/null)
    VALUE=$(echo "$line" | jq -r ".\"$KEY\"" 2>/dev/null)
    
    if [ -z "$KEY" ] || [ "$KEY" = "null" ]; then
        continue
    fi
    
    echo -e "${BLUE}  Импорт: $KEY${NC}"
    
    # Отправляем через API
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
        "${AIRFLOW_URL}/api/v1/variables" \
        -H "Content-Type: application/json" \
        -u "admin:${AIRFLOW_ADMIN_PASSWORD}" \
        -d "{\"key\": \"$KEY\", \"value\": \"$VALUE\"}" \
        --insecure 2>/dev/null)
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
        echo -e "${GREEN}    ✅ Успешно${NC}"
        ((IMPORTED++))
    else
        echo -e "${YELLOW}    ⚠️  Ошибка (HTTP $HTTP_CODE)${NC}"
        ((FAILED++))
    fi
    
done < <(jq -c 'to_entries[] | {(.key): .value}' /tmp/airflow_variables.json)

echo ""
echo -e "${GREEN}✅ Импорт завершён${NC}"
echo -e "  Успешно: $IMPORTED"
echo -e "  Ошибок: $FAILED"

# ========================================
# Проверка импортированных переменных
# ========================================

echo ""
echo -e "${BLUE}🔍 Проверка переменных в Airflow...${NC}"

VARS_RESPONSE=$(curl -s -X GET \
    "${AIRFLOW_URL}/api/v1/variables" \
    -H "Content-Type: application/json" \
    -u "admin:${AIRFLOW_ADMIN_PASSWORD}" \
    --insecure 2>/dev/null)

VARS_COUNT=$(echo "$VARS_RESPONSE" | jq '.total_entries // 0' 2>/dev/null)

echo -e "${GREEN}✅ Всего переменных в Airflow: $VARS_COUNT${NC}"

# ========================================
# Cleanup
# ========================================

rm -f /tmp/airflow_variables.json

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Переменные импортированы!         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📋 Следующие шаги:${NC}"
echo -e "  1. Откройте Airflow UI: $AIRFLOW_URL"
echo -e "  2. Проверьте DAG: fish_classification_training"
echo -e "  3. Запустите обучение: Trigger DAG"
echo ""
