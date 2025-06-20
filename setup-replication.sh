#!/bin/bash
set -e

echo "=== Setting up Streaming Replication for Citus Workers ==="

# Function to check if a service is ready
check_service() {
    local service_name=$1
    local max_attempts=60
    local attempt=1
    
    echo "Checking if $service_name is ready..."
    while [ $attempt -le $max_attempts ]; do
        if docker compose exec -T "$service_name" pg_isready -U postgres > /dev/null 2>&1; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        echo "⏳ Waiting for $service_name... ($attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
reset_standby worker_citus1_standby
reset_standby worker_citus2_standby

# Step 3: Start standby containers to perform base backup
docker compose up -d worker_citus1_standby worker_citus2_standby
sleep 5

# Step 4: Restart standby nodes to ensure they start as standbys
docker compose restart worker_citus1_standby worker_citus2_standby

echo "✅ Replication setup complete. Standbys are following their primaries."