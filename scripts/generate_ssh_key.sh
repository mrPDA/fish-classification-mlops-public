#!/bin/bash

# ========================================
# 🔑 SSH Key Generation Script
# ========================================
# Генерация SSH ключа для DataProc кластеров

set -e

# Цвета
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🔑 Генерация SSH ключа для DataProc...${NC}"

# Создаём директорию для ключей
mkdir -p ssh_keys

# Проверяем существование ключа
if [ -f "ssh_keys/dataproc" ]; then
    echo -e "${YELLOW}⚠️  SSH ключ уже существует${NC}"
    echo -e "${YELLOW}Используем существующий ключ: ssh_keys/dataproc${NC}"
else
    # Генерируем новый ключ
    echo -e "${BLUE}🔧 Генерация нового SSH ключа...${NC}"
    ssh-keygen -t rsa -b 2048 -f ssh_keys/dataproc -N "" -C "dataproc@fish-ml"
    echo -e "${GREEN}✅ SSH ключ создан${NC}"
fi

# Выводим публичный ключ
echo ""
echo -e "${GREEN}📋 Публичный SSH ключ:${NC}"
cat ssh_keys/dataproc.pub
echo ""

# Сохраняем в переменную окружения для использования
export DATAPROC_SSH_KEY=$(cat ssh_keys/dataproc.pub)

echo -e "${GREEN}✅ SSH ключ готов к использованию${NC}"
echo -e "${BLUE}Путь: ssh_keys/dataproc.pub${NC}"
echo ""
