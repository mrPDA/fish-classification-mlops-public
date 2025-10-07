# ========================================
# Yandex Lockbox для автоматической передачи секретов в Airflow
# ========================================
#
# ВАЖНО: Согласно документации Yandex Cloud, для автоматической интеграции
# с Airflow Variables через Lockbox Backend, секреты должны иметь имя в формате:
# airflow/variables/<имя_переменной>
#
# Для каждой переменной создаётся отдельный секрет.
# ========================================

# ========================================
# Секреты для S3 доступа
# ========================================

resource "yandex_lockbox_secret" "s3_access_key" {
  name        = "airflow/variables/S3_ACCESS_KEY"
  description = "S3 Access Key for Airflow"
  folder_id   = var.folder_id

  labels = merge(local.common_labels, {
    component = "airflow"
    type      = "variable"
  })
}

resource "yandex_lockbox_secret_version" "s3_access_key_v1" {
  secret_id = yandex_lockbox_secret.s3_access_key.id

  entries {
    key        = "S3_ACCESS_KEY"
    text_value = yandex_iam_service_account_static_access_key.s3_key.access_key
  }
}

resource "yandex_lockbox_secret" "s3_secret_key" {
  name        = "airflow/variables/S3_SECRET_KEY"
  description = "S3 Secret Key for Airflow"
  folder_id   = var.folder_id

  labels = merge(local.common_labels, {
    component = "airflow"
    type      = "variable"
  })
}

resource "yandex_lockbox_secret_version" "s3_secret_key_v1" {
  secret_id = yandex_lockbox_secret.s3_secret_key.id

  entries {
    key        = "S3_SECRET_KEY"
    text_value = yandex_iam_service_account_static_access_key.s3_key.secret_key
  }
}

# ========================================
# Секреты для PostgreSQL
# ========================================

resource "yandex_lockbox_secret" "postgres_airflow_password" {
  name        = "airflow/variables/POSTGRES_AIRFLOW_PASSWORD"
  description = "PostgreSQL Airflow Password"
  folder_id   = var.folder_id

  labels = merge(local.common_labels, {
    component = "airflow"
    type      = "variable"
  })
}

resource "yandex_lockbox_secret_version" "postgres_airflow_password_v1" {
  secret_id = yandex_lockbox_secret.postgres_airflow_password.id

  entries {
    key        = "POSTGRES_AIRFLOW_PASSWORD"
    text_value = var.postgres_airflow_password
  }
}

# ========================================
# Секреты для MLflow
# ========================================

resource "yandex_lockbox_secret" "mlflow_ip" {
  name        = "airflow/variables/MLFLOW_IP"
  description = "MLflow Internal IP Address"
  folder_id   = var.folder_id

  labels = merge(local.common_labels, {
    component = "airflow"
    type      = "variable"
  })
}

resource "yandex_lockbox_secret_version" "mlflow_ip_v1" {
  secret_id = yandex_lockbox_secret.mlflow_ip.id

  entries {
    key        = "MLFLOW_IP"
    text_value = yandex_compute_instance.mlflow.network_interface.0.ip_address
  }
}

resource "yandex_lockbox_secret" "mlflow_tracking_uri" {
  name        = "airflow/variables/MLFLOW_TRACKING_URI"
  description = "MLflow Tracking URI"
  folder_id   = var.folder_id

  labels = merge(local.common_labels, {
    component = "airflow"
    type      = "variable"
  })
}

resource "yandex_lockbox_secret_version" "mlflow_tracking_uri_v1" {
  secret_id = yandex_lockbox_secret.mlflow_tracking_uri.id

  entries {
    key        = "MLFLOW_TRACKING_URI"
    text_value = "http://${yandex_compute_instance.mlflow.network_interface.0.ip_address}:5000"
  }
}

# ========================================
# Секреты для инфраструктуры (критичные для DataProc)
# ========================================

resource "yandex_lockbox_secret" "security_group_id" {
  name        = "airflow/variables/SECURITY_GROUP_ID"
  description = "Security Group ID for DataProc"
  folder_id   = var.folder_id

  labels = merge(local.common_labels, {
    component = "airflow"
    type      = "variable"
  })
}

resource "yandex_lockbox_secret_version" "security_group_id_v1" {
  secret_id = yandex_lockbox_secret.security_group_id.id

  entries {
    key        = "SECURITY_GROUP_ID"
    text_value = yandex_vpc_security_group.services_sg.id
  }
}

resource "yandex_lockbox_secret" "subnet_id" {
  name        = "airflow/variables/SUBNET_ID"
  description = "Subnet ID for DataProc"
  folder_id   = var.folder_id

  labels = merge(local.common_labels, {
    component = "airflow"
    type      = "variable"
  })
}

resource "yandex_lockbox_secret_version" "subnet_id_v1" {
  secret_id = yandex_lockbox_secret.subnet_id.id

  entries {
    key        = "SUBNET_ID"
    text_value = yandex_vpc_subnet.services_subnet.id
  }
}

resource "yandex_lockbox_secret" "dataproc_sa_id" {
  name        = "airflow/variables/DATAPROC_SERVICE_ACCOUNT_ID"
  description = "DataProc Service Account ID"
  folder_id   = var.folder_id

  labels = merge(local.common_labels, {
    component = "airflow"
    type      = "variable"
  })
}

resource "yandex_lockbox_secret_version" "dataproc_sa_id_v1" {
  secret_id = yandex_lockbox_secret.dataproc_sa_id.id

  entries {
    key        = "DATAPROC_SERVICE_ACCOUNT_ID"
    text_value = yandex_iam_service_account.s3_sa.id
  }
}

# ========================================
# Секреты для Cloud инфраструктуры
# ========================================

resource "yandex_lockbox_secret" "cloud_id" {
  name        = "airflow/variables/CLOUD_ID"
  description = "Yandex Cloud ID"
  folder_id   = var.folder_id

  labels = merge(local.common_labels, {
    component = "airflow"
    type      = "variable"
  })
}

resource "yandex_lockbox_secret_version" "cloud_id_v1" {
  secret_id = yandex_lockbox_secret.cloud_id.id

  entries {
    key        = "CLOUD_ID"
    text_value = var.cloud_id
  }
}

resource "yandex_lockbox_secret" "folder_id" {
  name        = "airflow/variables/FOLDER_ID"
  description = "Yandex Folder ID"
  folder_id   = var.folder_id

  labels = merge(local.common_labels, {
    component = "airflow"
    type      = "variable"
  })
}

resource "yandex_lockbox_secret_version" "folder_id_v1" {
  secret_id = yandex_lockbox_secret.folder_id.id

  entries {
    key        = "FOLDER_ID"
    text_value = var.folder_id
  }
}

resource "yandex_lockbox_secret" "zone" {
  name        = "airflow/variables/ZONE"
  description = "Yandex Zone"
  folder_id   = var.folder_id

  labels = merge(local.common_labels, {
    component = "airflow"
    type      = "variable"
  })
}

resource "yandex_lockbox_secret_version" "zone_v1" {
  secret_id = yandex_lockbox_secret.zone.id

  entries {
    key        = "ZONE"
    text_value = var.zone
  }
}

resource "yandex_lockbox_secret" "network_id" {
  name        = "airflow/variables/NETWORK_ID"
  description = "VPC Network ID"
  folder_id   = var.folder_id

  labels = merge(local.common_labels, {
    component = "airflow"
    type      = "variable"
  })
}

resource "yandex_lockbox_secret_version" "network_id_v1" {
  secret_id = yandex_lockbox_secret.network_id.id

  entries {
    key        = "NETWORK_ID"
    text_value = data.yandex_vpc_network.default.id
  }
}

# ========================================
# Секреты для S3
# ========================================

resource "yandex_lockbox_secret" "s3_bucket_name" {
  name        = "airflow/variables/S3_BUCKET_NAME"
  description = "S3 Bucket Name"
  folder_id   = var.folder_id

  labels = merge(local.common_labels, {
    component = "airflow"
    type      = "variable"
  })
}

resource "yandex_lockbox_secret_version" "s3_bucket_name_v1" {
  secret_id = yandex_lockbox_secret.s3_bucket_name.id

  entries {
    key        = "S3_BUCKET_NAME"
    text_value = yandex_storage_bucket.data.bucket
  }
}

resource "yandex_lockbox_secret" "s3_endpoint_url" {
  name        = "airflow/variables/S3_ENDPOINT_URL"
  description = "S3 Endpoint URL"
  folder_id   = var.folder_id

  labels = merge(local.common_labels, {
    component = "airflow"
    type      = "variable"
  })
}

resource "yandex_lockbox_secret_version" "s3_endpoint_url_v1" {
  secret_id = yandex_lockbox_secret.s3_endpoint_url.id

  entries {
    key        = "S3_ENDPOINT_URL"
    text_value = "https://storage.yandexcloud.net"
  }
}

# ========================================
# Общий секрет для всех остальных переменных (legacy)
# Этот секрет используется для ручного импорта через скрипт
# ========================================

resource "yandex_lockbox_secret" "airflow_variables" {
  name        = "${local.project_name}-${local.suffix}-airflow-vars-legacy"
  description = "Airflow Variables and Secrets (Legacy - for manual import)"
  folder_id   = var.folder_id

  labels = merge(local.common_labels, {
    component = "airflow"
    type      = "variables-legacy"
  })
}

# ========================================
# Версия секрета с переменными
# ========================================

resource "yandex_lockbox_secret_version" "airflow_variables_v1" {
  secret_id = yandex_lockbox_secret.airflow_variables.id

  # ========================================
  # Секретные переменные
  # ========================================

  entries {
    key        = "S3_ACCESS_KEY"
    text_value = yandex_iam_service_account_static_access_key.s3_key.access_key
  }

  entries {
    key        = "S3_SECRET_KEY"
    text_value = yandex_iam_service_account_static_access_key.s3_key.secret_key
  }

  entries {
    key        = "POSTGRES_AIRFLOW_PASSWORD"
    text_value = var.postgres_airflow_password
  }

  entries {
    key        = "POSTGRES_MLOPS_PASSWORD"
    text_value = var.postgres_mlops_password
  }

  # ========================================
  # Обычные переменные (не секретные, но удобно хранить вместе)
  # ========================================

  entries {
    key        = "CLOUD_ID"
    text_value = var.cloud_id
  }

  entries {
    key        = "FOLDER_ID"
    text_value = var.folder_id
  }

  entries {
    key        = "ZONE"
    text_value = var.zone
  }

  entries {
    key        = "NETWORK_ID"
    text_value = data.yandex_vpc_network.default.id
  }

  entries {
    key        = "SUBNET_ID"
    text_value = yandex_vpc_subnet.services_subnet.id
  }

  entries {
    key        = "SECURITY_GROUP_ID"
    text_value = yandex_vpc_security_group.services_sg.id
  }

  entries {
    key        = "S3_BUCKET_NAME"
    text_value = yandex_storage_bucket.data.bucket
  }

  entries {
    key        = "S3_ENDPOINT_URL"
    text_value = "https://storage.yandexcloud.net"
  }

  entries {
    key        = "DATAPROC_SERVICE_ACCOUNT_ID"
    text_value = yandex_iam_service_account.s3_sa.id
  }

  entries {
    key        = "MLFLOW_TRACKING_URI"
    text_value = "http://${yandex_compute_instance.mlflow.network_interface.0.ip_address}:5000"
  }

  entries {
    key        = "MLFLOW_EXPERIMENT_NAME"
    text_value = "fish-classification"
  }

  # ========================================
  # Параметры обучения модели
  # ========================================

  entries {
    key        = "NUM_CLASSES"
    text_value = "17"
  }

  entries {
    key        = "IMAGE_SIZE"
    text_value = "224"
  }

  entries {
    key        = "BATCH_SIZE"
    text_value = "32"
  }

  entries {
    key        = "EPOCHS"
    text_value = "20"
  }

  entries {
    key        = "LEARNING_RATE"
    text_value = "0.001"
  }

  entries {
    key        = "DEFAULT_RETRIES"
    text_value = "2"
  }

  entries {
    key        = "ENVIRONMENT"
    text_value = var.environment
  }

  # ========================================
  # SSH ключ для DataProc (если существует)
  # ========================================

  entries {
    key        = "YC_SSH_PUBLIC_KEY"
    text_value = fileexists(pathexpand("~/.ssh/id_rsa.pub")) ? file(pathexpand("~/.ssh/id_rsa.pub")) : "ssh-rsa PLACEHOLDER"
  }

  # ========================================
  # Service Account JSON для DataProc
  # ========================================

  entries {
    key        = "DP_SA_JSON"
    text_value = fileexists("${path.module}/sa-key.json") ? file("${path.module}/sa-key.json") : jsonencode({
      type                = "service_account"
      service_account_id  = yandex_iam_service_account.s3_sa.id
    })
  }
}

# ========================================
# Права доступа для Airflow SA к Lockbox
# ========================================

# Доступ к S3 ключам
resource "yandex_lockbox_secret_iam_binding" "s3_access_key_access" {
  secret_id = yandex_lockbox_secret.s3_access_key.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

resource "yandex_lockbox_secret_iam_binding" "s3_secret_key_access" {
  secret_id = yandex_lockbox_secret.s3_secret_key.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

# Доступ к PostgreSQL паролю
resource "yandex_lockbox_secret_iam_binding" "postgres_password_access" {
  secret_id = yandex_lockbox_secret.postgres_airflow_password.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

# Доступ к MLflow IP
resource "yandex_lockbox_secret_iam_binding" "mlflow_ip_access" {
  secret_id = yandex_lockbox_secret.mlflow_ip.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

# Доступ к MLflow Tracking URI
resource "yandex_lockbox_secret_iam_binding" "mlflow_tracking_uri_access" {
  secret_id = yandex_lockbox_secret.mlflow_tracking_uri.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

# Доступ к Security Group ID
resource "yandex_lockbox_secret_iam_binding" "security_group_id_access" {
  secret_id = yandex_lockbox_secret.security_group_id.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

# Доступ к Subnet ID
resource "yandex_lockbox_secret_iam_binding" "subnet_id_access" {
  secret_id = yandex_lockbox_secret.subnet_id.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

# Доступ к DataProc SA ID
resource "yandex_lockbox_secret_iam_binding" "dataproc_sa_id_access" {
  secret_id = yandex_lockbox_secret.dataproc_sa_id.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

# Доступ к Cloud ID
resource "yandex_lockbox_secret_iam_binding" "cloud_id_access" {
  secret_id = yandex_lockbox_secret.cloud_id.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

# Доступ к Folder ID
resource "yandex_lockbox_secret_iam_binding" "folder_id_access" {
  secret_id = yandex_lockbox_secret.folder_id.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

# Доступ к Zone
resource "yandex_lockbox_secret_iam_binding" "zone_access" {
  secret_id = yandex_lockbox_secret.zone.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

# Доступ к Network ID
resource "yandex_lockbox_secret_iam_binding" "network_id_access" {
  secret_id = yandex_lockbox_secret.network_id.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

# Доступ к S3 Bucket Name
resource "yandex_lockbox_secret_iam_binding" "s3_bucket_name_access" {
  secret_id = yandex_lockbox_secret.s3_bucket_name.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

# Доступ к S3 Endpoint URL
resource "yandex_lockbox_secret_iam_binding" "s3_endpoint_url_access" {
  secret_id = yandex_lockbox_secret.s3_endpoint_url.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

# Доступ к legacy секрету (для ручного импорта)
resource "yandex_lockbox_secret_iam_binding" "airflow_access" {
  secret_id = yandex_lockbox_secret.airflow_variables.id
  role      = "lockbox.payloadViewer"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

# ========================================
# Outputs
# ========================================

output "lockbox_secret_id" {
  description = "Lockbox Secret ID"
  value       = yandex_lockbox_secret.airflow_variables.id
}

output "lockbox_secret_name" {
  description = "Lockbox Secret Name"
  value       = yandex_lockbox_secret.airflow_variables.name
}

output "lockbox_variables_count" {
  description = "Number of variables in Lockbox"
  value       = length(yandex_lockbox_secret_version.airflow_variables_v1.entries)
}
