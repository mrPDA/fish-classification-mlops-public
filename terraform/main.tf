# 🐟 Fish Classification System - Hybrid Architecture
# =================================================
# Managed Services + Kubernetes for ML Inference

terraform {
  required_version = ">= 1.0"
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "~> 0.100"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "yandex" {
  service_account_key_file = var.service_account_key_file
  cloud_id                  = var.cloud_id
  folder_id                 = var.folder_id
  zone                      = var.zone
}

# Random suffix for unique resource names
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

locals {
  project_name = "fish-classification"
  suffix       = random_string.suffix.result
  common_labels = {
    project     = local.project_name
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ========================================
# Network Infrastructure
# ========================================

# Используем существующую default сеть
data "yandex_vpc_network" "default" {
  name = "default"
}

# Создаём subnet для Kubernetes
resource "yandex_vpc_subnet" "k8s_subnet" {
  name           = "${local.project_name}-${local.suffix}-k8s-subnet"
  zone           = var.zone
  network_id     = data.yandex_vpc_network.default.id
  v4_cidr_blocks = ["10.10.0.0/24"]

  labels = local.common_labels
}

# NAT Gateway для доступа в интернет из подсети
resource "yandex_vpc_gateway" "nat_gateway" {
  name = "${local.project_name}-${local.suffix}-nat-gateway"
  shared_egress_gateway {}
}

# Route table с NAT Gateway
resource "yandex_vpc_route_table" "rt" {
  name       = "${local.project_name}-${local.suffix}-route-table"
  network_id = data.yandex_vpc_network.default.id

  static_route {
    destination_prefix = "0.0.0.0/0"
    gateway_id         = yandex_vpc_gateway.nat_gateway.id
  }
}

# Создаём subnet для managed services (Airflow, PostgreSQL)
resource "yandex_vpc_subnet" "services_subnet" {
  name           = "${local.project_name}-${local.suffix}-services-subnet"
  zone           = var.zone
  network_id     = data.yandex_vpc_network.default.id
  v4_cidr_blocks = ["10.11.0.0/24"]
  route_table_id = yandex_vpc_route_table.rt.id

  labels = local.common_labels
}

# Security group для Kubernetes
resource "yandex_vpc_security_group" "k8s_sg" {
  name        = "${local.project_name}-${local.suffix}-k8s-sg"
  description = "Security group for Kubernetes cluster"
  network_id  = data.yandex_vpc_network.default.id

  # Allow all outbound traffic
  egress {
    protocol       = "ANY"
    description    = "Allow all outbound traffic"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow Kubernetes API
  ingress {
    protocol       = "TCP"
    description    = "Kubernetes API"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 443
  }

  # Allow Kubernetes API alternative
  ingress {
    protocol       = "TCP"
    description    = "Kubernetes API alternative"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 6443
  }

  # Allow NodePort services
  ingress {
    protocol       = "TCP"
    description    = "NodePort services"
    v4_cidr_blocks = ["0.0.0.0/0"]
    from_port      = 30000
    to_port        = 32767
  }

  # Allow HTTP/HTTPS for LoadBalancers
  ingress {
    protocol       = "TCP"
    description    = "HTTP"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 80
  }

  ingress {
    protocol       = "TCP"
    description    = "HTTPS"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 443
  }

  # Allow SSH
  ingress {
    protocol       = "TCP"
    description    = "SSH"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 22
  }

  # Allow internal communication
  ingress {
    protocol          = "ANY"
    description       = "Internal cluster communication"
    predefined_target = "self_security_group"
  }

  # NodePort range for K8s services
  ingress {
    protocol       = "TCP"
    description    = "Kubernetes NodePort range"
    v4_cidr_blocks = ["0.0.0.0/0"]
    from_port      = 30000
    to_port        = 32767
  }

  labels = local.common_labels
}

# Security group для managed services
resource "yandex_vpc_security_group" "services_sg" {
  name        = "${local.project_name}-${local.suffix}-services-sg"
  description = "Security group for managed services"
  network_id  = data.yandex_vpc_network.default.id

  # Allow all outbound traffic
  egress {
    protocol       = "ANY"
    description    = "Allow all outbound traffic"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH
  ingress {
    protocol       = "TCP"
    description    = "SSH"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 22
  }

  # Allow internal communication for DataProc clusters
  ingress {
    protocol          = "ANY"
    description       = "Internal cluster communication"
    predefined_target = "self_security_group"
  }
  
  # PostgreSQL (direct)
  ingress {
    protocol       = "TCP"
    description    = "PostgreSQL"
    v4_cidr_blocks = ["10.10.0.0/24", "10.11.0.0/24"]
    port           = 5432
  }
  
  # PostgreSQL (PgBouncer)
  ingress {
    protocol       = "TCP"
    description    = "PostgreSQL PgBouncer"
    v4_cidr_blocks = ["10.10.0.0/24", "10.11.0.0/24"]
    port           = 6432
  }
  
  # Kafka
  ingress {
    protocol       = "TCP"
    description    = "Kafka"
    v4_cidr_blocks = ["10.10.0.0/24", "10.11.0.0/24"]
    port           = 9091
  }

  # Airflow Web UI
  ingress {
    protocol       = "TCP"
    description    = "Airflow Web UI"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 8080
  }

  # MLflow UI
  ingress {
    protocol       = "TCP"
    description    = "MLflow UI"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 5000
  }

  # Grafana UI
  ingress {
    protocol       = "TCP"
    description    = "Grafana UI"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 3000
  }

  # Prometheus UI
  ingress {
    protocol       = "TCP"
    description    = "Prometheus UI"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 9090
  }

  labels = local.common_labels
}

# ========================================
# Service Accounts
# ========================================

resource "yandex_iam_service_account" "k8s_sa" {
  name        = "${local.project_name}-${local.suffix}-k8s-sa"
  description = "Service account for Kubernetes cluster"
}

resource "yandex_iam_service_account" "k8s_nodes_sa" {
  name        = "${local.project_name}-${local.suffix}-nodes-sa"
  description = "Service account for Kubernetes nodes"
}

# IAM роли для K8s service account
resource "yandex_resourcemanager_folder_iam_member" "k8s_cluster_agent" {
  folder_id = var.folder_id
  role      = "k8s.clusters.agent"
  member    = "serviceAccount:${yandex_iam_service_account.k8s_sa.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "k8s_vpc_admin" {
  folder_id = var.folder_id
  role      = "vpc.publicAdmin"
  member    = "serviceAccount:${yandex_iam_service_account.k8s_sa.id}"
}

# IAM роли для nodes service account
resource "yandex_resourcemanager_folder_iam_member" "k8s_nodes_puller" {
  folder_id = var.folder_id
  role      = "container-registry.images.puller"
  member    = "serviceAccount:${yandex_iam_service_account.k8s_nodes_sa.id}"
}

# ========================================
# S3 Object Storage
# ========================================

resource "yandex_iam_service_account" "s3_sa" {
  name        = "${local.project_name}-${local.suffix}-s3-sa"
  description = "Service account for S3 access"
}

resource "yandex_resourcemanager_folder_iam_member" "s3_editor" {
  folder_id = var.folder_id
  role      = "storage.editor"
  member    = "serviceAccount:${yandex_iam_service_account.s3_sa.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "s3_airflow_integration" {
  folder_id = var.folder_id
  role      = "managed-airflow.integrationProvider"
  member    = "serviceAccount:${yandex_iam_service_account.s3_sa.id}"
}

# IAM роль для создания DataProc кластеров из Airflow
resource "yandex_resourcemanager_folder_iam_member" "s3_dataproc_admin" {
  folder_id = var.folder_id
  role      = "dataproc.admin"
  member    = "serviceAccount:${yandex_iam_service_account.s3_sa.id}"
}

# IAM роль для работы DataProc agent
resource "yandex_resourcemanager_folder_iam_member" "s3_dataproc_agent" {
  folder_id = var.folder_id
  role      = "dataproc.agent"
  member    = "serviceAccount:${yandex_iam_service_account.s3_sa.id}"
}

# IAM роль для автомасштабирования DataProc
resource "yandex_resourcemanager_folder_iam_member" "s3_dataproc_provisioner" {
  folder_id = var.folder_id
  role      = "dataproc.provisioner"
  member    = "serviceAccount:${yandex_iam_service_account.s3_sa.id}"
}

# IAM роль для работы с VPC (нужна для DataProc)
resource "yandex_resourcemanager_folder_iam_member" "s3_vpc_user" {
  folder_id = var.folder_id
  role      = "vpc.user"
  member    = "serviceAccount:${yandex_iam_service_account.s3_sa.id}"
}

# IAM роль для использования сервисного аккаунта в DataProc
resource "yandex_iam_service_account_iam_member" "s3_sa_user" {
  service_account_id = yandex_iam_service_account.s3_sa.id
  role               = "iam.serviceAccounts.user"
  member             = "serviceAccount:${yandex_iam_service_account.s3_sa.id}"
}

resource "yandex_iam_service_account_static_access_key" "s3_key" {
  service_account_id = yandex_iam_service_account.s3_sa.id
  description        = "Static access key for S3"
}

resource "yandex_storage_bucket" "data" {
  bucket        = "${local.project_name}-data-${local.suffix}"
  access_key    = yandex_iam_service_account_static_access_key.s3_key.access_key
  secret_key    = yandex_iam_service_account_static_access_key.s3_key.secret_key
  force_destroy = true  # Автоматически удалять со всем содержимым

  anonymous_access_flags {
    read = false
    list = false
  }
}

# Создаём структуру папок в S3
locals {
  s3_folders = [
    "datasets/raw/",
    "datasets/processed/",
    "models/",
    "mlflow-artifacts/",
    "airflow-dags/",
    "logs/"
  ]
}

resource "yandex_storage_object" "folders" {
  for_each = toset(local.s3_folders)

  bucket     = yandex_storage_bucket.data.bucket
  key        = "${each.value}.keep"
  content    = "# Folder structure placeholder"
  access_key = yandex_iam_service_account_static_access_key.s3_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.s3_key.secret_key
}

# ========================================
# S3 Outputs
# ========================================

output "s3_bucket_name" {
  description = "S3 bucket name"
  value       = yandex_storage_bucket.data.bucket
}

output "s3_access_key" {
  description = "S3 access key"
  value       = yandex_iam_service_account_static_access_key.s3_key.access_key
  sensitive   = true
}

output "s3_secret_key" {
  description = "S3 secret key"
  value       = yandex_iam_service_account_static_access_key.s3_key.secret_key
  sensitive   = true
}

# ========================================
# Additional Outputs for Airflow Setup
# ========================================

output "cloud_id" {
  description = "Yandex Cloud ID"
  value       = var.cloud_id
}

output "folder_id" {
  description = "Yandex Cloud Folder ID"
  value       = var.folder_id
}

output "zone" {
  description = "Yandex Cloud Zone"
  value       = var.zone
}

output "network_id" {
  description = "VPC Network ID"
  value       = data.yandex_vpc_network.default.id
}

output "subnet_id" {
  description = "Services Subnet ID"
  value       = yandex_vpc_subnet.services_subnet.id
}

output "security_group_id" {
  description = "Services Security Group ID"
  value       = yandex_vpc_security_group.services_sg.id
}

output "mlflow_vm_ip" {
  description = "MLflow VM IP address"
  value       = try(yandex_compute_instance.mlflow.network_interface.0.ip_address, "")
}

output "dataproc_sa_id" {
  description = "DataProc Service Account ID"
  value       = yandex_iam_service_account.s3_sa.id
}
