# Databricks Job Runner with Parameters

A simple Dash application that submits Databricks jobs with custom parameters and retrieves results.

## Features

- 🚀 Submit Databricks jobs with custom parameters
- 📊 Retrieve and display job results
- 🔧 Easy configuration via `app.yaml`
- 💼 Uses Databricks SDK with pre-configured profile
- 🎨 Clean, modern UI with Bootstrap

## Configuration

### Job ID Configuration

The job ID is configured in `app.yaml` as an environment variable. This makes it easy to change without modifying code:

```yaml
env:
  - name: 'DATABRICKS_JOB_ID'
    value: '921773893211960'  # Change this to your job ID
```

**Why use app.yaml for job_id?**
- ✅ Environment-specific configuration (dev/staging/prod)
- ✅ Can use secrets: `valueFrom: 'secret/scope/key'`
- ✅ No code changes needed between environments
- ✅ Follows Databricks Apps best practices

### Job Parameters

Job parameters are entered through the UI, NOT in `app.yaml`:

**Why NOT use app.yaml for job parameters?**
- ❌ Job parameters are meant to be dynamic user inputs
- ❌ Hardcoding them defeats the purpose of parameterization
- ❌ Users need flexibility to change parameters per run
- ✅ UI input allows real-time parameter changes

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Local Development

```bash
python app.py
```

Then open your browser to `http://localhost:8050`

### Deploy as Databricks App

1. Ensure you have a Databricks workspace with Apps enabled
2. Update `DATABRICKS_JOB_ID` in `app.yaml` with your job ID
3. Deploy the app using Databricks CLI or UI
4. The `app.yaml` file will automatically configure the environment

## How It Works

1. **Submit Job**: Enter your job parameters in JSON format and click "Submit Job"
2. **Get Results**: Once submitted, click "Get Results" to fetch the job output
3. The app displays:
   - Run ID
   - Job status
   - Output (notebook, SQL, DBT, or logs)

## Example Parameters

```json
{
  "param1": "value1",
  "param2": "value2",
  "date": "2024-01-01",
  "environment": "production"
}
```

## Architecture

```
┌─────────────┐
│  app.yaml   │ ← Job ID configuration
└─────────────┘
      ↓
┌─────────────┐
│   app.py    │ ← Dash application
└─────────────┘
      ↓
┌─────────────┐
│ Databricks  │ ← Job execution
│    Jobs     │
└─────────────┘
```

## Environment Variables

- `DATABRICKS_JOB_ID` (required): The Databricks job ID to run
- Standard Databricks SDK authentication (via profile or environment)

## Notes

- The app assumes you have a Databricks profile configured (e.g., in `~/.databrickscfg`)
- Job parameters must be valid JSON
- Results may take time to appear if the job is still running

