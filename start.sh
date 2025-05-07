#!/bin/bash

# Exit on error
set -e

echo "Setting up Python virtual environment..."

# Check if Python 3.11 is installed
if ! command -v python3.11 &> /dev/null; then
    echo "Python 3.11 is not installed. Installing..."
    sudo apt-get update
    sudo apt-get install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt-get update
    sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating new virtual environment..."
    python3.11 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv package installer..."
    pip install uv
fi

# Install dependencies using uv
echo "Installing dependencies using uv..."
uv pip install -r requirements.txt

# Check if frontend build exists
if [ ! -d "app/ui" ]; then
    echo "Building frontend..."
    cd frontend
    npm install
    npm run build
    cd ..
    
    # Create ui directory and copy build files
    mkdir -p app/ui/static
    cp -r frontend/build/* app/ui/
fi

# Run the application
echo "Starting the application..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Deactivate virtual environment on exit
trap "deactivate" EXIT
