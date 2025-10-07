#!/bin/bash

# ========================================
# Скрипт для развертывания Grafana
# ========================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}📊 Grafana Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Переход в директорию Terraform
cd "$TERRAFORM_DIR"

# Проверка наличия конфигурации
if [ ! -f "grafana.tf" ]; then
    echo -e "${RED}❌ Error: grafana.tf not found!${NC}"
    exit 1
fi

# Проверка инициализации Terraform
if [ ! -d ".terraform" ]; then
    echo -e "${YELLOW}🔧 Initializing Terraform...${NC}"
    terraform init
fi

# План развертывания
echo -e "${YELLOW}📋 Planning Grafana deployment...${NC}"
terraform plan -target=yandex_compute_instance.grafana

# Подтверждение
echo ""
read -p "$(echo -e ${YELLOW}Do you want to deploy Grafana? [y/N]:${NC} )" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ Deployment cancelled${NC}"
    exit 1
fi

# Развертывание
echo -e "${GREEN}🚀 Deploying Grafana...${NC}"
terraform apply -target=yandex_compute_instance.grafana -auto-approve

# Получение outputs
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Grafana Deployed Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

GRAFANA_URL=$(terraform output -raw grafana_url 2>/dev/null || echo "N/A")
GRAFANA_IP=$(terraform output -raw grafana_external_ip 2>/dev/null || echo "N/A")

echo -e "${GREEN}📊 Grafana URL:${NC} $GRAFANA_URL"
echo -e "${GREEN}🌐 External IP:${NC} $GRAFANA_IP"
echo -e "${GREEN}👤 Username:${NC} admin"
echo -e "${GREEN}🔑 Password:${NC} admin ${YELLOW}(change on first login)${NC}"
echo ""
echo -e "${YELLOW}⏳ Grafana is starting... This may take 2-3 minutes${NC}"
echo -e "${YELLOW}📝 Check setup logs: ssh ubuntu@$GRAFANA_IP 'tail -f /var/log/grafana-setup.log'${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"

