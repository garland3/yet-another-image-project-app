# Use Ubuntu as the base image
# use multi-stage build to enable the dev environment to only use the base image
FROM ubuntu:22.04 AS base

# Set noninteractive installation
ENV DEBIAN_FRONTEND=noninteractive

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
    software-properties-common \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Add deadsnakes PPA for Python 3.11
RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create symbolic links for python and pip
RUN ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Create a Python virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install uv package installer
RUN pip install --no-cache-dir uv

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

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

FROM base AS builder

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    uv pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY ./app /app/app
# COPY .env /app/.env

# Copy frontend files selectively (excluding node_modules)
WORKDIR /app
# Copy package.json and package-lock.json
COPY ./frontend/package.json ./frontend/package-lock.json ./frontend/
# Copy public directory
COPY ./frontend/public ./frontend/public
# Copy src directory
COPY ./frontend/src ./frontend/src
# Copy config files
COPY ./frontend/.gitignore ./frontend/config-overrides.js ./frontend/README.md ./frontend/

# Install frontend dependencies and build
WORKDIR /app/frontend
RUN npm install
RUN npm run build
RUN ls -la build || echo "Build directory not found"

# Return to app directory
WORKDIR /app

# Final stage
FROM base AS final

# Copy Python dependencies from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy backend code
COPY --from=builder /app/app /app/app
# Copy frontend build files
COPY --from=builder /app/frontend/build /app/ui2


# RUN cp -R /app/frontend/build/* /app/ui2
# SEt the env var FRONTEND_BUILD_PATH
ENV FRONTEND_BUILD_PATH=/app/ui2


WORKDIR /app
EXPOSE 8000

# Use uv to run uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
# For production, use:
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
