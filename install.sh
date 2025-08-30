#!/usr/bin/env bash

# Install Node.js version 22 and remove other versions
# Also install uv and Python dependencies
# Set CONTAINER_ENGINE=docker or CONTAINER_ENGINE=podman (defaults to docker)

set -euo pipefail

CONTAINER_ENGINE="${CONTAINER_ENGINE:-docker}"

say() { echo "[install] $*"; }

install_dependencies() {
    # Remove other Node.js versions
    sudo apt remove -y nodejs npm
    
    # Install Node.js version 22
    say "Installing Node.js version 22"
    
    # Add NodeSource repository for Node.js 22
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    
    # Install Node.js 22
    sudo apt install -y nodejs
    
    # Verify Node.js installation
    if command -v node >/dev/null 2>&1; then
        say "Node.js version installed: $(node --version)"
    else
        say "ERROR: Node.js installation failed"
        exit 1
    fi
    
    if command -v npm >/dev/null 2>&1; then
        say "npm version installed: $(npm --version)"
    else
        say "ERROR: npm installation failed"
        exit 1
    fi
    
    # Install uv
    if ! command -v uv >/dev/null 2>&1; then
        say "Installing uv"
        python3 -m pip install uv
    else
        say "uv already installed: $(uv --version)"
    fi
    
    # Create and activate virtual environment in backend directory
    if [[ ! -d backend/.venv ]]; then
        say "Creating Python virtual environment with uv in backend/"
        cd backend
        uv venv .venv
        cd ..
    fi
    
    # Activate virtual environment
    say "Activating Python virtual environment"
    source backend/.venv/bin/activate
    
    # Install Python dependencies
    if [[ -f requirements.txt ]]; then
        say "Installing Python dependencies"
        uv pip install -r requirements.txt
    else
        say "requirements.txt not found; skipping pip install"
    fi
}

# Run the installation
install_dependencies
