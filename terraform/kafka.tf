# ========================================
# Managed Service for Apache Kafka
# ========================================

resource "yandex_mdb_kafka_cluster" "main" {
  name        = "${local.project_name}-${local.suffix}-kafka"
  environment = upper(var.environment)
  network_id  = data.yandex_vpc_network.default.id
  
  config {
    version          = "3.6"
    brokers_count    = 1
    zones            = [var.zone]
    assign_public_ip = false
    
    kafka {
      resources {
        resource_preset_id = "s2.micro"  # 2 vCPU, 8 GB RAM
        disk_type_id       = "network-hdd"  # HDD для экономии квоты SSD
        disk_size          = 32  # GB
      }
      
      kafka_config {
        compression_type                = "COMPRESSION_TYPE_GZIP"
        log_flush_interval_messages     = 1024
        log_flush_interval_ms           = 1000
        log_flush_scheduler_interval_ms = 1000
        log_retention_bytes             = 1073741824  # 1 GB
        log_retention_hours             = 168         # 7 days
        log_retention_minutes           = 10080
        log_segment_bytes               = 134217728   # 128 MB
        num_partitions                  = 3
        default_replication_factor      = 1
      }
    }
    
    zookeeper {
      resources {
        resource_preset_id = "s2.micro"
        disk_type_id       = "network-hdd"  # HDD для экономии квоты SSD
        disk_size          = 10
      }
    }
  }
  
  subnet_ids = [yandex_vpc_subnet.services_subnet.id]
  
  security_group_ids = [yandex_vpc_security_group.services_sg.id]
  
  user {
    name     = "kafka_user"
    password = var.kafka_password
    permission {
      topic_name = "*"
      role       = "ACCESS_ROLE_PRODUCER"
    }
    permission {
      topic_name = "*"
      role       = "ACCESS_ROLE_CONSUMER"
    }
  }
  
  depends_on = [
    yandex_vpc_subnet.services_subnet,
    yandex_vpc_security_group.services_sg
  ]
  
  labels = {
    environment = var.environment
    project     = local.project_name
    managed_by  = "terraform"
  }
}

# Topics will be created automatically by applications
# But we can pre-create them if needed:
resource "yandex_mdb_kafka_topic" "classification_requests" {
  cluster_id         = yandex_mdb_kafka_cluster.main.id
  name               = "fish-classification-requests"
  partitions         = 3
  replication_factor = 1
  
  topic_config {
    compression_type = "COMPRESSION_TYPE_GZIP"
    retention_bytes  = 1073741824  # 1 GB
    retention_ms     = 604800000   # 7 days
  }
}

resource "yandex_mdb_kafka_topic" "classification_results" {
  cluster_id         = yandex_mdb_kafka_cluster.main.id
  name               = "fish-classification-results"
  partitions         = 3
  replication_factor = 1
  
  topic_config {
    compression_type = "COMPRESSION_TYPE_GZIP"
    retention_bytes  = 1073741824  # 1 GB
    retention_ms     = 604800000   # 7 days
  }
}

# ========================================
# Outputs
# ========================================

output "kafka_cluster_id" {
  description = "Kafka cluster ID"
  value       = yandex_mdb_kafka_cluster.main.id
}

output "kafka_cluster_name" {
  description = "Kafka cluster name"
  value       = yandex_mdb_kafka_cluster.main.name
}

output "kafka_brokers" {
  description = "Kafka broker hosts"
  value       = [for host in yandex_mdb_kafka_cluster.main.host : "${host.name}:9091"]
}

output "kafka_connection_string" {
  description = "Kafka connection string for applications"
  value       = join(",", [for host in yandex_mdb_kafka_cluster.main.host : "${host.name}:9091"])
}

output "kafka_user" {
  description = "Kafka username"
  value       = "kafka_user"
}

output "kafka_password" {
  description = "Kafka password"
  value       = var.kafka_password
  sensitive   = true
}
