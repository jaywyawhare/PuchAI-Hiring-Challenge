#!/bin/bash

echo "🐳 Setting up PostgreSQL with pgvector..."

# Remove existing container if it exists
sudo docker stop warpspeed-postgres 2>/dev/null || true
sudo docker rm warpspeed-postgres 2>/dev/null || true

# Run PostgreSQL with pgvector extension
sudo docker run -d \
  --name warpspeed-postgres \
  -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=whatsapp_bot \
  pgvector/pgvector:pg16

echo "⏳ Waiting for PostgreSQL to start..."
sleep 10

# Check if container is running
if sudo docker ps | grep -q warpspeed-postgres; then
    echo "✅ PostgreSQL container is running"
    sudo docker ps | grep warpspeed-postgres
else
    echo "❌ Failed to start PostgreSQL container"
    exit 1
fi

echo "🎉 Docker setup completed!"
