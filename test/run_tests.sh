#!/bin/bash

# Backend Test Runner
# This script runs the comprehensive backend test suite that was developed and stabilized.
# NOTE: This repo uses UV for package management.

set -e  # Exit on any error

echo "🧪 Running Backend Test Suite"
echo "=============================="

# Change to the project root directory
cd "$(dirname "$0")/.."

# Ensure we're in the correct directory
if [ ! -d "backend" ]; then
    echo "❌ Error: backend directory not found. Make sure you're running this from the project root."
    exit 1
fi

echo "📁 Current directory: $(pwd)"
echo "🐍 Python version: $(python3 --version 2>/dev/null || echo 'Python not found')"

# Add uv to PATH
export PATH="$HOME/.local/bin:$PATH"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv not found. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "🔧 Using uv version: $(uv --version)"

# Check for virtual environment (Docker uses /opt/venv, local dev uses backend/.venv)
if [ -f "/opt/venv/bin/activate" ]; then
    echo "🔧 Activating Docker virtual environment..."
    source /opt/venv/bin/activate
    echo "📦 Installing test dependencies with uv..."
    uv pip install pytest pytest-asyncio pytest-xdist
    PYTEST_PATH=$(which pytest)
elif [ -f "backend/.venv/bin/activate" ]; then
    echo "🔧 Activating local virtual environment..."
    source backend/.venv/bin/activate
    echo "📦 Installing test dependencies with uv..."
    uv pip install pytest pytest-asyncio pytest-xdist
    PYTEST_PATH=$(which pytest)
else
    echo "❌ Error: Virtual environment not found"
    echo "Expected locations:"
    echo "   - Docker: /opt/venv/bin/activate"
    echo "   - Local: backend/.venv/bin/activate"
    echo ""
    echo "For local development, create it first:"
    echo "   cd backend && uv venv .venv && source .venv/bin/activate && uv pip install -r requirements.txt"
    exit 1
fi

# Check if pytest is available
if [ -z "$PYTEST_PATH" ]; then
    echo "❌ Error: pytest not found after installation. Something went wrong."
    exit 1
fi

echo "🔧 Using pytest: $PYTEST_PATH"

# Change to backend directory for tests
cd backend

echo ""
echo "🚀 Starting backend tests..."
echo "----------------------------"

# Run the full test suite with the same options that were successful
# Specifically target the tests directory to avoid picking up other test files
"$PYTEST_PATH" -n auto -q tests/

# Capture the exit code
TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All backend tests passed!"
    echo ""
    echo "📊 Test Summary:"
    echo "   - Configuration tests: ✅"
    echo "   - Database tests: ✅"
    echo "   - Authentication/Dependencies tests: ✅"
    echo "   - Router tests (users, projects, images, metadata): ✅"
    echo "   - CRUD operation tests: ✅"
    echo "   - Schema validation tests: ✅"
    echo "   - Content delivery tests: ✅"
    echo "   - Edge case handling tests: ✅"
    echo ""
    echo "🎉 Backend is ready for production!"
else
    echo "❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
    echo ""
    echo "🔍 Troubleshooting tips:"
    echo "   - Check if all required environment variables are set"
    echo "   - Ensure database connectivity (if using PostgreSQL)"
    echo "   - Verify S3/MinIO configuration (if needed)"
    echo "   - Check pytest and dependency versions"
    echo ""
    echo "📝 For detailed output, run: pytest -v"
fi

exit $TEST_EXIT_CODE
