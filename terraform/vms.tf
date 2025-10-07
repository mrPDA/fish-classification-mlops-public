# ========================================
# Virtual Machines for MLflow & Grafana
# ========================================

# Ubuntu 22.04 LTS image
data "yandex_compute_image" "ubuntu" {
  family = "ubuntu-2204-lts"
}

# ========================================
# MLflow Server VM
# ========================================

resource "yandex_compute_instance" "mlflow" {
  name        = "${local.project_name}-${local.suffix}-mlflow"
  description = "MLflow Tracking Server"
  zone        = var.zone

  resources {
    cores  = var.mlflow_vm_cores
    memory = var.mlflow_vm_memory
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.id
      size     = var.mlflow_vm_disk_size
      type     = "network-hdd"  # HDD для экономии квоты SSD
    }
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.services_subnet.id
    nat       = true  # Для внешнего доступа к MLflow UI
    security_group_ids = [yandex_vpc_security_group.services_sg.id]
  }

  metadata = {
    ssh-keys  = "${var.ssh_user}:${file(var.ssh_public_key_path)}"
    user-data = templatefile("${path.module}/cloud-init/mlflow-init.yaml", {
      postgres_host     = yandex_mdb_postgresql_cluster.main.host[0].fqdn
      postgres_db       = "mlops"
      postgres_user     = "mlops_user"
      postgres_password = var.postgres_mlops_password
      s3_bucket         = yandex_storage_bucket.data.bucket
      s3_access_key     = yandex_iam_service_account_static_access_key.s3_key.access_key
      s3_secret_key     = yandex_iam_service_account_static_access_key.s3_key.secret_key
      s3_endpoint       = "https://storage.yandexcloud.net"
    })
  }

  scheduling_policy {
    preemptible = var.use_preemptible_nodes
  }

  labels = merge(local.common_labels, {
    service = "mlflow"
  })
}

# ========================================
# Prometheus VM (базовый мониторинг)
# ========================================

resource "yandex_compute_instance" "prometheus" {
  name        = "${local.project_name}-${local.suffix}-prometheus"
  description = "Prometheus Monitoring"
  zone        = var.zone

  resources {
    cores  = 2
    memory = 2
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.id
      size     = 20
      type     = "network-hdd"  # HDD для экономии квоты SSD
    }
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.services_subnet.id
    nat       = true  # Для внешнего доступа к Prometheus UI
    security_group_ids = [yandex_vpc_security_group.services_sg.id]
  }

  metadata = {
    ssh-keys  = "${var.ssh_user}:${file(var.ssh_public_key_path)}"
    user-data = templatefile("${path.module}/cloud-init/prometheus-init.yaml", {
      mlflow_ip = yandex_compute_instance.mlflow.network_interface.0.ip_address
    })
  }

  scheduling_policy {
    preemptible = var.use_preemptible_nodes
  }

  labels = merge(local.common_labels, {
    service = "monitoring"
  })

  depends_on = [yandex_compute_instance.mlflow]
}

# ========================================
# Security Groups для VMs
# ========================================

# Правила уже добавлены в main.tf в yandex_vpc_security_group.services_sg

# ========================================
# Outputs
# ========================================

output "mlflow_url" {
  description = "MLflow UI URL"
  value       = "http://${yandex_compute_instance.mlflow.network_interface.0.nat_ip_address}:5000"
}

output "prometheus_url" {
  description = "Prometheus UI URL"
  value       = "http://${yandex_compute_instance.prometheus.network_interface.0.nat_ip_address}:9090"
}

output "mlflow_ssh" {
  description = "SSH command for MLflow server"
  value       = "ssh ${var.ssh_user}@${yandex_compute_instance.mlflow.network_interface.0.nat_ip_address}"
}

output "prometheus_ssh" {
  description = "SSH command for Prometheus server"
  value       = "ssh ${var.ssh_user}@${yandex_compute_instance.prometheus.network_interface.0.nat_ip_address}"
}
