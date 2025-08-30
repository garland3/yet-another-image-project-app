#!/usr/bin/env bash

# Start local Postgres and MinIO if not already running, then launch backend and frontend dev servers.
# Set CONTAINER_ENGINE=docker or CONTAINER_ENGINE=podman (defaults to docker)

set -euo pipefail

CONTAINER_ENGINE="${CONTAINER_ENGINE:-docker}"
NETWORK_NAME="data_mgmt_net"
PG_CONTAINER="postgres_db"
MINIO_CONTAINER="minio_storage"
PG_VOLUME="postgres_data"
MINIO_VOLUME="minio_data"

# Load .env if present to map variables to containers (non-fatal if missing)
if [[ -f .env ]]; then
	# shellcheck disable=SC1091
	set -a; source .env; set +a
fi

# Defaults for local dev if not supplied via .env
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-postgres}"
POSTGRES_PORT_HOST="${POSTGRES_PORT:-5433}"

S3_ACCESS_KEY="${S3_ACCESS_KEY:-minioadmin}"
S3_SECRET_KEY="${S3_SECRET_KEY:-minioadminpassword}"
S3_BUCKET="${S3_BUCKET:-data-storage}"

say() { echo "[startup] $*"; }

have_cmd() { command -v "$1" >/dev/null 2>&1; }

ensure_network() {
	if ! "$CONTAINER_ENGINE" network ls --format '{{.Name}}' | grep -qx "$NETWORK_NAME"; then
		say "Creating network $NETWORK_NAME"
		"$CONTAINER_ENGINE" network create "$NETWORK_NAME" >/dev/null
	fi
}

ensure_volume() {
	local vol="$1"
	if ! "$CONTAINER_ENGINE" volume ls --format '{{.Name}}' | grep -qx "$vol"; then
		say "Creating volume $vol"
		"$CONTAINER_ENGINE" volume create "$vol" >/dev/null
	fi
}

container_running() {
	local name="$1"
	"$CONTAINER_ENGINE" ps --format '{{.Names}}' | grep -qx "$name"
}

container_exists() {
	local name="$1"
	"$CONTAINER_ENGINE" ps -a --format '{{.Names}}' | grep -qx "$name"
}

start_postgres() {
	ensure_network
	ensure_volume "$PG_VOLUME"

	if container_running "$PG_CONTAINER"; then
		say "Postgres already running ($PG_CONTAINER)"
	else
		if container_exists "$PG_CONTAINER"; then
			say "Starting existing Postgres container"
			"$CONTAINER_ENGINE" start "$PG_CONTAINER" >/dev/null
		else
			say "Launching Postgres ($PG_CONTAINER) on host port $POSTGRES_PORT_HOST"
			"$CONTAINER_ENGINE" run -d \
				--name "$PG_CONTAINER" \
				--network "$NETWORK_NAME" \
				-p "${POSTGRES_PORT_HOST}:5432" \
				-e POSTGRES_USER="$POSTGRES_USER" \
				-e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
				-e POSTGRES_DB="$POSTGRES_DB" \
				-v "${PG_VOLUME}:/var/lib/postgresql/data" \
				postgres:15 >/dev/null
		fi
	fi

	# Wait until Postgres reports ready
	say "Waiting for Postgres to become ready..."
	local tries=0
	until "$CONTAINER_ENGINE" exec "$PG_CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
		tries=$((tries+1))
		if (( tries > 60 )); then
			echo "Postgres did not become ready in time" >&2
			exit 1
		fi
		sleep 1
	done
	say "Postgres is ready."
}

start_minio() {
	ensure_network
	ensure_volume "$MINIO_VOLUME"

	if container_running "$MINIO_CONTAINER"; then
		say "MinIO already running ($MINIO_CONTAINER)"
	else
		if container_exists "$MINIO_CONTAINER"; then
			say "Starting existing MinIO container"
			"$CONTAINER_ENGINE" start "$MINIO_CONTAINER" >/dev/null
		else
			say "Launching MinIO ($MINIO_CONTAINER) on ports 9000/9090"
			"$CONTAINER_ENGINE" run -d \
				--name "$MINIO_CONTAINER" \
				--network "$NETWORK_NAME" \
				-p 9000:9000 -p 9090:9090 \
				-e MINIO_ROOT_USER="$S3_ACCESS_KEY" \
				-e MINIO_ROOT_PASSWORD="$S3_SECRET_KEY" \
				-v "${MINIO_VOLUME}:/data" \
				minio/minio:latest \
				server /data --console-address ":9090" >/dev/null
		fi
	fi

	# Wait for MinIO live endpoint
	if have_cmd curl; then
		say "Waiting for MinIO to become ready..."
		local tries=0
		until curl -sf "http://localhost:9000/minio/health/live" >/dev/null; do
			tries=$((tries+1))
			if (( tries > 120 )); then
				echo "MinIO did not become ready in time" >&2
				exit 1
			fi
			sleep 1
		done
		say "MinIO is ready."
	else
		say "curl not found; skipping MinIO readiness check"
	fi
}

start_backend() {
	# Ensure Python virtual environment is activated
	if [[ -z "${VIRTUAL_ENV:-}" ]]; then
		if [[ -f backend/.venv/bin/activate ]]; then
			say "Activating Python virtual environment"
			source backend/.venv/bin/activate
		else
			say "WARNING: Python virtual environment not found in backend/"
		fi
	fi
	
	say "Starting backend (uvicorn) on http://localhost:8000"
	cd backend
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
	UVICORN_PID=$!
	cd ..
}

start_frontend() {
	# Check if Node.js and npm are installed (should be done via install.sh)
	if ! command -v node >/dev/null 2>&1; then
		say "ERROR: Node.js is not installed. Please run install.sh first."
		exit 1
	fi
	
	if ! command -v npm >/dev/null 2>&1; then
		say "ERROR: npm is not installed. Please run install.sh first."
		exit 1
	fi
	
	say "Starting frontend (React) on http://localhost:3000"
	pushd frontend >/dev/null
	npm run start
	popd >/dev/null
}

cleanup() {
	say "Shutting down dev servers..."
	if [[ -n "${UVICORN_PID:-}" ]] && ps -p "$UVICORN_PID" >/dev/null 2>&1; then
		kill "$UVICORN_PID" || true
	fi
}

trap cleanup EXIT INT TERM

# Parse command line arguments
START_FRONTEND=false
START_BACKEND=false

while getopts "fb" opt; do
  case $opt in
    f)
      START_FRONTEND=true
      ;;
    b)
      START_BACKEND=true
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      echo "Usage: $0 [-f] [-b]" >&2
      exit 1
      ;;
  esac
done

# If no flags are provided, start both services by default
if [[ "$START_FRONTEND" == false && "$START_BACKEND" == false ]]; then
    START_FRONTEND=true
    START_BACKEND=true
fi

say "Using container engine: $CONTAINER_ENGINE"

# Always start containers (postgres and minio)
start_postgres
start_minio

# Start backend if -b flag is provided or no flags are provided
if [[ "$START_BACKEND" == true ]]; then
    start_backend
fi

# Start frontend if -f flag is provided or no flags are provided
if [[ "$START_FRONTEND" == true ]]; then
    start_frontend
fi

# Script exits after frontend stops (if started); trap will cleanup backend.
