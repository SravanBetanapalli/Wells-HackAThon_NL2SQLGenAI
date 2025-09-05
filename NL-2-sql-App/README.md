# AI SQL Bot

A Natural Language to SQL Query Processing application with AI Agents, featuring PII safety guardrails and Schema-Infused Prompting.

## Quick Start (Recommended)

The easiest way to start the app is using the provided scripts:

```bash
# 1. Navigate to the NL-2-sql-App directory
cd NL-2-sql-App

# 2. Set up the UV environment (first time only)
./setup_uv.sh

# 3. Set up environment variables
./setup_env.sh

# 4. Start the application
./run_app.sh
```

## Manual Setup (Alternative)

If you prefer to run commands manually:

```bash
# 1. Navigate to the NL-2-sql-App directory
cd NL-2-sql-App

# 2. Create and activate UV virtual environment
uv venv
source .venv/bin/activate

# 3. Install dependencies
uv pip install -e .

# 4. Set up environment variables (creates .env file)
./setup_env.sh

# 5. Initialize the database
sqlite3 banking.db < db/schema.sql
sqlite3 banking.db < db/sample_data.sql

# 6. Start the Streamlit app
uv run streamlit run app.py
```

## What Each Step Does

- **`setup_uv.sh`**: Creates a UV virtual environment and installs all dependencies
- **`setup_env.sh`**: Creates a `.env` file with OpenAI API keys and configuration
- **`run_app.sh`**: Checks for virtual environment, initializes database if needed, and starts the Streamlit app
- **Database initialization**: Sets up SQLite database with banking schema and sample data

## Prerequisites

- Python 3.12+ 
- UV package manager installed
- OpenAI API key (already configured in setup_env.sh)

## Access

The app will be accessible at `http://localhost:8501` once started.

## Features

- **PII Safety Guardrails**: Detects and protects personally identifiable information
- **Schema-Infused Prompting**: Uses database schema and metadata for enhanced query generation
- **AI Agent Pipeline**: Multi-agent system for planning, retrieval, SQL generation, validation, execution, and summarization