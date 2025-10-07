#!/bin/bash

# ========================================
# 🔐 Развёртывание Airflow с Lockbox автоматизацией
# ========================================

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                            ║${NC}"
echo -e "${CYAN}║     🔐 РАЗВЁРТЫВАНИЕ С LOCKBOX АВТОМАТИЗАЦИЕЙ 🔐         ║${NC}"
echo -e "${CYAN}║                                                            ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ========================================
# Проверка наличия Terraform
# ========================================

if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Terraform не установлен${NC}"
    exit 1
fi

# ========================================
# Переход в директорию terraform
# ========================================

cd terraform 2>/dev/null || cd ../terraform 2>/dev/null || {
    echo -e "${RED}❌ Не найдена папка terraform${NC}"
    exit 1
}

echo -e "${BLUE}📊 Текущая директория: $(pwd)${NC}"
echo ""

# ========================================
# Проверка наличия lockbox.tf
# ========================================

if [ ! -f "lockbox.tf" ]; then
    echo -e "${RED}❌ Файл lockbox.tf не найден${NC}"
    echo -e "${YELLOW}Убедитесь, что lockbox.tf создан в terraform/${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Файл lockbox.tf найден${NC}"
echo ""

# ========================================
# Terraform init (обновление провайдеров)
# ========================================

echo -e "${BLUE}🔧 Инициализация Terraform...${NC}"
terraform init -upgrade > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Terraform инициализирован${NC}"
else
    echo -e "${RED}❌ Ошибка инициализации Terraform${NC}"
    exit 1
fi
echo ""

# ========================================
# Terraform plan для Lockbox
# ========================================

echo -e "${BLUE}📋 Проверка плана развёртывания...${NC}"
echo ""

terraform plan \
    -target=yandex_lockbox_secret.airflow_variables \
    -target=yandex_lockbox_secret_version.airflow_variables_v1 \
    -target=yandex_lockbox_secret_iam_binding.airflow_access \
    -target=yandex_airflow_cluster.main \
    -out=/tmp/lockbox_plan.tfplan

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ Ошибка при создании плана${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}📊 План создан. Проверьте изменения выше.${NC}"
echo ""
read -p "Продолжить развёртывание? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⚠️  Развёртывание отменено${NC}"
    rm -f /tmp/lockbox_plan.tfplan
    exit 0
fi

# ========================================
# Terraform apply
# ========================================

echo ""
echo -e "${BLUE}🚀 Применение изменений...${NC}"
echo -e "${YELLOW}Это может занять 15-20 минут для Airflow кластера${NC}"
echo ""

terraform apply /tmp/lockbox_plan.tfplan

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Изменения успешно применены!${NC}"
else
    echo ""
    echo -e "${RED}❌ Ошибка при применении изменений${NC}"
    rm -f /tmp/lockbox_plan.tfplan
    exit 1
fi

rm -f /tmp/lockbox_plan.tfplan

# ========================================
# Получение информации о Lockbox
# ========================================

echo ""
echo -e "${BLUE}📊 Информация о Lockbox:${NC}"
echo ""

LOCKBOX_ID=$(terraform output -raw lockbox_secret_id 2>/dev/null)
LOCKBOX_NAME=$(terraform output -raw lockbox_secret_name 2>/dev/null)
VARS_COUNT=$(terraform output -raw lockbox_variables_count 2>/dev/null)

echo -e "  Secret ID: ${CYAN}$LOCKBOX_ID${NC}"
echo -e "  Secret Name: ${CYAN}$LOCKBOX_NAME${NC}"
echo -e "  Variables Count: ${CYAN}$VARS_COUNT${NC}"

# ========================================
# Проверка статуса Airflow
# ========================================

echo ""
echo -e "${BLUE}📊 Проверка статуса Airflow кластера...${NC}"
echo ""

AIRFLOW_ID=$(terraform output -raw airflow_cluster_id 2>/dev/null)

if [ -z "$AIRFLOW_ID" ]; then
    echo -e "${YELLOW}⚠️  Airflow кластер ещё не создан или импортирован${NC}"
else
    AIRFLOW_STATUS=$(yc airflow cluster get $AIRFLOW_ID --format json 2>/dev/null | jq -r '.status')
    AIRFLOW_HEALTH=$(yc airflow cluster get $AIRFLOW_ID --format json 2>/dev/null | jq -r '.health // "unknown"')
    
    echo -e "  Cluster ID: ${CYAN}$AIRFLOW_ID${NC}"
    echo -e "  Status: ${CYAN}$AIRFLOW_STATUS${NC}"
    echo -e "  Health: ${CYAN}$AIRFLOW_HEALTH${NC}"
fi

cd ..

# ========================================
# Итоги
# ========================================

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║     ✅ LOCKBOX РАЗВЁРНУТ И НАСТРОЕН! ✅                   ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}📋 Что сделано:${NC}"
echo -e "  ✅ Создан Lockbox секрет с $VARS_COUNT переменными"
echo -e "  ✅ Настроены права доступа для Airflow SA"
echo -e "  ✅ Airflow кластер обновлён для использования Lockbox"
echo ""

echo -e "${BLUE}🎯 Следующие шаги:${NC}"
echo ""

if [ "$AIRFLOW_STATUS" = "RUNNING" ]; then
    echo -e "${GREEN}✅ Airflow готов к использованию!${NC}"
    echo ""
    echo -e "  1. Переменные автоматически доступны в DAG:"
    echo -e "     ${CYAN}from airflow.models import Variable${NC}"
    echo -e "     ${CYAN}cloud_id = Variable.get('CLOUD_ID')${NC}"
    echo ""
    echo -e "  2. Запустите обучение:"
    echo -e "     ${CYAN}./scripts/trigger_training_dag.sh${NC}"
elif [ "$AIRFLOW_STATUS" = "CREATING" ]; then
    echo -e "${YELLOW}⏱️  Airflow кластер создаётся...${NC}"
    echo ""
    echo -e "  1. Дождитесь статуса RUNNING:"
    echo -e "     ${CYAN}yc airflow cluster get $AIRFLOW_ID${NC}"
    echo ""
    echo -e "  2. Или запустите автоматизацию:"
    echo -e "     ${CYAN}./scripts/auto_deploy_and_train.sh${NC}"
else
    echo -e "${YELLOW}⚠️  Проверьте статус Airflow кластера${NC}"
fi

echo ""
echo -e "${BLUE}📚 Документация:${NC}"
echo -e "  • terraform/lockbox.tf - конфигурация Lockbox"
echo -e "  • docs/AIRFLOW_VARIABLES_METHODS.md - все способы"
echo ""
