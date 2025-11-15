#!/usr/bin/env bash

# Backend run script
# Tries to load the virtual environment (.venv) from current dir or back one dir before proceeding
# Starts PostgreSQL and MinIO containers, then starts the FastAPI backend with uvicorn

# Check for virtual environment in current directory
if [ -d ".venv" ]; then
    echo "Found .venv in current directory, activating..."
    source .venv/bin/activate
# Check for virtual environment in parent directory
elif [ -d "../.venv" ]; then
    echo "Found .venv in parent directory, activating..."
    source ../.venv/bin/activate
else
    echo "No .venv found in current or parent directory, proceeding without virtual environment"
fi

echo "Starting uvicorn main:app --host 0.0.0.0 --port 8000"
uvicorn main:app --host 0.0.0.0 --port 8000
