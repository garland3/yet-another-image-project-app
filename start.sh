#!/usr/bin/env bash

# Start local Postgres and MinIO if not already running, then launch backend and frontend dev servers.
# This script calls install.sh to install dependencies and startup.sh to start services.
# Usage: ./start.sh [-f] [-b]
#   -f: Start frontend
#   -b: Start backend

set -euo pipefail

say() { echo "[start] $*"; }

# Parse command line arguments to pass through to startup.sh
STARTUP_ARGS=""
while getopts "fb" opt; do
  case $opt in
    f|b)
      STARTUP_ARGS="$STARTUP_ARGS -$opt"
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      echo "Usage: $0 [-f] [-b]" >&2
      exit 1
      ;;
  esac
done

# Check if install.sh exists and run it
if [[ -f ./install.sh ]]; then
    say "Running install.sh to ensure dependencies are installed"
    bash ./install.sh
else
    say "WARNING: install.sh not found, skipping dependency installation"
    say "You can also run backend/install.sh and frontend/install.sh separately"
fi

# Check if startup.sh exists and run it with the provided flags
if [[ -f ./startup.sh ]]; then
    say "Running startup.sh to start services"
    if [[ -n "$STARTUP_ARGS" ]]; then
        bash ./startup.sh $STARTUP_ARGS
    else
        bash ./startup.sh
    fi
else
    say "ERROR: startup.sh not found"
    exit 1
fi
