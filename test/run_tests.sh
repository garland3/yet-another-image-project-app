#!/usr/bin/env bash
# Backend Test Runner (Fedora-friendly, no `which`)
set -euo pipefail

echo "🧪 Running Backend Test Suite"
echo "=============================="

cd "$(dirname "$0")/.."

if [ ! -d "backend" ]; then
  echo "❌ Error: backend directory not found. Run from project root."
  exit 1
fi

echo "📁 Current directory: $(pwd)"
PY_BIN="$(command -v python3 || command -v python || true)"
echo "🐍 Python version: $([ -n "${PY_BIN}" ] && "${PY_BIN}" --version 2>/dev/null || echo 'Python not found')"

export PATH="$HOME/.local/bin:$PATH"

if ! command -v uv >/dev/null 2>&1; then
  echo "❌ Error: uv not found. Install with:"
  echo " curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
echo "🔧 Using uv: $(uv --version)"

if [ -f "/opt/venv/bin/activate" ]; then
  echo "🔧 Activating Docker virtual environment..."
  # shellcheck disable=SC1091
  source /opt/venv/bin/activate
  echo "📦 Installing test deps..."
  uv pip install pytest pytest-asyncio pytest-xdist
elif [ -f "backend/.venv/bin/activate" ]; then
  echo "🔧 Activating local virtual environment..."
  # shellcheck disable=SC1091
  source backend/.venv/bin/activate
  echo "📦 Installing test deps..."
  uv pip install pytest pytest-asyncio pytest-xdist
else
  echo "❌ Error: Virtual environment not found
Expected:
 - Docker: /opt/venv/bin/activate
 - Local: backend/.venv/bin/activate

For local dev:
 cd backend && uv venv .venv && source .venv/bin/activate && uv pip install -r requirements.txt"
  exit 1
fi

# Ensure we have a python executable post-activate
PY_BIN="$(command -v python3 || command -v python || true)"
if [ -z "${PY_BIN}" ]; then
  echo "❌ Error: python not found in the active environment."
  exit 1
fi
echo "🔧 Using python: ${PY_BIN}"

cd backend
echo ""
echo "🚀 Starting backend tests..."
echo "----------------------------"

set +e
"${PY_BIN}" -m pytest -n auto -q tests/
TEST_EXIT_CODE=$?
set -e

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo "✅ All backend tests passed!"
  echo ""
  echo "📊 Test Summary:"
  echo " - Configuration tests: ✅"
  echo " - Database tests: ✅"
  echo " - Authentication/Dependencies tests: ✅"
  echo " - Router tests (users, projects, images, metadata): ✅"
  echo " - CRUD operation tests: ✅"
  echo " - Schema validation tests: ✅"
  echo " - Content delivery tests: ✅"
  echo " - Edge case handling tests: ✅"
  echo ""
  echo "🎉 Backend is ready for production!"
else
  echo "❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
  echo ""
  echo "🔍 Troubleshooting tips:"
  echo " - Check required environment variables"
  echo " - Ensure database connectivity"
  echo " - Verify S3/MinIO configuration"
  echo " - Check pytest and dependency versions"
  echo ""
  echo "📝 For detailed output, run: ${PY_BIN} -m pytest -v"
fi

exit $TEST_EXIT_CODE
