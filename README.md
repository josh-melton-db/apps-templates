# Azure Databricks with Unity Catalog Deployment

This Terraform configuration deploys the following Azure resources:

- **Azure Resource Group**: Container for all resources
- **Azure Databricks Workspace**: Premium tier with Unity Catalog enabled
- **Azure Log Analytics Workspace**: For monitoring and logging
- **Unity Catalog Metastore**: For data governance and management
- **Virtual Network**: Custom VNet with dedicated subnets for Databricks
- **Storage Account**: ADLS Gen2 for Unity Catalog storage
- **Serverless Egress Gateway**: Network policy for controlled outbound access

## Prerequisites

1. **Azure CLI**: Install and authenticate with `az login`
2. **Terraform**: Install Terraform v1.0+
3. **Azure Permissions**: Ensure you have Contributor access to the subscription
4. **Databricks Account Admin**: Account admin privileges required for network policies
5. **Databricks Authentication**: Configure account-level authentication (see below)

## Quick Start

### 1. Configure Databricks Account Authentication

For the serverless egress gateway, you need account-level authentication using the Databricks CLI:

```bash
# Install Databricks CLI if not already installed
pip install databricks-cli

# Login to your Databricks account (requires Account Admin privileges)
databricks auth login --host https://accounts.azuredatabricks.net --account-id <your-account-id>
```

This will open a browser window for authentication and store the credentials securely.

### 2. Set Required Variables

Find your Databricks Account ID:
- Go to [Databricks Account Console](https://accounts.azuredatabricks.net/)
- Your Account ID is in the URL: `https://accounts.azuredatabricks.net/account/<ACCOUNT-ID>`

```bash
export TF_VAR_databricks_account_id="<your-databricks-account-id>"
```

### 3. Deploy Infrastructure

1. **Clone and navigate to the directory**:
   ```bash
   cd /path/to/this/directory
   ```

2. **Initialize Terraform**:
   ```bash
   terraform init
   ```

3. **Plan the deployment**:
   ```bash
   terraform plan
   ```

4. **Deploy the infrastructure**:
   ```bash
   terraform apply
   ```

### Troubleshooting Authentication

If you encounter "invalid Databricks Account configuration" errors:

1. **Account Admin Required**: Ensure you have Account Admin privileges in your Databricks account
2. **CLI Authentication**: Make sure you've run `databricks auth login` with the correct account ID
3. **Account ID**: Verify your account ID in the [Databricks Account Console](https://accounts.azuredatabricks.net)
4. **Re-authenticate**: Try logging out and back in:
   ```bash
   databricks auth logout
   databricks auth login --host https://accounts.azuredatabricks.net --account-id <your-account-id>
   ```

**Manual Fallback Option:**
If Terraform authentication continues to fail, you can create the network policy manually:
1. Go to [Databricks Account Console](https://accounts.azuredatabricks.net)
2. Navigate to **Settings** → **Network Policies**  
3. Create a new policy with these settings:
   - **Policy Type**: Serverless Egress Gateway
   - **Restriction Mode**: RESTRICTED_ACCESS
   - **Allowed Destinations**: `pypi.org`, `files.pythonhosted.org`, `pypi.python.org`, `ods.opinsights.azure.com`
   - **Enforcement**: Mixed mode (dry run for DBSQL/ML_SERVING, enforced for others)
4. Attach the policy to your workspace

## Configuration

### Required Variables

- `location`: Azure region (default: "East US 2")
- `resource_group_name`: Resource group name (default: "databricks-apps-template-rg")
- `databricks_workspace_name`: Databricks workspace name (default: "databricks-apps-template-workspace")
- `log_analytics_workspace_name`: Log Analytics workspace name (default: "databricks-apps-logs")
- `databricks_account_id`: Databricks Account ID (required for network policies)

### Optional Variables

- `tags`: Map of tags to apply to resources
- `additional_allowed_domains`: Additional domains to allow in the serverless egress policy (default: `[]`)

## Unity Catalog Setup

After deployment, Unity Catalog will be automatically configured with:

- A dedicated metastore in your specified region
- ADLS Gen2 storage account with hierarchical namespace enabled
- Automatic assignment of the workspace to the metastore

## Serverless Egress Gateway (Network Policy)

This deployment includes a **deny-by-default** serverless egress gateway that controls outbound network access from serverless compute resources. The policy is automatically created and attached via Terraform.

### Allowed Destinations

- **PyPI - Python Package Index**:
  - `pypi.org`, `files.pythonhosted.org`, `pypi.python.org`

- **Azure Log Analytics**:
  - `ods.opinsights.azure.com` - For custom log data ingestion

### Configuration Options

- **Mixed Enforcement**: DBSQL and Model Serving use dry run mode, all other products are enforced
- **Additional Domains**: Add custom domains via `additional_allowed_domains` variable
- **Internet Access**: Set to `RESTRICTED_ACCESS` for deny-by-default behavior

### Testing and Validation

1. **DBSQL & Model Serving**: These services operate in dry run mode - requests are logged but not blocked
2. **Other Products**: Notebooks, jobs, and pipelines have restrictions actively enforced
3. **Review Logs**: Check `system.access.outbound_network` table in Unity Catalog for denied/logged requests
4. **Add Domains**: Include additional required domains in `additional_allowed_domains`

### Important Notes

- **DBSQL & Model Serving**: Dry run mode - violations logged but not blocked
- **Notebooks, Jobs, Pipelines**: Fully enforced - violations are blocked
- All other outbound traffic is **denied by default**
- Changes take effect within 10 minutes
- Restart serverless compute after changing enforcement mode

## Outputs

The configuration provides several useful outputs:

- `databricks_workspace_url`: Direct URL to access your Databricks workspace
- `log_analytics_workspace_id`: Log Analytics workspace ID for monitoring setup
- `unity_catalog_metastore_id`: Unity Catalog metastore ID
- `network_policy_id`: Databricks network policy ID for serverless egress gateway
- `network_policy_restriction_mode`: Network policy restriction mode (RESTRICTED)
- `network_policy_enforcement_mode`: Policy enforcement mode (DRY_RUN or ENFORCED)
- Network resource IDs for integration purposes

## Post-Deployment Steps

1. **Access Databricks**: Use the `databricks_workspace_url` output to access your workspace
2. **Configure Unity Catalog**: 
   - Create catalogs, schemas, and tables as needed
   - Set up data access policies
   - Configure external locations if needed
3. **Test Serverless Egress Gateway**: The network policy is automatically configured - monitor logs and disable dry run when ready
4. **Set up monitoring**: Use the Log Analytics workspace for Databricks monitoring

## Clean Up

To destroy all resources:

```bash
terraform destroy
```

## Security Considerations

- The Databricks workspace is deployed with a premium SKU for Unity Catalog support
- Network security groups are created but with default rules
- Storage account uses private endpoints where possible
- **Serverless egress gateway** implements deny-by-default outbound access control
- Network policy starts in dry-run mode to prevent disruption during initial deployment
- Consider implementing additional security measures based on your organization's requirements

## Troubleshooting

- **Provider Authentication**: Ensure `az login` is completed
- **Permissions**: Verify Contributor access to the subscription
- **Regional Availability**: Ensure Unity Catalog is available in your chosen region
- **Naming Conflicts**: Adjust resource names if conflicts occur

For additional support, refer to the [Azure Databricks documentation](https://docs.microsoft.com/en-us/azure/databricks/) and [Unity Catalog documentation](https://docs.databricks.com/data-governance/unity-catalog/index.html).