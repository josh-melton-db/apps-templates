terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~>1.0"
    }
  }
}

provider "azurerm" {
  features {}
}

provider "databricks" {
  azure_workspace_resource_id = azurerm_databricks_workspace.this.id
  auth_type                   = "azure-cli"
}

# Databricks provider for account-level operations
provider "databricks" {
  alias = "account"
  host  = "https://accounts.azuredatabricks.net"
  # Uses Databricks CLI authentication with specific profile
  profile = "ACCOUNT-ccb842e7-2376-4152-b0b0-29fa952379b8"
}