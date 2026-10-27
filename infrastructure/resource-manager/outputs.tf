output "instance_id" {
  value = var.create_instance && length(oci_core_instance.sds_automated) > 0 ? oci_core_instance.sds_automated[0].id : null
}

output "public_ip" {
  value = var.create_instance && length(oci_core_instance.sds_automated) > 0 ? oci_core_instance.sds_automated[0].public_ip : null
}

output "subnet_id" {
  value = local.subnet_id
}

output "nsg_id" {
  value = local.nsg_id
}

output "approved_commit" {
  value = local.approved_commit
}

output "boot_profile" {
  value = "application"
}

output "application_status" {
  value = var.create_instance ? "APPLICATION_INSTALLATION_CHECKED_BY_JOB" : "BYPASSED"
}
