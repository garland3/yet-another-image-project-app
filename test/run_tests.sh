#!/bin/bash

# Backend Test Runner
# This script runs the comprehensive backend test suite that was developed and stabilized.

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

# Check for virtual environment in backend directory and activate it if it exists
if [ -f "backend/.venv/bin/activate" ]; then
    echo "🔧 Activating virtual environment..."
    source backend/.venv/bin/activate
    echo "📦 Installing pytest-xdist..."
    pip install pytest-xdist
    PYTEST_PATH=$(which pytest)
else
    # Check if pytest is available in system PATH
    PYTEST_PATH=$(command -v pytest 2>/dev/null || echo "")
fi

# Check if pytest is available
if [ -z "$PYTEST_PATH" ]; then
    echo "❌ Error: pytest not found. Please install it first:"
    if [ -f "backend/.venv/bin/activate" ]; then
        echo "   cd backend && source .venv/bin/activate && pip install pytest pytest-asyncio"
    else
        echo "   pip install pytest pytest-asyncio"
    fi
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
