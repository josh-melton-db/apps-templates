variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "East US 2"
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "databricks-apps-template-rg"
}

variable "databricks_workspace_name" {
  description = "Name of the Databricks workspace"
  type        = string
  default     = "databricks-apps-template-workspace"
}

variable "log_analytics_workspace_name" {
  description = "Name of the Log Analytics workspace"
  type        = string
  default     = "databricks-apps-logs"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default = {
    keep-until = "2026-07-27"
    owner     = "josh.melton@databricks.com"
  }
}

variable "enable_network_policy_dry_run" {
  description = "Legacy variable - network policy now uses mixed enforcement (SQL/ML_SERVING=dry_run, others=enforced)"
  type        = bool
  default     = true
}

variable "additional_allowed_domains" {
  description = "Additional domains to allow in the serverless egress policy"
  type        = list(string)
  default     = []
}

variable "databricks_account_id" {
  description = "Databricks Account ID for account-level operations (required for network policies)"
  type        = string
  default     = "ccb842e7-2376-4152-b0b0-29fa952379b8"
}

