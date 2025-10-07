#!/bin/bash

# ========================================
# 🤖 ПОЛНАЯ АВТОМАТИЗАЦИЯ: Ожидание Airflow → Импорт переменных → Запуск обучения
# ========================================

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

AIRFLOW_CLUSTER_ID="c9qovnmqug9fv5nfdi8j"

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                            ║${NC}"
echo -e "${CYAN}║     🤖 ПОЛНАЯ АВТОМАТИЗАЦИЯ РАЗВЁРТЫВАНИЯ 🤖             ║${NC}"
echo -e "${CYAN}║                                                            ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ========================================
# ШАГ 1: Ожидание готовности Airflow кластера
# ========================================

echo -e "${BLUE}📊 ШАГ 1/3: Ожидание готовности Airflow кластера...${NC}"
echo -e "${YELLOW}Это может занять 15-20 минут${NC}"
echo ""

START_TIME=$(date +%s)
CHECK_INTERVAL=60  # Проверяем каждую минуту

while true; do
    CLUSTER_INFO=$(yc airflow cluster get $AIRFLOW_CLUSTER_ID --format json 2>/dev/null)
    STATUS=$(echo "$CLUSTER_INFO" | jq -r '.status')
    HEALTH=$(echo "$CLUSTER_INFO" | jq -r '.health // "unknown"')
    
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    ELAPSED_MIN=$((ELAPSED / 60))
    
    echo -e "$(date '+%H:%M:%S') - Статус: ${CYAN}$STATUS${NC} | Health: ${CYAN}$HEALTH${NC} | Прошло: ${ELAPSED_MIN} мин"
    
    if [ "$STATUS" = "RUNNING" ] && [ "$HEALTH" = "ALIVE" ]; then
        echo ""
        echo -e "${GREEN}✅ Airflow кластер готов!${NC}"
        echo -e "${GREEN}   Время создания: ${ELAPSED_MIN} минут${NC}"
        break
    elif [ "$STATUS" = "ERROR" ]; then
        echo ""
        echo -e "${RED}❌ Ошибка создания кластера${NC}"
        echo -e "${YELLOW}Проверьте логи:${NC}"
        echo "yc airflow cluster get $AIRFLOW_CLUSTER_ID"
        exit 1
    fi
    
    sleep $CHECK_INTERVAL
done

echo ""
sleep 5

# ========================================
# ШАГ 2: Импорт переменных в Airflow
# ========================================

echo -e "${BLUE}📊 ШАГ 2/3: Импорт переменных в Airflow...${NC}"
echo ""

# Проверяем наличие скрипта
if [ ! -f "./scripts/import_airflow_variables.sh" ]; then
    echo -e "${RED}❌ Скрипт import_airflow_variables.sh не найден${NC}"
    exit 1
fi

# Запускаем импорт переменных
echo -e "${CYAN}Запуск импорта переменных...${NC}"
./scripts/import_airflow_variables.sh

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Переменные успешно импортированы!${NC}"
else
    echo ""
    echo -e "${RED}❌ Ошибка импорта переменных${NC}"
    echo -e "${YELLOW}Попробуйте импортировать вручную:${NC}"
    echo "./scripts/import_airflow_variables.sh"
    exit 1
fi

echo ""
sleep 5

# ========================================
# ШАГ 3: Запуск обучения модели
# ========================================

echo -e "${BLUE}📊 ШАГ 3/3: Запуск обучения модели...${NC}"
echo ""

# Проверяем наличие скрипта
if [ ! -f "./scripts/trigger_training_dag.sh" ]; then
    echo -e "${RED}❌ Скрипт trigger_training_dag.sh не найден${NC}"
    exit 1
fi

# Запускаем обучение
echo -e "${CYAN}Запуск DAG для обучения...${NC}"
./scripts/trigger_training_dag.sh

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Обучение запущено успешно!${NC}"
else
    echo ""
    echo -e "${RED}❌ Ошибка запуска обучения${NC}"
    echo -e "${YELLOW}Попробуйте запустить вручную:${NC}"
    echo "./scripts/trigger_training_dag.sh"
    exit 1
fi

# ========================================
# ЗАВЕРШЕНИЕ
# ========================================

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║     🎉 ВСЁ ГОТОВО! ОБУЧЕНИЕ ЗАПУЩЕНО! 🎉                 ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Получаем Airflow URL
cd terraform 2>/dev/null || cd ../terraform 2>/dev/null
AIRFLOW_HOST=$(yc airflow cluster get $AIRFLOW_CLUSTER_ID --format json 2>/dev/null | jq -r '.config.webserver.url // empty')
if [ -z "$AIRFLOW_HOST" ]; then
    AIRFLOW_HOST=$(yc airflow cluster list-hosts $AIRFLOW_CLUSTER_ID --format json 2>/dev/null | jq -r '.[0].name // empty')
fi
AIRFLOW_URL="https://${AIRFLOW_HOST}"
MLFLOW_URL=$(terraform output -raw mlflow_url 2>/dev/null)
cd ..

echo -e "${BLUE}📊 Мониторинг обучения:${NC}"
echo -e "  • Airflow UI: ${CYAN}${AIRFLOW_URL}${NC}"
echo -e "  • MLflow UI:  ${CYAN}${MLFLOW_URL}${NC}"
echo ""
echo -e "${YELLOW}Логин Airflow:${NC} admin"
echo -e "${YELLOW}Пароль:${NC} (из terraform.tfvars)"
echo ""
echo -e "${BLUE}📝 Следующие шаги:${NC}"
echo -e "  1. Откройте Airflow UI и мониторьте выполнение DAG"
echo -e "  2. Проверяйте метрики в MLflow"
echo -e "  3. После завершения обучения модель будет в MLflow Registry"
echo ""
