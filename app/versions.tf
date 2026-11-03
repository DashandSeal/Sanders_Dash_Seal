terraform {
  required_version = ">= 1.5.7, < 1.6.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "9.11.0"
    }
  }
}

# Resource Manager provides job authentication. No VM principal or API key here.
provider "oci" {
  region = var.region
}
