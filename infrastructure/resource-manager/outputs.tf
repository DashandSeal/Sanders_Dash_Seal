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
  value = "application"
}
output "application_status" {
  value = var.create_instance ? "APPLICATION_INSTALLATION_CHECKED_BY_JOB: completion requires exact release and public process health. TLS and business-integration readiness remain separate; inspect /readyz and host logs." : "NOT_INSTALLED: additional resource creation is disabled; no deployment was performed by this stack."
}
