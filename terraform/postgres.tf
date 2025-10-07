# ========================================
# Managed PostgreSQL
# ========================================

resource "yandex_mdb_postgresql_cluster" "main" {
  name        = "${local.project_name}-${local.suffix}-pg"
  environment = upper(var.environment)
  network_id  = data.yandex_vpc_network.default.id

  config {
    version = "15"
    resources {
      resource_preset_id = var.postgres_preset  # s2.micro для экономии
      disk_type_id       = "network-ssd"  # SSD обязателен для s2.micro с 1 хостом
      disk_size          = var.postgres_disk_size  # Нельзя уменьшить размер существующего диска
    }

    # Оптимизация для ML workload
    postgresql_config = {
      max_connections                = 200
      shared_buffers                 = 268435456  # 256MB
      effective_cache_size           = 1073741824 # 1GB
      work_mem                       = 4194304    # 4MB
    }
  }

  # Базы данных
  database {
    name  = "airflow"
    owner = "airflow_user"
  }

  database {
    name  = "mlops"
    owner = "mlops_user"
  }

  # Пользователи
  user {
    name     = "airflow_user"
    password = var.postgres_airflow_password
    permission {
      database_name = "airflow"
    }
  }

  user {
    name     = "mlops_user"
    password = var.postgres_mlops_password
    permission {
      database_name = "mlops"
    }
  }

  # Размещение в зоне
  host {
    zone      = var.zone
    subnet_id = yandex_vpc_subnet.services_subnet.id
    assign_public_ip = false  # Безопасность: доступ только изнутри VPC
  }

  security_group_ids = [yandex_vpc_security_group.services_sg.id]

  # Бэкапы
  maintenance_window {
    type = "WEEKLY"
    day  = "SUN"
    hour = 2
  }

  labels = local.common_labels
}

# Output для подключения
output "postgres_connection_airflow" {
  description = "PostgreSQL connection string for Airflow"
  value = format(
    "postgresql://%s:%s@%s:6432/%s",
    "airflow_user",
    var.postgres_airflow_password,
    yandex_mdb_postgresql_cluster.main.host[0].fqdn,
    "airflow"
  )
  sensitive = true
}

output "postgres_connection_mlops" {
  description = "PostgreSQL connection string for MLOps"
  value = format(
    "postgresql://%s:%s@%s:6432/%s",
    "mlops_user",
    var.postgres_mlops_password,
    yandex_mdb_postgresql_cluster.main.host[0].fqdn,
    "mlops"
  )
  sensitive = true
}

output "postgres_host" {
  description = "PostgreSQL host FQDN"
  value       = yandex_mdb_postgresql_cluster.main.host[0].fqdn
}
