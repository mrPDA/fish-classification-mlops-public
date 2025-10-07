# ========================================
# Kubernetes Cluster
# ========================================

resource "yandex_kubernetes_cluster" "main" {
  name        = "${local.project_name}-${local.suffix}-k8s"
  description = "Kubernetes cluster for ML Inference API"
  network_id  = data.yandex_vpc_network.default.id

  master {
    version = var.k8s_version
    zonal {
      zone      = var.zone
      subnet_id = yandex_vpc_subnet.k8s_subnet.id
    }

    public_ip = true  # Для доступа извне

    security_group_ids = [yandex_vpc_security_group.k8s_sg.id]

    maintenance_policy {
      auto_upgrade = true

      maintenance_window {
        start_time = "03:00"
        duration   = "3h"
      }
    }
  }

  service_account_id      = yandex_iam_service_account.k8s_sa.id
  node_service_account_id = yandex_iam_service_account.k8s_nodes_sa.id

  release_channel = "REGULAR"

  labels = local.common_labels

  depends_on = [
    yandex_resourcemanager_folder_iam_member.k8s_cluster_agent,
    yandex_resourcemanager_folder_iam_member.k8s_vpc_admin,
    yandex_resourcemanager_folder_iam_member.k8s_nodes_puller,
  ]
}

# ========================================
# Node Groups
# ========================================

# API Worker Nodes - для Inference API
resource "yandex_kubernetes_node_group" "api_workers" {
  cluster_id  = yandex_kubernetes_cluster.main.id
  name        = "api-workers"
  description = "Worker nodes for Inference API"
  version     = var.k8s_version

  instance_template {
    platform_id = "standard-v3"

    network_interface {
      nat                = true
      subnet_ids         = [yandex_vpc_subnet.k8s_subnet.id]
      security_group_ids = [yandex_vpc_security_group.k8s_sg.id]
    }

    resources {
      memory = var.k8s_api_memory  # 8 GB
      cores  = var.k8s_api_cores   # 4 cores
    }

    boot_disk {
      type = "network-hdd"  # HDD для экономии квоты SSD
      size = var.k8s_api_disk_size  # 64 GB
    }

    scheduling_policy {
      preemptible = var.use_preemptible_nodes  # Экономия для учебного проекта
    }

    metadata = {
      ssh-keys = "${var.ssh_user}:${file(var.ssh_public_key_path)}"
    }

    labels = merge(local.common_labels, {
      workload-type = "api"
      node-type     = "inference"
    })
  }

  scale_policy {
    auto_scale {
      min     = var.k8s_api_min_nodes
      max     = var.k8s_api_max_nodes
      initial = var.k8s_api_initial_nodes
    }
  }

  allocation_policy {
    location {
      zone = var.zone
    }
  }

  maintenance_policy {
    auto_upgrade = true
    auto_repair  = true

    maintenance_window {
      start_time = "03:00"
      duration   = "3h"
    }
  }
}

# Kafka & Workers Nodes - ОТКЛЮЧЕНО (используется Managed Kafka)
# resource "yandex_kubernetes_node_group" "kafka_workers" {
#   cluster_id  = yandex_kubernetes_cluster.main.id
#   name        = "kafka-workers"
#   description = "Worker nodes for Kafka and ML Workers"
#   version     = var.k8s_version
# 
#   instance_template {
#     platform_id = "standard-v3"
# 
#     network_interface {
#       nat                = true
#       subnet_ids         = [yandex_vpc_subnet.k8s_subnet.id]
#       security_group_ids = [yandex_vpc_security_group.k8s_sg.id]
#     }
# 
#     resources {
#       memory = var.k8s_kafka_memory
#       cores  = var.k8s_kafka_cores
#     }
# 
#     boot_disk {
#       type = "network-ssd"
#       size = var.k8s_kafka_disk_size
#     }
# 
#     scheduling_policy {
#       preemptible = var.use_preemptible_nodes
#     }
# 
#     metadata = {
#       ssh-keys = "${var.ssh_user}:${file(var.ssh_public_key_path)}"
#     }
# 
#     labels = merge(local.common_labels, {
#       workload-type = "kafka"
#       node-type     = "messaging"
#     })
#   }
# 
#   scale_policy {
#     fixed_scale {
#       size = var.k8s_kafka_nodes
#     }
#   }
# 
#   allocation_policy {
#     location {
#       zone = var.zone
#     }
#   }
# 
#   maintenance_policy {
#     auto_upgrade = true
#     auto_repair  = true
# 
#     maintenance_window {
#       start_time = "03:00"
#       duration   = "3h"
#     }
#   }
# }

# ========================================
# Outputs
# ========================================

output "k8s_cluster_id" {
  description = "Kubernetes cluster ID"
  value       = yandex_kubernetes_cluster.main.id
}

output "k8s_cluster_name" {
  description = "Kubernetes cluster name"
  value       = yandex_kubernetes_cluster.main.name
}

output "k8s_cluster_endpoint" {
  description = "Kubernetes cluster endpoint"
  value       = yandex_kubernetes_cluster.main.master[0].external_v4_endpoint
}

output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = "yc managed-kubernetes cluster get-credentials ${yandex_kubernetes_cluster.main.id} --external --force"
}
