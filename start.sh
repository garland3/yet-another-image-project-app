#!/bin/bash

# Start the backend server in the background
echo "Starting backend server..."
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Wait a moment for the backend to initialize
sleep 5

# Start the frontend development server
echo "Starting frontend server..."
cd frontend && npm start

# When the frontend server is stopped (Ctrl+C), also stop the backend
kill $BACKEND_PID
