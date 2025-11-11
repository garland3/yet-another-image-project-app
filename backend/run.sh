#!/usr/bin/env bash

# Backend run script
# Starts PostgreSQL and MinIO containers, then starts the FastAPI backend with uvicorn
echo " uvicorn main:app --host 0.0.0.0 --port 8000 "
uvicorn main:app --host 0.0.0.0 --port 8000
