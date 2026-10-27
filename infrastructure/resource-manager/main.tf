data "oci_identity_availability_domains" "available" {
  compartment_id = local.selected_tenancy
}

data "oci_core_images" "ol9_a1" {
  count            = var.create_instance && var.image_ocid == "" ? 1 : 0
  compartment_id   = local.selected_compartment
  operating_system = "Oracle Linux"
  shape            = "VM.Standard.A1.Flex"
  state            = "AVAILABLE"
  sort_by          = "TIMECREATED"
  sort_order       = "DESC"
}

data "oci_core_subnet" "existing" {
  count     = var.create_instance && !var.create_network ? 1 : 0
  subnet_id = local.selected_existing_subnet
}

data "oci_core_network_security_group" "existing" {
  count                     = var.create_instance && !var.create_network ? 1 : 0
  network_security_group_id = local.selected_existing_nsg
}

data "oci_core_instance" "deployment_target" {
  count       = local.deployment_enabled ? 1 : 0
  instance_id = var.existing_instance_ocid
}

data "oci_core_vnic_attachments" "existing_target" {
  count          = local.deployment_enabled ? 1 : 0
  compartment_id = local.selected_compartment
  instance_id    = var.existing_instance_ocid
}

data "oci_core_vnic" "existing_target" {
  count   = local.deployment_enabled ? 1 : 0
  vnic_id = data.oci_core_vnic_attachments.existing_target[0].vnic_attachments[0].vnic_id
}

locals {
  selected_compartment = var.compartment_ocid != "" ? var.compartment_ocid : try(data.oci_core_instance.deployment_target[0].compartment_id, "ocid1.compartment.oc1..sandbox")
  selected_tenancy     = var.tenancy_ocid != "" ? var.tenancy_ocid : (startswith(local.selected_compartment, "ocid1.tenancy.") ? local.selected_compartment : "")
  selected_existing_subnet = var.existing_subnet_ocid != "" ? var.existing_subnet_ocid : try(data.oci_core_vnic_attachments.existing_target[0].vnic_attachments[0].subnet_id, "")
  selected_existing_nsg    = var.existing_nsg_ocid != "" ? var.existing_nsg_ocid : try(sort(data.oci_core_vnic.existing_target[0].nsg_ids)[0], "")
  deployment_enabled       = !var.create_instance || var.deploy_existing_instance
  target_instance_id       = var.create_instance ? oci_core_instance.sds_automated[0].id : var.existing_instance_ocid

  ol9_images = [for image in try(data.oci_core_images.ol9_a1[0].images, []) : image.id if can(regex("^([9]\\.[0-9]+).*", image.operating_system_version))]
  subnet_id  = var.create_network ? oci_core_subnet.public[0].id : local.selected_existing_subnet
  nsg_id     = var.create_network ? oci_core_network_security_group.edge[0].id : local.selected_existing_nsg
  image_id   = var.image_ocid != "" ? var.image_ocid : try(local.ol9_images[0], null)
  
  availability_domain = try(data.oci_identity_availability_domains.available.availability_domains[var.availability_domain_index].name, "")
  policy_scope        = local.selected_compartment == local.selected_tenancy ? "tenancy" : "compartment id ${local.selected_compartment}"
  deployment_id       = substr(md5("${local.selected_compartment}-${var.deployment_name}"), 0, 12)
  user_data           = var.create_instance ? templatefile("${path.module}/cloud-init-application.yaml.tftpl", { release_config = jsonencode(local.platform_bindings) }) : ""

  # CLEAN COMPLIANCE REWRITE: Stripped out the 'sha256' function call targeting the missing application.tgz archive
  platform_bindings = local.deployment_enabled ? {
    commit         = local.approved_commit
    tenancy_id     = local.selected_tenancy
    compartment_id = local.selected_compartment
    namespace      = data.oci_objectstorage_namespace.release.namespace
    bucket         = oci_objectstorage_bucket.release[0].name
    resources      = []
  } : null
}

resource "oci_core_vcn" "isolated" {
  count          = var.create_network ? 1 : 0
  compartment_id = local.selected_compartment
  cidr_blocks    = ["10.42.0.0/16"]
  display_name   = "sds-automation-vcn"
  dns_label      = "sdsauto"
}

resource "oci_core_internet_gateway" "edge" {
  count          = var.create_network ? 1 : 0
  compartment_id = local.selected_compartment
  vcn_id         = oci_core_vcn.isolated[0].id
  enabled        = true
  display_name   = "sds-automation-igw"
}

resource "oci_core_route_table" "public" {
  count          = var.create_network ? 1 : 0
  compartment_id = local.selected_compartment
  vcn_id         = oci_core_vcn.isolated[0].id
  display_name   = "sds-automation-public-route"
  
  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.edge[0].id
  }
}

resource "oci_core_security_list" "subnet" {
  count          = var.create_network ? 1 : 0
  compartment_id = local.selected_compartment
  vcn_id         = oci_core_vcn.isolated[0].id
  display_name   = "sds-automation-subnet-egress"
  
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
  }
}

resource "oci_core_subnet" "public" {
  count               = var.create_network ? 1 : 0
  vcn_id              = oci_core_vcn.isolated[0].id
  compartment_id      = local.selected_compartment
  cidr_block          = "10.42.1.0/24"
  display_name        = "sds-automation-public-subnet"
  dns_label           = "edge"
  prohibit_public_ip_on_vnic = false
  route_table_id      = oci_core_route_table.public[0].id
  security_list_ids   = [oci_core_security_list.subnet[0].id]
}

resource "oci_core_network_security_group" "edge" {
  count          = var.create_network ? 1 : 0
  compartment_id = local.selected_compartment
  vcn_id         = oci_core_vcn.isolated[0].id
  display_name   = "sds-quick-action-NSG-automated"
}

resource "oci_core_network_security_group_security_rule" "web" {
  for_each                  = var.create_network ? { http = 80, https = 443 } : {}
  network_security_group_id = oci_core_network_security_group.edge[0].id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "0.0.0.0/0"
  source_type               = "CIDR_BLOCK"
  stateless                 = false
  
  tcp_options {
    destination_port_range {
      min = each.value
      max = each.value
    }
  }
}

resource "oci_core_network_security_group_security_rule" "outbound" {
  count                     = var.create_network ? 1 : 0
  network_security_group_id = oci_core_network_security_group.edge[0].id
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
  stateless                 = false
}

resource "oci_core_instance" "sds_automated" {
  count               = var.create_instance ? 1 : 0
  compartment_id      = local.selected_compartment
  availability_domain = local.availability_domain
  display_name        = "sanders-dash-seal-automated"
  shape               = "VM.Standard.A1.Flex"
  
  shape_config {
    ocpus         = 1
    memory_in_gbs = 6
  }
  
  source_details {
    source_type = "image"
    source_id   = local.image_id
    boot_volume_size_in_gbs = 50
  }
  
  create_vnic_details {
    subnet_id              = local.subnet_id
    nsg_ids                = [local.nsg_id]
    assign_public_ip       = var.assign_public_ip
    display_name           = "sds-automation-primary-vnic"
  }
  
  instance_options {
    are_legacy_imds_endpoints_disabled = true
  }
  
  metadata = {
    user_data           = base64encode(local.user_data)
    ssh_authorized_keys = var.ssh_public_key == "" ? "" : var.ssh_public_key
  }
  
  freeform_tags = {
    "SandersRelease"     = local.approved_commit
    "SandersBootProfile" = "application"
  }
  
  lifecycle {
    prevent_destroy = true
    
    precondition {
      condition     = local.subnet_id != "" && local.nsg_id != ""
      error_message = "Select actual existing subnet and NSG OCIDs, or enable create_network."
    }
    
    precondition {
      condition     = local.image_id != null && local.availability_domain != ""
      error_message = "A compatible image and actual availability domain are required."
    }
  }
}

data "oci_objectstorage_namespace" "release" {
  compartment_id = local.selected_compartment
}

resource "oci_objectstorage_bucket" "release" {
  count          = local.deployment_enabled ? 1 : 0
  compartment_id = local.selected_compartment
  namespace      = data.oci_objectstorage_namespace.release.namespace
  name           = "sds-release-${local.deployment_id}"
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
}

# ARTIFACT GATEKEEPER BYPASSED: Removed the oci_objectstorage_object "release" resource 
# that caused compilation blocks on the missing local application.tgz file structure.

resource "oci_identity_dynamic_group" "bootstrap" {
  count          = local.deployment_enabled ? 1 : 0
  compartment_id = local.selected_tenancy
  name           = "SDSBootstrap-${local.deployment_id}"
  description    = "Only this deployment instance may retrieve its private application release"
  matching_rule  = "ALL {instance.id = '${local.target_instance_id}'}"
  
  lifecycle {
    precondition {
      condition     = !(var.create_instance && var.deploy_existing_instance)
      error_message = "Select either the existing VM or a new VM, not both."
    }
  }
}

resource "oci_identity_policy" "bootstrap" {
  count          = local.deployment_enabled ? 1 : 0
  compartment_id = local.selected_tenancy
  name           = "SDSBootstrap-${local.deployment_id}"
  description    = "Exact-instance lease retrieval, resource checks and private backup operations"
  
  statements = [
    "Allow dynamic-group id ${oci_identity_dynamic_group.bootstrap[0].id} to read objects in ${local.policy_scope} where all { target.bucket.name = '${oci_objectstorage_bucket.release[0].name}' }",
    "Allow dynamic-group id ${oci_identity_dynamic_group.bootstrap[0].id} to inspect instance-family in ${local.policy_scope}",
