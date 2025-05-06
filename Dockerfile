# Use an official Python runtime as a parent image
# use multi-stage build to enable the dev environment to only use the base image
FROM python:3.11-slim AS base

# Install system dependencies and tools for development
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    curl \
    vim \
    wget \
    ca-certificates \
    gnupg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Node.js (includes npm) using NodeSource repository
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    NODE_MAJOR=20 && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && apt-get install nodejs -y --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install debugging tools
RUN pip install --no-cache-dir debugpy

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

FROM base AS builder

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY ./app /app/app
# COPY .env /app/.env

# Add frontend setup steps
WORKDIR /app/frontend
COPY ./frontend/package.json ./frontend/package-lock.json ./
RUN npm install
RUN npm run build

# Expose backend port
WORKDIR /app
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
# For production, use:
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
