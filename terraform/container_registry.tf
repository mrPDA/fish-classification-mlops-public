# ========================================
# Yandex Container Registry
# ========================================

resource "yandex_container_registry" "main" {
  name      = "${local.project_name}-${local.suffix}-registry"
  folder_id = var.folder_id

  labels = local.common_labels
}

# IAM для доступа к registry
resource "yandex_container_registry_iam_binding" "puller" {
  registry_id = yandex_container_registry.main.id
  role        = "container-registry.images.puller"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

resource "yandex_container_registry_iam_binding" "pusher" {
  registry_id = yandex_container_registry.main.id
  role        = "container-registry.images.pusher"

  members = [
    "serviceAccount:${yandex_iam_service_account.s3_sa.id}",
  ]
}

# Outputs
output "container_registry_id" {
  description = "Container Registry ID"
  value       = yandex_container_registry.main.id
}

output "container_registry_name" {
  description = "Container Registry Name"
  value       = yandex_container_registry.main.name
}

