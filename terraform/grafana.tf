# ========================================
# Grafana для мониторинга ML-инфраструктуры
# ========================================

# Compute instance для Grafana
resource "yandex_compute_instance" "grafana" {
  name        = "${local.project_name}-${local.suffix}-grafana"
  platform_id = "standard-v3"
  zone        = var.zone
  hostname    = "grafana"

  resources {
    cores  = 2
    memory = 4
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.id
      size     = 30
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.services_subnet.id
    nat       = true
    security_group_ids = [yandex_vpc_security_group.services_sg.id]
  }

  metadata = {
    ssh-keys = "${var.ssh_user}:${file(var.ssh_public_key_path)}"
    user-data = templatefile("${path.module}/cloud-init/grafana-init.yaml", {
      mlflow_ip           = yandex_compute_instance.mlflow.network_interface.0.ip_address
      postgres_host       = yandex_mdb_postgresql_cluster.main.host.0.fqdn
      postgres_password   = var.postgres_airflow_password
      s3_bucket           = yandex_storage_bucket.data.bucket
      s3_access_key       = yandex_iam_service_account_static_access_key.s3_key.access_key
      s3_secret_key       = yandex_iam_service_account_static_access_key.s3_key.secret_key
      folder_id           = var.folder_id
      service_account_id  = yandex_iam_service_account.s3_sa.id
    })
  }

  labels = merge(local.common_labels, {
    component = "monitoring"
    service   = "grafana"
  })

  # Зависимости
  depends_on = [
    yandex_compute_instance.mlflow,
    yandex_mdb_postgresql_cluster.main,
  ]
}

# Outputs
output "grafana_external_ip" {
  description = "Grafana external IP"
  value       = yandex_compute_instance.grafana.network_interface.0.nat_ip_address
}

output "grafana_internal_ip" {
  description = "Grafana internal IP"
  value       = yandex_compute_instance.grafana.network_interface.0.ip_address
}

output "grafana_url" {
  description = "Grafana URL"
  value       = "http://${yandex_compute_instance.grafana.network_interface.0.nat_ip_address}:3000"
}

