data "oci_identity_availability_domains" "available" {
  compartment_id = var.tenancy_ocid
}

data "oci_core_images" "ol9_a1" {
  count = var.create_instance && var.image_ocid == "" ? 1 : 0
  compartment_id = var.compartment_ocid
  operating_system = "Oracle Linux"
  shape = "VM.Standard.A1.Flex"
  state = "AVAILABLE"
  sort_by = "TIMECREATED"
  sort_order = "DESC"
}

data "oci_core_subnet" "existing" {
  count = var.create_instance && !var.create_network ? 1 : 0
  subnet_id = var.existing_subnet_ocid
}
data "oci_core_network_security_group" "existing" {
  count = var.create_instance && !var.create_network ? 1 : 0
  network_security_group_id = var.existing_nsg_ocid
}

locals {
  ol9_images = [for image in try(data.oci_core_images.ol9_a1[0].images, []) : image.id if can(regex("^9([.].*)?$", image.operating_system_version))]
  subnet_id = var.create_network ? oci_core_subnet.public[0].id : var.existing_subnet_ocid
  nsg_id = var.create_network ? oci_core_network_security_group.edge[0].id : var.existing_nsg_ocid
  image_id = var.image_ocid != "" ? var.image_ocid : try(local.ol9_images[0], null)
  availability_domain = try(data.oci_identity_availability_domains.available.availability_domains[var.availability_domain_index].name, null)
  policy_scope = var.compartment_ocid == var.tenancy_ocid ? "tenancy" : "compartment id ${var.compartment_ocid}"
  deployment_id = substr(md5("${var.compartment_ocid}:${var.deployment_name}"), 0, 12)
  user_data = var.create_instance ? templatefile("${path.module}/cloud-init-application.yaml.tftpl", { release_config = jsonencode({
    commit = local.approved_commit,
    tenancy_id = var.tenancy_ocid,
    compartment_id = var.compartment_ocid,
    namespace = data.oci_objectstorage_namespace.release.namespace,
    bucket = oci_objectstorage_bucket.release[0].name,
    object = oci_objectstorage_object.release[0].object,
    sha256 = filesha256("${path.module}/application.tgz")
  }) }) : ""
}

resource "oci_core_vcn" "isolated" {
  count = var.create_network ? 1 : 0
  compartment_id = var.compartment_ocid
  cidr_blocks = ["10.42.0.0/16"]
  display_name = "sds-automation-vcn"
  dns_label = "sdsauto"
}
resource "oci_core_internet_gateway" "edge" {
  count = var.create_network ? 1 : 0
  compartment_id = var.compartment_ocid
  vcn_id = oci_core_vcn.isolated[0].id
  enabled = true
  display_name = "sds-automation-igw"
}
resource "oci_core_route_table" "public" {
  count = var.create_network ? 1 : 0
  compartment_id = var.compartment_ocid
  vcn_id = oci_core_vcn.isolated[0].id
  display_name = "sds-automation-public-route"
  route_rules {
    destination = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.edge[0].id
  }
}
resource "oci_core_security_list" "subnet" {
  count = var.create_network ? 1 : 0
  compartment_id = var.compartment_ocid
  vcn_id = oci_core_vcn.isolated[0].id
  display_name = "sds-automation-subnet-egress"
  egress_security_rules {
    protocol = "all"
    destination = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
  }
}
resource "oci_core_subnet" "public" {
  count = var.create_network ? 1 : 0
  compartment_id = var.compartment_ocid
  vcn_id = oci_core_vcn.isolated[0].id
  cidr_block = "10.42.1.0/24"
  display_name = "sds-automation-public-subnet"
  dns_label = "edge"
  prohibit_public_ip_on_vnic = false
  route_table_id = oci_core_route_table.public[0].id
  security_list_ids = [oci_core_security_list.subnet[0].id]
}
resource "oci_core_network_security_group" "edge" {
  count = var.create_network ? 1 : 0
  compartment_id = var.compartment_ocid
  vcn_id = oci_core_vcn.isolated[0].id
  display_name = "ig-quick-action-NSG-automated"
}
resource "oci_core_network_security_group_security_rule" "web" {
  for_each = var.create_network ? { http = 80, https = 443 } : {}
  network_security_group_id = oci_core_network_security_group.edge[0].id
  direction = "INGRESS"
  protocol = "6"
  source = "0.0.0.0/0"
  source_type = "CIDR_BLOCK"
  stateless = false
  tcp_options {
    destination_port_range {
      min = each.value
      max = each.value
    }
  }
}
resource "oci_core_network_security_group_security_rule" "outbound" {
  count = var.create_network ? 1 : 0
  network_security_group_id = oci_core_network_security_group.edge[0].id
  direction = "EGRESS"
  protocol = "all"
  destination = "0.0.0.0/0"
  destination_type = "CIDR_BLOCK"
  stateless = false
}

resource "oci_core_instance" "sds_automated" {
  count = var.create_instance ? 1 : 0
  availability_domain = local.availability_domain
  compartment_id = var.compartment_ocid
  display_name = "sanders-dash-seal-automated"
  shape = "VM.Standard.A1.Flex"
  shape_config {
    ocpus = 1
    memory_in_gbs = 6
  }
  source_details {
    source_type = "image"
    source_id = local.image_id
    boot_volume_size_in_gbs = 50
  }
  create_vnic_details {
    subnet_id = local.subnet_id
    nsg_ids = [local.nsg_id]
    assign_public_ip = var.assign_public_ip
    display_name = "sds-automation-primary-vnic"
  }
  instance_options {
    are_legacy_imds_endpoints_disabled = true
  }
  metadata = merge({ user_data = base64encode(local.user_data) }, var.ssh_public_key == "" ? {} : { ssh_authorized_keys = var.ssh_public_key })
  freeform_tags = { "SandersRelease" = local.approved_commit, "SandersBootProfile" = "application" }
  lifecycle {
    prevent_destroy = true
    precondition {
      condition = local.subnet_id != "" && local.nsg_id != ""
      error_message = "Select actual existing subnet and NSG OCIDs, or enable create_network."
    }
    precondition {
      condition = local.image_id != null && local.availability_domain != null
      error_message = "A compatible image and actual availability domain are required."
    }
    precondition {
      condition = var.create_network || try(data.oci_core_subnet.existing[0].vcn_id == data.oci_core_network_security_group.existing[0].vcn_id, false)
      error_message = "The existing subnet and NSG must belong to the same actual VCN."
    }
    precondition {
      condition = !var.assign_public_ip || var.create_network || try(!data.oci_core_subnet.existing[0].prohibit_public_ip_on_vnic, false)
      error_message = "The selected subnet prohibits assigning a public IP."
    }
    precondition {
      condition = !startswith(var.compartment_ocid, "ocid1.tenancy.") || var.compartment_ocid == var.tenancy_ocid
      error_message = "The root compartment must be this tenancy's actual OCID."
    }
    precondition {
      condition = length(base64encode(local.user_data)) < 30000
      error_message = "User data exceeds the conservative metadata budget."
    }
    precondition {
      condition = var.assign_public_ip
      error_message = "Public application deployment requires a public IPv4."
    }
  }
}

data "oci_objectstorage_namespace" "release" {
  compartment_id = var.compartment_ocid
}
resource "oci_objectstorage_bucket" "release" {
  count = var.create_instance ? 1 : 0
  compartment_id = var.compartment_ocid
  namespace = data.oci_objectstorage_namespace.release.namespace
  name = "sds-release-${local.deployment_id}"
  access_type = "NoPublicAccess"
  storage_tier = "Standard"
}
resource "oci_objectstorage_object" "release" {
  count = var.create_instance ? 1 : 0
  namespace = data.oci_objectstorage_namespace.release.namespace
  bucket = oci_objectstorage_bucket.release[0].name
  object = "releases/${local.approved_commit}.tgz"
  source = "${path.module}/application.tgz"
  content_type = "application/gzip"
}
resource "oci_identity_dynamic_group" "bootstrap" {
  count = var.create_instance ? 1 : 0
  compartment_id = var.tenancy_ocid
  name = "SDSBootstrap${local.deployment_id}"
  description = "Only this deployment instance may retrieve its private application release"
  matching_rule = "ALL {instance.id = '${oci_core_instance.sds_automated[0].id}'}"
}
resource "oci_identity_policy" "bootstrap" {
  count = var.create_instance ? 1 : 0
  compartment_id = var.tenancy_ocid
  name = "SDSBootstrap${local.deployment_id}"
  description = "Scoped read-only release retrieval and primary VNIC metadata"
  statements = [
    "Allow dynamic-group id ${oci_identity_dynamic_group.bootstrap[0].id} to read objects in ${local.policy_scope} where all {target.bucket.name='${oci_objectstorage_bucket.release[0].name}', request.permission='OBJECT_READ'}",
    "Allow dynamic-group id ${oci_identity_dynamic_group.bootstrap[0].id} to inspect instance-family in ${local.policy_scope}",
    "Allow dynamic-group id ${oci_identity_dynamic_group.bootstrap[0].id} to read vnics in ${local.policy_scope}",
    "Allow dynamic-group id ${oci_identity_dynamic_group.bootstrap[0].id} to inspect all-resources in ${local.policy_scope}",
    "Allow dynamic-group id ${oci_identity_dynamic_group.bootstrap[0].id} to inspect compartments in tenancy",
    "Allow dynamic-group id ${oci_identity_dynamic_group.bootstrap[0].id} to inspect tenancies in tenancy"
  ]
}
resource "terraform_data" "application_installation" {
  count = var.create_instance ? 1 : 0
  triggers_replace = [oci_core_instance.sds_automated[0].id, local.approved_commit]
  depends_on = [oci_identity_policy.bootstrap]
  provisioner "local-exec" {
    command = "python3 \"${path.module}/wait_application.py\""
    environment = {
      SDS_EXPECTED_PUBLIC_IPV4 = oci_core_instance.sds_automated[0].public_ip
      SDS_EXPECTED_COMMIT = local.approved_commit
    }
  }
}
