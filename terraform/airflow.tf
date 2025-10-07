# ========================================
# Managed Service for Apache Airflow
# ========================================

resource "yandex_airflow_cluster" "main" {
  name        = "${local.project_name}-${local.suffix}-airflow"
  description = "Managed Airflow for ML Pipeline orchestration"
  folder_id   = var.folder_id
  
  subnet_ids         = [yandex_vpc_subnet.services_subnet.id]
  security_group_ids = [yandex_vpc_security_group.services_sg.id]

  # Apache Airflow version
  airflow_version = var.airflow_version

  # Webserver configuration
  webserver = {
    count              = 1
    resource_preset_id = var.airflow_webserver_preset
  }

  # Scheduler configuration
  scheduler = {
    count              = 1
    resource_preset_id = var.airflow_scheduler_preset
  }

  # Workers configuration с автоскейлингом
  worker = {
    min_count          = var.airflow_min_workers
    max_count          = var.airflow_max_workers
    resource_preset_id = var.airflow_worker_preset
  }

  # Code sync - откуда брать DAGs
  code_sync = {
    s3 = {
      bucket = yandex_storage_bucket.data.bucket
    }
  }

  # Python packages (минимальный набор для избежания конфликтов)
  pip_packages = [
    "apache-airflow-providers-yandex",
    "apache-airflow-providers-amazon",
    "boto3",
    "psycopg2-binary",
    "PyJWT",  # Для получения IAM токенов из ключа сервисного аккаунта
    "requests",  # Для HTTP запросов к MLflow API
  ]

  # Airflow configuration (только разрешённые параметры)
  airflow_config = {
    "core" = {
      "load_examples" = "False"
    }
    "webserver" = {
      "expose_config" = "True"
    }
    "scheduler" = {
      "dag_dir_list_interval" = "60"
      "catchup_by_default"    = "False"
    }
  }

  # Service Account для доступа к S3 и другим ресурсам
  service_account_id = yandex_iam_service_account.s3_sa.id

  # Admin password
  admin_password = var.airflow_admin_password

  # Lockbox Secrets Backend для автоматической передачи переменных
  # Airflow автоматически найдёт все секреты с префиксом airflow/variables/
  # и создаст соответствующие Variables
  lockbox_secrets_backend = {
    enabled = true
  }

  labels = local.common_labels

  depends_on = [
    yandex_mdb_postgresql_cluster.main,
    yandex_storage_bucket.data,
    yandex_compute_instance.mlflow,
    yandex_vpc_security_group.services_sg,
    yandex_vpc_subnet.services_subnet,
    # Legacy secret
    yandex_lockbox_secret_version.airflow_variables_v1,
    # Critical secrets
    yandex_lockbox_secret_version.s3_access_key_v1,
    yandex_lockbox_secret_version.s3_secret_key_v1,
    yandex_lockbox_secret_version.postgres_airflow_password_v1,
    # MLflow
    yandex_lockbox_secret_version.mlflow_ip_v1,
    yandex_lockbox_secret_version.mlflow_tracking_uri_v1,
    # Infrastructure
    yandex_lockbox_secret_version.security_group_id_v1,
    yandex_lockbox_secret_version.subnet_id_v1,
    yandex_lockbox_secret_version.dataproc_sa_id_v1,
    yandex_lockbox_secret_version.cloud_id_v1,
    yandex_lockbox_secret_version.folder_id_v1,
    yandex_lockbox_secret_version.zone_v1,
    yandex_lockbox_secret_version.network_id_v1,
    # S3
    yandex_lockbox_secret_version.s3_bucket_name_v1,
    yandex_lockbox_secret_version.s3_endpoint_url_v1,
    # IAM bindings
    yandex_lockbox_secret_iam_binding.s3_access_key_access,
    yandex_lockbox_secret_iam_binding.s3_secret_key_access,
    yandex_lockbox_secret_iam_binding.postgres_password_access,
    yandex_lockbox_secret_iam_binding.mlflow_ip_access,
    yandex_lockbox_secret_iam_binding.mlflow_tracking_uri_access,
    yandex_lockbox_secret_iam_binding.security_group_id_access,
    yandex_lockbox_secret_iam_binding.subnet_id_access,
    yandex_lockbox_secret_iam_binding.dataproc_sa_id_access,
    yandex_lockbox_secret_iam_binding.cloud_id_access,
    yandex_lockbox_secret_iam_binding.folder_id_access,
    yandex_lockbox_secret_iam_binding.zone_access,
    yandex_lockbox_secret_iam_binding.network_id_access,
    yandex_lockbox_secret_iam_binding.s3_bucket_name_access,
    yandex_lockbox_secret_iam_binding.s3_endpoint_url_access,
  ]
}

# ========================================
# Airflow Connections (через Terraform)
# ========================================

# S3 Connection для логов и DAGs
resource "null_resource" "airflow_s3_connection" {
  triggers = {
    airflow_cluster_id = yandex_airflow_cluster.main.id
  }

  provisioner "local-exec" {
    command = <<-EOT
      # Подождём, пока Airflow поднимется
      sleep 60
      
      # Создадим connection для S3 через Airflow CLI
      # (требует настроенного доступа к Airflow cluster)
      echo "S3 connection should be created manually via Airflow UI or API"
    EOT
  }
}

# ========================================
# Outputs
# ========================================

output "airflow_cluster_id" {
  description = "Airflow Cluster ID"
  value       = yandex_airflow_cluster.main.id
}

output "airflow_cluster_name" {
  description = "Airflow Cluster Name"
  value       = yandex_airflow_cluster.main.name
}

output "airflow_admin_user" {
  description = "Airflow admin username"
  value       = "admin"
}

output "airflow_admin_password" {
  description = "Airflow admin password"
  value       = var.airflow_admin_password
  sensitive   = true
}

output "airflow_dags_s3_path" {
  description = "S3 path for Airflow DAGs"
  value       = "s3://${yandex_storage_bucket.data.bucket}/airflow-dags/"
}
