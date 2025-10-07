#!/bin/bash

# ========================================
# 📊 Мониторинг развёртывания Airflow
# ========================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                            ║${NC}"
echo -e "${CYAN}║     📊 МОНИТОРИНГ РАЗВЁРТЫВАНИЯ AIRFLOW 📊               ║${NC}"
echo -e "${CYAN}║                                                            ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Получаем Cluster ID из Terraform
cd terraform 2>/dev/null || cd ../terraform 2>/dev/null || {
    echo -e "${RED}❌ Не найдена папка terraform${NC}"
    exit 1
}

echo -e "${BLUE}🔍 Поиск Airflow кластера...${NC}"
echo ""

# Ждём появления кластера
MAX_WAIT=60
WAITED=0
CLUSTER_ID=""

while [ $WAITED -lt $MAX_WAIT ]; do
    CLUSTER_ID=$(yc airflow cluster list --format json 2>/dev/null | jq -r '.[0].id // empty')
    
    if [ ! -z "$CLUSTER_ID" ]; then
        echo -e "${GREEN}✅ Кластер найден: $CLUSTER_ID${NC}"
        break
    fi
    
    echo -e "$(date '+%H:%M:%S') - Ожидание создания кластера..."
    sleep 5
    WAITED=$((WAITED + 5))
done

if [ -z "$CLUSTER_ID" ]; then
    echo -e "${YELLOW}⚠️  Кластер ещё не создан. Проверьте логи:${NC}"
    echo -e "   tail -f /tmp/airflow_deploy_fixed.log"
    exit 0
fi

echo ""
echo -e "${BLUE}⏱️  Мониторинг статуса кластера...${NC}"
echo -e "${YELLOW}Это займёт ~15-20 минут${NC}"
echo ""

START_TIME=$(date +%s)

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    MINUTES=$((ELAPSED / 60))
    SECONDS=$((ELAPSED % 60))
    
    STATUS=$(yc airflow cluster get "$CLUSTER_ID" --format json 2>/dev/null | jq -r '.status // "UNKNOWN"')
    HEALTH=$(yc airflow cluster get "$CLUSTER_ID" --format json 2>/dev/null | jq -r '.health // "unknown"')
    
    echo -e "$(date '+%H:%M:%S') [${MINUTES}m ${SECONDS}s] - Status: ${CYAN}$STATUS${NC} | Health: ${CYAN}$HEALTH${NC}"
    
    if [ "$STATUS" = "RUNNING" ] && [ "$HEALTH" = "ALIVE" ]; then
        echo ""
        echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║                                                            ║${NC}"
        echo -e "${GREEN}║     ✅ AIRFLOW КЛАСТЕР ГОТОВ! ✅                          ║${NC}"
        echo -e "${GREEN}║                                                            ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        
        # Получаем URL
        WEBSERVER_URL=$(yc airflow cluster get "$CLUSTER_ID" --format json 2>/dev/null | jq -r '.config.webserver.url // "N/A"')
        
        echo -e "${BLUE}📊 Информация о кластере:${NC}"
        echo -e "  Cluster ID: ${CYAN}$CLUSTER_ID${NC}"
        echo -e "  Status: ${GREEN}$STATUS${NC}"
        echo -e "  Health: ${GREEN}$HEALTH${NC}"
        echo -e "  Webserver URL: ${CYAN}https://$WEBSERVER_URL${NC}"
        echo -e "  Время создания: ${CYAN}${MINUTES}m ${SECONDS}s${NC}"
        echo ""
        
        echo -e "${BLUE}🎯 Следующие шаги:${NC}"
        echo -e "  1. Переменные автоматически доступны через Lockbox"
        echo -e "  2. Откройте Airflow UI: ${CYAN}https://$WEBSERVER_URL${NC}"
        echo -e "  3. Логин: ${CYAN}admin${NC}"
        echo -e "  4. Пароль: ${CYAN}(из terraform.tfvars)${NC}"
        echo -e "  5. Проверьте DAG: ${CYAN}fish_classification_training${NC}"
        echo -e "  6. Запустите обучение: ${CYAN}./scripts/trigger_training_dag.sh${NC}"
        echo ""
        
        break
    fi
    
    if [ "$STATUS" = "ERROR" ]; then
        echo ""
        echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║                                                            ║${NC}"
        echo -e "${RED}║     ❌ ОШИБКА СОЗДАНИЯ КЛАСТЕРА ❌                        ║${NC}"
        echo -e "${RED}║                                                            ║${NC}"
        echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${YELLOW}Проверьте логи:${NC}"
        echo -e "  tail -100 /tmp/airflow_deploy_fixed.log"
        echo ""
        exit 1
    fi
    
    sleep 30
done

cd ..

echo -e "${GREEN}✨ Готово!${NC}"
