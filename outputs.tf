# Resource Group Outputs
output "resource_group_name" {
  description = "Name of the created resource group"
  value       = azurerm_resource_group.this.name
}

output "resource_group_location" {
  description = "Location of the created resource group"
  value       = azurerm_resource_group.this.location
}

# Databricks Workspace Outputs
output "databricks_workspace_url" {
  description = "URL of the Databricks workspace"
  value       = "https://${azurerm_databricks_workspace.this.workspace_url}/"
}

output "databricks_workspace_id" {
  description = "The Databricks workspace ID"
  value       = azurerm_databricks_workspace.this.workspace_id
}

output "databricks_workspace_resource_id" {
  description = "The Azure resource ID of the Databricks workspace"
  value       = azurerm_databricks_workspace.this.id
}

# Log Analytics Workspace Outputs
output "log_analytics_workspace_id" {
  description = "The Log Analytics workspace ID"
  value       = azurerm_log_analytics_workspace.this.workspace_id
}

output "log_analytics_workspace_name" {
  description = "The Log Analytics workspace name"
  value       = azurerm_log_analytics_workspace.this.name
}

output "log_analytics_primary_shared_key" {
  description = "The primary shared key for the Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.this.primary_shared_key
  sensitive   = true
}

# Unity Catalog Outputs
output "unity_catalog_metastore_id" {
  description = "Unity Catalog metastore ID"
  value       = databricks_metastore.this.id
}

output "unity_catalog_storage_account_name" {
  description = "Storage account name for Unity Catalog"
  value       = azurerm_storage_account.unity_catalog.name
}

output "unity_catalog_storage_root" {
  description = "Storage root path for Unity Catalog"
  value       = databricks_metastore.this.storage_root
}

# Network Outputs
output "virtual_network_id" {
  description = "Virtual network ID"
  value       = azurerm_virtual_network.this.id
}

output "public_subnet_id" {
  description = "Public subnet ID"
  value       = azurerm_subnet.public.id
}

output "private_subnet_id" {
  description = "Private subnet ID"
  value       = azurerm_subnet.private.id
}

# Network Policy Outputs
output "network_policy_id" {
  description = "Databricks network policy ID for serverless egress gateway"
  value       = databricks_account_network_policy.serverless_egress_gateway.network_policy_id
}

output "network_policy_restriction_mode" {
  description = "Network policy restriction mode"
  value       = databricks_account_network_policy.serverless_egress_gateway.egress.network_access.restriction_mode
}

output "network_policy_enforcement_mode" {
  description = "Network policy enforcement mode (DRY_RUN or ENFORCED)"
  value       = databricks_account_network_policy.serverless_egress_gateway.egress.network_access.policy_enforcement.enforcement_mode
}

# SQL Warehouse Outputs
output "sql_warehouse_id" {
  description = "ID of the SQL warehouse"
  value       = databricks_sql_endpoint.sql_warehouse.id
}

output "sql_warehouse_jdbc_url" {
  description = "JDBC URL for the SQL warehouse"
  value       = databricks_sql_endpoint.sql_warehouse.jdbc_url
}

output "sql_warehouse_odbc_params" {
  description = "ODBC connection parameters for the SQL warehouse"
  value       = databricks_sql_endpoint.sql_warehouse.odbc_params
  sensitive   = true
}

output "sql_warehouse_name" {
  description = "Name of the SQL warehouse"
  value       = databricks_sql_endpoint.sql_warehouse.name
}

# Job Outputs
output "job_id" {
  description = "ID of the Databricks job"
  value       = databricks_job.test_job.id
}

output "job_url" {
  description = "URL of the Databricks job"
  value       = databricks_job.test_job.url
}

# Databricks App Outputs
output "databricks_app_name" {
  description = "Name of the Databricks App"
  value       = databricks_app.example_app.name
}

output "databricks_app_url" {
  description = "URL of the deployed Databricks App"
  value       = databricks_app.example_app.url
}

