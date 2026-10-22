output "instance_id" {
  value = try(oci_core_instance.sds_automated[0].id, null)
}
output "public_ip" {
  value = try(oci_core_instance.sds_automated[0].public_ip, null)
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
  value = var.boot_profile
}
output "application_status" {
  value = "NOT_VERIFIED: Terraform Apply provisions infrastructure; inspect cloud-init, authority, runtime and readiness evidence before activation."
}
