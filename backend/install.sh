#!/usr/bin/env bash

# Backend installation script
# Installs uv and Python dependencies for the FastAPI backend

set -euo pipefail

say() { echo "[backend-install] $*"; }

install_backend_dependencies() {
    # Check if we're in the backend directory
    if [[ ! -f "main.py" ]]; then
        say "ERROR: This script must be run from the backend directory"
        exit 1
    fi
    
    # Install uv if not already installed
    if ! command -v uv >/dev/null 2>&1; then
        say "Installing uv"
        python3 -m pip install uv
    else
        say "uv already installed: $(uv --version)"
    fi
    
    # Create and activate virtual environment
    if [[ ! -d .venv ]]; then
        say "Creating Python virtual environment with uv"
        uv venv .venv
    else
        say "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    say "Activating Python virtual environment"
    source .venv/bin/activate
    
    # Copy .env file from parent directory if it exists and backend doesn't have one
    if [[ -f ../.env && ! -f .env ]]; then
        say "Copying .env file from parent directory"
        cp ../.env .
    fi
    
    # Install Python dependencies
    if [[ -f requirements.txt ]]; then
        say "Installing Python dependencies"
        uv pip install -r requirements.txt
        say "Backend dependencies installed successfully"
    else
        say "requirements.txt not found in backend directory; skipping pip install"
    fi
}

# Run the installation
install_backend_dependencies