# Resource Group
resource "azurerm_resource_group" "this" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "this" {
  name                = var.log_analytics_workspace_name
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = var.tags
}

# Databricks Workspace with Unity Catalog enabled
resource "azurerm_databricks_workspace" "this" {
  name                = var.databricks_workspace_name
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  sku                 = "premium"

  # Enable Unity Catalog
  managed_services_cmk_key_vault_key_id = null
  
  custom_parameters {
    no_public_ip                                         = true
    public_subnet_name                                   = "public-subnet"
    private_subnet_name                                  = "private-subnet"
    virtual_network_id                                   = azurerm_virtual_network.this.id
    public_subnet_network_security_group_association_id = azurerm_subnet_network_security_group_association.public.id
    private_subnet_network_security_group_association_id = azurerm_subnet_network_security_group_association.private.id
  }

  tags = var.tags

  depends_on = [
    azurerm_subnet_network_security_group_association.public,
    azurerm_subnet_network_security_group_association.private,
  ]
}

# Virtual Network for Databricks
resource "azurerm_virtual_network" "this" {
  name                = "vnet-${var.databricks_workspace_name}"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name

  tags = var.tags
}

# Public Subnet
resource "azurerm_subnet" "public" {
  name                 = "public-subnet"
  resource_group_name  = azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = ["10.0.1.0/24"]

  delegation {
    name = "databricks-delegation-public"
    service_delegation {
      name = "Microsoft.Databricks/workspaces"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action",
      ]
    }
  }
}

# Private Subnet
resource "azurerm_subnet" "private" {
  name                 = "private-subnet"
  resource_group_name  = azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = ["10.0.2.0/24"]

  delegation {
    name = "databricks-delegation-private"
    service_delegation {
      name = "Microsoft.Databricks/workspaces"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action",
      ]
    }
  }
}

# Network Security Group for Public Subnet
resource "azurerm_network_security_group" "public" {
  name                = "nsg-public-${var.databricks_workspace_name}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name

  tags = var.tags
}

# Network Security Group for Private Subnet
resource "azurerm_network_security_group" "private" {
  name                = "nsg-private-${var.databricks_workspace_name}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name

  tags = var.tags
}

# Associate NSG with Public Subnet
resource "azurerm_subnet_network_security_group_association" "public" {
  subnet_id                 = azurerm_subnet.public.id
  network_security_group_id = azurerm_network_security_group.public.id
}

# Associate NSG with Private Subnet
resource "azurerm_subnet_network_security_group_association" "private" {
  subnet_id                 = azurerm_subnet.private.id
  network_security_group_id = azurerm_network_security_group.private.id
}

# Random suffix for storage account name
resource "random_string" "storage_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Storage Account for Unity Catalog
resource "azurerm_storage_account" "unity_catalog" {
  name                     = "ucsa${random_string.storage_suffix.result}"
  resource_group_name      = azurerm_resource_group.this.name
  location                 = azurerm_resource_group.this.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true

  tags = var.tags
}

# Storage Container for Unity Catalog
resource "azurerm_storage_container" "unity_catalog" {
  name                  = "unity-catalog"
  storage_account_name  = azurerm_storage_account.unity_catalog.name
  container_access_type = "private"
}

# Azure Databricks Access Connector (Managed Identity for Unity Catalog)
resource "azurerm_databricks_access_connector" "unity_catalog" {
  name                = "dac-${var.databricks_workspace_name}"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Role assignment for Access Connector to access Storage Account
resource "azurerm_role_assignment" "unity_catalog_storage" {
  scope                = azurerm_storage_account.unity_catalog.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.unity_catalog.identity[0].principal_id

  depends_on = [azurerm_databricks_access_connector.unity_catalog]
}

# Databricks Storage Credential for Unity Catalog
resource "databricks_storage_credential" "unity_catalog" {
  name = "unity-catalog-storage-credential-new"
  
  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.unity_catalog.id
  }

  depends_on = [
    azurerm_databricks_workspace.this,
    azurerm_role_assignment.unity_catalog_storage
  ]
}

# Unity Catalog Metastore with Storage Credential
resource "databricks_metastore" "this" {
  name                        = "unity-catalog-metastore-new"
  storage_root                = "abfss://unity-catalog@${azurerm_storage_account.unity_catalog.name}.dfs.core.windows.net/"
  region                      = azurerm_resource_group.this.location
  storage_root_credential_id  = databricks_storage_credential.unity_catalog.storage_credential_id

  depends_on = [
    azurerm_databricks_workspace.this,
    databricks_storage_credential.unity_catalog
  ]
}

# Assign Databricks workspace to metastore
resource "databricks_metastore_assignment" "this" {
  workspace_id = azurerm_databricks_workspace.this.workspace_id
  metastore_id = databricks_metastore.this.id

  depends_on = [databricks_metastore.this]
}

# Databricks Account Network Policy for Serverless Egress Gateway
resource "databricks_account_network_policy" "serverless_egress_gateway" {
  provider          = databricks.account
  account_id        = var.databricks_account_id
  network_policy_id = "serverless-egress-gateway"
  egress = {
    network_access = {
      restriction_mode = "RESTRICTED_ACCESS"
      
      # Allowed domains for Python package installation and Azure Log Analytics
      allowed_internet_destinations = [
        {
          destination = "pypi.org"
          internet_destination_type = "DNS_NAME"
        },
        {
          destination = "files.pythonhosted.org"
          internet_destination_type = "DNS_NAME"
        },
        {
          destination = "pypi.python.org"
          internet_destination_type = "DNS_NAME"
        },
        {
          destination = "ods.opinsights.azure.com"
          internet_destination_type = "DNS_NAME"
        }
      ]
      
      # Policy enforcement configuration
      # Enforce for all products except DBSQL and ML_SERVING which use dry run
      policy_enforcement = {
        enforcement_mode = "ENFORCED"
        dry_run_mode_product_filter = ["DBSQL", "ML_SERVING"]
      }
    }
  }
  
  depends_on = [azurerm_databricks_workspace.this]
}

# SQL Warehouse (2X-Small)
resource "databricks_sql_endpoint" "sql_warehouse" {
  name             = "SQL Warehouse 2X-Small"
  cluster_size     = "2X-Small"
  warehouse_type   = "PRO"
  max_num_clusters = 1
  min_num_clusters = 1
  auto_stop_mins   = 15
  enable_serverless_compute = true

  depends_on = [
    databricks_metastore_assignment.this
  ]
}

# Data sources for job cluster configuration
data "databricks_spark_version" "latest_lts" {
  long_term_support = true
}

data "databricks_node_type" "smallest" {
  local_disk = true
}

# Databricks Job based on YAML specification
resource "databricks_job" "test_job" {
  name = "test job"

  task {
    task_key = "test"

    notebook_task {
      notebook_path = "/Workspace/Users/josh.melton@databricks.com/test notebook"
      source        = "WORKSPACE"
    }
  }

  depends_on = [
    databricks_metastore_assignment.this
  ]
}
  
# Attach the network policy to the workspace using workspace_network_option
resource "databricks_workspace_network_option" "this" {
  provider          = databricks.account
  workspace_id      = azurerm_databricks_workspace.this.workspace_id
  network_policy_id = databricks_account_network_policy.serverless_egress_gateway.network_policy_id
  
  depends_on = [
    databricks_account_network_policy.serverless_egress_gateway,
    databricks_metastore_assignment.this
  ]
}

# Secret scope for app secrets
resource "databricks_secret_scope" "app_scope" {
  name = "app-scope"

  depends_on = [
    databricks_metastore_assignment.this
  ]
}

# Azure Log Analytics Workspace ID secret
resource "databricks_secret" "azure_logs_workspace_id" {
  key          = "AZURE_LOG_ANALYTICS_WORKSPACE_ID"
  string_value = azurerm_log_analytics_workspace.this.workspace_id
  scope        = databricks_secret_scope.app_scope.name

  depends_on = [databricks_secret_scope.app_scope]
}

# Azure Log Analytics Shared Key secret
resource "databricks_secret" "azure_logs_shared_key" {
  key          = "AZURE_LOG_ANALYTICS_SHARED_KEY"
  string_value = azurerm_log_analytics_workspace.this.primary_shared_key
  scope        = databricks_secret_scope.app_scope.name

  depends_on = [databricks_secret_scope.app_scope]
}

# Databricks App deployment for the example-app
resource "databricks_app" "example_app" {
  name        = "example-app"
  description = "Example Databricks App demonstrating SQL warehouse queries, job submission, and model serving"
  
  # User API scopes for on-behalf-of-user authentication
  user_api_scopes = [
    "sql",
    "dashboards.genie",
    "files.files",
    "serving.serving-endpoints",
    "vectorsearch.vector-search-indexes"
  ]

  resources = [{
    name = "sql_warehouse"
    sql_warehouse = {
      id         = databricks_sql_endpoint.sql_warehouse.id
      permission = "CAN_USE"
    }
    },
    {
      name = "model_serving_endpoint"
      serving_endpoint = {
        name       = "databricks-gemma-3-12b"
        permission = "CAN_QUERY"
      }
    },
    {
      name = "default_job"
      job = {
        id         = databricks_job.test_job.id
        permission = "CAN_MANAGE_RUN"
      }
    },
    {
      name = "azure_logs_workspace_id"
      secret = {
        scope      = "app-scope"
        key        = "AZURE_LOG_ANALYTICS_WORKSPACE_ID"
        permission = "READ"
      }
    },
    {
      name = "azure_logs_shared_key"
      secret = {
        scope      = "app-scope"
        key        = "AZURE_LOG_ANALYTICS_SHARED_KEY"
        permission = "READ"
      }
    }]

  depends_on = [
    databricks_sql_endpoint.sql_warehouse,
    databricks_job.test_job,
    databricks_metastore_assignment.this,
    databricks_secret.azure_logs_workspace_id,
    databricks_secret.azure_logs_shared_key
  ]
}