variable "tenancy_ocid" {
  type = string
  description = "Actual tenancy OCID; Resource Manager prepopulates this."
  validation {
    condition = can(regex("^ocid1\\.tenancy\\.oc1\\.\\.[A-Za-z0-9]{40,}$", var.tenancy_ocid))
    error_message = "Use the actual tenancy OCID."
  }
}
variable "compartment_ocid" {
  type = string
  description = "Actual root tenancy OCID or selected compartment OCID."
  validation {
    condition = can(regex("^ocid1\\.(tenancy|compartment)\\.oc1\\.\\.[A-Za-z0-9]{40,}$", var.compartment_ocid))
    error_message = "Use a complete actual compartment/root tenancy OCID."
  }
}
variable "region" {
  type = string
  default = "us-phoenix-1"
  validation {
    condition = var.region == "us-phoenix-1"
    error_message = "This stack targets the existing Phoenix home-region plan."
  }
}
variable "create_instance" {
  type = bool
  default = true
  description = "Enable one NEW 1-OCPU/6-GB A1 instance after reviewing remaining tenancy capacity. Does not update the existing VM."
}
variable "create_network" {
  type = bool
  default = false
  description = "Create a separate VCN/network; default reuses the existing subnet and NSG."
}
variable "existing_subnet_ocid" {
  type = string
  default = ""
  validation {
    condition = var.existing_subnet_ocid == "" || can(regex("^ocid1\\.subnet\\.oc1\\.phx\\.[A-Za-z0-9]{40,}$", var.existing_subnet_ocid))
    error_message = "Use the actual Phoenix subnet OCID, not its display name."
  }
}
variable "existing_nsg_ocid" {
  type = string
  default = ""
  validation {
    condition = var.existing_nsg_ocid == "" || can(regex("^ocid1\\.networksecuritygroup\\.oc1\\.phx\\.[A-Za-z0-9]{40,}$", var.existing_nsg_ocid))
    error_message = "Use the actual ig-quick-action-NSG OCID."
  }
}
variable "image_ocid" {
  type = string
  default = ""
  description = "Optional explicit compatible Oracle Linux 9 ARM64 image. Empty selects the latest matching platform image at Plan time."
  validation {
    condition = var.image_ocid == "" || can(regex("^ocid1\\.image\\.oc1\\.phx\\.[A-Za-z0-9]{40,}$", var.image_ocid))
    error_message = "Use a real Phoenix image OCID or leave empty for the platform image lookup."
  }
}
variable "availability_domain_index" {
  type = number
  default = 0
  description = "Index into actual tenancy availability domains (0, 1 or 2); shape capacity still depends on OCI."
  validation {
    condition = contains([0, 1, 2], var.availability_domain_index)
    error_message = "Choose 0, 1 or 2."
  }
}
variable "assign_public_ip" {
  type = bool
  default = true
}
variable "ssh_public_key" {
  type = string
  default = ""
  description = "Optional OpenSSH PUBLIC key for recovery. No private key, password or token."
  validation {
    condition = var.ssh_public_key == "" || can(regex("^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256) [A-Za-z0-9+/=]+( .*)?$", var.ssh_public_key))
    error_message = "Supply an OpenSSH public key or leave empty."
  }
}
variable "deployment_name" {
  type = string
  default = "sanders-dash-seal"
  description = "Unique name for this stack's private artifact bucket and IAM identities."
  validation {
    condition = can(regex("^[a-z][a-z0-9-]{2,39}$", var.deployment_name))
    error_message = "Use 3–40 lowercase letters, digits and hyphens."
  }
}
