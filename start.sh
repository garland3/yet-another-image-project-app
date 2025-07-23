#!/bin/bash

# Start uvicorn server in the background
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# Navigate to frontend directory and start npm
cd ../frontend && npm run start

# The script will wait for the npm process to finish
# To kill both processes properly, you can add a trap