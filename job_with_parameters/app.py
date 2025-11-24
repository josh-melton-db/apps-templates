import os
import json
from dash import Dash, html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
from databricks.sdk import WorkspaceClient

# Initialize Databricks client
w = WorkspaceClient()

# Get job ID from environment variable (configured in app.yaml)
JOB_ID = os.getenv('DATABRICKS_JOB_ID', '921773893211960')

# Initialize Dash app with Bootstrap theme
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# App layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Databricks Job Runner", className="text-center mb-4 mt-4"),
            html.Hr(),
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Job Configuration", className="card-title"),
                    html.P(f"Job ID: {JOB_ID}", className="text-muted mb-3"),
                    
                    html.Label("Job Parameters (JSON format):", className="fw-bold"),
                    dcc.Textarea(
                        id='job-params-input',
                        value='{\n  "param1": "value1",\n  "param2": "value2"\n}',
                        style={'width': '100%', 'height': 150, 'fontFamily': 'monospace'},
                        className="mb-3"
                    ),
                    
                    dbc.Button(
                        "Submit Job",
                        id="submit-button",
                        color="primary",
                        size="lg",
                        className="w-100 mb-2"
                    ),
                    
                    dbc.Button(
                        "Get Results",
                        id="get-results-button",
                        color="success",
                        size="lg",
                        className="w-100",
                        disabled=True
                    ),
                ])
            ], className="mb-4")
        ], width=12, lg=6),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Output", className="card-title"),
                    dcc.Loading(
                        id="loading",
                        type="default",
                        children=html.Div(id='output-display', style={'whiteSpace': 'pre-wrap', 'fontFamily': 'monospace'})
                    )
                ])
            ], className="mb-4")
        ], width=12, lg=6)
    ]),
    
    # Hidden div to store run_id
    dcc.Store(id='run-id-store')
    
], fluid=True)


@callback(
    [Output('output-display', 'children'),
     Output('run-id-store', 'data'),
     Output('get-results-button', 'disabled')],
    Input('submit-button', 'n_clicks'),
    State('job-params-input', 'value'),
    prevent_initial_call=True
)
def submit_job(n_clicks, params_json):
    """Submit a Databricks job with parameters"""
    try:
        # Parse parameters
        parameters = json.loads(params_json)
        
        # Submit the job
        run = w.jobs.run_now(job_id=JOB_ID, job_parameters=parameters)
        
        output = f"✅ Job submitted successfully!\n\n"
        output += f"Run ID: {run.run_id}\n"
        output += f"Job ID: {JOB_ID}\n"
        output += f"Parameters: {json.dumps(parameters, indent=2)}\n\n"
        output += f"Click 'Get Results' to fetch the output once the job completes."
        
        return output, run.run_id, False
        
    except json.JSONDecodeError as e:
        return f"❌ Invalid JSON format:\n{str(e)}", None, True
    except Exception as e:
        return f"❌ Error submitting job:\n{str(e)}", None, True


@callback(
    Output('output-display', 'children', allow_duplicate=True),
    Input('get-results-button', 'n_clicks'),
    State('run-id-store', 'data'),
    prevent_initial_call=True
)
def get_results(n_clicks, run_id):
    """Get the results of a Databricks job run"""
    if not run_id:
        return "❌ No run ID available. Please submit a job first."
    
    try:
        # Get run output
        results = w.jobs.get_run_output(run_id)
        
        output = f"📊 Job Results\n\n"
        output += f"Run ID: {run_id}\n"
        output += f"Status: {results.metadata.state.life_cycle_state if results.metadata else 'Unknown'}\n\n"
        
        if results.notebook_output:
            output += f"Notebook Output:\n{results.notebook_output.result}\n"
        elif results.sql_output:
            output += f"SQL Output:\n{results.sql_output}\n"
        elif results.dbt_output:
            output += f"DBT Output:\n{results.dbt_output}\n"
        elif results.logs:
            output += f"Logs:\n{results.logs}\n"
        else:
            output += "No output available yet. The job may still be running."
        
        return output
        
    except Exception as e:
        return f"❌ Error fetching results:\n{str(e)}"


if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0', port=8050)

