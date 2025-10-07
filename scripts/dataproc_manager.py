#!/usr/bin/env python3
"""
DataProc Cluster Manager
Управление DataProc кластерами через Yandex Cloud REST API
Используется в Airflow DAG для создания/удаления кластеров
"""

import os
import sys
import time
import json
import requests
from typing import Dict, Optional


class DataProcManager:
    """Менеджер для управления DataProc кластерами через REST API"""
    
    def __init__(self, iam_token: str, folder_id: str):
        """
        Args:
            iam_token: IAM токен для аутентификации
            folder_id: ID каталога Yandex Cloud
        """
        self.iam_token = iam_token
        self.folder_id = folder_id
        self.base_url = "https://dataproc.api.cloud.yandex.net/dataproc/v1"
        self.headers = {
            "Authorization": f"Bearer {iam_token}",
            "Content-Type": "application/json"
        }
    
    def create_cluster(
        self,
        cluster_name: str,
        zone: str,
        subnet_id: str,
        service_account_id: str,
        security_group_id: str,
        s3_bucket: str,
        ssh_public_keys: list,
        description: str = "DataProc cluster for ML training"
    ) -> str:
        """
        Создаёт DataProc кластер
        
        Returns:
            cluster_id: ID созданного кластера
        """
        print(f"🚀 Создание DataProc кластера: {cluster_name}")
        
        # Конфигурация кластера
        cluster_config = {
            "folderId": self.folder_id,
            "name": cluster_name,
            "description": description,
            "labels": {
                "created_by": "airflow",
                "purpose": "ml_training"
            },
            "configSpec": {
                "versionId": "2.1",  # Hadoop 3.2, Spark 3.0
                "hadoop": {
                    "services": ["HDFS", "YARN", "SPARK", "LIVY"],
                    "properties": {
                        "yarn:yarn.resourcemanager.am.max-attempts": "5",
                        "spark:spark.sql.warehouse.dir": f"s3a://{s3_bucket}/spark-warehouse/"
                    },
                    "sshPublicKeys": ssh_public_keys
                },
                "subclustersSpec": [
                    {
                        "name": "masternode",
                        "role": "MASTERNODE",
                        "resources": {
                            "resourcePresetId": "s2.small",  # 4 vCPU, 16 GB RAM
                            "diskTypeId": "network-ssd",
                            "diskSize": "107374182400"  # 100 GB
                        },
                        "subnetId": subnet_id,
                        "hostsCount": "1"
                    },
                    {
                        "name": "datanode",
                        "role": "DATANODE",
                        "resources": {
                            "resourcePresetId": "s2.small",  # 4 vCPU, 16 GB RAM
                            "diskTypeId": "network-ssd",
                            "diskSize": "107374182400"  # 100 GB
                        },
                        "subnetId": subnet_id,
                        "hostsCount": "2"
                    }
                ]
            },
            "zoneId": zone,
            "serviceAccountId": service_account_id,
            "bucket": s3_bucket,
            "uiProxy": True,
            "securityGroupIds": [security_group_id],
            "deletionProtection": False
        }
        
        # Отправка запроса
        url = f"{self.base_url}/clusters"
        print(f"📤 POST {url}")
        print(f"📋 Config: {json.dumps(cluster_config, indent=2)}")
        
        response = requests.post(
            url,
            headers=self.headers,
            json=cluster_config,
            timeout=30
        )
        
        if response.status_code not in [200, 201]:
            error_msg = f"Ошибка создания кластера: {response.status_code} - {response.text}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        
        operation = response.json()
        operation_id = operation.get("id")
        print(f"✅ Операция создания запущена: {operation_id}")
        
        # Ожидание завершения операции
        cluster_id = self._wait_operation(operation_id)
        print(f"✅ Кластер создан: {cluster_id}")
        
        return cluster_id
    
    def get_cluster_status(self, cluster_id: str) -> Dict:
        """
        Получает статус кластера
        
        Returns:
            dict с полями: status, health
        """
        url = f"{self.base_url}/clusters/{cluster_id}"
        response = requests.get(url, headers=self.headers, timeout=10)
        
        if response.status_code != 200:
            raise Exception(f"Ошибка получения статуса: {response.status_code} - {response.text}")
        
        cluster = response.json()
        return {
            "status": cluster.get("status"),
            "health": cluster.get("health"),
            "name": cluster.get("name"),
            "created_at": cluster.get("createdAt")
        }
    
    def wait_cluster_ready(self, cluster_id: str, timeout: int = 1800) -> bool:
        """
        Ожидает готовности кластера
        
        Args:
            cluster_id: ID кластера
            timeout: Таймаут в секундах (по умолчанию 30 минут)
        
        Returns:
            True если кластер готов, иначе Exception
        """
        print(f"⏳ Ожидание готовности кластера {cluster_id}...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status_info = self.get_cluster_status(cluster_id)
            status = status_info["status"]
            health = status_info["health"]
            
            print(f"  Status: {status}, Health: {health}")
            
            if status == "RUNNING" and health == "ALIVE":
                elapsed = int(time.time() - start_time)
                print(f"✅ Кластер готов! (заняло {elapsed} секунд)")
                return True
            
            if status in ["ERROR", "STOPPING", "STOPPED"]:
                raise Exception(f"Кластер в неожиданном состоянии: {status}")
            
            time.sleep(30)  # Проверяем каждые 30 секунд
        
        raise Exception(f"Таймаут ожидания готовности кластера ({timeout} сек)")
    
    def delete_cluster(self, cluster_id: str) -> None:
        """Удаляет DataProc кластер"""
        print(f"🗑️  Удаление DataProc кластера: {cluster_id}")
        
        url = f"{self.base_url}/clusters/{cluster_id}"
        response = requests.delete(url, headers=self.headers, timeout=30)
        
        if response.status_code not in [200, 204]:
            error_msg = f"Ошибка удаления кластера: {response.status_code} - {response.text}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        
        operation = response.json()
        operation_id = operation.get("id")
        print(f"✅ Операция удаления запущена: {operation_id}")
        
        # Ожидание завершения операции
        self._wait_operation(operation_id)
        print(f"✅ Кластер удалён: {cluster_id}")
    
    def _wait_operation(self, operation_id: str, timeout: int = 3600) -> Optional[str]:
        """
        Ожидает завершения операции
        
        Returns:
            resource_id если операция успешна
        """
        url = f"https://operation.api.cloud.yandex.net/operations/{operation_id}"
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                raise Exception(f"Ошибка проверки операции: {response.status_code}")
            
            operation = response.json()
            done = operation.get("done", False)
            
            if done:
                if "error" in operation:
                    error = operation["error"]
                    raise Exception(f"Операция завершилась с ошибкой: {error}")
                
                # Извлекаем ID ресурса из metadata или response
                metadata = operation.get("metadata", {})
                response_data = operation.get("response", {})
                
                cluster_id = metadata.get("clusterId") or response_data.get("clusterId")
                return cluster_id
            
            time.sleep(10)  # Проверяем каждые 10 секунд
        
        raise Exception(f"Таймаут ожидания операции ({timeout} сек)")
    
    @staticmethod
    def get_iam_token_from_sa_key(sa_key_json: str) -> str:
        """
        Получает IAM токен из JSON ключа сервисного аккаунта
        
        Args:
            sa_key_json: JSON строка с ключом сервисного аккаунта
        
        Returns:
            IAM токен
        """
        import jwt
        
        sa_key = json.loads(sa_key_json)
        
        now = int(time.time())
        payload = {
            'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            'iss': sa_key['service_account_id'],
            'iat': now,
            'exp': now + 3600
        }
        
        # Создаём JWT
        encoded_token = jwt.encode(
            payload,
            sa_key['private_key'],
            algorithm='PS256',
            headers={'kid': sa_key['id']}
        )
        
        # Обмениваем JWT на IAM токен
        response = requests.post(
            'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            json={'jwt': encoded_token},
            timeout=10
        )
        
        if response.status_code != 200:
            raise Exception(f"Ошибка получения IAM токена: {response.status_code} - {response.text}")
        
        return response.json()['iamToken']


def main():
    """CLI для тестирования"""
    import argparse
    
    parser = argparse.ArgumentParser(description="DataProc Cluster Manager")
    parser.add_argument("action", choices=["create", "delete", "status"], help="Действие")
    parser.add_argument("--cluster-id", help="ID кластера (для delete/status)")
    parser.add_argument("--cluster-name", help="Имя кластера (для create)")
    parser.add_argument("--sa-key-file", required=True, help="Путь к JSON ключу сервисного аккаунта")
    parser.add_argument("--folder-id", required=True, help="ID каталога")
    parser.add_argument("--zone", default="ru-central1-a", help="Зона")
    parser.add_argument("--subnet-id", help="ID подсети")
    parser.add_argument("--service-account-id", help="ID сервисного аккаунта")
    parser.add_argument("--security-group-id", help="ID группы безопасности")
    parser.add_argument("--s3-bucket", help="Имя S3 бакета")
    parser.add_argument("--ssh-key", help="Путь к публичному SSH ключу")
    
    args = parser.parse_args()
    
    # Читаем ключ сервисного аккаунта
    with open(args.sa_key_file, 'r') as f:
        sa_key_json = f.read()
    
    # Получаем IAM токен
    print("🔑 Получение IAM токена...")
    iam_token = DataProcManager.get_iam_token_from_sa_key(sa_key_json)
    print("✅ IAM токен получен")
    
    # Создаём менеджер
    manager = DataProcManager(iam_token, args.folder_id)
    
    # Выполняем действие
    if args.action == "create":
        # Читаем SSH ключ
        with open(args.ssh_key, 'r') as f:
            ssh_key = f.read().strip()
        
        cluster_id = manager.create_cluster(
            cluster_name=args.cluster_name,
            zone=args.zone,
            subnet_id=args.subnet_id,
            service_account_id=args.service_account_id,
            security_group_id=args.security_group_id,
            s3_bucket=args.s3_bucket,
            ssh_public_keys=[ssh_key]
        )
        
        print(f"\n✅ Кластер создан: {cluster_id}")
        print(f"⏳ Ожидание готовности...")
        manager.wait_cluster_ready(cluster_id)
        print(f"✅ Кластер готов к работе!")
        
    elif args.action == "delete":
        manager.delete_cluster(args.cluster_id)
        print(f"✅ Кластер удалён")
        
    elif args.action == "status":
        status = manager.get_cluster_status(args.cluster_id)
        print(f"\n📊 Статус кластера:")
        print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
