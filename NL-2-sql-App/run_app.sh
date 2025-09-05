#!/bin/bash

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run ./setup_uv.sh first"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Initialize database if needed
if [ ! -f "banking.db" ]; then
    echo "🔄 Initializing database..."
    sqlite3 banking.db < db/schema.sql
    sqlite3 banking.db < db/sample_data.sql
fi

# Run the application
echo "🚀 Starting Streamlit app..."
uv run streamlit run app.py
