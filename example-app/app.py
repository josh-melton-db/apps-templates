#!/usr/bin/env python3
"""
Databricks Example App demonstrating various techniques using Dash UI:
- SQL warehouse queries with parameterization
- Job submission
- Model serving API calls
- Input validation
- Error handling
- Secrets management
- Logging to stdout/stderr and Azure Log Analytics
"""

import os
import sys
import logging
import json
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
from dotenv import load_dotenv

# Import utility functions
from src.utils import (
    initialize_utils,
    execute_sql_query,
    submit_databricks_job,
    call_model_serving_endpoint,
    get_app_status,
    send_test_log,
    handle_error
)

# Load environment variables from .env file (for local development)
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)








# Initialize Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Databricks App Template"

# Suppress callback exceptions for dynamically generated components
app.config.suppress_callback_exceptions = True

# App layout
app.layout = dbc.Container([
    dbc.NavbarSimple(
        brand="Databricks Example App",
        brand_href="#",
        color="primary",
        dark=True,
        className="mb-4"
    ),
    
    dcc.Store(id='app-status-store'),
    
    dbc.Card([
        dbc.CardHeader([
            dbc.Tabs([
                dbc.Tab(label="Status", tab_id="status-tab"),
                dbc.Tab(label="SQL Warehouse", tab_id="sql-tab"),
                dbc.Tab(label="Job Submission", tab_id="job-tab"),
                dbc.Tab(label="Model Serving", tab_id="model-tab"),
                dbc.Tab(label="Logging Test", tab_id="logging-tab"),
            ], id="tabs", active_tab="status-tab")
        ]),
        dbc.CardBody([
            html.Div(id="tab-content")
        ])
    ])
], fluid=True)


# Tab content callbacks
@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab")
)
def render_tab_content(active_tab):
    if active_tab == "status-tab":
        return dbc.Card([
            dbc.CardHeader("App Status"),
            dbc.CardBody([
                dcc.Loading(
                    id="status-loading",
                    type="default",
                    children=html.Div(id="status-display")
                ),
                dbc.Button("Refresh Status", id="refresh-status-btn", color="info", size="sm", className="mt-2")
            ])
        ])
    
    elif active_tab == "sql-tab":
        return dbc.Card([
            dbc.CardHeader("SQL Warehouse Query"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Query Template (use :param_name for parameters)"),
                        dbc.Textarea(
                            id="sql-query-input",
                            placeholder="SELECT * FROM main.default.03_route_optimization WHERE cluster_id = :cluster_id",
                            value="SELECT * FROM main.default.03_route_optimization WHERE cluster_id = :cluster_id",
                            rows=3
                        )
                    ], width=12)
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Cluster ID"),
                        dbc.Input(id="sql-cluster-id", placeholder="1", value="1")
                    ], width=6),
                    dbc.Col([
                        dbc.Label("Warehouse ID (optional)"),
                        dbc.Input(id="warehouse-id-input", placeholder="Leave empty to use default")
                    ], width=6)
                ], className="mt-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Execute Query", id="execute-sql-btn", color="primary", className="mt-3")
                    ])
                ]),
                html.Hr(),
                dcc.Loading(
                    id="sql-loading",
                    type="default",
                    children=html.Div(id="sql-results")
                )
            ])
        ])
    
    elif active_tab == "job-tab":
        return dbc.Card([
            dbc.CardHeader("Job Submission"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Job ID"),
                        dbc.Input(
                            id="job-id-input", 
                            type="number", 
                            placeholder="36617962351231", 
                            value=os.getenv('DEFAULT_JOB_ID', '36617962351231')
                        )
                    ], width=12)
                ]),

                dbc.Row([
                    dbc.Col([
                        dbc.Button("Submit Job", id="submit-job-btn", color="success", className="mt-3")
                    ])
                ]),
                html.Hr(),
                dcc.Loading(
                    id="job-loading",
                    type="default",
                    children=html.Div(id="job-results")
                )
            ])
        ])
    
    elif active_tab == "model-tab":
        return dbc.Card([
            dbc.CardHeader("Model Serving"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Endpoint Name"),
                        dbc.Input(id="model-endpoint-input", placeholder="databricks-gemma-3-12b", value="databricks-gemma-3-12b")
                    ], width=12)
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Model Configuration"),
                        html.Div([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Prompt/Message", size="sm"),
                                    dbc.Textarea(
                                        id="model-prompt",
                                        placeholder="What is machine learning?",
                                        value="What is machine learning?",
                                        rows=3,
                                        className="mb-2"
                                    )
                                ], width=12)
                            ]),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Max Tokens", size="sm"),
                                    dbc.Input(id="model-max-tokens", placeholder="100", value="100", type="number", size="sm")
                                ], width=4),
                                dbc.Col([
                                    dbc.Label("Temperature", size="sm"),
                                    dbc.Input(id="model-temperature", placeholder="0.7", value="0.7", type="number", step="0.1", min="0", max="2", size="sm")
                                ], width=4),
                                dbc.Col([
                                    dbc.Label("Top P", size="sm"),
                                    dbc.Input(id="model-top-p", placeholder="1.0", type="number", step="0.1", min="0", max="1", size="sm")
                                ], width=4)
                            ], className="mb-2"),

                        ])
                    ], width=12)
                ], className="mt-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Call Model", id="call-model-btn", color="warning", className="mt-3")
                    ])
                ]),
                html.Hr(),
                dcc.Loading(
                    id="model-loading",
                    type="default",
                    children=html.Div(id="model-results")
                )
            ])
        ])
    
    elif active_tab == "logging-tab":
        return dbc.Card([
            dbc.CardHeader("Logging Test"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Log Message"),
                        dbc.Input(id="log-message-input", placeholder="Test log message", value="Test log message")
                    ], width=8),
                    dbc.Col([
                        dbc.Label("Log Level"),
                        dcc.Dropdown(
                            id="log-level-input",
                            options=[
                                {"label": "Info", "value": "info"},
                                {"label": "Warning", "value": "warning"},
                                {"label": "Error", "value": "error"}
                            ],
                            value="info"
                        )
                    ], width=4)
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Send Log", id="send-log-btn", color="info", className="mt-3")
                    ])
                ]),
                html.Hr(),
                dcc.Loading(
                    id="log-loading",
                    type="default",
                    children=html.Div(id="log-results")
                )
            ])
        ])
    
    # Default return for unknown tabs
    return html.Div("Select a tab to view content")


# Status callback
@app.callback(
    Output("status-display", "children"),
    Input("refresh-status-btn", "n_clicks")
)
def update_status(n_clicks):
    health_status = get_app_status()
    
    if health_status.get("status") == "healthy":
        # Determine alert color based on auth status
        auth_mode = health_status.get('auth_mode', 'unknown')
        if auth_mode == 'user_authorization':
            alert_color = "success"
        elif auth_mode == 'cli_fallback':
            alert_color = "info"
        else:
            alert_color = "warning"
            
        status_items = [
            html.H6("✅ App Status: Healthy", className="mb-2"),
            html.P(f"🔗 App Service Principal: {health_status.get('app_service_principal', 'unknown')}", className="mb-1"),
            html.P(f"📊 Azure Logging: {'Configured' if health_status['azure_logging_configured'] else 'Not configured'}", className="mb-1"),
            html.P(f"🔐 Auth Mode: {auth_mode.replace('_', ' ').title()}", className="mb-1"),
            html.P(f"👤 Current User: {health_status.get('current_user', 'unknown')}", className="mb-1"),
            html.P(f"✅ User Authorized: {'Yes' if health_status.get('user_authorized', False) else 'No'}", className="mb-1"),
            html.P(f"📱 App Name: {health_status['app_name']}", className="mb-1"),
            html.P(f"🏢 Workspace ID: {health_status['workspace_id']}", className="mb-1"),
        ]
        
        # Add note if present
        if health_status.get('note'):
            status_items.append(html.P(f"ℹ️ Note: {health_status['note']}", className="mb-1"))
            
        status_items.append(html.Small(f"Last updated: {health_status['timestamp']}"))
        
        return dbc.Alert(status_items, color=alert_color)
    else:
        return dbc.Alert(f"❌ {health_status.get('error', 'Unknown error')}", color="danger")


# SQL Query callback
@app.callback(
    Output("sql-results", "children"),
    Input("execute-sql-btn", "n_clicks"),
    State("sql-query-input", "value"),
    State("sql-cluster-id", "value"),
    State("warehouse-id-input", "value")
)
def execute_sql_query_callback(n_clicks, query_template, cluster_id, warehouse_id):
    if not n_clicks:
        return ""
    
    # Build parameters dictionary from form inputs
    parameters = {}
    if cluster_id:
        parameters["cluster_id"] = cluster_id
    
    # Convert parameters to JSON string for the existing execute_sql_query function
    parameters_json = json.dumps(parameters) if parameters else "{}"
    
    result = execute_sql_query(query_template, parameters_json, warehouse_id)
    
    if result["success"]:
        if result["data"]:
            return [
                dbc.Alert(f"✅ Query executed successfully! Statement ID: {result['statement_id']}", color="success"),
                html.H6(f"Results ({result['row_count']} rows):"),
                dash_table.DataTable(
                    data=result["data"],
                    columns=result["columns"],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '10px'},
                    style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
                )
            ]
        else:
            return dbc.Alert(f"✅ Query executed successfully! Statement ID: {result['statement_id']} (No results returned)", color="info")
    else:
        return dbc.Alert(f"❌ {result['error']}", color="danger")


# Job submission callback
@app.callback(
    Output("job-results", "children"),
    Input("submit-job-btn", "n_clicks"),
    State("job-id-input", "value")
)
def submit_job_callback(n_clicks, job_id):
    if not n_clicks:
        return ""
    
    # No parameters - just submit the job with empty parameters
    parameters_json = "{}"
    
    result = submit_databricks_job(job_id, parameters_json)
    
    if result["success"]:
        return dbc.Alert([
            html.H6(f"✅ Job submitted successfully!"),
            html.P(f"Job ID: {result['job_id']}"),
            html.P(f"Run ID: {result['run_id']}"),
            html.P(f"Parameters: {result['parameters']}"),
            html.P(f"Auth Method: {result.get('auth_method', 'unknown')}"),
            html.P(f"Submitted at: {result['timestamp']}")
        ], color="success")
    else:
        return dbc.Alert(f"❌ {result['error']}", color="danger")


# Model serving callback
@app.callback(
    Output("model-results", "children"),
    Input("call-model-btn", "n_clicks"),
    State("model-endpoint-input", "value"),
    State("model-prompt", "value"),
    State("model-max-tokens", "value"),
    State("model-temperature", "value"),
    State("model-top-p", "value")
)
def call_model_serving_callback(n_clicks, endpoint_name, prompt, max_tokens, temperature, top_p):
    if not n_clicks:
        return ""
    
    # Build inputs dictionary from form inputs
    inputs = {}
    
    # Build messages array - always use "user" role
    if prompt:
        inputs["messages"] = [{"role": "user", "content": prompt}]
    else:
        inputs["messages"] = [{"role": "user", "content": "Hello, can you help me?"}]
    
    # Add generation parameters
    if max_tokens:
        inputs["max_tokens"] = int(max_tokens)
    if temperature:
        inputs["temperature"] = float(temperature)
    if top_p:
        inputs["top_p"] = float(top_p)
    
    # Convert inputs to JSON string for the existing call_model_serving_endpoint function
    inputs_json = json.dumps(inputs)
    
    result = call_model_serving_endpoint(endpoint_name, inputs_json)
    
    if result["success"]:
        return dbc.Alert([
            html.H6(f"✅ Model serving call successful!"),
            html.P(f"Endpoint: {result['endpoint_name']}"),
            html.P(f"Timestamp: {result['timestamp']}"),
            html.Hr(),
            html.H6("Response:"),
            html.Pre(json.dumps(result["result"], indent=2))
        ], color="success")
    else:
        return dbc.Alert(f"❌ {result['error']}", color="danger")


# Logging test callback
@app.callback(
    Output("log-results", "children"),
    Input("send-log-btn", "n_clicks"),
    State("log-message-input", "value"),
    State("log-level-input", "value")
)
def test_logging_callback(n_clicks, message, level):
    if not n_clicks:
        return ""
    
    result = send_test_log(message, level)
    
    if result["success"]:
        return dbc.Alert([
            html.H6("✅ Log sent successfully!"),
            html.P(f"Level: {result['level'].upper()}"),
            html.P(f"Message: {result['message']}"),
            html.P(f"Timestamp: {result['timestamp']}")
        ], color="success")
    else:
        return dbc.Alert(f"❌ {result['error']}", color="danger")


def main():
    """Main application entry point for Databricks Apps"""
    try:
        # Initialize all utility components
        initialize_utils()
        
        # Get port from environment variable (automatically provided by Databricks Apps)
        port = int(os.getenv('DATABRICKS_APP_PORT', 8080))
        
        logger.info(f"Starting Databricks Apps Example with Dash UI on port {port}")
        logger.info(f"App Name: {os.getenv('DATABRICKS_APP_NAME', 'unknown')}")
        logger.info(f"Workspace ID: {os.getenv('DATABRICKS_WORKSPACE_ID', 'unknown')}")
        
        # Run the Dash app - must bind to 0.0.0.0 per Databricks Apps requirements
        app.run(
            host='0.0.0.0',
            port=port,
            debug=True
        )
        
    except Exception as e:
        error_msg = handle_error(e, "app_startup")
        logger.error(f"Failed to start application: {error_msg}")
        sys.exit(1)


if __name__ == '__main__':
    main()
    