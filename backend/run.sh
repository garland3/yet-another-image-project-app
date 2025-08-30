#!/usr/bin/env bash

# Backend run script
# Starts the FastAPI backend with uvicorn

set -euo pipefail

say() { echo "[backend-run] $*"; }

start_backend() {
    # Check if we're in the backend directory
    if [[ ! -f "main.py" ]]; then
        say "ERROR: This script must be run from the backend directory"
        exit 1
    fi
    
    # Ensure Python virtual environment is activated
    if [[ -z "${VIRTUAL_ENV:-}" ]]; then
        if [[ -f .venv/bin/activate ]]; then
            say "Activating Python virtual environment"
            source .venv/bin/activate
        else
            say "ERROR: Python virtual environment not found. Please run install.sh first."
            exit 1
        fi
    else
        say "Virtual environment already activated: $VIRTUAL_ENV"
    fi
    
    # Check if uvicorn is available
    if ! command -v uvicorn >/dev/null 2>&1; then
        say "ERROR: uvicorn is not installed. Please run install.sh first."
        exit 1
    fi
    
    say "Starting FastAPI backend on http://localhost:8000"
    say "Press Ctrl+C to stop the server"
    
    # Start the FastAPI application
    # Note: Using 'main:app' instead of 'app.main:app' since we're now in the backend directory
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
}

# Run the backend
start_backend