#!/bin/bash

echo "🚀 Setting up development environment..."

# Update package list
echo "📦 Updating package list..."
apt-get update

# Install PostgreSQL
echo "🐘 Installing PostgreSQL..."
DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql postgresql-contrib

# Start PostgreSQL service
echo "🔧 Starting PostgreSQL service..."
service postgresql start

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 3

# Configure PostgreSQL
echo "⚙️  Configuring PostgreSQL..."
# Try to configure PostgreSQL, but don't fail if we can't
echo "Attempting to set PostgreSQL password..."
if su - postgres -c "psql -c \"ALTER USER postgres PASSWORD 'postgres';\"" >/dev/null 2>&1; then
    echo "✅ PostgreSQL password set successfully"
else
    echo "⚠️  Could not set PostgreSQL password (may require manual setup)"
fi

echo "Attempting to create database..."
if su - postgres -c "createdb postgres" >/dev/null 2>&1; then
    echo "✅ Database created successfully"
else
    echo "⚠️  Could not create database (may already exist or require manual setup)"
fi

# Configure PostgreSQL to start automatically
echo "🔄 Setting up auto-start..."
echo "service postgresql start" >> ~/.bashrc

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install --no-cache-dir --upgrade -r requirements.txt
else
    echo "⚠️  No requirements.txt found, skipping Python dependencies"
fi

echo "✅ Setup complete!"
echo "📊 Database URL: postgresql://postgres:postgres@localhost:5432/postgres"
echo "🔗 You can now connect to PostgreSQL with user 'postgres' and password 'postgres'"