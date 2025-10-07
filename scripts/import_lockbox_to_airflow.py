#!/usr/bin/env python3
"""
Автоматический импорт переменных из Yandex Lockbox в Airflow Variables

Этот скрипт:
1. Получает все переменные из Lockbox
2. Импортирует их в Airflow Variables через REST API
3. Может быть запущен автоматически после развёртывания Airflow
"""

import os
import sys
import json
import requests
import subprocess
from typing import Dict, List
import time


def get_lockbox_variables(secret_id: str) -> Dict[str, str]:
    """
    Получает все переменные из Lockbox через yc CLI
    """
    print(f"📦 Fetching variables from Lockbox: {secret_id}")
    
    try:
        result = subprocess.run(
            ['yc', 'lockbox', 'payload', 'get', secret_id, '--format', 'json'],
            capture_output=True,
            text=True,
            check=True
        )
        
        payload = json.loads(result.stdout)
        variables = {}
        
        for entry in payload.get('entries', []):
            key = entry.get('key')
            value = entry.get('text_value')
            if key and value:
                variables[key] = value
        
        print(f"✅ Found {len(variables)} variables in Lockbox")
        return variables
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error fetching Lockbox: {e.stderr}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing Lockbox response: {e}")
        sys.exit(1)


def wait_for_airflow(airflow_url: str, timeout: int = 300) -> bool:
    """
    Ждёт, пока Airflow станет доступен
    """
    print(f"⏳ Waiting for Airflow at {airflow_url} (timeout: {timeout}s)")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{airflow_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Airflow is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(10)
        print("   Still waiting...")
    
    print(f"❌ Airflow did not become ready within {timeout}s")
    return False


def import_variables_to_airflow(
    airflow_url: str,
    username: str,
    password: str,
    variables: Dict[str, str]
) -> None:
    """
    Импортирует переменные в Airflow через REST API
    """
    print(f"\n📤 Importing {len(variables)} variables to Airflow...")
    
    # Создаём сессию с аутентификацией
    session = requests.Session()
    session.auth = (username, password)
    
    # Проверяем доступ
    try:
        response = session.get(f"{airflow_url}/api/v1/variables")
        response.raise_for_status()
        print(f"✅ Successfully authenticated to Airflow API")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to authenticate to Airflow API: {e}")
        sys.exit(1)
    
    # Импортируем переменные
    success_count = 0
    error_count = 0
    
    for key, value in variables.items():
        try:
            # Проверяем, существует ли переменная
            check_response = session.get(f"{airflow_url}/api/v1/variables/{key}")
            
            if check_response.status_code == 200:
                # Переменная существует, обновляем
                response = session.patch(
                    f"{airflow_url}/api/v1/variables/{key}",
                    json={"key": key, "value": value},
                    headers={"Content-Type": "application/json"}
                )
                action = "Updated"
            else:
                # Переменная не существует, создаём
                response = session.post(
                    f"{airflow_url}/api/v1/variables",
                    json={"key": key, "value": value},
                    headers={"Content-Type": "application/json"}
                )
                action = "Created"
            
            if response.status_code in [200, 201]:
                print(f"   ✅ {action}: {key}")
                success_count += 1
            else:
                print(f"   ❌ Failed to import {key}: {response.status_code} - {response.text}")
                error_count += 1
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error importing {key}: {e}")
            error_count += 1
    
    print(f"\n📊 Import Summary:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Errors: {error_count}")
    
    if error_count > 0:
        sys.exit(1)


def main():
    """
    Основная функция
    """
    print("=" * 80)
    print("🔐 Lockbox → Airflow Variables Import Tool")
    print("=" * 80)
    
    # Получаем параметры из переменных окружения или аргументов
    lockbox_secret_id = os.getenv('LOCKBOX_SECRET_ID')
    airflow_url = os.getenv('AIRFLOW_URL')
    airflow_username = os.getenv('AIRFLOW_USERNAME', 'admin')
    airflow_password = os.getenv('AIRFLOW_PASSWORD')
    
    # Проверяем обязательные параметры
    if not lockbox_secret_id:
        print("❌ LOCKBOX_SECRET_ID environment variable is required")
        print("   Example: export LOCKBOX_SECRET_ID=e6q1el9pcc78q3kmuhcd")
        sys.exit(1)
    
    if not airflow_url:
        print("❌ AIRFLOW_URL environment variable is required")
        print("   Example: export AIRFLOW_URL=https://c-xxx.airflow.yandexcloud.net")
        sys.exit(1)
    
    if not airflow_password:
        print("❌ AIRFLOW_PASSWORD environment variable is required")
        print("   Example: export AIRFLOW_PASSWORD=your_password")
        sys.exit(1)
    
    print(f"\n📋 Configuration:")
    print(f"   Lockbox Secret ID: {lockbox_secret_id}")
    print(f"   Airflow URL: {airflow_url}")
    print(f"   Airflow Username: {airflow_username}")
    print()
    
    # 1. Ждём, пока Airflow станет доступен
    if not wait_for_airflow(airflow_url):
        sys.exit(1)
    
    # 2. Получаем переменные из Lockbox
    variables = get_lockbox_variables(lockbox_secret_id)
    
    # 3. Импортируем переменные в Airflow
    import_variables_to_airflow(
        airflow_url=airflow_url,
        username=airflow_username,
        password=airflow_password,
        variables=variables
    )
    
    print("\n" + "=" * 80)
    print("✅ Import completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
