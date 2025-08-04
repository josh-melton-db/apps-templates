#!/usr/bin/env python3
"""
Utility functions for Databricks Example App:
- Logging and alerting to Azure Log Analytics
- Error handling
- Databricks client management
- SQL warehouse queries
- Job submission
- Model serving API calls
"""

import os
import sys
import logging
import json
import traceback
import signal
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError, field_validator
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.service.sql import StatementParameterListItem
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
import requests
import pandas as pd
from flask import request

# Azure logging imports
try:
    from azure.core.credentials import AccessToken
    from azure.identity import DefaultAzureCredential
    import hashlib
    import hmac
    import base64
    AZURE_LOGGING_AVAILABLE = True
except ImportError:
    AZURE_LOGGING_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

# Global variables for clients
databricks_client: WorkspaceClient
azure_log_workspace_id: Optional[str] = None
azure_log_shared_key: Optional[str] = None


# Pydantic Models for Validation
class SQLQueryRequest(BaseModel):
    """Pydantic model for SQL query validation"""
    query_template: str
    parameters: Dict[str, Any] = {}
    warehouse_id: Optional[str] = None
    
    @field_validator('query_template')
    @classmethod
    def validate_query_template(cls, v):
        if not v or not v.strip():
            raise ValueError('Query template cannot be empty')
        # Basic SQL injection prevention - ensure it's a parameterized query
        if '${' not in v and '{{' not in v and ':' not in v:
            logger.warning("Query template should use parameters to prevent SQL injection")
        return v.strip()


class JobSubmissionRequest(BaseModel):
    """Pydantic model for job submission validation"""
    job_id: int
    parameters: Dict[str, str] = {}
    
    @field_validator('job_id')
    @classmethod
    def validate_job_id(cls, v):
        if v <= 0:
            raise ValueError('Job ID must be positive')
        return v


class ModelServingRequest(BaseModel):
    """Pydantic model for model serving validation"""
    endpoint_name: str
    inputs: Dict[str, Any]
    
    @field_validator('endpoint_name')
    @classmethod
    def validate_endpoint_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Endpoint name cannot be empty')
        return v.strip()


# Azure Logging Functions
def setup_azure_logging():
    """Setup Azure Log Analytics logging"""
    global azure_log_workspace_id, azure_log_shared_key
    
    azure_log_workspace_id = os.getenv('AZURE_LOG_ANALYTICS_WORKSPACE_ID')
    azure_log_shared_key = os.getenv('AZURE_LOG_ANALYTICS_SHARED_KEY')
    
    if azure_log_workspace_id and azure_log_shared_key and AZURE_LOGGING_AVAILABLE:
        logger.info("Azure Log Analytics configured for REST API logging")
    else:
        logger.warning("Azure Log Analytics not configured - missing credentials")


def send_to_azure_logs(log_type: str, data: Dict[str, Any]):
    """Send custom logs to Azure Log Analytics"""
    if not azure_log_workspace_id or not azure_log_shared_key:
        return
    
    try:
        # Build the signature for Azure Log Analytics REST API
        method = 'POST'
        content_type = 'application/json'
        resource = '/api/logs'
        rfc1123date = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        json_data = json.dumps(data)
        content_length = len(json_data)
        
        string_to_hash = f"{method}\n{content_length}\n{content_type}\nx-ms-date:{rfc1123date}\n{resource}"
        bytes_to_hash = bytes(string_to_hash, encoding='utf-8')
        decoded_key = base64.b64decode(azure_log_shared_key)
        encoded_hash = base64.b64encode(hmac.new(decoded_key, bytes_to_hash, digestmod=hashlib.sha256).digest()).decode()
        authorization = f"SharedKey {azure_log_workspace_id}:{encoded_hash}"
        
        uri = f"https://{azure_log_workspace_id}.ods.opinsights.azure.com{resource}?api-version=2016-04-01"
        
        headers = {
            'Content-Type': content_type,
            'Authorization': authorization,
            'Log-Type': log_type,
            'x-ms-date': rfc1123date
        }
        
        response = requests.post(uri, data=json_data, headers=headers, timeout=30)
        response.raise_for_status()
        logger.info(f"Successfully sent logs to Azure Log Analytics: {log_type}")
        
    except Exception as e:
        logger.error(f"Failed to send logs to Azure Log Analytics: {e}")


# Error Handling
def handle_error(error: Exception, context: str = "unknown") -> str:
    """Centralized error handling"""
    error_id = datetime.now(timezone.utc).isoformat()
    error_details = {
        "error_id": error_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": context,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc()
    }
    
    # Log to stdout/stderr
    logger.error(f"Error in {context}: {error}", exc_info=True)
    
    # Log to Azure
    send_to_azure_logs("DatabricksApp_Error", error_details)
    
    return f"Error ({error_id}): {str(error)}"


# Databricks Client Management
def setup_databricks_client():
    """Initialize Databricks workspace client - used for app identity operations only"""
    global databricks_client
    
    try:
        # Initialize client for app identity operations (logging, etc.)
        # This is separate from user authorization which is handled per-request
        databricks_client = WorkspaceClient()
        
        # Test the connection (but don't fail startup if this doesn't work)
        current_user = databricks_client.current_user.me()
        logger.info(f"App service principal connected to Databricks as: {current_user.user_name}")
        
        # Log to Azure
        send_to_azure_logs("DatabricksApp_Connection", {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "app_service_principal_connected",
            "user": current_user.user_name,
            "workspace_url": os.getenv('DATABRICKS_HOST', 'cli-configured'),
            "workspace_id": os.getenv('DATABRICKS_WORKSPACE_ID', 'unknown'),
            "app_name": os.getenv('DATABRICKS_APP_NAME', 'local-dev')
        })
        
    except Exception as e:
        logger.warning(f"Could not establish app service principal connection: {e}")
        logger.info("App will use per-request user authorization instead")
        logger.info("For local development: run 'databricks auth login' if you need CLI authentication")
        
        # Set to None - we'll rely on per-request user authorization
        databricks_client = None
        
        send_to_azure_logs("DatabricksApp_Warning", {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "app_service_principal_unavailable",
            "error": str(e),
            "mode": "user_authorization_only"
        })


def get_databricks_client() -> Optional[WorkspaceClient]:
    """Get the current Databricks client (may be None if service principal not available)"""
    return databricks_client


def get_user_access_token() -> Optional[str]:
    """Extract user access token from request headers for user authorization"""
    try:
        # Check if we're in a Flask request context
        if not hasattr(request, 'headers'):
            # Not in request context (e.g., during startup or non-web operations)
            return None
            
        # Get the user's access token from the forwarded header
        user_token = request.headers.get('x-forwarded-access-token')
        if not user_token:
            # This is normal for local development - no warning needed
            return None
        
        logger.info("Successfully retrieved user access token from request headers")
        return user_token
        
    except RuntimeError as e:
        # Flask request context not available (normal during startup/testing)
        if "outside of request context" in str(e).lower():
            return None
        else:
            logger.error(f"Failed to retrieve user access token: {e}")
            return None
    except Exception as e:
        logger.error(f"Failed to retrieve user access token: {e}")
        return None


def get_user_authorized_client() -> Optional[WorkspaceClient]:
    """Create a Databricks client using user authorization for deployed apps"""
    try:
        user_token = get_user_access_token()
        
        # Check if we're in a Databricks Apps environment
        is_databricks_app = os.getenv('DATABRICKS_APP_NAME') is not None
        
        if user_token and is_databricks_app:
            # In Databricks Apps environment - use user token for on-behalf-of-user auth
            logger.info("Using user authorization token from x-forwarded-access-token header")
            
            # Get host from environment
            host = os.getenv('DATABRICKS_HOST')
            if not host:
                logger.error("DATABRICKS_HOST environment variable not found")
                return None
            
            # Temporarily clear service principal environment variables to avoid conflicts
            # Save original values to restore later
            original_client_id = os.environ.get('DATABRICKS_CLIENT_ID')
            original_client_secret = os.environ.get('DATABRICKS_CLIENT_SECRET')
            
            try:
                # Remove service principal credentials temporarily
                if 'DATABRICKS_CLIENT_ID' in os.environ:
                    del os.environ['DATABRICKS_CLIENT_ID']
                if 'DATABRICKS_CLIENT_SECRET' in os.environ:
                    del os.environ['DATABRICKS_CLIENT_SECRET']
                
                # Create client with only user token and host
                user_client = WorkspaceClient(
                    host=host,
                    token=user_token
                )
                
                logger.info("Successfully created user-authorized Databricks client")
                return user_client
                
            finally:
                # Restore original environment variables
                if original_client_id:
                    os.environ['DATABRICKS_CLIENT_ID'] = original_client_id
                if original_client_secret:
                    os.environ['DATABRICKS_CLIENT_SECRET'] = original_client_secret
            
        elif not is_databricks_app:
            # Local development - fall back to CLI authentication
            logger.info("Local development detected, falling back to CLI authentication")
            
            # Clear app-specific environment variables that might interfere with CLI auth
            original_host = os.environ.get('DATABRICKS_HOST')
            original_client_id = os.environ.get('DATABRICKS_CLIENT_ID')
            original_client_secret = os.environ.get('DATABRICKS_CLIENT_SECRET')
            
            try:
                # Temporarily remove these to force CLI auth
                if 'DATABRICKS_HOST' in os.environ:
                    del os.environ['DATABRICKS_HOST']
                if 'DATABRICKS_CLIENT_ID' in os.environ:
                    del os.environ['DATABRICKS_CLIENT_ID']
                if 'DATABRICKS_CLIENT_SECRET' in os.environ:
                    del os.environ['DATABRICKS_CLIENT_SECRET']
                
                cli_client = WorkspaceClient()
                logger.info("Successfully created CLI-authenticated Databricks client")
                return cli_client
                
            finally:
                # Restore original environment variables
                if original_host:
                    os.environ['DATABRICKS_HOST'] = original_host
                if original_client_id:
                    os.environ['DATABRICKS_CLIENT_ID'] = original_client_id
                if original_client_secret:
                    os.environ['DATABRICKS_CLIENT_SECRET'] = original_client_secret
        else:
            # Databricks Apps environment but no user token - this indicates a configuration issue
            logger.error("Running in Databricks Apps environment but no user access token found")
            logger.error("Ensure user authorization is enabled for this app and the user has granted consent")
            return None
        
    except Exception as e:
        logger.error(f"Failed to create Databricks client: {e}")
        return None


# Signal Handling
def setup_signal_handlers():
    """Setup graceful shutdown handling for Databricks Apps"""
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        send_to_azure_logs("DatabricksApp_Shutdown", {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "app_shutdown_requested",
            "signal": signum
        })
        # Databricks Apps requirement: shutdown within 15 seconds
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


# SQL Query Functions
def execute_sql_query(query_template: str, parameters_json: str, warehouse_id: Optional[str] = None) -> Dict[str, Any]:
    """Execute a SQL query against Databricks SQL warehouse using user authorization"""
    try:
        # Parse parameters
        parameters = json.loads(parameters_json) if parameters_json else {}
        
        # Validate input
        query_request = SQLQueryRequest(
            query_template=query_template,
            parameters=parameters,
            warehouse_id=warehouse_id if warehouse_id else None
        )
        
        # Get warehouse ID from request or environment
        warehouse_id = query_request.warehouse_id or os.getenv('SQL_WAREHOUSE_ID')
        if not warehouse_id:
            raise ValueError("SQL warehouse ID is required")
        
        # Get user-authorized client
        user_client = get_user_authorized_client()
        if not user_client:
            if os.getenv('DATABRICKS_APP_NAME'):
                raise ValueError("Unable to authenticate with Databricks. Ensure user authorization is enabled for this app and the user has granted consent.")
            else:
                raise ValueError("Unable to authenticate with Databricks. Please run 'databricks auth login' for local development.")
        
        # Prepare parameterized query
        query_parameters = []
        for key, value in query_request.parameters.items():
            query_parameters.append(
                StatementParameterListItem(name=key, value=str(value))
            )
        
        logger.info(f"Executing SQL query with user authorization and {len(query_parameters)} parameters")
        
        # Execute query using user-authorized client
        result = user_client.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=query_request.query_template,
            parameters=query_parameters
        )
        
        # Log to Azure
        send_to_azure_logs("DatabricksApp_SQLQuery", {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "sql_query_executed",
            "warehouse_id": warehouse_id,
            "statement_id": result.statement_id,
            "parameter_count": len(query_parameters),
            "row_count": len(result.result.data_array) if result.result and result.result.data_array else 0
        })
        
        # Format results
        if result.result and result.result.data_array:
            # Convert to DataFrame for better display
            df = pd.DataFrame(result.result.data_array)
            return {
                "success": True,
                "statement_id": result.statement_id,
                "data": df.to_dict('records'),
                "columns": [{"name": str(i), "id": str(i)} for i in df.columns],
                "row_count": len(result.result.data_array)
            }
        else:
            return {
                "success": True,
                "statement_id": result.statement_id,
                "data": [],
                "columns": [],
                "row_count": 0
            }
            
    except Exception as e:
        error_msg = handle_error(e, "execute_sql_query")
        return {
            "success": False,
            "error": error_msg
        }


# Job Submission Functions
def submit_databricks_job(job_id: int, parameters_json: str) -> Dict[str, Any]:
    """Submit a Databricks job with parameters using app service principal or CLI authentication"""
    try:
        # Parse parameters
        parameters = json.loads(parameters_json) if parameters_json else {}
        
        # Validate input
        job_request = JobSubmissionRequest(job_id=job_id, parameters=parameters)
        
        # Use app service principal client (for deployed apps) or CLI client (for local dev)
        # Job submission typically requires elevated privileges that may not be available 
        # in user authorization scopes
        client = get_databricks_client()
        
        if not client:
            # Fallback to CLI authentication for local development
            if not os.getenv('DATABRICKS_APP_NAME'):
                logger.info("Using CLI authentication for job submission (local development)")
                try:
                    client = WorkspaceClient()
                except Exception as cli_error:
                    raise ValueError("Unable to authenticate with Databricks. Please run 'databricks auth login' for local development.")
            else:
                raise ValueError("App service principal not available for job submission. Check app configuration.")
        
        auth_method = "app_service_principal" if os.getenv('DATABRICKS_APP_NAME') else "cli_authentication"
        logger.info(f"Submitting job {job_request.job_id} with {auth_method} and parameters: {job_request.parameters}")
        
        # Submit job using service principal or CLI client
        run_response = client.jobs.run_now(
            job_id=job_request.job_id,
            job_parameters=job_request.parameters
        )
        
        # Log to Azure
        send_to_azure_logs("DatabricksApp_JobSubmission", {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "job_submitted",
            "job_id": job_request.job_id,
            "run_id": run_response.run_id,
            "parameter_count": len(job_request.parameters),
            "auth_method": auth_method
        })
        
        return {
            "success": True,
            "job_id": job_request.job_id,
            "run_id": run_response.run_id,
            "parameters": job_request.parameters,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "auth_method": auth_method
        }
        
    except Exception as e:
        error_msg = handle_error(e, "submit_job")
        return {
            "success": False,
            "error": error_msg
        }


# Model Serving Functions
def call_model_serving_endpoint(endpoint_name: str, inputs_json: str) -> Dict[str, Any]:
    """Call a Databricks model serving endpoint using user authorization"""
    try:
        # Parse inputs
        inputs = json.loads(inputs_json) if inputs_json else {}
        
        # Get user-authorized client
        user_client = get_user_authorized_client()
        if not user_client:
            if os.getenv('DATABRICKS_APP_NAME'):
                raise ValueError("Unable to authenticate with Databricks. Ensure user authorization is enabled for this app and the user has granted consent.")
            else:
                raise ValueError("Unable to authenticate with Databricks. Please run 'databricks auth login' for local development.")
        
        logger.info(f"Calling model serving endpoint with user authorization: {endpoint_name}")
        
        # Create messages from inputs or use default
        messages = []
        
        if inputs.get("messages"):
            # If messages are provided directly in inputs
            for msg in inputs["messages"]:
                messages.append(ChatMessage(
                    role=ChatMessageRole.USER if msg.get("role", "user") == "user" else ChatMessageRole.SYSTEM,
                    content=msg.get("content", "")
                ))
        elif inputs.get("prompt") or inputs.get("content"):
            # If a single prompt/content is provided
            content = inputs.get("prompt") or inputs.get("content", "")
            messages = [
                ChatMessage(
                    role=ChatMessageRole.USER,
                    content=content
                )
            ]
        else:
            # Default fallback
            messages = [
                ChatMessage(
                    role=ChatMessageRole.USER,
                    content="Hello, can you help me?"
                )
            ]
        
        # Call endpoint using user-authorized client
        response = user_client.serving_endpoints.query(
            name=endpoint_name,
            messages=messages
        )
        
        # Convert the response to a dictionary for consistent handling
        result = response.as_dict()
        
        # Log to Azure
        send_to_azure_logs("DatabricksApp_ModelServing", {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "model_serving_called",
            "endpoint_name": endpoint_name,
            "input_keys": list(inputs.keys()),
            "response_received": True
        })
        
        return {
            "success": True,
            "endpoint_name": endpoint_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result": result
        }
        
    except Exception as e:
        error_msg = handle_error(e, "call_model_serving")
        return {
            "success": False,
            "error": error_msg
        }


# Health Check Functions
def get_app_status() -> Dict[str, Any]:
    """Get current application status"""
    try:
        # Check if service principal client is available
        service_principal_available = databricks_client is not None
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "app_service_principal": "available" if service_principal_available else "not available",
            "azure_logging_configured": azure_log_workspace_id is not None,
            "app_name": os.getenv('DATABRICKS_APP_NAME', 'local-dev'),
            "workspace_id": os.getenv('DATABRICKS_WORKSPACE_ID', 'unknown'),
            "user_authorization": "enabled"
        }
        
        # Try to get current user info using user authorization or CLI fallback
        try:
            user_client = get_user_authorized_client()
            if user_client:
                current_user = user_client.current_user.me()
                user_token = get_user_access_token()
                
                if user_token:
                    health_status["auth_mode"] = "user_authorization"
                    health_status["current_user"] = current_user.user_name
                    health_status["user_authorized"] = True
                else:
                    health_status["auth_mode"] = "cli_fallback"
                    health_status["current_user"] = current_user.user_name
                    health_status["user_authorized"] = True
                    health_status["note"] = "Using CLI authentication for local development"
            else:
                health_status["auth_mode"] = "none"
                health_status["current_user"] = "authentication failed"
                health_status["user_authorized"] = False
        except Exception as user_error:
            health_status["auth_mode"] = "error"
            health_status["current_user"] = f"error: {str(user_error)}"
            health_status["user_authorized"] = False
        
        send_to_azure_logs("DatabricksApp_Health", health_status)
        return health_status
        
    except Exception as e:
        error_msg = handle_error(e, "status_check")
        return {
            "status": "unhealthy",
            "error": error_msg,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Logging Test Functions
def send_test_log(message: str, level: str = "info") -> Dict[str, Any]:
    """Send a test log message"""
    try:
        message = message or "Test log message"
        level = level or "info"
        
        # Log to stdout/stderr based on level
        if level == 'error':
            logger.error(f"Test error log: {message}")
        elif level == 'warning':
            logger.warning(f"Test warning log: {message}")
        else:
            logger.info(f"Test info log: {message}")
        
        # Log to Azure
        send_to_azure_logs("DatabricksApp_TestLog", {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "test_log_generated",
            "level": level,
            "message": message,
            "endpoint": "dash_ui"
        })
        
        return {
            "success": True,
            "level": level,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        error_msg = handle_error(e, "test_logging")
        return {
            "success": False,
            "error": error_msg
        }


# Initialization Functions
def initialize_utils():
    """Initialize all utility components"""
    setup_signal_handlers()
    setup_azure_logging()
    setup_databricks_client()