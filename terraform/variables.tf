# ========================================
# Yandex Cloud Configuration
# ========================================

variable "service_account_key_file" {
  description = "Path to service account key file"
  type        = string
}

variable "cloud_id" {
  description = "Yandex Cloud ID"
  type        = string
}

variable "folder_id" {
  description = "Yandex Cloud Folder ID"
  type        = string
}

variable "zone" {
  description = "Yandex Cloud zone"
  type        = string
  default     = "ru-central1-a"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
  
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

# ========================================
# SSH Configuration
# ========================================

variable "ssh_public_key_path" {
  description = "Path to SSH public key"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "ssh_user" {
  description = "SSH user name"
  type        = string
  default     = "ubuntu"
}

# ========================================
# PostgreSQL Configuration
# ========================================

variable "postgres_preset" {
  description = "PostgreSQL resource preset"
  type        = string
  default     = "s2.micro"  # 2 vCPU, 8 GB RAM
}

variable "postgres_disk_size" {
  description = "PostgreSQL disk size in GB"
  type        = number
  default     = 50
}

variable "postgres_airflow_password" {
  description = "Password for Airflow PostgreSQL user"
  type        = string
  sensitive   = true
}

variable "postgres_mlops_password" {
  description = "Password for MLOps PostgreSQL user"
  type        = string
  sensitive   = true
}

variable "kafka_password" {
  description = "Password for Kafka user"
  type        = string
  sensitive   = true
  default     = "KafkaSecurePass123!"
}

# ========================================
# Kubernetes Configuration
# ========================================

variable "k8s_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.30"
}

variable "use_preemptible_nodes" {
  description = "Use preemptible nodes for cost savings"
  type        = bool
  default     = true  # Экономия для учебного проекта
}

# API Workers Configuration
variable "k8s_api_memory" {
  description = "Memory for API worker nodes (GB)"
  type        = number
  default     = 4  # Уменьшено с 8 до 4
}

variable "k8s_api_cores" {
  description = "CPU cores for API worker nodes"
  type        = number
  default     = 2  # Уменьшено с 4 до 2
}

variable "k8s_api_disk_size" {
  description = "Disk size for API worker nodes (GB)"
  type        = number
  default     = 32  # Уменьшено с 64 до 32
}

variable "k8s_api_min_nodes" {
  description = "Minimum number of API worker nodes"
  type        = number
  default     = 1  # Уменьшено с 2 до 1 (минимум)
}

variable "k8s_api_max_nodes" {
  description = "Maximum number of API worker nodes"
  type        = number
  default     = 10  # Максимум остаётся (при нагрузке)
}

variable "k8s_api_initial_nodes" {
  description = "Initial number of API worker nodes"
  type        = number
  default     = 1  # Стартуем с 1 ноды (экономия)
}

# Kafka Workers Configuration
variable "k8s_kafka_memory" {
  description = "Memory for Kafka worker nodes (GB)"
  type        = number
  default     = 4  # Уменьшено с 8 до 4 (Kafka managed)
}

variable "k8s_kafka_cores" {
  description = "CPU cores for Kafka worker nodes"
  type        = number
  default     = 2  # Уменьшено с 4 до 2 (Kafka managed)
}

variable "k8s_kafka_disk_size" {
  description = "Disk size for Kafka worker nodes (GB)"
  type        = number
  default     = 32  # Уменьшено с 96 до 32 (Kafka managed)
}

variable "k8s_kafka_nodes" {
  description = "Number of Kafka worker nodes"
  type        = number
  default     = 0  # Kafka managed (не нужны воркеры в K8s)
}

# ========================================
# ML Configuration
# ========================================

variable "num_classes" {
  description = "Number of fish species classes"
  type        = number
  default     = 17  # Из datasets_final
}

variable "model_type" {
  description = "ML model type"
  type        = string
  default     = "efficientnet-b4"
}

variable "image_size" {
  description = "Input image size"
  type        = number
  default     = 224
}

# ========================================
# Managed Airflow Configuration  
# ========================================

variable "airflow_version" {
  description = "Apache Airflow version"
  type        = string
  default     = "2.8"
}

variable "airflow_admin_password" {
  description = "Airflow admin password"
  type        = string
  sensitive   = true
}

variable "airflow_webserver_preset" {
  description = "Airflow webserver resource preset"
  type        = string
  default     = "c1-m4"  # 1 vCPU, 4 GB RAM
}

variable "airflow_scheduler_preset" {
  description = "Airflow scheduler resource preset"  
  type        = string
  default     = "c1-m4"
}

variable "airflow_worker_preset" {
  description = "Airflow worker resource preset"
  type        = string
  default     = "c2-m8"  # 2 vCPU, 8 GB RAM
}

variable "airflow_min_workers" {
  description = "Minimum number of Airflow workers"
  type        = number
  default     = 1
}

variable "airflow_max_workers" {
  description = "Maximum number of Airflow workers"
  type        = number
  default     = 5
}

# ========================================
# VM Configuration (MLflow, Grafana)
# ========================================

variable "mlflow_vm_cores" {
  description = "MLflow VM CPU cores"
  type        = number
  default     = 2
}

variable "mlflow_vm_memory" {
  description = "MLflow VM memory (GB)"
  type        = number
  default     = 4
}

variable "mlflow_vm_disk_size" {
  description = "MLflow VM disk size (GB)"
  type        = number
  default     = 50
}

variable "grafana_vm_cores" {
  description = "Grafana VM CPU cores"
  type        = number
  default     = 2
}

variable "grafana_vm_memory" {
  description = "Grafana VM memory (GB)"
  type        = number
  default     = 4
}

variable "grafana_vm_disk_size" {
  description = "Grafana VM disk size (GB)"
  type        = number
  default     = 30
}
