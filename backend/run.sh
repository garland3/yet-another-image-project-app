#!/usr/bin/env bash

# Backend run script
# Starts PostgreSQL and MinIO containers, then starts the FastAPI backend with uvicorn
echo " uvicorn main:app --host 0.0.0.0 --port 8000 "

set -euo pipefail

CONTAINER_ENGINE="${CONTAINER_ENGINE:-docker}"
NETWORK_NAME="data_mgmt_net"
PG_CONTAINER="postgres_db"
MINIO_CONTAINER="minio_storage"
PG_VOLUME="postgres_data"
MINIO_VOLUME="minio_data"

# Load .env if present to map variables to containers (non-fatal if missing)
if [[ -f ../.env ]]; then
	# shellcheck disable=SC1091
	set -a; source ../.env; set +a
elif [[ -f .env ]]; then
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

say() { echo "[backend-run] $*"; }

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
    # Check if we're in the backend directory
    if [[ ! -f "main.py" ]]; then
        say "ERROR: This script must be run from the backend directory"
        exit 1
    fi
    
    say "Using container engine: $CONTAINER_ENGINE"
    
    # Start containers first
    start_postgres
    start_minio
    
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
    uvicorn main:app --host 0.0.0.0 --port 8000
}

# Stop any existing uvicorn instance if running (ignore if none)
pkill -f 'uvicorn main:app' || echo "[backend-run] No existing uvicorn process to stop"
sleep 3
# Run the backend
start_backend