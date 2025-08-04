# Databricks Example App

A comprehensive example Databricks App demonstrating best practices and various integration techniques using **native Databricks Apps features** (no Docker required) with a **Dash web UI**.

This app leverages the [Databricks Apps platform](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/best-practices) which provides:
- **Managed Python 3.11 Environment**: No container required, runs on Ubuntu 22.04 LTS
- **Automatic Authentication**: Uses Databricks CLI configuration locally, automatic in Apps
- **Pre-installed Libraries**: Common frameworks already available (including Dash!)
- **Native Resource Management**: Secrets and warehouses managed through valueFrom references

## Features Demonstrated

✅ **SQL Warehouse Integration**: Execute parameterized SQL queries to prevent injection attacks  
✅ **Job Submission**: Submit Databricks jobs programmatically  
✅ **Model Serving**: Call Databricks model serving endpoints  
✅ **User Authorization**: Execute operations with logged-in user's permissions and Unity Catalog policies  
✅ **Input Validation**: Robust input validation using Pydantic  
✅ **Error Handling**: Comprehensive error handling with structured logging  
✅ **Secrets Management**: Use secrets with `valueFrom` in app configuration  
✅ **Dual Logging**: Log to both stdout/stderr and Azure Log Analytics  
✅ **Port Binding**: Listen on 0.0.0.0 with configurable port via `DATABRICKS_APP_PORT`  
✅ **Pinned Dependencies**: Use requirements.txt with pinned library versions  
✅ **Fine-grained Permissions**: Uses user authorization with scoped permissions  
✅ **Graceful Shutdown**: Handle SIGTERM signals within 15-second requirement  

## Project Structure

```
example-app/
├── app.py               # Dash web application with all functionality
├── requirements.txt     # Additional dependencies (leverages pre-installed libraries)
├── app.yaml             # Databricks App native configuration
└── README.md           # This documentation
```

## Web UI Features

The app provides a **Dash-based web interface** with multiple tabs:

### 📊 **SQL Warehouse Tab**
- Execute parameterized SQL queries
- JSON parameter input with validation
- Results displayed in interactive data tables
- Warehouse ID override support

### 🚀 **Job Submission Tab**
- Submit Databricks jobs by ID
- JSON parameter configuration
- Real-time job submission status
- Run ID tracking

### 🤖 **Model Serving Tab**
- Call model serving endpoints
- JSON input formatting
- Prediction result display
- OAuth2 authentication handling

### 📝 **Logging Test Tab**
- Test logging functionality
- Multiple log levels (Info, Warning, Error)
- Dual logging verification
- Azure Log Analytics integration

### ✅ **Status Dashboard**
- Real-time health monitoring
- Connection status indicators
- App metadata display
- Refresh functionality

## Environment Variables

### Automatically Provided by Databricks Apps
These are provided automatically and don't need configuration:

| Variable | Description | 
|----------|-------------|
| `DATABRICKS_HOST` | Databricks workspace URL |
| `DATABRICKS_CLIENT_ID` | Service principal client ID (for app identity) |
| `DATABRICKS_CLIENT_SECRET` | Service principal secret (for app identity) |
| `DATABRICKS_APP_PORT` | Port to bind to |
| `DATABRICKS_APP_NAME` | Name of the running app |
| `DATABRICKS_WORKSPACE_ID` | Workspace unique ID |

### HTTP Headers (User Authorization)
When user authorization is enabled, this header is automatically provided:

| Header | Description |
|--------|-------------|
| `x-forwarded-access-token` | User's access token for on-behalf-of-user operations |

### Configured via Resources and valueFrom
These are provided through the app configuration:

| Variable | Description | Source |
|----------|-------------|--------|
| `SQL_WAREHOUSE_ID` | Default SQL warehouse ID | valueFrom resource |
| `MODEL_SERVING_ENDPOINT` | Model serving endpoint URL | valueFrom resource |
| `AZURE_LOG_ANALYTICS_WORKSPACE_ID` | Azure Log Analytics workspace ID | valueFrom resource |
| `AZURE_LOG_ANALYTICS_SHARED_KEY` | Azure Log Analytics shared key | valueFrom resource |

## Security Features

### SQL Injection Prevention
- Uses parameterized queries with Databricks SDK
- Validates query templates contain parameter placeholders
- Never concatenates user input directly into SQL

### Input Validation
- Pydantic models validate all request payloads
- Type checking and data validation
- Custom validators for business logic

### Error Handling
- Structured error responses with unique error IDs
- Different HTTP status codes for different error types
- No sensitive information leaked in error messages

## User Authorization

This app uses **user authorization** (on-behalf-of-user authentication) instead of the app's service principal. This means:

### How It Works
**In Databricks Apps Environment:**
- When users access the app, Databricks forwards their access token in the `x-forwarded-access-token` header
- The app extracts this token and uses it to create user-authorized Databricks clients
- All operations execute with the user's permissions and Unity Catalog policies are enforced

**In Local Development:**
- When no user token is available, the app falls back to CLI authentication
- Uses `databricks auth login` configuration for seamless local development
- No environment variables required - just working CLI authentication

### Benefits
✅ **Fine-grained Access Control**: Each user sees only data they're authorized to access  
✅ **Unity Catalog Integration**: Row-level filters and column masks apply automatically  
✅ **Audit Trail**: Operations are logged under the user's identity, not the app's  
✅ **No Permission Escalation**: App cannot access resources the user cannot access  
✅ **Consistent Governance**: Access control aligns with workspace-level governance policies  

### Configured Scopes
The app requests the following scopes in `app.yaml`:
- `sql`: For SQL warehouse queries with user permissions
- `jobs`: For job submission with user permissions  
- `serving`: For model serving endpoint access
- `iam.access-control:read`: Basic user identity information (required)
- `iam.current-user:read`: Current user information (required)

### Status Display
The Status tab shows:
- **App Service Principal**: Whether the app's service principal is available
- **Auth Mode**: Current authentication method (User Authorization, CLI Fallback, etc.)
- **Current User**: Who is currently authenticated
- **User Authorized**: Whether user authorization is working
- Visual indicators with different colors based on auth status

### Migration from Service Principal
This app was migrated from service principal authentication to user authorization with flexible fallback. Key changes:

**Code Changes:**
- `utils.py`: Added `get_user_access_token()` and `get_user_authorized_client()` functions
- All Databricks operations now use user-authorized clients with CLI fallback
- `app.yaml`: Added `user_authorization` configuration with required scopes
- Enhanced status display to show current user and authorization status

**Improved Local Development:**
- ✅ No environment variables required for authentication
- ✅ Uses standard `databricks auth login` CLI configuration
- ✅ Graceful fallback when user tokens aren't available
- ✅ Works offline for UI development and testing
- ✅ Clear status indicators showing current auth mode

## Logging

### Stdout/Stderr Logging
- Structured logging with timestamps and levels
- Separate handlers for stdout and stderr
- JSON-compatible log format

### Azure Log Analytics Integration
- Custom log types for different events:
  - `DatabricksApp_Connection`: Connection events
  - `DatabricksApp_SQLQuery`: SQL query executions
  - `DatabricksApp_JobSubmission`: Job submissions
  - `DatabricksApp_ModelServing`: Model serving calls
  - `DatabricksApp_Health`: Health check events
  - `DatabricksApp_Error`: Error events
  - `DatabricksApp_Startup`: Application startup
  - `DatabricksApp_TestLog`: Test logging events

## Deployment

### Local Development

**Step 1: Install Dependencies**
```bash
pip install -r requirements.txt
```

**Step 2: Configure Authentication**
```bash
# Set up Databricks CLI authentication (one-time setup) 
# This is all you need for authentication - no environment variables required!
databricks auth login
```

**Step 3: Configure Service Settings (Optional)**
Create a `.env` file in the `example-app/` directory for service-specific settings:
```bash
# Service Configuration (optional - can be entered in UI)
SQL_WAREHOUSE_ID=your-sql-warehouse-id
DEFAULT_JOB_ID=12345
MODEL_SERVING_ENDPOINT=your-model-endpoint-name

# Azure Logs (optional)
AZURE_LOG_ANALYTICS_WORKSPACE_ID=your-workspace-id
AZURE_LOG_ANALYTICS_SHARED_KEY=your-shared-key

# App Settings (optional)
DATABRICKS_APP_PORT=8080
LOG_LEVEL=INFO
```

**Step 4: Run the App**
```bash
python app.py
# Opens at http://localhost:8080
```

**Authentication Methods:**
- **With CLI authenticated**: Full functionality using your CLI credentials (fallback mode)
- **In Databricks Apps**: Automatic user authorization with user's permissions
- **Without CLI auth**: App will show connection errors but still demonstrate UI

**First time setup:** Run `databricks auth login` for OAuth-based authentication

### Databricks Apps Deployment

**Step 1: Find Your Configuration Values**
- **SQL Warehouse ID**: Go to SQL Warehouses → click your warehouse → copy ID from URL
- **Job ID**: Go to Workflows → Jobs → click your job → copy ID from URL  
- **Model Endpoint**: Go to Serving → note the endpoint name
- **Azure Logs**: Azure Portal → Log Analytics → Settings → Agents → copy Workspace ID & Primary Key

**Step 2: Create Resources**
```bash
# Create resources that will be referenced by valueFrom
databricks apps create-resource sql_warehouse --value "your-warehouse-id"
databricks apps create-resource default_job --value "12345" 
databricks apps create-resource azure_logs_workspace_id --value "your-workspace-id"
databricks apps create-resource azure_logs_shared_key --value "your-shared-key"
databricks apps create-resource model_serving_endpoint --value "your-endpoint-name"
```

**Step 3: Deploy**
```bash
databricks apps deploy --source-path . --app-name example-app
```

## Example Usage

### Access the Web UI
```bash
# After starting the app
open http://localhost:8080
```

### SQL Query Example
1. Navigate to the **SQL Warehouse** tab
2. Enter query template: `SELECT current_timestamp() as timestamp, :message as message`
3. Enter parameters: `{"message": "Hello from Databricks!"}`
4. Click **Execute Query**

### Job Submission Example
1. Navigate to the **Job Submission** tab
2. Enter Job ID: `123`
3. Enter parameters: `{"env": "production", "date": "2024-01-01"}`
4. Click **Submit Job**

### Model Serving Example
1. Navigate to the **Model Serving** tab
2. Enter endpoint name: `my-model-endpoint`
3. Enter inputs: `{"feature1": 1.5, "feature2": "category_a"}`
4. Click **Call Model**

## Dependencies

### Pre-installed Libraries (Per [Databricks Apps System Environment](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/system-env))
These are automatically available:
- `databricks-sdk==0.33.0`: Databricks SDK for Python
- `dash==2.18.1`: Web application framework (used for UI!)
- `mlflow-skinny==2.16.2`: MLflow integration
- `streamlit==1.38.0`, `gradio==4.44.0`: Alternative UI frameworks

### Additional Dependencies
Only these need to be specified in `requirements.txt`:
- `dash-bootstrap-components==1.5.0`: Bootstrap components for Dash
- `pandas==2.1.4`: Data manipulation for interactive tables
- `pydantic==2.5.2`: Data validation
- `azure-monitor-opentelemetry==1.2.0`: Azure logging integration
- `requests==2.31.0`: HTTP client
- Additional utilities for configuration and logging

## Error Handling Examples

The app demonstrates comprehensive error handling:
- **400 Bad Request**: Invalid input validation
- **500 Internal Server Error**: Unexpected application errors
- **502 Bad Gateway**: External service errors (Databricks API, etc.)

Each error includes:
- Unique error ID for tracking
- Timestamp
- Error context
- Structured error message
- Logging to both local and Azure logs