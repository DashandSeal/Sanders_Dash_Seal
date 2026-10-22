# Actual service resources; Terraform owns lifecycle, the application binds them.
resource "oci_objectstorage_bucket" "ledger" {
  count = local.deployment_enabled ? 1 : 0
  compartment_id = local.selected_compartment
  namespace = data.oci_objectstorage_namespace.release.namespace
  name = "sds-ledger-backups-${local.deployment_id}"
  access_type = "NoPublicAccess"
  storage_tier = "Standard"
  versioning = "Disabled"
  auto_tiering = "Disabled"
  lifecycle { prevent_destroy = true }
}
resource "oci_ons_notification_topic" "platform" {
  count = local.deployment_enabled ? 1 : 0
  compartment_id = local.selected_compartment
  name = "sds-platform-${local.deployment_id}"
  description = "Sanders Dash & Seal operational alarms"
}
resource "oci_monitoring_alarm" "platform" {
  for_each = local.deployment_enabled ? {
    host_unavailable = "PlatformHeartbeat[5m]{resourceId = \"${local.target_instance_id}\"}.absent()"
    backup_failed = "BackupVerified[1h]{resourceId = \"${local.target_instance_id}\"}.min() < 1"
  } : {}
  compartment_id = local.selected_compartment
  metric_compartment_id = local.selected_compartment
  namespace = "sds_platform"
  display_name = "sds-${each.key}-${local.deployment_id}"
  query = each.value
  severity = "CRITICAL"
  is_enabled = true
  destinations = [oci_ons_notification_topic.platform[0].id]
  pending_duration = each.key == "host_unavailable" ? "PT15M" : "PT5M"
  body = "Inspect Sanders Dash & Seal service journals; no customer data is included."
}
locals {
  platform_bindings = local.deployment_enabled ? {
    schema = 1
    instance_id = var.create_instance ? null : var.existing_instance_ocid
    compartment_id = local.selected_compartment
    namespace = data.oci_objectstorage_namespace.release.namespace
    region = var.region
    bucket = oci_objectstorage_bucket.ledger[0].name
    topic_id = oci_ons_notification_topic.platform[0].id
    metric_namespace = "sds_platform"
    budget_bytes = 20000000000
    max_snapshot_bytes = 1000000000
  } : null
  existing_release_config = var.deploy_existing_instance ? {
    commit = local.approved_commit
    tenancy_id = local.selected_tenancy
    compartment_id = local.selected_compartment
    namespace = data.oci_objectstorage_namespace.release.namespace
    bucket = oci_objectstorage_bucket.release[0].name
    object = oci_objectstorage_object.release[0].object
    sha256 = filesha256("${path.module}/application.tgz")
    resources = local.platform_bindings
  } : null
}
resource "oci_objectstorage_object" "existing_installer" {
  count = var.deploy_existing_instance ? 1 : 0
  namespace = data.oci_objectstorage_namespace.release.namespace
  bucket = oci_objectstorage_bucket.release[0].name
  object = "installers/${local.approved_commit}.sh"
  content = templatefile("${path.module}/install-existing.sh.tftpl", {
    release_config_base64 = base64encode(jsonencode(local.existing_release_config))
  })
  content_type = "text/x-shellscript"
}
output "existing_install_command" {
  value = var.deploy_existing_instance ? {
    compartment_id = local.selected_compartment
    instance_id = local.target_instance_id
    namespace = data.oci_objectstorage_namespace.release.namespace
    bucket = oci_objectstorage_bucket.release[0].name
    object = oci_objectstorage_object.existing_installer[0].object
    sha256 = sha256(oci_objectstorage_object.existing_installer[0].content)
    commit = local.approved_commit
  } : null
}
output "platform_resources" { value = local.platform_bindings }
